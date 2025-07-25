"""
Main MCP Browser proxy implementation.

Provides a generic, minimalistic interface for interacting with MCP servers
with automatic routing, sparse mode, and context optimization.
"""

import json
import asyncio
from typing import Dict, Any, Optional, Union
from pathlib import Path

from .config import ConfigLoader, MCPBrowserConfig
from .server import MCPServer
from .multi_server import MultiServerManager
from .registry import ToolRegistry
from .filter import MessageFilter, VirtualToolHandler
from .buffer import JsonRpcBuffer
from .logging_config import get_logger, TRACE


class MCPBrowser:
    """
    Generic MCP protocol browser with minimal API.
    
    Provides two main methods:
    - call(): Execute any JSON-RPC call
    - discover(): Explore available tools using JSONPath
    """
    
    def __init__(self, config_path: Optional[Path] = None, server_name: Optional[str] = None,
                 enable_builtin_servers: bool = True):
        """
        Initialize MCP Browser.
        
        Args:
            config_path: Optional path to configuration file
            server_name: Optional MCP server name to use (overrides default)
            enable_builtin_servers: Whether to start built-in servers (screen, memory, etc.)
        """
        self.config_loader = ConfigLoader(config_path)
        self.config: Optional[MCPBrowserConfig] = None
        self.server: Optional[MCPServer] = None
        self.multi_server: Optional[MultiServerManager] = None
        self.registry = ToolRegistry()
        self.filter: Optional[MessageFilter] = None
        self.virtual_handler: Optional[VirtualToolHandler] = None
        self._server_name = server_name
        self._enable_builtin_servers = enable_builtin_servers
        self._initialized = False
        self._response_buffer: Dict[Union[str, int], asyncio.Future] = {}
        self._next_id = 1
        self.logger = get_logger(__name__)
        self._config_watcher = None
        self._server_configs = {}
        self._config_mtime = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def initialize(self):
        """Initialize the browser and start MCP server."""
        if self._initialized:
            return
            
        # Load configuration
        self.config = self.config_loader.load()
        
        # Determine which server to use
        server_name = self._server_name or self.config.default_server
        if not server_name or server_name not in self.config.servers:
            raise ValueError(f"Server '{server_name}' not found in configuration")
        
        server_config = self.config.servers[server_name]
        
        # Create multi-server manager if using built-in servers
        if self._enable_builtin_servers:
            self.multi_server = MultiServerManager(logger=self.logger)
            await self.multi_server.start_builtin_servers()
        
        # Create main server if specified
        if server_name != "builtin-only":
            self.server = MCPServer(server_config, logger=get_logger(__name__, server_name))
            # Set up message handling
            self.server.add_message_handler(self._handle_server_message)
            # Start server
            await self.server.start()
        
        # Create filter and handler
        self.filter = MessageFilter(self.registry, sparse_mode=self.config.sparse_mode)
        self.virtual_handler = VirtualToolHandler(self.registry, self._forward_to_server)
        
        # Initialize connection
        await self._initialize_connection()
        
        # Start config file watcher
        await self._start_config_watcher()
        
        # Store server configs for discovery
        self._update_server_configs()
        
        self._initialized = True
        
    async def close(self):
        """Close the browser and stop all MCP servers."""
        if self._config_watcher:
            self._config_watcher.cancel()
        if self.server:
            await self.server.stop()
        if self.multi_server:
            await self.multi_server.stop_all()
        self._initialized = False
        
    async def call(self, jsonrpc_object: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a JSON-RPC call.
        
        This is the main generic interface for all MCP operations.
        
        Args:
            jsonrpc_object: Complete JSON-RPC request object
            
        Returns:
            JSON-RPC response object
            
        Example:
            response = await browser.call({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "Bash",
                    "arguments": {"command": "ls"}
                }
            })
        """
        # Ensure request has an ID
        if "id" not in jsonrpc_object:
            jsonrpc_object = jsonrpc_object.copy()
            jsonrpc_object["id"] = self._next_id
            self._next_id += 1
        
        request_id = jsonrpc_object["id"]
        
        # Handle initialize request specially when acting as a server
        if jsonrpc_object.get("method") == "initialize":
            # Initialize ourselves if needed
            if not self._initialized:
                await self.initialize()
            
            # Return our capabilities
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "mcp-browser",
                        "version": "0.1.0"
                    }
                }
            }
        
        # Initialize if needed for other requests
        if not self._initialized:
            await self.initialize()
        
        # Check if this is a virtual tool call
        if jsonrpc_object.get("method") == "tools/call":
            tool_name = jsonrpc_object.get("params", {}).get("name")
            
            if self.filter.is_virtual_tool(tool_name):
                # Handle virtual tool locally
                response = await self.virtual_handler.handle_tool_call(jsonrpc_object)
                if response:
                    return response
            elif tool_name == "onboarding" and self.multi_server:
                # Special handling for onboarding tool - route to built-in server
                try:
                    args = jsonrpc_object.get("params", {}).get("arguments", {})
                    response = await self.multi_server.route_tool_call(
                        "builtin:onboarding::onboarding", args
                    )
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": response
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32603, "message": str(e)}
                    }
        
        # Check if we have a server
        if not self.server:
            # In builtin-only mode, try to route to multi-server
            if self.multi_server:
                # Try to route based on method
                method = jsonrpc_object.get("method")
                
                if method == "tools/list":
                    # Get all tools and apply sparse filter
                    tools = await self.multi_server.get_all_tools()
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"tools": tools}
                    }
                    # Always filter to show only sparse tools
                    filtered_response = self.filter.filter_incoming(response)
                    return filtered_response
                    
                elif method == "tools/call":
                    # Route tool call to multi-server
                    tool_name = jsonrpc_object.get("params", {}).get("name")
                    args = jsonrpc_object.get("params", {}).get("arguments", {})
                    try:
                        result = await self.multi_server.route_tool_call(tool_name, args)
                        return {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": result
                        }
                    except Exception as e:
                        return {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -32603, "message": str(e)}
                        }
                
                elif method == "prompts/list":
                    # No prompts in builtin-only mode
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"prompts": []}
                    }
                
                elif method == "prompts/get":
                    # No prompts available
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32602, "message": "Prompt not found"}
                    }
                
                elif method == "resources/list":
                    # No resources in builtin-only mode
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"resources": []}
                    }
                
                elif method == "resources/read":
                    # No resources available
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32602, "message": "Resource not found"}
                    }
                
                elif method == "completion/complete":
                    # No completions in builtin-only mode
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"completion": {"values": []}}
                    }
                
                else:
                    # Unknown method
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method '{method}' not found"
                        }
                    }
            
            # No server available
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": "No MCP server available"
                }
            }
        
        # Log at trace level for raw I/O
        raw_request = json.dumps(jsonrpc_object)
        self.logger.log(TRACE, f">>> {self._server_name}: {raw_request}")
        
        # Create future for response
        future = asyncio.Future()
        self._response_buffer[request_id] = future
        
        # Send to server
        self.server.send_raw(raw_request)
        
        # Wait for response
        try:
            response = await asyncio.wait_for(future, timeout=self.config.timeout)
            self.logger.log(TRACE, f"<<< {self._server_name}: {json.dumps(response)}")
            return response
        except asyncio.TimeoutError:
            del self._response_buffer[request_id]
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": "Request timeout"
                }
            }
    
    def discover(self, jsonpath: str) -> Any:
        """
        Discover available tools and their properties using JSONPath.
        
        This is a synchronous convenience method for tool discovery.
        
        Args:
            jsonpath: JSONPath expression to query tool registry
            
        Returns:
            Query results (list, dict, or primitive value)
            
        Examples:
            # Get all tool names
            tools = browser.discover("$.tools[*].name")
            
            # Get specific tool
            bash_tool = browser.discover("$.tools[?(@.name=='Bash')]")
            
            # Get all input schemas
            schemas = browser.discover("$.tools[*].inputSchema")
        """
        return self.registry.discover(jsonpath)
    
    async def _initialize_connection(self):
        """Initialize MCP connection and populate tool registry."""
        # Only initialize if we have a server
        if not self.server:
            return
            
        # Send initialize request directly to server
        init_response = await self.server.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-browser",
                "version": "0.1.0"
            }
        })
        
        if "error" in init_response:
            raise RuntimeError(f"Failed to initialize: {init_response['error']}")
        
        # Get tool list from main server
        if self.server:
            tools_response = await self.server.send_request("tools/list", {})
            
            if "error" in tools_response:
                raise RuntimeError(f"Failed to list tools: {tools_response['error']}")
                
            # Update registry with tools
            if "result" in tools_response and "tools" in tools_response["result"]:
                self.registry.update_tools(tools_response["result"]["tools"])
        
        # Also get tools from multi-server if enabled
        if self.multi_server:
            builtin_tools = await self.multi_server.get_all_tools()
            # Add to registry without going through filter
            existing_tools = self.registry.raw_tool_list
            self.registry.update_tools(existing_tools + builtin_tools)
    
    def _handle_server_message(self, message: dict):
        """Handle incoming message from MCP server."""
        # Apply incoming filter
        filtered = self.filter.filter_incoming(message)
        if not filtered:
            return
        
        # Check if this is a response to a pending request
        msg_id = filtered.get("id")
        if msg_id in self._response_buffer:
            future = self._response_buffer.pop(msg_id)
            future.set_result(filtered)
    
    async def _forward_to_server(self, request: dict) -> dict:
        """Forward a request to the MCP server and get response."""
        # This is used by the virtual tool handler for mcp_call
        return await self.call(request)
    
    async def _start_config_watcher(self):
        """Start watching the config file for changes."""
        config_path = self.config_loader.config_path
        if not config_path.exists():
            return
            
        # Store initial mtime
        self._config_mtime = config_path.stat().st_mtime
        
        async def watch_config():
            """Watch for config file changes."""
            while True:
                try:
                    await asyncio.sleep(2)  # Check every 2 seconds
                    
                    if not config_path.exists():
                        continue
                        
                    current_mtime = config_path.stat().st_mtime
                    if current_mtime != self._config_mtime:
                        self.logger.info("Config file changed, reloading...")
                        self._config_mtime = current_mtime
                        
                        # Reload config
                        try:
                            new_config = self.config_loader.load()
                            self.config = new_config
                            self._update_server_configs()
                            self.logger.info("Config reloaded successfully")
                        except Exception as e:
                            self.logger.error(f"Failed to reload config: {e}")
                            
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Config watcher error: {e}")
                    await asyncio.sleep(5)
        
        self._config_watcher = asyncio.create_task(watch_config())
    
    def _update_server_configs(self):
        """Update server configurations for discovery."""
        self._server_configs = {}
        
        if self.config and self.config.servers:
            for name, server in self.config.servers.items():
                self._server_configs[name] = {
                    "name": name,
                    "description": server.description or f"MCP server: {name}",
                    "command": server.command,
                    "available": True
                }
        
        # Update registry metadata with server info
        self.registry._metadata["servers"] = self._server_configs


# Convenience function for simple usage
async def create_browser(config_path: Optional[Path] = None, 
                        server_name: Optional[str] = None) -> MCPBrowser:
    """Create and initialize an MCP Browser instance."""
    browser = MCPBrowser(config_path, server_name)
    await browser.initialize()
    return browser