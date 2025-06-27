"""
Base MCP server implementation for Python.

Provides a foundation for building MCP servers with standard
JSON-RPC handling and tool management.
"""

import sys
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod


class BaseMCPServer(ABC):
    """Base class for MCP servers."""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._running = False
        
    @abstractmethod
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a tool call. Must be implemented by subclasses."""
        pass
    
    def register_tool(self, name: str, description: str, input_schema: Dict[str, Any], 
                     handler: Optional[Callable] = None):
        """Register a tool with the server."""
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
            "handler": handler
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": self.name,
                            "version": self.version
                        }
                    }
                }
            
            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": list(self.tools.values())
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name not in self.tools:
                    raise Exception(f"Tool '{tool_name}' not found")
                
                # Use registered handler if available, otherwise use abstract method
                tool_info = self.tools[tool_name]
                if tool_info.get("handler"):
                    result = await tool_info["handler"](arguments)
                else:
                    result = await self.handle_tool_call(tool_name, arguments)
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            
            else:
                raise Exception(f"Method '{method}' not found")
                
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    async def run(self):
        """Run the MCP server, reading from stdin and writing to stdout."""
        self._running = True
        
        # Platform-specific non-blocking setup
        try:
            import fcntl
            import os
            flags = fcntl.fcntl(sys.stdin.fileno(), fcntl.F_GETFL)
            fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)
        except ImportError:
            # Windows doesn't have fcntl
            pass
        
        buffer = ""
        
        while self._running:
            try:
                # Try to read available data
                chunk = sys.stdin.read(4096)
                if chunk:
                    buffer += chunk
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line:
                            try:
                                request = json.loads(line)
                                response = await self.handle_request(request)
                                print(json.dumps(response), flush=True)
                            except json.JSONDecodeError:
                                pass
                            except Exception as e:
                                error_response = {
                                    "jsonrpc": "2.0",
                                    "id": None,
                                    "error": {
                                        "code": -32700,
                                        "message": "Parse error"
                                    }
                                }
                                print(json.dumps(error_response), flush=True)
                
            except BlockingIOError:
                # No data available, sleep briefly
                await asyncio.sleep(0.01)
            except EOFError:
                # stdin closed
                break
            except KeyboardInterrupt:
                break
    
    def content_text(self, text: str) -> Dict[str, Any]:
        """Helper to create text content response."""
        return {
            "content": [{
                "type": "text",
                "text": text
            }]
        }