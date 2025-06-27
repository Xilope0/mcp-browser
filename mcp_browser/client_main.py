#!/usr/bin/env python3
"""
MCP Browser Client - Connect to daemon or run standalone.

This client can:
1. Connect to a running daemon
2. Auto-start daemon if not running
3. Run in standalone mode
4. Act as MCP server (stdin/stdout)
"""

import os
import sys
import asyncio
import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any

from .proxy import MCPBrowser
from .daemon import MCPBrowserClient, get_socket_path, is_daemon_running
from .logging_config import setup_logging, get_logger
from .config import ConfigLoader


def start_daemon_if_needed(server_name: Optional[str] = None, timeout: float = 5.0) -> bool:
    """Start daemon if not running. Returns True if daemon is available."""
    socket_path = get_socket_path(server_name)
    
    if is_daemon_running(socket_path):
        return True
    
    # Start daemon
    cmd = [sys.executable, "-m", "mcp_browser.daemon_main"]
    if server_name:
        cmd.extend(["--server", server_name])
    
    # Start in background
    subprocess.Popen(cmd, start_new_session=True,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL)
    
    # Wait for daemon to start
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_daemon_running(socket_path):
            return True
        time.sleep(0.1)
    
    return False


async def run_mcp_server_mode(args):
    """Run as MCP server (stdin/stdout) forwarding to daemon."""
    logger = get_logger(__name__)
    
    # Try to use daemon
    socket_path = get_socket_path(args.server)
    use_daemon = False
    
    if args.use_daemon != "never":
        if args.use_daemon == "always" or is_daemon_running(socket_path):
            use_daemon = True
        elif args.use_daemon == "auto":
            # Try to start daemon
            use_daemon = start_daemon_if_needed(args.server)
    
    if use_daemon:
        logger.info(f"Using daemon at {socket_path}")
        async with MCPBrowserClient(socket_path) as client:
            # Forward stdin/stdout to daemon
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
                                print(json.dumps(response), flush=True)
                            except json.JSONDecodeError:
                                pass
                            except Exception as e:
                                logger.error(f"Error forwarding to daemon: {e}")
                                
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
    else:
        # Run standalone
        logger.info("Running in standalone mode")
        browser = MCPBrowser(
            server_name=args.server,
            config_path=Path(args.config) if args.config else None,
            enable_builtin_servers=not args.no_builtin
        )
        
        await browser.initialize()
        
        try:
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
                                print(json.dumps(response), flush=True)
                            except json.JSONDecodeError:
                                pass
                                
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
        finally:
            await browser.close()


async def run_command(args, request: Dict[str, Any]):
    """Run a single command through daemon or standalone."""
    logger = get_logger(__name__)
    
    # Try daemon first if enabled
    socket_path = get_socket_path(args.server)
    
    if args.use_daemon != "never":
        if is_daemon_running(socket_path) or (args.use_daemon == "auto" and start_daemon_if_needed(args.server)):
            logger.debug(f"Using daemon at {socket_path}")
            async with MCPBrowserClient(socket_path) as client:
                return await client.call(request)
    
    # Fallback to standalone
    logger.debug("Running in standalone mode")
    browser = MCPBrowser(
        server_name=args.server,
        config_path=Path(args.config) if args.config else None,
        enable_builtin_servers=not args.no_builtin
    )
    
    await browser.initialize()
    try:
        return await browser.call(request)
    finally:
        await browser.close()


def build_request(args) -> Dict[str, Any]:
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
    elif args.command == "jsonrpc":
        request = json.loads(args.request)
        if "jsonrpc" not in request:
            request["jsonrpc"] = "2.0"
        if "id" not in request:
            request["id"] = 1
        return request
    else:
        raise ValueError(f"Unknown command: {args.command}")


def format_response(args, response: Dict[str, Any]):
    """Format response for display."""
    if args.json:
        print(json.dumps(response))
        return
    
    if "error" in response:
        print(f"Error: {response['error'].get('message', 'Unknown error')}")
        return
    
    result = response.get("result", {})
    
    if args.command == "tools-list":
        tools = result.get("tools", [])
        if tools:
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool['name']}: {tool.get('description', '')}")
        else:
            print("No tools found")
    
    elif args.command == "tools-call":
        if "content" in result:
            for content in result["content"]:
                if content.get("type") == "text":
                    print(content.get("text", ""))
                else:
                    print(json.dumps(content, indent=2))
        else:
            print(json.dumps(result, indent=2))
    
    else:
        print(json.dumps(result, indent=2))


def main():
    """Main entry point for client."""
    parser = argparse.ArgumentParser(
        description="MCP Browser Client - Connect to daemon or run standalone",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Connection options
    parser.add_argument("--server", "-s", help="Target MCP server name")
    parser.add_argument("--config", "-c", help="Custom configuration file path")
    parser.add_argument("--use-daemon", choices=["auto", "always", "never"],
                       default="auto", help="Daemon usage mode (default: auto)")
    parser.add_argument("--no-builtin", action="store_true",
                       help="Disable built-in servers")
    
    # Output options
    parser.add_argument("--json", action="store_true",
                       help="Output raw JSON responses")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    parser.add_argument("--log-level", choices=["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Set logging level")
    parser.add_argument("--log-file", help="Log to file instead of stderr")
    
    # Mode options
    parser.add_argument("--mode", choices=["command", "server", "interactive"],
                       default="command", help="Operating mode")
    
    # Commands
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # tools/list
    tools_list = subparsers.add_parser("tools-list", help="List available tools")
    
    # tools/call
    tools_call = subparsers.add_parser("tools-call", help="Call a tool")
    tools_call.add_argument("name", help="Tool name")
    tools_call.add_argument("arguments", help="Tool arguments as JSON")
    
    # Raw JSON-RPC
    jsonrpc = subparsers.add_parser("jsonrpc", help="Send raw JSON-RPC request")
    jsonrpc.add_argument("request", help="JSON-RPC request")
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = Path(args.log_file) if args.log_file else None
    
    # In server mode, use syslog unless a log file is specified
    use_syslog = args.mode == "server" and not log_file
    
    setup_logging(
        debug=args.debug,
        log_file=log_file,
        log_level=args.log_level,
        use_syslog=use_syslog
    )
    
    # Log startup message
    logger = get_logger(__name__)
    if args.mode == "server":
        logger.debug("mcp-browser client started in server mode")

    
    # Handle modes
    if args.mode == "server":
        # Run as MCP server
        asyncio.run(run_mcp_server_mode(args))
    elif args.mode == "interactive":
        # TODO: Implement interactive mode
        print("Interactive mode not yet implemented")
    else:
        # Command mode
        if not args.command:
            parser.print_help()
            sys.exit(1)
        
        async def run():
            request = build_request(args)
            response = await run_command(args, request)
            format_response(args, response)
        
        asyncio.run(run())


if __name__ == "__main__":
    main()
