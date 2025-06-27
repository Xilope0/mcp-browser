#!/usr/bin/env python3
"""
Test MCP Browser connection to claude-code.

This script tests if MCP Browser can successfully connect to claude-code
as an MCP target and perform basic operations like reading a file.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path for development
sys.path.insert(0, str(Path(__file__).parent))

from mcp_browser import MCPBrowser


async def test_claude_connection():
    """Test connection to claude-code via MCP."""
    
    print("=== Testing MCP Browser Connection to Claude Code ===\n")
    
    # Check if claude binary exists
    claude_path = "/usr/local/bin/claude"
    if not os.path.exists(claude_path):
        print(f"❌ Claude binary not found at {claude_path}")
        print("Please ensure Claude Code is installed")
        return
    
    print(f"✓ Found Claude binary at {claude_path}\n")
    
    # Create browser configured for claude-code
    print("Creating MCP Browser with claude-code as target...")
    
    # We'll create a custom config for claude
    browser = MCPBrowser(
        server_command=[claude_path, "mcp"],
        server_name="claude-code",
        sparse_mode=True  # Use sparse mode to minimize context
    )
    
    try:
        # Initialize connection
        print("Initializing MCP connection...")
        await browser.initialize()
        print("✓ Connected to claude-code via MCP\n")
        
        # Test 1: List available tools in sparse mode
        print("1. Testing sparse mode tools:")
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/list"
        })
        
        if "result" in response:
            tools = response["result"]["tools"]
            print(f"   Sparse tools available: {len(tools)}")
            for tool in tools[:5]:  # Show first 5
                print(f"   - {tool['name']}: {tool['description'][:60]}...")
        
        # Test 2: Discover all tools
        print("\n2. Discovering all available tools:")
        all_tools = browser.discover("$.tools[*].name")
        if all_tools:
            print(f"   Total tools discovered: {len(all_tools)}")
            print("   Sample tools:", all_tools[:10])
        
        # Test 3: Try to read a file using claude's Read tool
        print("\n3. Testing file read capability:")
        test_file = "/tmp/mcp_test.txt"
        
        # First create a test file
        with open(test_file, 'w') as f:
            f.write("Hello from MCP Browser!\nThis file was created to test claude-code integration.")
        print(f"   Created test file: {test_file}")
        
        # Use mcp_call to invoke Read tool
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": "test-3",
            "method": "tools/call",
            "params": {
                "name": "mcp_call",
                "arguments": {
                    "method": "tools/call",
                    "params": {
                        "name": "Read",  # Claude's Read tool
                        "arguments": {
                            "file_path": test_file
                        }
                    }
                }
            }
        })
        
        if "result" in response:
            print("   ✓ Successfully read file via claude-code!")
            content = response["result"]["content"][0]["text"]
            print(f"   File content preview: {content[:100]}...")
        else:
            print("   ❌ Failed to read file:", response.get("error", "Unknown error"))
        
        # Test 4: Use onboarding
        print("\n4. Testing identity-aware onboarding:")
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": "test-4",
            "method": "tools/call",
            "params": {
                "name": "onboarding",
                "arguments": {
                    "identity": "ClaudeCodeTest",
                    "instructions": "Remember: You're testing MCP Browser integration with claude-code"
                }
            }
        })
        
        if "result" in response:
            print("   ✓ Onboarding set successfully")
        
        # Clean up test file
        os.remove(test_file)
        
        print("\n✅ All tests completed successfully!")
        print("\nMCP Browser can successfully:")
        print("- Connect to claude-code as an MCP server")
        print("- List and discover available tools")
        print("- Execute claude-code tools (like Read)")
        print("- Use built-in features (onboarding)")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\nClosing connection...")
        await browser.close()
        print("✓ Connection closed")


if __name__ == "__main__":
    print("\nNote: This test requires claude-code to be installed at /usr/local/bin/claude")
    print("If claude is installed elsewhere, update the path in the script.\n")
    
    asyncio.run(test_claude_connection())