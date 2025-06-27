#!/usr/bin/env python3
"""
MCP Browser command-line interface.
"""

import os
import sys
import asyncio
import argparse
import json
import signal
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

from .proxy import MCPBrowser
from .config import ConfigLoader
from .default_configs import ConfigManager
from .daemon import MCPBrowserDaemon, MCPBrowserClient, get_socket_path, is_daemon_running
from .logging_config import setup_logging, get_logger


def build_mcp_request(args) -> Dict[str, Any]:
    """Build JSON-RPC request from command line arguments."""
    if args.command == "tools-list":
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
    
    elif args.command == "tools-call":
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": args.name,
                "arguments": json.loads(args.arguments)
            }
        }
    
    elif args.command == "resources-list":
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/list",
            "params": {}
        }
    
    elif args.command == "resources-read":
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {
                "uri": args.uri
            }
        }
    
    elif args.command == "prompts-list":
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "prompts/list",
            "params": {}
        }
    
    elif args.command == "prompts-get":
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "prompts/get",
            "params": {
                "name": args.name,
                "arguments": json.loads(args.arguments)
            }
        }
    
    elif args.command == "completion":
        params = {}
        if args.ref:
            params["ref"] = {"type": "ref/resource", "uri": args.ref}
        if args.argument:
            params["argument"] = args.argument
            
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "completion/complete",
            "params": params
        }
    
    elif args.command == "jsonrpc":
        request = json.loads(args.request)
        if "jsonrpc" not in request:
            request["jsonrpc"] = "2.0"
        if "id" not in request:
            request["id"] = 1
        return request
    
    else:
        raise ValueError(f"Unknown command: {args.command}")


def format_mcp_response(args, request: Dict[str, Any], response: Dict[str, Any]):
    """Format and print MCP response based on command."""
    logger = get_logger(__name__)
    if args.debug:
        logger.debug(f"Request: {json.dumps(request)}")
        logger.debug(f"Response: {json.dumps(response)}")
    
    # Format output based on command
    if args.command == "tools-list" and "result" in response:
        tools = response["result"].get("tools", [])
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
    
    elif args.command == "tools-call" and "result" in response:
        # Format tool response
        result = response["result"]
        if "content" in result:
            for content in result["content"]:
                if content.get("type") == "text":
                    print(content.get("text", ""))
                else:
                    print(json.dumps(content, indent=2))
        else:
            print(json.dumps(result, indent=2))
    
    elif args.command == "resources-list" and "result" in response:
        resources = response["result"].get("resources", [])
        print(f"Found {len(resources)} resources:")
        for res in resources:
            print(f"  - {res['uri']}: {res.get('name', 'Unnamed')}")
    
    elif args.command == "prompts-list" and "result" in response:
        prompts = response["result"].get("prompts", [])
        print(f"Found {len(prompts)} prompts:")
        for prompt in prompts:
            print(f"  - {prompt['name']}: {prompt.get('description', 'No description')}")
    
    elif args.command == "jsonrpc":
        # For raw JSON-RPC, output the full response as JSON
        print(json.dumps(response))
    
    else:
        # Default: pretty print result
        if "result" in response:
            print(json.dumps(response["result"], indent=2))
        elif "error" in response:
            print(f"Error: {response['error'].get('message', 'Unknown error')}")
            if args.debug:
                logger.debug(f"Error details: {json.dumps(response['error'])}")
        else:
            print(json.dumps(response, indent=2))


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


async def handle_mcp_command(args):
    """Handle MCP method commands by simulating JSON-RPC calls."""
    # Check if we should use daemon mode
    socket_path = get_socket_path(args.server)
    
    if hasattr(args, 'use_daemon') and args.use_daemon and is_daemon_running(socket_path):
        # Use daemon client
        async with MCPBrowserClient(socket_path) as client:
            request = build_mcp_request(args)
            response = await client.call(request)
            format_mcp_response(args, request, response)
        return
    
    # Create browser directly
    config_path = Path(args.config) if args.config else None
    
    # Set debug in config if requested
    if args.debug and config_path is None:
        from .config import ConfigLoader
        loader = ConfigLoader()
        config = loader.load()
        config.debug = True
    
    browser = MCPBrowser(
        server_name=args.server,
        config_path=config_path,
        enable_builtin_servers=not args.no_builtin
    )
    
    try:
        await browser.initialize()
        
        # Build and send request
        request = build_mcp_request(args)
        response = await browser.call(request)
        
        # Format response
        format_mcp_response(args, request, response)
        
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc(file=sys.stderr)
    finally:
        await browser.close()


