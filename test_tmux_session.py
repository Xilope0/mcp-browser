#!/usr/bin/env python3
"""Test tmux session functionality."""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_browser import MCPBrowser


async def test_tmux_session():
    """Test tmux session functionality."""
    browser = MCPBrowser(enable_builtin_servers=True)
    
    await browser.initialize()
    
    print("=== Testing Tmux Session Functionality ===\n")
    
    # Create a test session
    print("1. Creating test session...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "builtin:tmux::create_session",
            "arguments": {
                "name": "tmux-test",
                "command": "bash"
            }
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    # Execute a command in the session
    print("\n2. Executing command in session...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "builtin:tmux::execute",
            "arguments": {
                "session": "tmux-test",
                "command": "echo 'Tmux session test - Hello World!'"
            }
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    # Wait a moment for output
    await asyncio.sleep(0.5)
    
    # Test peek functionality
    print("\n3. Testing peek functionality...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "builtin:tmux::peek",
            "arguments": {
                "session": "tmux-test",
                "lines": 10
            }
        }
    })
    
    if "result" in response:
        output = response["result"]["content"][0]["text"]
        print(f"   Output:\n{output}")
        
        # Check if we can see the executed command output
        if "Tmux session test" in output:
            print("\n✓ Peek works correctly!")
        else:
            print("\n⚠ Peek output might not show recent commands")
    else:
        print(f"   Error: {response}")
    
    # List sessions
    print("\n4. Listing sessions...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "builtin:tmux::list_sessions",
            "arguments": {}
        }
    })
    
    if "result" in response:
        sessions_output = response["result"]["content"][0]["text"]
        print(f"   Sessions:\n{sessions_output}")
        
        # Check if session is listed
        if "tmux-test" in sessions_output:
            print("\n✓ Tmux session is listed!")
        else:
            print("\n⚠ Session not found in list")
    else:
        print(f"   Error: {response}")
    
    # Get attach instructions
    print("\n5. Getting attach instructions...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "builtin:tmux::attach_session",
            "arguments": {
                "session": "tmux-test"
            }
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    # Test share instructions
    print("\n6. Getting share instructions...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "builtin:tmux::share_session",
            "arguments": {
                "session": "tmux-test"
            }
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    # Clean up
    print("\n7. Cleaning up...")
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "builtin:tmux::kill_session",
            "arguments": {"session": "tmux-test"}
        }
    })
    print(f"   Result: {response.get('result', {}).get('content', [{}])[0].get('text', 'Error')}")
    
    await browser.close()


if __name__ == "__main__":
    asyncio.run(test_tmux_session())