"""
MCP server process management.

Handles spawning, lifecycle management, and communication with MCP servers.
Supports both interactive and non-interactive modes.
"""

import os
import json
import asyncio
import subprocess
from typing import Optional, Dict, Any, Callable, List
from pathlib import Path

from .buffer import JsonRpcBuffer
from .config import MCPServerConfig
from .logging_config import get_logger, TRACE
import logging


class MCPServer:
    """Manages a single MCP server process."""
    
    def __init__(self, config: MCPServerConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or get_logger(__name__)
        self.process: Optional[subprocess.Popen] = None
        self.buffer = JsonRpcBuffer()
        self._running = False
        self._message_handlers: List[Callable[[dict], None]] = []
        self._next_id = 1
        self._pending_requests: Dict[Union[str, int], asyncio.Future] = {}
        self._last_error_time: Optional[float] = None
        self._offline_since: Optional[float] = None
        
    async def start(self):
        """Start the MCP server process."""
        if self.process:
            return
        
        # Check if server is marked as offline
        import time
        if self._offline_since:
            offline_duration = time.time() - self._offline_since
            if offline_duration < 1800:  # 30 minutes
                self.logger.warning(f"Server has been offline for {offline_duration:.0f}s, skipping start")
                raise RuntimeError(f"Server marked as offline since {offline_duration:.0f}s ago")
        
        # Prepare environment
        env = os.environ.copy()
        env.update({
            "NODE_NO_READLINE": "1",
            "PYTHONUNBUFFERED": "1",
            **self.config.env
        })
        
        # Build command
        cmd = self.config.command + self.config.args
        
        self.logger.info(f"Starting MCP server: {' '.join(cmd)}")
        
        try:
            # Start process
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=0  # Unbuffered
            )
            
            self._running = True
            self._offline_since = None  # Clear offline state
            
            # Start reading outputs
            asyncio.create_task(self._read_stdout())
            asyncio.create_task(self._read_stderr())
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            self._mark_offline()
            raise
    
    async def stop(self):
        """Stop the MCP server process."""
        self._running = False
        
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self.process.wait),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                self.process.kill()
            
            self.process = None
    
    def _mark_offline(self):
        """Mark server as offline."""
        import time
        self._offline_since = time.time()
        self.logger.warning(f"Server marked as offline")
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request and wait for response.
        
        Args:
            method: JSON-RPC method name
            params: Optional parameters
            
        Returns:
            Response result or raises exception on error
        """
        if not self.process:
            raise RuntimeError("MCP server not started")
        
        request_id = self._next_id
        self._next_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        # Send request
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str)
        self.process.stdin.flush()
        
        self.logger.log(TRACE, f">>> {request_str.strip()}")
        
        # Wait for response with appropriate timeout
        timeout = 3.0 if method == "initialize" or method == "tools/list" else 30.0
        
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            del self._pending_requests[request_id]
            self.logger.error(f"Timeout waiting for response to {method} (timeout={timeout}s)")
            self._mark_offline()
            raise TimeoutError(f"No response for request {request_id}")
    
    def send_raw(self, message: str):
        """Send raw message to MCP server (for pass-through)."""
        if not self.process:
            raise RuntimeError("MCP server not started")
        
        if not message.endswith('\n'):
            message += '\n'
        
        self.logger.log(TRACE, f">>> {message.strip()}")
        
        self.process.stdin.write(message)
        self.process.stdin.flush()
    
    def add_message_handler(self, handler: Callable[[dict], None]):
        """Add a handler for incoming messages."""
        self._message_handlers.append(handler)
    
    async def _read_stdout(self):
        """Read and process stdout from MCP server."""
        while self._running and self.process:
            try:
                line = await asyncio.to_thread(self.process.stdout.readline)
                if not line:
                    break
                
                messages = self.buffer.append(line)
                for msg in messages:
                    await self._handle_message(msg)
                    
            except Exception as e:
                self.logger.error(f"Error reading stdout: {e}")
                self._mark_offline()
                break
    
    async def _read_stderr(self):
        """Read and log stderr from MCP server."""
        while self._running and self.process:
            try:
                line = await asyncio.to_thread(self.process.stderr.readline)
                if not line:
                    break
                
                if line.strip():
                    self.logger.warning(f"stderr: {line.strip()}")
                    
            except Exception:
                break
    
    async def _handle_message(self, message: dict):
        """Handle an incoming JSON-RPC message."""
        self.logger.log(TRACE, f"<<< {json.dumps(message)}")
        
        # Check if it's a response to a pending request
        msg_id = message.get("id")
        if msg_id in self._pending_requests:
            future = self._pending_requests.pop(msg_id)
            
            if "error" in message:
                future.set_exception(Exception(message["error"].get("message", "Unknown error")))
            else:
                future.set_result(message.get("result"))
        
        # Call registered handlers
        for handler in self._message_handlers:
            try:
                handler(message)
            except Exception as e:
                self.logger.error(f"Handler error: {e}")