async def run_daemon_mode(browser: MCPBrowser, socket_path: Path):
    """Run MCP Browser in daemon mode."""
    daemon = MCPBrowserDaemon(browser, socket_path)
    await daemon.start()


async def start_daemon_background(args):
    """Start daemon in background."""
    socket_path = get_socket_path(args.server)
    
    if is_daemon_running(socket_path):
        print(f"Daemon already running for server: {args.server or 'default'}")
        return
    
    # Fork to background
    pid = os.fork()
    if pid > 0:
        # Parent process
        print(f"Starting daemon in background (PID: {pid})")
        return
    
    # Child process
    # Detach from terminal
    os.setsid()
    
    # Redirect stdout/stderr to log file
    log_dir = socket_path.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"mcp-browser-{args.server or 'default'}.log"
    
    with open(log_file, 'a') as log:
        sys.stdout = log
        sys.stderr = log
        
        # Create browser
        config_path = Path(args.config) if args.config else None
        browser = MCPBrowser(
            server_name=args.server,
            config_path=config_path,
            enable_builtin_servers=not args.no_builtin
        )
        
        # Run daemon
        asyncio.run(run_daemon_mode(browser, socket_path))


def stop_daemon(args):
    """Stop running daemon."""
    socket_path = get_socket_path(args.server)
    
    if not is_daemon_running(socket_path):
        print(f"No daemon running for server: {args.server or 'default'}")
        return
    
    pid_file = socket_path.with_suffix('.pid')
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to daemon (PID: {pid})")
    except Exception as e:
        print(f"Error stopping daemon: {e}")


def show_daemon_status(args):
    """Show daemon status."""
    socket_path = get_socket_path(args.server)
    
    if is_daemon_running(socket_path):
        pid_file = socket_path.with_suffix('.pid')
        pid = pid_file.read_text().strip()
        print(f"Daemon running (PID: {pid})")
        print(f"Socket: {socket_path}")
    else:
        print(f"No daemon running for server: {args.server or 'default'}")


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


async def run_server_mode_with_daemon(socket_path: Path):
    """Run as MCP server but forward to daemon."""
    import sys
    
    async with MCPBrowserClient(socket_path) as client:
        # Read JSON-RPC from stdin, forward to daemon, write to stdout
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
                            response = await client.call(request)
                            print(json.dumps(response))
                            sys.stdout.flush()
                        except json.JSONDecodeError:
                            pass
                            
            except KeyboardInterrupt:
                break
            except EOFError:
                break


