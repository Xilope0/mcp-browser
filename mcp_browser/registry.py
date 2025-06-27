"""
Tool registry for storing and discovering MCP tools.

Manages tool descriptions, provides JSONPath-based discovery,
and supports sparse mode for context optimization.
"""

import json
from typing import Dict, Any, List, Optional, Union
from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JsonPathParserError


class ToolRegistry:
    """Registry for MCP tools with discovery capabilities."""
    
    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self.raw_tool_list: List[Dict[str, Any]] = []
        self._metadata: Dict[str, Any] = {}
    
    def update_tools(self, tools: List[Dict[str, Any]]):
        """
        Update the registry with a list of tools.
        
        Args:
            tools: List of tool definitions from MCP server
        """
        self.raw_tool_list = tools
        self.tools.clear()
        
        for tool in tools:
            if "name" in tool:
                self.tools[tool["name"]] = tool
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a tool definition by name."""
        return self.tools.get(name)
    
    def get_all_tool_names(self) -> List[str]:
        """Get all registered tool names."""
        return list(self.tools.keys())
    
    def discover(self, jsonpath: str) -> Union[List[Any], Any, None]:
        """
        Discover tools using JSONPath queries.
        
        Args:
            jsonpath: JSONPath expression to query tools
            
        Returns:
            Query results or None if no matches
            
        Examples:
            $.tools[*].name - Get all tool names
            $.tools[?(@.name=='Bash')] - Get Bash tool details
            $.tools[*].inputSchema - Get all input schemas
        """
        try:
            expr = jsonpath_parse(jsonpath)
        except (JsonPathParserError, Exception):
            return None
        
        # Create a searchable structure
        search_data = {
            "tools": self.raw_tool_list,
            "tool_names": self.get_all_tool_names(),
            "metadata": self._metadata,
            "servers": self._metadata.get("servers", {})
        }
        
        # Execute JSONPath query
        matches = expr.find(search_data)
        
        if not matches:
            return None
        elif len(matches) == 1:
            return matches[0].value
        else:
            return [match.value for match in matches]
    
    def get_sparse_tools(self) -> List[Dict[str, Any]]:
        """
        Get minimal tool list for sparse mode.
        
        Returns only essential meta-tools for discovery.
        """
        tool_count = len(self.tools)
        server_count = len(self._metadata.get("servers", {}))
        
        sparse_tools = [
            {
                "name": "mcp_discover",
                "description": f"Discover available tools and servers using JSONPath. {tool_count} tools from {server_count} servers available.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "jsonpath": {
                            "type": "string",
                            "description": "JSONPath expression (e.g., '$.tools[*].name')"
                        }
                    },
                    "required": ["jsonpath"]
                }
            },
            {
                "name": "mcp_call",
                "description": "Execute any MCP tool by constructing a JSON-RPC call.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "JSON-RPC method (e.g., 'tools/call')"
                        },
                        "params": {
                            "type": "object",
                            "description": "Method parameters"
                        }
                    },
                    "required": ["method", "params"]
                }
            },
            {
                "name": "onboarding",
                "description": "Get or set identity-specific onboarding instructions for AI contexts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "identity": {
                            "type": "string",
                            "description": "Identity for onboarding (e.g., 'Claude', project name)"
                        },
                        "instructions": {
                            "type": "string",
                            "description": "Optional: Set new instructions. If omitted, retrieves existing."
                        },
                        "append": {
                            "type": "boolean",
                            "description": "Append to existing instructions instead of replacing",
                            "default": False
                        }
                    },
                    "required": ["identity"]
                }
            }
        ]
        
        return sparse_tools
    
    def set_metadata(self, key: str, value: Any):
        """Set metadata that can be discovered via JSONPath."""
        self._metadata[key] = value
    
    def to_json(self) -> str:
        """Export registry as JSON for debugging."""
        return json.dumps({
            "tools": self.raw_tool_list,
            "metadata": self._metadata
        }, indent=2)