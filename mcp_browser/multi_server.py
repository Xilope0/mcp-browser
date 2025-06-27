"""
Multi-server management for MCP Browser.

Manages multiple MCP servers including built-in servers that are
automatically started with the browser.
"""

import os
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

from .server import MCPServer
from .config import MCPServerConfig
from .logging_config import get_logger


class MultiServerManager:
    """Manages multiple MCP servers."""
    
    def __init__(self, logger=None):
        self.logger = logger or get_logger(__name__)
        self.servers: Dict[str, MCPServer] = {}
        self.builtin_servers = self._get_builtin_servers()
        
    def _get_builtin_servers(self) -> Dict[str, MCPServerConfig]:
        """Get configuration for built-in MCP servers."""
        base_path = Path(__file__).parent.parent / "mcp_servers"
        
        return {
            "builtin:screen": MCPServerConfig(
                command=["python3", str(base_path / "screen" / "screen_server.py")],
                name="screen",
                description="GNU screen session management"
            ),
            "builtin:memory": MCPServerConfig(
                command=["python3", str(base_path / "memory" / "memory_server.py")],
                name="memory",
                description="Persistent memory and context management"
            ),
            "builtin:patterns": MCPServerConfig(
                command=["python3", str(base_path / "pattern_manager" / "pattern_server.py")],
                name="patterns",
                description="Auto-response pattern management"
            ),
            "builtin:onboarding": MCPServerConfig(
                command=["python3", str(base_path / "onboarding" / "onboarding_server.py")],
                name="onboarding",
                description="Identity-aware onboarding management"
            )
        }
    
    async def start_builtin_servers(self):
        """Start all built-in servers."""
        for name, config in self.builtin_servers.items():
            self.logger.info(f"Starting built-in server: {name}")
            
            server = MCPServer(config, logger=get_logger(__name__, name))
            try:
                await server.start()
                self.servers[name] = server
                
                # Initialize each server
                await server.send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "mcp-browser",
                        "version": "0.1.0"
                    }
                })
                self.logger.info(f"Successfully initialized {name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize {name}: {e}")
    
    async def add_server(self, name: str, config: MCPServerConfig):
        """Add and start a custom server."""
        if name in self.servers:
            raise ValueError(f"Server {name} already exists")
        
        server = MCPServer(config, logger=get_logger(__name__, name))
        await server.start()
        self.servers[name] = server
        
        # Initialize
        await server.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-browser",
                "version": "0.1.0"
            }
        })
    
    async def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get tools from all servers."""
        all_tools = []
        
        for server_name, server in self.servers.items():
            try:
                response = await server.send_request("tools/list", {})
                tools = response.get("tools", [])
                
                # Add server prefix to tool names to avoid conflicts
                for tool in tools:
                    # Keep original name for display
                    tool["_original_name"] = tool["name"]
                    tool["_server"] = server_name
                    # Prefix tool name with server
                    tool["name"] = f"{server_name}::{tool['name']}"
                    tool["description"] = f"[{server_name}] {tool['description']}"
                
                all_tools.extend(tools)
                
            except Exception as e:
                self.logger.warning(f"Failed to get tools from {server_name}: {e}")
        
        return all_tools
    
    async def route_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route a tool call to the appropriate server."""
        # Check if tool has server prefix
        if "::" in tool_name:
            server_name, actual_tool = tool_name.split("::", 1)
            
            if server_name in self.servers:
                # Call the tool on the specific server
                response = await self.servers[server_name].send_request("tools/call", {
                    "name": actual_tool,
                    "arguments": arguments
                })
                return response
            else:
                raise Exception(f"Server {server_name} not found")
        else:
            # Try to find tool in any server (backward compatibility)
            for server_name, server in self.servers.items():
                try:
                    response = await server.send_request("tools/call", {
                        "name": tool_name,
                        "arguments": arguments
                    })
                    return response
                except Exception:
                    continue
            
            raise Exception(f"Tool {tool_name} not found in any server")
    
    async def stop_all(self):
        """Stop all servers."""
        # Create a copy of the dictionary to avoid iteration errors
        servers_copy = dict(self.servers)
        
        for name, server in servers_copy.items():
            self.logger.info(f"Stopping server: {name}")
            try:
                await server.stop()
            except Exception as e:
                self.logger.error(f"Error stopping server {name}: {e}")
        
        self.servers.clear()