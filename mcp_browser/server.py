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
from .utils import debug_print, debug_json


class MCPServer:
    """Manages a single MCP server process."""
    
    def __init__(self, config: MCPServerConfig, debug: bool = False):
        self.config = config
        self.debug = debug
        self.process: Optional[subprocess.Popen] = None
        self.buffer = JsonRpcBuffer()
        self._running = False
        self._message_handlers: List[Callable[[dict], None]] = []
        self._next_id = 1
        self._pending_requests: Dict[Union[str, int], asyncio.Future] = {}
        
    async def start(self):
        """Start the MCP server process."""
        if self.process:
            return
        
        # Prepare environment
        env = os.environ.copy()
        env.update({
            "NODE_NO_READLINE": "1",
            "PYTHONUNBUFFERED": "1",
            **self.config.env
        })
        
        # Build command
        cmd = self.config.command + self.config.args
        
        if self.debug:
            debug_print(f"Starting MCP server: {' '.join(cmd)}")
        
        # Start process
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE if self.debug else subprocess.DEVNULL,
            env=env,
            text=True,
            bufsize=0  # Unbuffered
        )
        
        self._running = True
        
        # Start reading outputs
        asyncio.create_task(self._read_stdout())
        if self.debug:
            asyncio.create_task(self._read_stderr())
    
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
        
        if self.debug:
            debug_print(f"Sent: {request_str.strip()}")
        
        # Wait for response
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            del self._pending_requests[request_id]
            raise TimeoutError(f"No response for request {request_id}")
    
    def send_raw(self, message: str):
        """Send raw message to MCP server (for pass-through)."""
        if not self.process:
            raise RuntimeError("MCP server not started")
        
        if not message.endswith('\n'):
            message += '\n'
        
        if self.debug:
            debug_print(f"MCP Server sending: {message.strip()}")
        
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
                if self.debug:
                    debug_print(f"Error reading stdout: {e}")
                break
    
    async def _read_stderr(self):
        """Read and log stderr from MCP server."""
        while self._running and self.process:
            try:
                line = await asyncio.to_thread(self.process.stderr.readline)
                if not line:
                    break
                
                debug_print(f"MCP stderr: {line.strip()}")
                    
            except Exception:
                break
    
    async def _handle_message(self, message: dict):
        """Handle an incoming JSON-RPC message."""
        if self.debug:
            debug_json("Received", message)
        
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
                if self.debug:
                    debug_print(f"Handler error: {e}")