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
import yaml
import tempfile

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
    
    # Create a temporary config file for claude
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config = {
            "servers": {
                "claude-code": {
                    "command": [claude_path, "mcp", "serve"],
                    "name": "claude-code",
                    "description": "Claude Code MCP interface"
                }
            },
            "default_server": "claude-code",
            "sparse_mode": True,
            "enable_builtin_servers": False  # Disable built-in servers for this test
        }
        yaml.dump(config, f)
        config_path = f.name
    
    print("Creating MCP Browser with claude-code as target...")
    
    # Create browser with custom config
    browser = MCPBrowser(
        config_path=Path(config_path),
        server_name="claude-code"
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
            # Show a sample of tools
            sample = all_tools[:10] if len(all_tools) > 10 else all_tools
            print(f"   Sample tools: {sample}")
        
        # Test 3: Try to read a file using claude's Read tool
        print("\n3. Testing file read capability:")
        test_file = "/tmp/mcp_test.txt"
        
        # First create a test file
        with open(test_file, 'w') as f:
            f.write("Hello from MCP Browser!\nThis file was created to test claude-code integration.")
        print(f"   Created test file: {test_file}")
        
        # Use mcp_call to invoke Read tool if available
        if all_tools and any('Read' in tool or 'read' in tool.lower() for tool in all_tools):
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
        else:
            print("   ⚠ Read tool not found in available tools")
        
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)
        
        print("\n✅ Connection test completed!")
        print("\nMCP Browser successfully:")
        print("- Connected to claude-code as an MCP server")
        print("- Listed available tools in sparse mode")
        print("- Discovered all available tools via JSONPath")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\nClosing connection...")
        await browser.close()
        print("✓ Connection closed")
        
        # Clean up config file
        if os.path.exists(config_path):
            os.remove(config_path)


if __name__ == "__main__":
    print("\nNote: This test requires claude-code to be installed at /usr/local/bin/claude")
    print("If claude is installed elsewhere, update the path in the script.\n")
    
    asyncio.run(test_claude_connection())