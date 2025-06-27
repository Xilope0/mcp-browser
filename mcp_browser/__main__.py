#!/usr/bin/env python3
"""
MCP Browser command-line interface.
"""

import sys
import asyncio
import argparse
import json
from pathlib import Path

from .proxy import MCPBrowser


async def interactive_mode(browser: MCPBrowser):
    """Run MCP Browser in interactive mode."""
    print("MCP Browser Interactive Mode")
    print("Type 'help' for commands, 'exit' to quit\n")
    
    while True:
        try:
            command = input("> ").strip()
            
            if command == "exit":
                break
            elif command == "help":
                print("\nCommands:")
                print("  list              - List available tools (sparse mode)")
                print("  discover <path>   - Discover tools using JSONPath") 
                print("  call <json>       - Execute JSON-RPC call")
                print("  onboard <id>      - Get onboarding for identity")
                print("  exit              - Exit interactive mode")
                print("\nExamples:")
                print('  discover $.tools[*].name')
                print('  call {"method": "tools/list"}')
                print('  onboard MyProject')
                continue
                
            elif command.startswith("discover "):
                jsonpath = command[9:]
                result = browser.discover(jsonpath)
                print(json.dumps(result, indent=2))
                
            elif command.startswith("call "):
                json_str = command[5:]
                request = json.loads(json_str)
                if "jsonrpc" not in request:
                    request["jsonrpc"] = "2.0"
                response = await browser.call(request)
                print(json.dumps(response, indent=2))
                
            elif command.startswith("onboard "):
                identity = command[8:]
                response = await browser.call({
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "onboarding",
                        "arguments": {"identity": identity}
                    }
                })
                if "result" in response:
                    print(response["result"]["content"][0]["text"])
                    
            elif command == "list":
                response = await browser.call({
                    "jsonrpc": "2.0",
                    "method": "tools/list"
                })
                if "result" in response:
                    tools = response["result"]["tools"]
                    for tool in tools:
                        print(f"- {tool['name']}: {tool['description']}")
                        
            else:
                print("Unknown command. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            print("\nUse 'exit' to quit")
        except Exception as e:
            print(f"Error: {e}")


async def run_server_mode(browser: MCPBrowser):
    """Run MCP Browser as an MCP server (stdin/stdout)."""
    import sys
    
    await browser.initialize()
    
    # Read JSON-RPC from stdin, write to stdout
    buffer = ""
    while True:
        try:
            chunk = sys.stdin.read(4096)
            if not chunk:
                break
                
            buffer += chunk
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if line.strip():
                    try:
                        request = json.loads(line)
                        response = await browser.call(request)
                        print(json.dumps(response))
                        sys.stdout.flush()
                    except json.JSONDecodeError:
                        pass
                        
        except KeyboardInterrupt:
            break
        except EOFError:
            break


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MCP Browser - Generic MCP interface")
    parser.add_argument("--server", "-s", help="Target MCP server name")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument("--mode", choices=["interactive", "server"], 
                       default="interactive", help="Operating mode")
    parser.add_argument("--no-sparse", action="store_true", 
                       help="Disable sparse mode")
    parser.add_argument("--no-builtin", action="store_true",
                       help="Disable built-in servers")
    
    args = parser.parse_args()
    
    # Create browser
    config_path = Path(args.config) if args.config else None
    browser = MCPBrowser(
        server_name=args.server,
        config_path=config_path,
        enable_builtin_servers=not args.no_builtin
    )
    
    # Run in appropriate mode
    if args.mode == "server":
        asyncio.run(run_server_mode(browser))
    else:
        asyncio.run(async_main(browser))


async def async_main(browser: MCPBrowser):
    """Async main for interactive mode."""
    try:
        await browser.initialize()
        await interactive_mode(browser)
    finally:
        await browser.close()


if __name__ == "__main__":
    main()