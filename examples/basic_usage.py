"""
Basic usage example for MCP Browser.

Demonstrates the minimal API: call() and discover()
"""

import asyncio
import json
from mcp_browser import MCPBrowser


async def main():
    # Create browser instance
    async with MCPBrowser() as browser:
        print("=== MCP Browser Basic Usage ===\n")
        
        # 1. List available tools (sparse mode active)
        print("1. Listing tools (sparse mode):")
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        })
        
        if "result" in response:
            tools = response["result"]["tools"]
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description'][:60]}...")
        
        # 2. Discover all actual tools using JSONPath
        print("\n2. Discovering all tool names:")
        tool_names = browser.discover("$.tools[*].name")
        print(f"  Found {len(tool_names) if tool_names else 0} tools")
        if tool_names:
            print(f"  First 5: {tool_names[:5]}")
        
        # 3. Get details for a specific tool
        print("\n3. Getting details for a specific tool:")
        bash_tool = browser.discover("$.tools[?(@.name=='Bash')]")
        if bash_tool:
            print(f"  Bash tool schema:")
            print(json.dumps(bash_tool[0] if isinstance(bash_tool, list) else bash_tool, indent=2)[:200] + "...")
        
        # 4. Use mcp_call to execute a tool
        print("\n4. Executing a tool via mcp_call:")
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "mcp_call",
                "arguments": {
                    "method": "tools/call",
                    "params": {
                        "name": "echo",  # Assuming echo tool exists
                        "arguments": {
                            "message": "Hello from MCP Browser!"
                        }
                    }
                }
            }
        })
        
        if "result" in response:
            print("  Success:", response["result"])
        else:
            print("  Error:", response.get("error", {}).get("message"))
        
        # 5. Direct JSON-RPC call
        print("\n5. Direct JSON-RPC call:")
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "ping",  # If server supports ping
            "params": {}
        })
        print("  Response:", response)


if __name__ == "__main__":
    asyncio.run(main())