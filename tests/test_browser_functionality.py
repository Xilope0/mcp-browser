#!/usr/bin/env python3
"""
Test MCP Browser core functionality without external servers.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path

from mcp_browser import MCPBrowser


@pytest.mark.asyncio
async def test_browser_without_servers():
    """Test MCP Browser core functionality without external servers."""
    
    print("=== Testing MCP Browser Core Functionality ===\n")
    
    # Create browser without any servers
    browser = MCPBrowser(enable_builtin_servers=False)
    
    try:
        # Manual initialization without servers
        from mcp_browser.config import MCPBrowserConfig
        from mcp_browser.registry import ToolRegistry
        from mcp_browser.filter import MessageFilter, VirtualToolHandler
        
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
        
        print("✓ Browser initialized without external servers\n")
        
        # Test 1: Test sparse tools directly
        print("1. Testing sparse mode tools:")
        sparse_tools = browser.registry.get_sparse_tools()
        assert len(sparse_tools) == 3  # Sparse mode shows only 3 tools
        print(f"   ✓ Found {len(sparse_tools)} sparse tools")
        for tool in sparse_tools:
            print(f"      - {tool['name']}")
        
        # Test 2: Add some test tools and use mcp_discover
        print("\n2. Testing tool discovery:")
        test_tools = [
            {"name": "test_tool1", "description": "Test Tool 1"},
            {"name": "test_tool2", "description": "Test Tool 2"},
            {"name": "test_tool3", "description": "Test Tool 3"}
        ]
        browser.registry.update_tools(test_tools)
        
        # Test virtual tool handler directly
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
        all_tools = json.loads(response["result"]["content"][0]["text"])
        assert len(all_tools) == 3
        print(f"   ✓ Discovered {len(all_tools)} test tools: {all_tools}")
        
        # Test 3: Test message filtering
        print("\n3. Testing message filtering:")
        test_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": test_tools
            }
        }
        
        filtered = browser.filter.filter_incoming(test_message)
        assert filtered is not None
        assert len(filtered["result"]["tools"]) == 3  # Sparse tools
        assert filtered["result"]["tools"][0]["name"] == "mcp_discover"
        print("   ✓ Message filtering works correctly")
        
        # Test 4: Test JSONPath discovery
        print("\n4. Testing JSONPath discovery:")
        result = browser.registry.discover("$.tools[*].description")
        assert result == ["Test Tool 1", "Test Tool 2", "Test Tool 3"]
        print("   ✓ JSONPath discovery works correctly")
            
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise
        
    finally:
        # No need to close since we didn't start any servers
        pass

def main():
    asyncio.run(test_browser_without_servers())


if __name__ == "__main__":
    main()
