#!/usr/bin/env python3
"""Test multiuser functionality in screen server."""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_browser import MCPBrowser


async def test_screen_multiuser():
    """Test screen multiuser session functionality."""
    browser = MCPBrowser(enable_builtin_servers=True)
    
    await browser.initialize()
    
    print("=== Testing Screen Multiuser Functionality ===\n")
    
    # Create a test session
    print("1. Creating test session...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "create_session",
            "arguments": {
                "name": "multiuser-test",
                "command": "bash"
            }
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    # Enable multiuser mode
    print("\n2. Enabling multiuser mode...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "enable_multiuser",
            "arguments": {
                "session": "multiuser-test"
            }
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    # Add a user to the session
    print("\n3. Adding user to session...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "add_user",
            "arguments": {
                "session": "multiuser-test",
                "user": "testuser"
            }
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    # Get attach instructions
    print("\n4. Getting attach instructions...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "attach_multiuser",
            "arguments": {
                "session": "multiuser-test",
                "user": "testuser"
            }
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    # Execute a command in the multiuser session
    print("\n5. Executing command in multiuser session...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "execute",
            "arguments": {
                "session": "multiuser-test",
                "command": "echo 'Multiuser session test - Hello World!'"
            }
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    # Wait a moment for output
    await asyncio.sleep(0.5)
    
    # Test peek functionality with multiuser session
    print("\n6. Testing peek with multiuser session...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "peek",
            "arguments": {
                "session": "multiuser-test",
                "lines": 10
            }
        }
    })
    
    if "result" in response:
        output = response["result"]["content"][0]["text"]
        print(f"   Output:\n{output}")
        
        # Check if we can see the executed command output
        if "Multiuser session test" in output:
            print("\n✓ Peek works correctly with multiuser session!")
        else:
            print("\n⚠ Peek output might not show recent commands")
    else:
        print(f"   Error: {response}")
    
    # List sessions to see multiuser status
    print("\n7. Listing sessions...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "list_sessions",
            "arguments": {}
        }
    })
    
    if "result" in response:
        sessions_output = response["result"]["content"][0]["text"]
        print(f"   Sessions:\n{sessions_output}")
        
        # Check if multiuser session is listed
        if "multiuser-test" in sessions_output:
            print("\n✓ Multiuser session is listed!")
        else:
            print("\n⚠ Session not found in list")
    else:
        print(f"   Error: {response}")
    
    # Clean up
    print("\n8. Cleaning up...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 8,
        "method": "tools/call",
        "params": {
            "name": "kill_session",
            "arguments": {"session": "multiuser-test"}
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    await browser.close()


if __name__ == "__main__":
    asyncio.run(test_screen_multiuser())