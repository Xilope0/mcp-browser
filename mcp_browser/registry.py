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
                "description": f"🔍 PROXY META-TOOL: Discover {tool_count} hidden tools from {server_count} MCP servers without loading them into context. This prevents context explosion while enabling full tool access via JSONPath queries. Use this to explore what's available before calling specific tools.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "jsonpath": {
                            "type": "string",
                            "description": "JSONPath expression to query tool catalog. Examples: '$.tools[*].name' (list all), '$.tools[?(@.name=='Bash')]' (find specific), '$.servers[*]' (list servers)"
                        }
                    },
                    "required": ["jsonpath"]
                }
            },
            {
                "name": "mcp_call",
                "description": f"🚀 PROXY META-TOOL: Execute any of the {tool_count} available MCP tools by constructing JSON-RPC calls. This is the universal interface to all hidden tools - you can call ANY tool discovered via mcp_discover without it being loaded into your context.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "JSON-RPC method to call. For tool execution use 'tools/call'. Other methods: 'tools/list', 'prompts/list', 'resources/list'"
                        },
                        "params": {
                            "type": "object",
                            "description": "Method parameters. For 'tools/call': {'name': 'tool_name', 'arguments': {...}}. The arguments object contains the actual tool parameters."
                        }
                    },
                    "required": ["method", "params"]
                }
            },
            {
                "name": "onboarding",
                "description": "📋 BUILT-IN TOOL: Manage persistent, identity-aware onboarding instructions. This tool lets AI instances leave instructions for future contexts based on identity (project name, user, etc). Perfect for maintaining context across sessions without consuming tokens.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "identity": {
                            "type": "string",
                            "description": "Identity key for onboarding instructions (e.g., 'Claude', 'MyProject', 'WebDev'). Each identity can have separate instructions."
                        },
                        "instructions": {
                            "type": "string",
                            "description": "Optional: New instructions to store. If omitted, retrieves existing instructions for this identity. Use this to leave notes for future AI sessions."
                        },
                        "append": {
                            "type": "boolean",
                            "description": "If true, append to existing instructions instead of replacing them entirely",
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