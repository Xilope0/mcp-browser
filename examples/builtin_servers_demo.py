#!/usr/bin/env python3
"""
Demonstration of MCP Browser with built-in servers.

Shows how the built-in servers (screen, memory, patterns, onboarding)
are automatically available and can be used through the unified interface.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_browser import MCPBrowser


async def demo_builtin_servers():
    """Demonstrate built-in server functionality."""
    
    print("=== MCP Browser Built-in Servers Demo ===\n")
    print("This demo shows the 4 built-in servers that start automatically:")
    print("- Screen: GNU screen session management")
    print("- Memory: Persistent project memory")
    print("- Patterns: Auto-response patterns")
    print("- Onboarding: Identity-aware onboarding")
    print("\n" + "-" * 60 + "\n")
    
    # Create browser with built-in servers only (no external server)
    browser = MCPBrowser(server_name="builtin-only")
    
    try:
        await browser.initialize()
        print("✓ MCP Browser initialized with built-in servers\n")
        
        # 1. Test Onboarding (directly available in sparse mode)
        print("1. ONBOARDING DEMONSTRATION")
        print("-" * 40)
        
        # First, get onboarding for a new identity
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": "onboard-1",
            "method": "tools/call",
            "params": {
                "name": "onboarding",
                "arguments": {
                    "identity": "DemoAssistant"
                }
            }
        })
        
        print("Getting onboarding for 'DemoAssistant':")
        if "result" in response:
            text = response["result"]["content"][0]["text"]
            print(text[:300] + "...\n")
        
        # Set onboarding instructions
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": "onboard-2",
            "method": "tools/call",
            "params": {
                "name": "onboarding",
                "arguments": {
                    "identity": "DemoAssistant",
                    "instructions": "Welcome back! Remember:\n- You're helping with the MCP Browser project\n- Focus on simplicity and clarity\n- The user prefers concise responses"
                }
            }
        })
        
        print("✓ Set onboarding instructions for DemoAssistant\n")
        
        # 2. Discover available tools
        print("\n2. DISCOVERING BUILT-IN TOOLS")
        print("-" * 40)
        
        # Use mcp_discover to find all tools
        all_tools = browser.discover("$.tools[*].name")
        print(f"Total tools available: {len(all_tools) if all_tools else 0}")
        
        # Group by server
        tool_groups = {}
        for tool in all_tools or []:
            if "::" in tool:
                server, tool_name = tool.split("::", 1)
                if server not in tool_groups:
                    tool_groups[server] = []
                tool_groups[server].append(tool_name)
        
        for server, tools in tool_groups.items():
            print(f"\n{server}:")
            for tool in tools[:3]:  # Show first 3
                print(f"  - {tool}")
            if len(tools) > 3:
                print(f"  ... and {len(tools) - 3} more")
        
        # 3. Use Memory server
        print("\n\n3. MEMORY SERVER DEMONSTRATION")
        print("-" * 40)
        
        # Add a task
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": "mem-1",
            "method": "tools/call",
            "params": {
                "name": "mcp_call",
                "arguments": {
                    "method": "tools/call",
                    "params": {
                        "name": "builtin:memory::task_add",
                        "arguments": {
                            "content": "Complete MCP Browser documentation",
                            "priority": "high"
                        }
                    }
                }
            }
        })
        
        print("Added task to memory")
        
        # Get memory summary
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": "mem-2",
            "method": "tools/call",
            "params": {
                "name": "mcp_call",
                "arguments": {
                    "method": "tools/call",
                    "params": {
                        "name": "builtin:memory::memory_summary",
                        "arguments": {}
                    }
                }
            }
        })
        
        if "result" in response:
            print("\nMemory Summary:")
            print(response["result"]["content"][0]["text"][:200] + "...")
        
        # 4. Use Screen server
        print("\n\n4. SCREEN SERVER DEMONSTRATION")
        print("-" * 40)
        
        # List sessions
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": "screen-1",
            "method": "tools/call",
            "params": {
                "name": "mcp_call",
                "arguments": {
                    "method": "tools/call",
                    "params": {
                        "name": "builtin:screen::list_sessions",
                        "arguments": {}
                    }
                }
            }
        })
        
        if "result" in response:
            print("Screen sessions:")
            print(response["result"]["content"][0]["text"])
        
        # 5. Pattern Manager
        print("\n\n5. PATTERN MANAGER DEMONSTRATION")
        print("-" * 40)
        
        # Add a pattern
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": "pattern-1",
            "method": "tools/call",
            "params": {
                "name": "mcp_call",
                "arguments": {
                    "method": "tools/call",
                    "params": {
                        "name": "builtin:patterns::add_pattern",
                        "arguments": {
                            "trigger": ["Continue?", "(y/n)"],
                            "response": "y",
                            "description": "Auto-confirm continue prompts"
                        }
                    }
                }
            }
        })
        
        print("✓ Added auto-response pattern for continue prompts")
        
        # List patterns
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": "pattern-2",
            "method": "tools/call",
            "params": {
                "name": "mcp_call",
                "arguments": {
                    "method": "tools/call",
                    "params": {
                        "name": "builtin:patterns::list_patterns",
                        "arguments": {}
                    }
                }
            }
        })
        
        if "result" in response:
            print("\nActive patterns:")
            print(response["result"]["content"][0]["text"][:200] + "...")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser.close()
        print("\n\n✓ MCP Browser closed")


if __name__ == "__main__":
    print("\nNote: This demo uses built-in Python MCP servers.")
    print("Make sure Python 3.8+ is available.\n")
    
    # Check for screen if on Linux/Mac
    import platform
    if platform.system() != "Windows":
        import subprocess
        try:
            subprocess.run(["screen", "--version"], capture_output=True, check=True)
        except:
            print("Warning: GNU screen not installed. Screen server features won't work.")
            print("Install with: sudo apt-get install screen (Ubuntu) or brew install screen (Mac)\n")
    
    asyncio.run(demo_builtin_servers())