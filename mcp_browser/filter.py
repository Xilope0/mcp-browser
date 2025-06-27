"""
Message filtering and transformation for sparse mode.

Intercepts and modifies JSON-RPC messages to implement
sparse mode and virtual tool injection.
"""

import sys
import json
from typing import Dict, Any, Optional, List, Callable, Union
from .registry import ToolRegistry


class MessageFilter:
    """Filter and transform JSON-RPC messages to always show sparse tools."""
    
    def __init__(self, registry: ToolRegistry, sparse_mode: bool = True):
        self.registry = registry
        # Ignore sparse_mode parameter - always use sparse mode
        self._handled_ids: set = set()
        
    def filter_outgoing(self, message: dict) -> Optional[dict]:
        """
        Filter messages going from client to server.
        
        Args:
            message: Outgoing JSON-RPC message
            
        Returns:
            Modified message or None to block
        """
        # For now, pass through all outgoing messages
        return message
    
    def filter_incoming(self, message: dict) -> Optional[dict]:
        """
        Filter messages coming from server to client.
        
        Args:
            message: Incoming JSON-RPC message
            
        Returns:
            Modified message or None to block
        """
        # Check if this is a duplicate error for a handled request
        if (message.get("id") in self._handled_ids and 
            message.get("error", {}).get("code") == -32603):
            # Block duplicate error
            self._handled_ids.discard(message.get("id"))
            return None
        
        # ALWAYS intercept tools/list responses to show only sparse tools
        if (message.get("id") and 
            message.get("result", {}).get("tools")):
            return self._filter_tools_response(message)
        
        return message
    
    def _filter_tools_response(self, message: dict) -> dict:
        """Apply sparse mode filtering to tools/list response."""
        tools = message["result"]["tools"]
        
        # Update registry with full tool list
        self.registry.update_tools(tools)
        
        # Replace with sparse tools
        message = message.copy()
        message["result"] = message["result"].copy()
        sparse_tools = self.registry.get_sparse_tools()
        message["result"]["tools"] = sparse_tools
        
        return message
    
    def mark_handled(self, request_id: Union[str, int]):
        """Mark a request ID as handled locally."""
        self._handled_ids.add(request_id)
    
    def is_virtual_tool(self, tool_name: str) -> bool:
        """Check if a tool is virtual (handled locally)."""
        return tool_name in ["mcp_discover", "mcp_call", "onboarding"]


class VirtualToolHandler:
    """Handles virtual tool calls that don't exist on the MCP server."""
    
    def __init__(self, registry: ToolRegistry, server_callback: Callable):
        self.registry = registry
        self.server_callback = server_callback
        
    async def handle_tool_call(self, message: dict) -> Optional[dict]:
        """
        Handle virtual tool calls.
        
        Args:
            message: Tool call request
            
        Returns:
            Response message or None if not handled
        """
        if message.get("method") != "tools/call":
            return None
            
        tool_name = message.get("params", {}).get("name")
        
        if tool_name == "mcp_discover":
            return await self._handle_discover(message)
        elif tool_name == "mcp_call":
            return await self._handle_call(message)
        elif tool_name == "onboarding":
            # Onboarding is handled specially in the proxy
            return None
        
        return None
    
    async def _handle_discover(self, message: dict) -> dict:
        """Handle mcp_discover tool call."""
        params = message.get("params", {}).get("arguments", {})
        jsonpath = params.get("jsonpath", "$.tools[*]")
        
        try:
            result = self.registry.discover(jsonpath)
            
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result, indent=2) if result else "No matches found"
                    }]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Discovery error: {str(e)}"
                }
            }
    
    async def _handle_call(self, message: dict) -> dict:
        """Handle mcp_call tool - forward transformed request."""
        params = message.get("params", {}).get("arguments", {})
        
        # Extract method and params from the tool arguments
        method = params.get("method")
        call_params = params.get("params", {})
        
        if not method:
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {
                    "code": -32602,
                    "message": "Missing 'method' parameter"
                }
            }
        
        # Create the actual JSON-RPC call
        forwarded_request = {
            "jsonrpc": "2.0",
            "id": message.get("id"),  # Use same ID for response mapping
            "method": method,
            "params": call_params
        }
        
        # Forward to server and get response
        try:
            # The server_callback should handle sending and receiving
            response = await self.server_callback(forwarded_request)
            return response
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }