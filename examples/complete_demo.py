#!/usr/bin/env python3
"""
Complete demonstration of MCP Browser functionality.

This example shows:
1. How sparse mode reduces context
2. Tool discovery using JSONPath
3. Tool execution via mcp_call
4. Direct JSON-RPC calls

Working Directory:
  Run this example from any directory. MCP servers will inherit
  the working directory from where you run this script.
  
  $ cd /your/project
  $ python /path/to/complete_demo.py
  
Note: Always use absolute paths when passing file arguments to tools.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_browser import MCPBrowser


async def demonstrate_mcp_browser():
    """Complete demonstration of MCP Browser features."""
    
    print("=== MCP Browser Complete Demo ===\n")
    print("This demo shows how MCP Browser provides full MCP access")
    print("through just 2 methods: call() and discover()\n")
    print("-" * 60)
    
    # Initialize browser with debug mode for visibility
    browser = MCPBrowser()
    browser.config_loader.DEFAULT_CONFIG["debug"] = True
    
    try:
        await browser.initialize()
        print("\n✓ MCP Browser initialized\n")
        
        # 1. Show sparse mode in action
        print("\n1. SPARSE MODE DEMONSTRATION")
        print("-" * 40)
        
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": "sparse-demo",
            "method": "tools/list",
            "params": {}
        })
        
        if "result" in response:
            tools = response["result"]["tools"]
            print(f"Initial tools exposed: {len(tools)}")
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description'][:50]}...")
            
            # Show actual tool count
            actual_count = len(browser.registry.tools)
            print(f"\nActual tools available: {actual_count}")
            print(f"Context saved: {actual_count - len(tools)} tool descriptions hidden")
        
        # 2. Demonstrate discovery
        print("\n\n2. TOOL DISCOVERY DEMONSTRATION")
        print("-" * 40)
        
        # Get all tool names
        print("\n→ Discovering all tool names:")
        tool_names = browser.discover("$.tools[*].name")
        if tool_names:
            print(f"  Found {len(tool_names)} tools: {', '.join(tool_names[:5])}...")
        
        # Find specific tools
        print("\n→ Finding tools with 'memory' in name:")
        memory_tools = browser.discover("$.tools[?(@.name =~ /.*memory.*/i)]")
        if memory_tools:
            for tool in memory_tools:
                print(f"  - {tool['name']}")
        
        # Get tool schema
        print("\n→ Getting schema for a specific tool:")
        schema = browser.discover("$.tools[0].inputSchema")
        if schema:
            print(f"  Schema type: {schema.get('type', 'unknown')}")
            if 'properties' in schema:
                print(f"  Properties: {list(schema['properties'].keys())}")
        
        # 3. Demonstrate tool execution
        print("\n\n3. TOOL EXECUTION DEMONSTRATION")
        print("-" * 40)
        
        # First, discover available tools to find one we can call
        first_tool = browser.discover("$.tools[0]")
        if first_tool:
            tool_name = first_tool["name"]
            print(f"\n→ Executing '{tool_name}' tool via mcp_call:")
            
            # Prepare arguments based on schema
            args = {}
            if "inputSchema" in first_tool:
                schema = first_tool["inputSchema"]
                if schema.get("type") == "object" and "properties" in schema:
                    # Create minimal valid arguments
                    for prop, prop_schema in schema["properties"].items():
                        if prop in schema.get("required", []):
                            if prop_schema.get("type") == "string":
                                args[prop] = "test"
                            elif prop_schema.get("type") == "number":
                                args[prop] = 0
                            elif prop_schema.get("type") == "boolean":
                                args[prop] = False
            
            response = await browser.call({
                "jsonrpc": "2.0",
                "id": "exec-demo",
                "method": "tools/call",
                "params": {
                    "name": "mcp_call",
                    "arguments": {
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": args
                        }
                    }
                }
            })
            
            if "result" in response:
                print("  ✓ Tool executed successfully")
                result_preview = str(response["result"])[:100]
                print(f"  Result preview: {result_preview}...")
            else:
                print(f"  ✗ Error: {response.get('error', {}).get('message', 'Unknown')}")
        
        # 4. Direct JSON-RPC demonstration
        print("\n\n4. DIRECT JSON-RPC DEMONSTRATION")
        print("-" * 40)
        
        print("\n→ Sending custom JSON-RPC request:")
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": "custom",
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {
                    "name": "mcp-browser-demo",
                    "version": "1.0"
                }
            }
        })
        
        if "result" in response:
            print("  ✓ Custom request successful")
            print(f"  Server info: {response['result'].get('serverInfo', {})}")
        
        # 5. Show AI-optimized usage pattern
        print("\n\n5. AI-OPTIMIZED USAGE PATTERN")
        print("-" * 40)
        
        print("\nFor AI systems, the entire MCP protocol is accessible via:")
        print("\n  # Execute any operation")
        print("  response = await browser.call(jsonrpc_object)")
        print("\n  # Discover tools and schemas")  
        print("  info = browser.discover(jsonpath_query)")
        print("\nThis minimal API provides full functionality with minimal context!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
    finally:
        await browser.close()
        print("\n✓ MCP Browser closed")


if __name__ == "__main__":
    print("\nNote: This demo requires an MCP server to be configured.")
    print("Edit config/default.yaml or create ~/.mcp-browser/config.yaml")
    print("to configure your MCP server.\n")
    
    asyncio.run(demonstrate_mcp_browser())