async def interactive_mode_with_daemon(socket_path: Path):
    """Run interactive mode connected to daemon."""
    async with MCPBrowserClient(socket_path) as client:
        print("MCP Browser Interactive Mode (Daemon)")
        print("=" * 50)
        print(f"Connected to daemon at: {socket_path}")
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
                    print("  exit              - Exit interactive mode")
                    continue
                    
                elif command.startswith("call "):
                    json_str = command[5:]
                    request = json.loads(json_str)
                    if "jsonrpc" not in request:
                        request["jsonrpc"] = "2.0"
                    if "id" not in request:
                        request["id"] = 1
                    response = await client.call(request)
                    print(json.dumps(response, indent=2))
                    
                elif command == "list":
                    response = await client.call({
                        "jsonrpc": "2.0",
                        "id": 1,
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


def main():
    """Main entry point."""
    # Parse args first to check for log configuration
    args_parser = argparse.ArgumentParser(add_help=False)
    args_parser.add_argument("--debug", action="store_true")
    args_parser.add_argument("--log-level")
    args_parser.add_argument("--log-file")
    early_args, _ = args_parser.parse_known_args()
    
    # Setup logging before anything else
    log_file = Path(early_args.log_file) if early_args.log_file else None
    setup_logging(
        debug=early_args.debug,
        log_file=log_file,
        log_level=early_args.log_level
    )
    
    # Now create the full parser
    parser = argparse.ArgumentParser(
        description="MCP Browser - Universal Model Context Protocol Interface",
        epilog="""
Examples:
  # Interactive mode
  mcp-browser                          # Start interactive mode with default server
  mcp-browser --server brave-search    # Use Brave Search server
  
  # Configuration
  mcp-browser --list-servers           # List configured servers
  mcp-browser --show-config            # Show current configuration
  mcp-browser --test                   # Test server connection
  
  # MCP method commands
  mcp-browser tools-list               # List available tools
  mcp-browser tools-call brave_web_search '{"query": "MCP protocol"}'
  mcp-browser resources-list           # List available resources
  mcp-browser resources-read "file:///path/to/file"
  mcp-browser prompts-list             # List available prompts
  mcp-browser prompts-get "greeting" --arguments '{"name": "Alice"}'
  
  # Raw JSON-RPC
  mcp-browser jsonrpc '{"method": "tools/list", "params": {}}'
  
  # Server mode
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
    parser.add_argument("--mode", choices=["interactive", "server", "daemon"], 
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
    parser.add_argument("--log-level", choices=["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Set logging level")
    parser.add_argument("--log-file", help="Log to file instead of stderr")
    parser.add_argument("--use-daemon", action="store_true",
                       help="Automatically use daemon if available")
    parser.add_argument("--daemon-start", action="store_true",
                       help="Start daemon in background")
    parser.add_argument("--daemon-stop", action="store_true",
                       help="Stop running daemon")
    parser.add_argument("--daemon-status", action="store_true",
                       help="Check daemon status")
    
    # MCP method commands
    subparsers = parser.add_subparsers(dest="command", help="MCP methods")
    
    # tools/list command
    list_tools = subparsers.add_parser("tools-list", help="List available tools")
    
    # tools/call command
    call_tool = subparsers.add_parser("tools-call", help="Call a tool")
    call_tool.add_argument("name", help="Tool name")
    call_tool.add_argument("arguments", help="Tool arguments as JSON")
    
    # resources/list command
    list_resources = subparsers.add_parser("resources-list", help="List available resources")
    
    # resources/read command
    read_resource = subparsers.add_parser("resources-read", help="Read a resource")
    read_resource.add_argument("uri", help="Resource URI")
    
    # prompts/list command
    list_prompts = subparsers.add_parser("prompts-list", help="List available prompts")
    
    # prompts/get command
    get_prompt = subparsers.add_parser("prompts-get", help="Get a prompt")
    get_prompt.add_argument("name", help="Prompt name")
    get_prompt.add_argument("--arguments", "-a", help="Prompt arguments as JSON", default="{}")
    
    # completion command
    completion = subparsers.add_parser("completion", help="Get completion")
    completion.add_argument("--ref", help="Reference for completion")
    completion.add_argument("--argument", help="Argument name")
    
    # Generic JSON-RPC command
    jsonrpc = subparsers.add_parser("jsonrpc", help="Send raw JSON-RPC request")
    jsonrpc.add_argument("request", help="JSON-RPC request")
    
    args = parser.parse_args()
    
    # Handle special commands first
    if args.list_servers:
        show_available_servers(args.config)
        return
    
    if args.show_config:
        show_configuration(args.config)
        return
    
    # Handle daemon management commands
    if args.daemon_start:
        asyncio.run(start_daemon_background(args))
        return
    
    if args.daemon_stop:
        stop_daemon(args)
        return
    
    if args.daemon_status:
        show_daemon_status(args)
        return
    
    # Handle MCP method commands
    if args.command:
        asyncio.run(handle_mcp_command(args))
        return
    
    # Create browser
    config_path = Path(args.config) if args.config else None
    
    # Apply log level to config if set
    if args.log_level == "TRACE" and config_path is None:
        from .config import ConfigLoader
        loader = ConfigLoader()
        config = loader.load()
        # TRACE level shows raw I/O
    
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
        # Run as MCP server (stdin/stdout) - can connect to daemon
        socket_path = get_socket_path(args.server)
        if args.use_daemon and is_daemon_running(socket_path):
            # Use daemon as backend
            asyncio.run(run_server_mode_with_daemon(socket_path))
        else:
            asyncio.run(run_server_mode(browser))
    elif args.mode == "daemon":
        # Run as daemon
        socket_path = get_socket_path(args.server)
        asyncio.run(run_daemon_mode(browser, socket_path))
    else:
        # Interactive mode - can use daemon if available
        socket_path = get_socket_path(args.server)
        if args.use_daemon and is_daemon_running(socket_path):
            asyncio.run(interactive_mode_with_daemon(socket_path))
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