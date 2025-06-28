"""
Tool registry for storing and discovering MCP tools.

Manages tool descriptions, provides JSONPath-based discovery,
and supports sparse mode for context optimization.
"""

import json
import re
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
        # Check if this is a regex query and handle it specially
        if "=~" in jsonpath:
            return self._regex_search(jsonpath)
        
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
    
    def _regex_search(self, jsonpath: str) -> Union[List[Any], Any, None]:
        """
        Handle regex-based JSONPath queries manually.
        
        Supports patterns like: $.tools[?(@.name =~ /pattern/flags)]
        """
        # Parse basic regex patterns for tools
        if "$.tools[?(@.name =~" in jsonpath:
            # Extract regex pattern
            match = re.search(r'/([^/]+)/([gi]*)', jsonpath)
            if not match:
                return None
            
            pattern = match.group(1)
            flags_str = match.group(2)
            
            # Convert flags
            flags = 0
            if 'i' in flags_str:
                flags |= re.IGNORECASE
            if 'g' in flags_str:
                pass  # Global is default behavior in Python findall
            
            try:
                regex = re.compile(pattern, flags)
            except re.error:
                return None
            
            # Search through tools
            matches = []
            for tool in self.raw_tool_list:
                tool_name = tool.get("name", "")
                if regex.search(tool_name):
                    matches.append(tool)
            
            return matches if matches else None
        
        elif "$.tools[?(@.description =~" in jsonpath:
            # Extract regex pattern for descriptions
            match = re.search(r'/([^/]+)/([gi]*)', jsonpath)
            if not match:
                return None
            
            pattern = match.group(1)
            flags_str = match.group(2)
            
            flags = 0
            if 'i' in flags_str:
                flags |= re.IGNORECASE
            
            try:
                regex = re.compile(pattern, flags)
            except re.error:
                return None
            
            # Search through tool descriptions
            matches = []
            for tool in self.raw_tool_list:
                description = tool.get("description", "")
                if regex.search(description):
                    matches.append(tool)
            
            return matches if matches else None
        
        # Fallback to basic JSONPath if regex pattern not recognized
        try:
            expr = jsonpath_parse(jsonpath.replace("=~", "=="))  # Try basic equality
            search_data = {
                "tools": self.raw_tool_list,
                "tool_names": self.get_all_tool_names(),
                "metadata": self._metadata,
                "servers": self._metadata.get("servers", {})
            }
            matches = expr.find(search_data)
            if not matches:
                return None
            elif len(matches) == 1:
                return matches[0].value
            else:
                return [match.value for match in matches]
        except:
            return None
    
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
    
    def get_full_api_documentation(self) -> Dict[str, Any]:
        """
        Generate comprehensive API documentation for AI consumption.
        
        Returns complete server and tool information in structured JSON format.
        """
        servers = self._metadata.get("servers", {})
        
        # Group tools by server
        tools_by_server = {}
        builtin_tools = []
        
        for tool in self.raw_tool_list:
            tool_name = tool.get("name", "")
            
            # Check if it's a server-namespaced tool
            if "::" in tool_name:
                server_ns = tool_name.split("::")[0]
                if server_ns not in tools_by_server:
                    tools_by_server[server_ns] = []
                tools_by_server[server_ns].append(tool)
            else:
                # Check if tool belongs to a specific server based on metadata
                found_server = None
                for server_name, server_info in servers.items():
                    server_tools = server_info.get("tools", [])
                    if any(t.get("name") == tool_name for t in server_tools):
                        found_server = server_name
                        break
                
                if found_server:
                    if found_server not in tools_by_server:
                        tools_by_server[found_server] = []
                    tools_by_server[found_server].append(tool)
                else:
                    builtin_tools.append(tool)
        
        # Build comprehensive documentation
        api_doc = {
            "mcp_browser_version": "0.2.0",
            "total_servers": len(servers) + (1 if builtin_tools else 0),
            "total_tools": len(self.raw_tool_list),
            "generation_timestamp": None,  # Will be set when called
            "servers": {},
            "builtin": {
                "name": "builtin",
                "description": "Built-in MCP Browser servers (screen, memory, patterns, onboarding)",
                "status": "active",
                "tools": builtin_tools,
                "tool_count": len(builtin_tools),
                "capabilities": ["screen_management", "memory_storage", "pattern_matching", "onboarding_management"]
            },
            "discovery_patterns": {
                "all_tools": "$.tools[*]",
                "all_tool_names": "$.tools[*].name", 
                "tools_by_server": "$.servers[*].tools[*]",
                "tool_schemas": "$.tools[*].inputSchema",
                "memory_tools": "$.tools[?(@.name =~ /memory|task|pattern|knowledge/i)]",
                "screen_tools": "$.tools[?(@.name =~ /screen|session/i)]",
                "find_tool_by_name": "$.tools[?(@.name=='TOOL_NAME')]",
                "server_capabilities": "$.servers[*].capabilities"
            },
            "sparse_mode_info": {
                "visible_tools": ["mcp_discover", "mcp_call", "onboarding"],
                "hidden_tools": len(self.raw_tool_list),
                "purpose": "Context optimization - full MCP API accessible via proxy tools"
            }
        }
        
        # Add external servers
        for server_name, server_info in servers.items():
            server_tools = tools_by_server.get(server_name, [])
            
            api_doc["servers"][server_name] = {
                "name": server_name,
                "description": server_info.get("description", ""),
                "command": server_info.get("command", []),
                "status": server_info.get("status", "unknown"),
                "tools": server_tools,
                "tool_count": len(server_tools),
                "tool_names": [t.get("name", "") for t in server_tools],
                "environment": server_info.get("env", {}),
                "working_directory": server_info.get("cwd"),
                "capabilities": self._extract_capabilities(server_tools)
            }
        
        return api_doc
    
    def _extract_capabilities(self, tools: List[Dict[str, Any]]) -> List[str]:
        """Extract capabilities from tool list."""
        capabilities = set()
        
        for tool in tools:
            name = tool.get("name", "").lower()
            desc = tool.get("description", "").lower()
            
            # Infer capabilities from tool names and descriptions
            if any(keyword in name for keyword in ["read", "write", "file"]):
                capabilities.add("file_operations")
            if any(keyword in name for keyword in ["search", "query", "find"]):
                capabilities.add("search_operations")
            if any(keyword in name for keyword in ["web", "http", "url"]):
                capabilities.add("web_operations")
            if any(keyword in name for keyword in ["git", "repo", "commit"]):
                capabilities.add("version_control")
            if any(keyword in name for keyword in ["memory", "store", "save"]):
                capabilities.add("data_storage")
            if any(keyword in name for keyword in ["exec", "run", "command"]):
                capabilities.add("command_execution")
            if any(keyword in desc for keyword in ["browser", "scrape", "crawl"]):
                capabilities.add("web_scraping")
        
        return sorted(list(capabilities))
    
    def set_metadata(self, metadata: Dict[str, Any]):
        """Set metadata about servers and configuration."""
        self._metadata = metadata
    
    def update_metadata(self, key: str, value: Any):
        """Set specific metadata that can be discovered via JSONPath."""
        self._metadata[key] = value
    
    def to_json(self) -> str:
        """Export registry as JSON for debugging."""
        return json.dumps({
            "tools": self.raw_tool_list,
            "metadata": self._metadata
        }, indent=2)