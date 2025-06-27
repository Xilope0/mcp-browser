"""Basic tests for MCP Browser."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch

from mcp_browser import MCPBrowser
from mcp_browser.registry import ToolRegistry
from mcp_browser.filter import MessageFilter


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
        assert registry.discover("$.tools[?(@.name=='Bash')]")[0]["name"] == "Bash"
        assert registry.discover("$.tools[0].description") == "Run commands"
        assert registry.discover("$.nonexistent") is None
    
    def test_sparse_tools(self):
        """Test sparse tool generation."""
        registry = ToolRegistry()
        registry.update_tools([{"name": "tool1"}, {"name": "tool2"}])
        
        sparse = registry.get_sparse_tools()
        assert len(sparse) == 2
        assert sparse[0]["name"] == "mcp_discover"
        assert sparse[1]["name"] == "mcp_call"
        assert "2 tools available" in sparse[0]["description"]


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
        assert len(filtered["result"]["tools"]) == 2
        assert filtered["result"]["tools"][0]["name"] == "mcp_discover"
        assert filtered["result"]["tools"][1]["name"] == "mcp_call"
        
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
    
    async def test_initialization(self):
        """Test browser initialization."""
        with patch('mcp_browser.proxy.MCPServer') as mock_server_class:
            mock_server = AsyncMock()
            mock_server_class.return_value = mock_server
            
            browser = MCPBrowser()
            
            # Mock successful initialization
            mock_server.send_request.side_effect = [
                # Initialize response
                {"result": {"protocolVersion": "0.1.0"}},
                # Tools list response
                {"result": {"tools": [{"name": "test", "description": "Test tool"}]}}
            ]
            
            await browser.initialize()
            
            assert browser._initialized
            assert mock_server.start.called
    
    async def test_call_method(self):
        """Test the generic call method."""
        with patch('mcp_browser.proxy.MCPServer') as mock_server_class:
            mock_server = AsyncMock()
            mock_server_class.return_value = mock_server
            mock_server.send_request.side_effect = [
                {"result": {"protocolVersion": "0.1.0"}},
                {"result": {"tools": []}}
            ]
            
            browser = MCPBrowser()
            await browser.initialize()
            
            # Set up response handling
            browser._response_buffer[1] = asyncio.Future()
            
            # Simulate server response
            async def simulate_response():
                await asyncio.sleep(0.1)
                browser._handle_server_message({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {"success": True}
                })
            
            asyncio.create_task(simulate_response())
            
            # Make call
            response = await browser.call({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "test",
                "params": {}
            })
            
            assert response["result"]["success"] is True
    
    async def test_discover_method(self):
        """Test the discover method."""
        browser = MCPBrowser()
        browser.registry.update_tools([
            {"name": "tool1", "description": "First tool"},
            {"name": "tool2", "description": "Second tool"}
        ])
        
        # Test discovery
        tool_names = browser.discover("$.tools[*].name")
        assert tool_names == ["tool1", "tool2"]
        
        specific_tool = browser.discover("$.tools[?(@.name=='tool1')]")
        assert specific_tool[0]["description"] == "First tool"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])