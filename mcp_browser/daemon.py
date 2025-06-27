"""
MCP Browser daemon implementation using Unix domain sockets.

Provides a persistent MCP Browser instance that multiple clients can connect to,
allowing shared state and better performance.
"""

import os
import json
import asyncio
import socket
from pathlib import Path
from typing import Optional, Dict, Any
import signal
import sys

try:
    import psutil
except ImportError:
    # Fallback if psutil is not available
    class psutil:
        @staticmethod
        def pid_exists(pid):
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False

from .proxy import MCPBrowser
from .logging_config import get_logger


class MCPBrowserDaemon:
    """Daemon mode for MCP Browser using Unix domain sockets."""
    
    def __init__(self, browser: MCPBrowser, socket_path: Path):
        self.browser = browser
        self.socket_path = socket_path
        self.server: Optional[asyncio.Server] = None
        self._running = False
        self._clients: set = set()
        self.logger = get_logger(__name__)
        
    async def start(self):
        """Start the daemon server."""
        # Ensure socket directory exists
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove existing socket if present
        if self.socket_path.exists():
            self.socket_path.unlink()
        
        # Create Unix domain socket server
        self.server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.socket_path)
        )
        
        # Set permissions
        os.chmod(self.socket_path, 0o600)
        
        # Write PID file
        pid_file = self.socket_path.with_suffix('.pid')
        pid_file.write_text(str(os.getpid()))
        
        self._running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.logger.info(f"MCP Browser daemon started on {self.socket_path}")
        self.logger.info(f"PID: {os.getpid()}")
        
        # Initialize browser
        await self.browser.initialize()
        
        # Run server
        async with self.server:
            await self.server.serve_forever()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self._running = False
        if self.server:
            self.server.close()
        sys.exit(0)
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a client connection."""
        client_addr = writer.get_extra_info('peername')
        self.logger.debug(f"Client connected: {client_addr}")
        self._clients.add(writer)
        
        try:
            buffer = ""
            while self._running:
                # Read data from client
                data = await reader.read(4096)
                if not data:
                    break
                
                buffer += data.decode('utf-8')
                
                # Process complete JSON objects
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        await self._process_request(line, writer)
                        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Client error: {e}")
        finally:
            self._clients.discard(writer)
            writer.close()
            await writer.wait_closed()
            self.logger.debug(f"Client disconnected: {client_addr}")
    
    async def _process_request(self, line: str, writer: asyncio.StreamWriter):
        """Process a JSON-RPC request from client."""
        try:
            request = json.loads(line)
            
            # Add debug output if configured
            if self.browser.config and self.browser.config.debug:
                self.logger.debug(f"Daemon received: {json.dumps(request)}")
            
            # Forward to browser
            response = await self.browser.call(request)
            
            # Send response back to client
            response_str = json.dumps(response) + '\n'
            writer.write(response_str.encode('utf-8'))
            await writer.drain()
            
            if self.browser.config and self.browser.config.debug:
                self.logger.debug(f"Daemon sent: {response_str.strip()}")
                
        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {e}"
                }
            }
            writer.write((json.dumps(error_response) + '\n').encode('utf-8'))
            await writer.drain()
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if 'request' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {e}"
                }
            }
            writer.write((json.dumps(error_response) + '\n').encode('utf-8'))
            await writer.drain()
    
    async def stop(self):
        """Stop the daemon server."""
        self._running = False
        
        # Close all client connections
        for writer in list(self._clients):
            writer.close()
            await writer.wait_closed()
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Clean up socket and PID files
        if self.socket_path.exists():
            self.socket_path.unlink()
        
        pid_file = self.socket_path.with_suffix('.pid')
        if pid_file.exists():
            pid_file.unlink()
        
        # Close browser
        await self.browser.close()


class MCPBrowserClient:
    """Client for connecting to MCP Browser daemon."""
    
    def __init__(self, socket_path: Path):
        self.socket_path = socket_path
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        
    async def connect(self):
        """Connect to the daemon."""
        if not self.socket_path.exists():
            raise ConnectionError(f"Daemon socket not found: {self.socket_path}")
        
        # Check if daemon is alive
        pid_file = self.socket_path.with_suffix('.pid')
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                if not psutil.pid_exists(pid):
                    # Stale socket/PID file
                    self.socket_path.unlink()
                    pid_file.unlink()
                    raise ConnectionError("Daemon not running (stale PID file)")
            except (ValueError, psutil.Error):
                pass
        
        # Connect to socket
        self.reader, self.writer = await asyncio.open_unix_connection(str(self.socket_path))
    
    async def call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request and get response."""
        if not self.writer:
            await self.connect()
        
        # Send request
        request_str = json.dumps(request) + '\n'
        self.writer.write(request_str.encode('utf-8'))
        await self.writer.drain()
        
        # Read response
        response_line = await self.reader.readline()
        if not response_line:
            raise ConnectionError("Connection closed by daemon")
        
        return json.loads(response_line.decode('utf-8'))
    
    async def close(self):
        """Close the connection."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


def get_socket_path(server_name: Optional[str] = None) -> Path:
    """Get the socket path for a given server name."""
    runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
    if not runtime_dir:
        runtime_dir = f"/tmp/mcp-browser-{os.getuid()}"
    
    socket_name = f"mcp-browser-{server_name}.sock" if server_name else "mcp-browser.sock"
    return Path(runtime_dir) / socket_name


def is_daemon_running(socket_path: Path) -> bool:
    """Check if a daemon is running for the given socket."""
    if not socket_path.exists():
        return False
    
    pid_file = socket_path.with_suffix('.pid')
    if not pid_file.exists():
        return False
    
    try:
        pid = int(pid_file.read_text().strip())
        return psutil.pid_exists(pid)
    except (ValueError, psutil.Error):
        return False