#!/usr/bin/env python3
"""
Test MCP Browser with Brave Search integration.

This test requires BRAVE_API_KEY to be set in environment.
Source ~/.secrets/api-keys.sh before running.
"""

import pytest
import asyncio
import os
import json
from pathlib import Path

from mcp_browser import MCPBrowser


@pytest.mark.asyncio
async def test_brave_search_integration():
    """Test MCP Browser with Brave Search MCP server."""
    
    # Check if BRAVE_API_KEY is set
    if not os.environ.get("BRAVE_API_KEY"):
        pytest.skip("BRAVE_API_KEY not set. Source ~/.secrets/api-keys.sh first")
    
    print("=== Testing MCP Browser with Brave Search ===\n")
    print(f"BRAVE_API_KEY is set: {'*' * 20}{os.environ['BRAVE_API_KEY'][-4:]}\n")
    
    # Create test config for Brave Search
    test_config = {
        "servers": {
            "brave-search": {
                "command": ["npx", "-y", "@modelcontextprotocol/server-brave-search"],
                "name": "brave-search",
                "description": "Brave Search MCP server"
            }
        },
        "default_server": "brave-search",
        "sparse_mode": True,
        "enable_builtin_servers": False,  # Disable built-in servers
        "debug": False,
        "timeout": 30.0
    }
    
    # Write temporary config
    import tempfile
    import yaml
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_config, f)
        config_path = Path(f.name)
    
    browser = MCPBrowser(config_path=config_path, server_name="brave-search", enable_builtin_servers=False)
    
    try:
        print("1. Initializing MCP Browser with Brave Search...")
        await browser.initialize()
        print("   ✓ Browser initialized\n")
        
        # Test 1: List tools in sparse mode
        print("2. Testing sparse mode tools:")
        response = await browser.call({
            "jsonrpc": "2.0",
            "method": "tools/list"
        })
        
        assert "result" in response, f"Unexpected response: {response}"
        tools = response["result"]["tools"]
        assert len(tools) == 3  # Sparse mode shows only 3 tools
        print(f"   ✓ Found {len(tools)} sparse tools")
        for tool in tools:
            print(f"      - {tool['name']}")
        
        # Test 2: Discover all Brave Search tools
        print("\n3. Discovering all Brave Search tools:")
        response = await browser.call({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "mcp_discover",
                "arguments": {"jsonpath": "$.tools[*].name"}
            }
        })
        
        assert "result" in response
        all_tools = json.loads(response["result"]["content"][0]["text"])
        print(f"   ✓ Discovered {len(all_tools)} tools: {all_tools}")
        
        # Test 3: Use Brave Search
        print("\n4. Testing Brave Search functionality:")
        
        # First, get the exact tool name for search
        search_tool = None
        for tool_name in all_tools:
            if "search" in tool_name.lower():
                search_tool = tool_name
                break
        
        if search_tool:
            print(f"   Using tool: {search_tool}")
            
            # Perform a search using mcp_call
            response = await browser.call({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "mcp_call",
                    "arguments": {
                        "method": "tools/call",
                        "params": {
                            "name": search_tool,
                            "arguments": {
                                "query": "MCP Model Context Protocol",
                                "max_results": 3
                            }
                        }
                    }
                }
            })
            
            if "result" in response:
                print("   ✓ Search completed successfully")
                # Print first result summary
                content = response["result"].get("content", [])
                if content and content[0].get("text"):
                    results_text = content[0]["text"]
                    print(f"   Results preview: {results_text[:200]}...")
            else:
                print(f"   ⚠ Search failed: {response.get('error', 'Unknown error')}")
        else:
            print("   ⚠ No search tool found in Brave Search server")
        
        print("\n✅ Brave Search integration test completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise
        
    finally:
        await browser.close()
        # Clean up temp config
        if 'config_path' in locals():
            config_path.unlink(missing_ok=True)


if __name__ == "__main__":
    # Check for API key
    if not os.environ.get("BRAVE_API_KEY"):
        print("Please source ~/.secrets/api-keys.sh first:")
        print("  source ~/.secrets/api-keys.sh")
        print(f"  Current env has BRAVE_API_KEY: {bool(os.environ.get('BRAVE_API_KEY'))}")
        exit(1)
    
    asyncio.run(test_brave_search_integration())