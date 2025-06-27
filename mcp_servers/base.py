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
        
        # Log server startup
        print(f"DEBUG: {self.name} server starting", file=sys.stderr, flush=True)
        
        # Use asyncio for stdin reading
        loop = asyncio.get_event_loop()
        stdin_reader = asyncio.StreamReader()
        stdin_protocol = asyncio.StreamReaderProtocol(stdin_reader)
        
        try:
            # Connect stdin to async reader
            await loop.connect_read_pipe(lambda: stdin_protocol, sys.stdin)
        except Exception as e:
            print(f"ERROR: {self.name} failed to setup async stdin: {e}", file=sys.stderr, flush=True)
            return
        
        # Main server loop
        while self._running:
            try:
                # Read a line with timeout to prevent hanging
                line = await asyncio.wait_for(
                    stdin_reader.readline(),
                    timeout=None  # No timeout - we want to wait indefinitely for commands
                )
                
                if not line:
                    # Empty bytes means EOF
                    print(f"DEBUG: {self.name} detected EOF on stdin", file=sys.stderr, flush=True)
                    break
                
                # Decode and process line
                line_str = line.decode('utf-8').strip()
                if not line_str:
                    continue
                
                print(f"DEBUG: {self.name} received: {line_str}", file=sys.stderr, flush=True)
                
                try:
                    request = json.loads(line_str)
                    response = await self.handle_request(request)
                    response_str = json.dumps(response)
                    print(f"DEBUG: {self.name} sending: {response_str}", file=sys.stderr, flush=True)
                    print(response_str, flush=True)
                except json.JSONDecodeError as e:
                    print(f"ERROR: {self.name} JSON decode error: {e}", file=sys.stderr, flush=True)
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    print(json.dumps(error_response), flush=True)
                except Exception as e:
                    print(f"ERROR: {self.name} request handling error: {e}", file=sys.stderr, flush=True)
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32603,
                            "message": str(e)
                        }
                    }
                    print(json.dumps(error_response), flush=True)
                    
            except asyncio.CancelledError:
                print(f"DEBUG: {self.name} cancelled", file=sys.stderr, flush=True)
                break
            except KeyboardInterrupt:
                print(f"DEBUG: {self.name} interrupted", file=sys.stderr, flush=True)
                break
            except Exception as e:
                print(f"ERROR: {self.name} unexpected error: {e}", file=sys.stderr, flush=True)
                # Continue running despite errors
                await asyncio.sleep(0.1)
        
        print(f"DEBUG: {self.name} server exiting", file=sys.stderr, flush=True)
    
    def content_text(self, text: str) -> Dict[str, Any]:
        """Helper to create text content response."""
        return {
            "content": [{
                "type": "text",
                "text": text
            }]
        }