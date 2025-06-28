"""Basic tests for MCP Browser."""

import pytest
import pytest_asyncio
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch

from mcp_browser import MCPBrowser
from mcp_browser.registry import ToolRegistry
from mcp_browser.filter import MessageFilter, VirtualToolHandler


class TestToolRegistry:
    """Test the tool registry functionality."""
    
    def test_update_tools(self):
        """Test updating registry with tools."""
        registry = ToolRegistry()
        tools = [
            {"name": "tool1", "description": "Tool 1"},
            {"name": "tool2", "description": "Tool 2"}
        ]
        
        registry.update_tools(tools)
        
        assert len(registry.tools) == 2
        assert registry.get_tool("tool1")["description"] == "Tool 1"
        assert registry.get_all_tool_names() == ["tool1", "tool2"]
    
    def test_discover_jsonpath(self):
        """Test JSONPath discovery."""
        registry = ToolRegistry()
        tools = [
            {"name": "Bash", "description": "Run commands"},
            {"name": "Read", "description": "Read files"}
        ]
        registry.update_tools(tools)
        
        # Test various JSONPath queries
        assert registry.discover("$.tools[*].name") == ["Bash", "Read"]
        assert registry.discover("$.tools[0].name") == "Bash"
        assert registry.discover("$.tools[0].description") == "Run commands"
        assert registry.discover("$.tools[1].name") == "Read"
        assert registry.discover("$.nonexistent") is None
    
    def test_sparse_tools(self):
        """Test sparse tool generation."""
        registry = ToolRegistry()
        registry.update_tools([{"name": "tool1"}, {"name": "tool2"}])
        
        sparse = registry.get_sparse_tools()
        assert len(sparse) == 3
        assert sparse[0]["name"] == "mcp_discover"
        assert sparse[1]["name"] == "mcp_call"
        assert sparse[2]["name"] == "onboarding"
        assert "2 hidden tools" in sparse[0]["description"]


class TestMessageFilter:
    """Test message filtering."""
    
    def test_sparse_mode_filtering(self):
        """Test that tools/list responses are filtered in sparse mode."""
        registry = ToolRegistry()
        filter = MessageFilter(registry, sparse_mode=True)
        
        # Mock tools/list response
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {"name": "tool1", "description": "Tool 1"},
                    {"name": "tool2", "description": "Tool 2"}
                ]
            }
        }
        
        filtered = filter.filter_incoming(message)
        
        # Should replace with sparse tools
        assert len(filtered["result"]["tools"]) == 3
        assert filtered["result"]["tools"][0]["name"] == "mcp_discover"
        assert filtered["result"]["tools"][1]["name"] == "mcp_call"
        assert filtered["result"]["tools"][2]["name"] == "onboarding"
        
        # Registry should have full tools
        assert len(registry.tools) == 2
    
    def test_duplicate_error_filtering(self):
        """Test filtering of duplicate errors for handled requests."""
        registry = ToolRegistry()
        filter = MessageFilter(registry)
        
        # Mark a request as handled
        filter.mark_handled(123)
        
        # Duplicate error should be filtered
        error_msg = {
            "jsonrpc": "2.0",
            "id": 123,
            "error": {"code": -32603, "message": "Tool not found"}
        }
        
        assert filter.filter_incoming(error_msg) is None
        
        # ID should be removed from handled set
        assert 123 not in filter._handled_ids


@pytest.mark.asyncio
class TestMCPBrowser:
    """Test the main MCP Browser functionality."""
    
    async def test_browser_without_servers(self):
        """Test browser without any servers (unit test mode)."""
        # Create browser without any servers
        browser = MCPBrowser(enable_builtin_servers=False)
        
        # Manually set up minimal config to avoid file loading
        from mcp_browser.config import MCPBrowserConfig
        browser.config = MCPBrowserConfig(
            servers={},
            default_server=None,
            sparse_mode=True,
            debug=False
        )
        
        # Initialize components without servers
        browser.registry = ToolRegistry()
        browser.filter = MessageFilter(browser.registry, sparse_mode=True)
        browser.virtual_handler = VirtualToolHandler(browser.registry, browser._forward_to_server)
        browser._initialized = True
        
        # Test basic functionality
        assert browser._initialized
        assert browser.registry is not None
        assert browser.filter is not None
        
        # Test registry with some tools
        browser.registry.update_tools([
            {"name": "test1", "description": "Test tool 1"},
            {"name": "test2", "description": "Test tool 2"}
        ])
        
        # Test discover method
        tool_names = browser.discover("$.tools[*].name")
        assert tool_names == ["test1", "test2"]
        
        # Test sparse tools
        sparse = browser.registry.get_sparse_tools()
        assert len(sparse) == 3
        assert sparse[0]["name"] == "mcp_discover"
    
    async def test_virtual_tool_handling(self):
        """Test virtual tool handling without real servers."""
        browser = MCPBrowser(enable_builtin_servers=False)
        
        # Set up minimal config
        from mcp_browser.config import MCPBrowserConfig
        browser.config = MCPBrowserConfig(
            servers={},
            default_server=None,
            sparse_mode=True,
            debug=False
        )
        
        browser.registry = ToolRegistry()
        browser.filter = MessageFilter(browser.registry, sparse_mode=True)
        browser.virtual_handler = VirtualToolHandler(browser.registry, browser._forward_to_server)
        browser._initialized = True
        
        # Add some test tools
        browser.registry.update_tools([
            {"name": "tool1", "description": "First tool"},
            {"name": "tool2", "description": "Second tool"}
        ])
        
        # Test mcp_discover virtual tool
        response = await browser.virtual_handler.handle_tool_call({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "mcp_discover",
                "arguments": {"jsonpath": "$.tools[*].name"}
            }
        })
        
        assert response is not None
        assert "result" in response
        assert "content" in response["result"]
        
        # Parse the response - it returns the actual values, not full objects
        content = json.loads(response["result"]["content"][0]["text"])
        assert content == ["tool1", "tool2"]
        
        # Also test getting full tools
        response2 = await browser.virtual_handler.handle_tool_call({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "mcp_discover",
                "arguments": {"jsonpath": "$.tools[0]"}
            }
        })
        
        content2 = json.loads(response2["result"]["content"][0]["text"])
        assert content2["name"] == "tool1"
        assert content2["description"] == "First tool"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])