#!/usr/bin/env python3
"""Test UTF-8 handling in screen peek functionality."""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_browser import MCPBrowser


async def test_screen_utf8():
    """Test screen peek with non-UTF8 content."""
    browser = MCPBrowser(enable_builtin_servers=True)
    
    await browser.initialize()
    
    print("=== Testing Screen UTF-8 Handling ===\n")
    
    # Create a test session
    print("1. Creating test session...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "create_session",
            "arguments": {
                "name": "utf8-test",
                "command": "bash"
            }
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    # Execute command that produces mixed encoding
    print("\n2. Executing command with mixed encoding...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "execute",
            "arguments": {
                "session": "utf8-test",
                "command": "echo -e 'UTF-8: café\\nBinary: \\x80\\x81\\x82\\nEmoji: 🤖'"
            }
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    # Wait a moment for output
    await asyncio.sleep(0.5)
    
    # Peek at the session
    print("\n3. Peeking at session output...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "peek",
            "arguments": {
                "session": "utf8-test",
                "lines": 10
            }
        }
    })
    
    if "result" in response:
        output = response["result"]["content"][0]["text"]
        print(f"   Output:\n{output}")
        
        # Check if we handled the encoding properly
        if "café" in output and "🤖" in output:
            print("\n✓ UTF-8 encoding handled correctly!")
        else:
            print("\n⚠ Some UTF-8 characters may not have been decoded properly")
    else:
        print(f"   Error: {response}")
    
    # Clean up
    print("\n4. Cleaning up...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "kill_session",
            "arguments": {"session": "utf8-test"}
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    await browser.close()


if __name__ == "__main__":
    asyncio.run(test_screen_utf8())