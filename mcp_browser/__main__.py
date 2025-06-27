#!/usr/bin/env python3
"""
MCP Browser command-line interface.
"""

import sys
import asyncio
import argparse
import json
from pathlib import Path
from typing import Optional
import yaml

from .proxy import MCPBrowser
from .config import ConfigLoader
from .default_configs import ConfigManager


async def interactive_mode(browser: MCPBrowser):
    """Run MCP Browser in interactive mode."""
    print("MCP Browser Interactive Mode")
    print("=" * 50)
    print(f"Server: {browser._server_name or browser.config.default_server}")
    print(f"Sparse mode: {'enabled' if browser.config.sparse_mode else 'disabled'}")
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
                print("  onboard [<id>]    - Show/set onboarding for identity")
                print("  reload            - Reload configuration")
                print("  status            - Show connection status")
                print("  exit              - Exit interactive mode")
                print("\nExamples:")
                print('  discover $.tools[*].name               # Get all tool names')
                print('  discover $.tools[0].inputSchema        # Get first tool schema')
                print('  call {"method": "tools/list"}          # Raw JSON-RPC call')
                print('  onboard MyProject                      # Get project onboarding')
                print('\nJSONPath syntax:')
                print('  $                 - Root object')
                print('  .tools[*]         - All tools')
                print('  .tools[0]         - First tool')
                print('  .tools[*].name    - All tool names')
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


def show_available_servers(config_path: Optional[str] = None):
    """Show list of available MCP servers from configuration."""
    loader = ConfigLoader(Path(config_path) if config_path else None)
    config = loader.load()
    
    print("Available MCP Servers:")
    print("=" * 50)
    
    for name, server in config.servers.items():
        print(f"\n{name}:")
        print(f"  Description: {server.description or 'No description'}")
        print(f"  Command: {' '.join(server.command) if server.command else 'Built-in only'}")
        if server.env:
            print(f"  Environment: {', '.join(server.env.keys())}")
    
    print(f"\nDefault server: {config.default_server}")
    print(f"Config location: {loader.config_path}")


def show_configuration(config_path: Optional[str] = None):
    """Show current configuration file path and content."""
    loader = ConfigLoader(Path(config_path) if config_path else None)
    
    print(f"Configuration file: {loader.config_path}")
    print("=" * 50)
    
    if loader.config_path.exists():
        with open(loader.config_path) as f:
            print(f.read())
    else:
        print("Configuration file not found. Will be created on first run.")


async def test_server_connection(browser: MCPBrowser, server_name: Optional[str] = None):
    """Test connection to specified MCP server."""
    print(f"Testing connection to server: {server_name or 'default'}")
    print("=" * 50)
    
    try:
        await browser.initialize()
        print("✓ Successfully connected to server")
        
        # Try to list tools
        response = await browser.call({
            "jsonrpc": "2.0",
            "method": "tools/list"
        })
        
        if "result" in response:
            tools = response["result"]["tools"]
            print(f"✓ Server provides {len(tools)} tools")
            if browser.config.sparse_mode:
                print("  (Showing sparse tools only)")
        else:
            print("✗ Failed to list tools")
            
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    finally:
        await browser.close()
    
    print("\nConnection test completed successfully!")


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
    parser = argparse.ArgumentParser(
        description="MCP Browser - Universal Model Context Protocol Interface",
        epilog="""
Examples:
  mcp-browser                          # Start interactive mode with default server
  mcp-browser --server brave-search    # Use Brave Search server
  mcp-browser --list-servers           # List configured servers
  mcp-browser --show-config            # Show current configuration
  mcp-browser --mode server            # Run as MCP server (stdin/stdout)
  
Configuration:
  Default config: ~/.claude/mcp-browser/config.yaml
  First run creates default configuration with examples
  
Environment:
  Set API keys as needed: BRAVE_API_KEY, GITHUB_TOKEN, etc.
  Or source from: source ~/.secrets/api-keys.sh
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--server", "-s", help="Target MCP server name (see --list-servers)")
    parser.add_argument("--config", "-c", help="Custom configuration file path")
    parser.add_argument("--mode", choices=["interactive", "server"], 
                       default="interactive", help="Operating mode (default: interactive)")
    parser.add_argument("--no-sparse", action="store_true", 
                       help="Disable sparse mode (show all tools)")
    parser.add_argument("--no-builtin", action="store_true",
                       help="Disable built-in servers (screen, memory, patterns)")
    parser.add_argument("--list-servers", action="store_true",
                       help="List available MCP servers from config")
    parser.add_argument("--show-config", action="store_true",
                       help="Show current configuration path and content")
    parser.add_argument("--test", action="store_true",
                       help="Test connection to specified server")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    
    args = parser.parse_args()
    
    # Handle special commands first
    if args.list_servers:
        show_available_servers(args.config)
        return
    
    if args.show_config:
        show_configuration(args.config)
        return
    
    # Create browser
    config_path = Path(args.config) if args.config else None
    browser = MCPBrowser(
        server_name=args.server,
        config_path=config_path,
        enable_builtin_servers=not args.no_builtin
    )
    
    # Handle test mode
    if args.test:
        asyncio.run(test_server_connection(browser, args.server))
        return
    
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