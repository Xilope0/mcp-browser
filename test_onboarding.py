#!/usr/bin/env python3
"""
Quick test of the onboarding functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_browser import MCPBrowser


async def test_onboarding():
    """Test onboarding functionality."""
    
    print("Testing MCP Browser Onboarding...\n")
    
    # Create browser with only built-in servers
    browser = MCPBrowser(server_name="builtin-only")
    
    try:
        await browser.initialize()
        print("✓ Browser initialized\n")
        
        # Test 1: Get onboarding for new identity
        print("1. Getting onboarding for 'TestBot':")
        response = await browser.call({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "onboarding",
                "arguments": {
                    "identity": "TestBot"
                }
            }
        })
        
        if "result" in response:
            content = response["result"]["content"][0]["text"]
            print(content[:200] + "...\n")
        
        # Test 2: Set onboarding
        print("2. Setting onboarding instructions:")
        response = await browser.call({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "onboarding",
                "arguments": {
                    "identity": "TestBot",
                    "instructions": "You are TestBot. Your primary goals:\n- Be helpful\n- Be concise\n- Remember context"
                }
            }
        })
        
        if "result" in response:
            print("✓ Instructions set\n")
        
        # Test 3: Retrieve onboarding
        print("3. Retrieving onboarding:")
        response = await browser.call({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "onboarding",
                "arguments": {
                    "identity": "TestBot"
                }
            }
        })
        
        if "result" in response:
            content = response["result"]["content"][0]["text"]
            print(content)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser.close()
        print("\n✓ Test complete")


if __name__ == "__main__":
    asyncio.run(test_onboarding())