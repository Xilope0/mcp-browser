#!/usr/bin/env python3
"""Test the enhanced discovery functionality."""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_browser import MCPBrowser


async def test_discovery():
    """Test discovery with server information."""
    browser = MCPBrowser(enable_builtin_servers=True)
    
    await browser.initialize()
    
    print("=== Testing Discovery ===\n")
    
    # Test 1: Discover all servers
    print("1. Discovering all servers:")
    servers = browser.discover("$.servers[*].name")
    print(f"   Found {len(servers) if servers else 0} servers: {servers}\n")
    
    # Test 2: Get server details
    print("2. Server details:")
    server_info = browser.discover("$.servers")
    if server_info:
        for name, info in server_info.items():
            print(f"   - {name}: {info.get('description', 'No description')}")
    print()
    
    # Test 3: Discover tools with server count
    print("3. Testing tools/list for sparse tools:")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    })
    
    if "result" in response:
        tools = response["result"]["tools"]
        for tool in tools:
            if tool["name"] == "mcp_discover":
                print(f"   mcp_discover description: {tool['description']}")
                break
    
    # Test 4: Onboarding content
    print("\n4. Getting default onboarding:")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "onboarding",
            "arguments": {"identity": "test-discovery"}
        }
    })
    
    if "result" in response:
        content = response["result"]["content"][0]["text"]
        # Just show first few lines
        lines = content.split('\n')[:10]
        print("   " + "\n   ".join(lines) + "\n   ...")
    
    await browser.close()


if __name__ == "__main__":
    asyncio.run(test_discovery())