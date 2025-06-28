#!/usr/bin/env python3
"""
Enhanced Interactive MCP Browser Client

Provides a user-friendly interactive interface for exploring and using MCP tools
with better discovery, autocompletion, and testing capabilities.
"""

import asyncio
import json
import readline
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import traceback

from .proxy import MCPBrowser
from .daemon import MCPBrowserClient, get_socket_path, is_daemon_running
from .logging_config import get_logger


class InteractiveMCPClient:
    """Enhanced interactive MCP browser client."""
    
    def __init__(self, server_name: Optional[str] = None, use_daemon: bool = True):
        self.server_name = server_name
        self.use_daemon = use_daemon
        self.browser: Optional[MCPBrowser] = None
        self.client: Optional[MCPBrowserClient] = None
        self.logger = get_logger(__name__)
        self.tool_cache: Dict[str, Any] = {}
        self.command_history: List[str] = []
        
        # Setup readline
        self._setup_readline()
        
    def _setup_readline(self):
        """Setup readline for better command line experience."""
        readline.set_completer(self._completer)
        readline.parse_and_bind('tab: complete')
        readline.set_completer_delims(' \t\n`!@#$%^&*()=+[{]}\\|;:\'",<>?')
        
        # Load history
        history_file = Path.home() / ".mcp_browser_history"
        try:
            readline.read_history_file(str(history_file))
        except FileNotFoundError:
            pass
            
        # Save history on exit
        import atexit
        atexit.register(readline.write_history_file, str(history_file))
    
    def _completer(self, text: str, state: int) -> Optional[str]:
        """Tab completion for commands and tool names."""
        if state == 0:
            # Get current line
            line = readline.get_line_buffer()
            
            # Complete commands
            commands = ['discover', 'call', 'list', 'help', 'quit', 'onboard', 'status', 'test']
            
            # Add tool names if we have them cached
            if self.tool_cache:
                commands.extend(self.tool_cache.keys())
            
            # Filter matches
            self.matches = [cmd for cmd in commands if cmd.startswith(text)]
        
        try:
            return self.matches[state]
        except IndexError:
            return None
    
    async def initialize(self):
        """Initialize the MCP browser connection."""
        print("🔍 MCP Browser Interactive Mode")
        print("Type 'help' for commands, 'quit' to exit")
        print()
        
        # Try to connect
        if self.use_daemon:
            socket_path = get_socket_path(self.server_name)
            if is_daemon_running(socket_path):
                try:
                    self.client = MCPBrowserClient(socket_path)
                    await self.client.__aenter__()
                    print(f"✅ Connected to daemon at {socket_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to connect to daemon: {e}")
                    self.client = None
        
        if not self.client:
            # Fallback to standalone
            print("🚀 Starting standalone MCP browser...")
            self.browser = MCPBrowser(server_name=self.server_name)
            await self.browser.initialize()
            print("✅ MCP browser initialized")
        
        # Load initial tool list
        await self._refresh_tools()
    
    async def _refresh_tools(self):
        """Refresh the tool cache."""
        try:
            response = await self._call_mcp({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            })
            
            if "result" in response and "tools" in response["result"]:
                self.tool_cache.clear()
                for tool in response["result"]["tools"]:
                    self.tool_cache[tool["name"]] = tool
        except Exception as e:
            self.logger.warning(f"Failed to refresh tools: {e}")
    
    async def _call_mcp(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP method through client or browser."""
        if self.client:
            return await self.client.call(request)
        elif self.browser:
            return await self.browser.call(request)
        else:
            raise RuntimeError("No MCP connection available")
    
    async def run(self):
        """Main interactive loop."""
        try:
            await self.initialize()
            
            while True:
                try:
                    # Get user input
                    line = input("mcp> ").strip()
                    if not line:
                        continue
                    
                    self.command_history.append(line)
                    
                    # Parse and execute command
                    await self._execute_command(line)
                    
                except KeyboardInterrupt:
                    print("\nUse 'quit' to exit")
                    continue
                except EOFError:
                    break
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            traceback.print_exc()
        finally:
            await self.cleanup()
    
    async def _execute_command(self, line: str):
        """Execute a user command."""
        parts = line.split()
        if not parts:
            return
        
        command = parts[0].lower()
        args = parts[1:]
        
        if command == 'help':
            self._show_help()
        elif command == 'quit' or command == 'exit':
            print("👋 Goodbye!")
            sys.exit(0)
        elif command == 'list':
            await self._list_tools(args)
        elif command == 'discover':
            await self._discover_tools(args)
        elif command == 'call':
            await self._call_tool(args)
        elif command == 'onboard':
            await self._manage_onboarding(args)
        elif command == 'status':
            await self._show_status()
        elif command == 'test':
            await self._test_tool(args)
        elif command == 'refresh':
            await self._refresh_tools()
            print("🔄 Tool cache refreshed")
        else:
            # Try to call it as a tool directly
            await self._call_tool_direct(command, args)
    
    def _show_help(self):
        """Show help information."""
        help_text = """
🔍 MCP Browser Interactive Commands

Basic Commands:
  help                    Show this help
  quit, exit             Exit the browser
  refresh                Refresh tool cache
  status                 Show connection status

Tool Discovery:
  list [pattern]         List available tools (optional filter)
  discover <jsonpath>    Discover tools using JSONPath
  
Tool Execution:
  call <tool> [args...]  Call a tool with arguments
  test <tool>            Test a tool with sample data
  <tool> [args...]       Direct tool call (shortcut)

Onboarding:
  onboard <identity>     Get onboarding for identity
  onboard <identity> <instructions>  Set onboarding

Examples:
  list                   # List all tools
  list bash              # List tools containing 'bash'
  discover $.tools[*].name            # Get all tool names
  discover $.tools[?(@.name=='Bash')] # Get Bash tool details
  call mcp_discover jsonpath="$.tools[*].name"
  test Bash              # Test Bash tool
  onboard Claude         # Get Claude's onboarding
  onboard Claude "Focus on code quality"  # Set onboarding
"""
        print(help_text)
    
    async def _list_tools(self, args: List[str]):
        """List available tools with optional filtering."""
        pattern = args[0] if args else None
        
        tools = list(self.tool_cache.values())
        if pattern:
            tools = [t for t in tools if pattern.lower() in t["name"].lower() or 
                    pattern.lower() in t.get("description", "").lower()]
        
        if not tools:
            print("❌ No tools found")
            return
        
        print(f"📋 Available Tools ({len(tools)} found):")
        print()
        
        for tool in tools:
            name = tool["name"]
            desc = tool.get("description", "No description")
            # Truncate long descriptions
            if len(desc) > 80:
                desc = desc[:77] + "..."
            
            # Add emoji based on tool type
            emoji = "🔍" if "discover" in name else "🚀" if "call" in name else "📋" if "onboard" in name else "🛠️"
            print(f"  {emoji} {name}")
            print(f"     {desc}")
            print()
    
    async def _discover_tools(self, args: List[str]):
        """Discover tools using JSONPath."""
        if not args:
            print("❌ Usage: discover <jsonpath>")
            print("Examples:")
            print("  discover $.tools[*].name")
            print("  discover $.tools[?(@.name=='Bash')]")
            return
        
        jsonpath = " ".join(args)
        
        try:
            response = await self._call_mcp({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "mcp_discover",
                    "arguments": {"jsonpath": jsonpath}
                }
            })
            
            if "result" in response:
                content = response["result"].get("content", [])
                if content and content[0].get("type") == "text":
                    result = content[0]["text"]
                    print("🔍 Discovery Result:")
                    print(result)
                else:
                    print("❌ No content in response")
            elif "error" in response:
                print(f"❌ Error: {response['error']['message']}")
            
        except Exception as e:
            print(f"❌ Discovery failed: {e}")
    
    async def _call_tool(self, args: List[str]):
        """Call a tool with arguments."""
        if not args:
            print("❌ Usage: call <tool_name> [key=value...]")
            print("Example: call mcp_discover jsonpath=\"$.tools[*].name\"")
            return
        
        tool_name = args[0]
        
        # Parse key=value arguments
        arguments = {}
        for arg in args[1:]:
            if "=" in arg:
                key, value = arg.split("=", 1)
                # Remove quotes if present
                value = value.strip('"\'')
                arguments[key] = value
            else:
                # Positional argument - try to guess the parameter name
                if tool_name in self.tool_cache:
                    tool = self.tool_cache[tool_name]
                    schema = tool.get("inputSchema", {})
                    props = schema.get("properties", {})
                    required = schema.get("required", [])
                    
                    # Use first required parameter
                    if required and len(arguments) == 0:
                        arguments[required[0]] = arg
                    else:
                        arguments[f"arg_{len(arguments)}"] = arg
        
        await self._execute_tool_call(tool_name, arguments)
    
    async def _call_tool_direct(self, tool_name: str, args: List[str]):
        """Direct tool call (shortcut syntax)."""
        if tool_name not in self.tool_cache:
            print(f"❌ Unknown tool: {tool_name}")
            print("Use 'list' to see available tools")
            return
        
        # Parse arguments like _call_tool
        arguments = {}
        for arg in args:
            if "=" in arg:
                key, value = arg.split("=", 1)
                value = value.strip('"\'')
                arguments[key] = value
            else:
                # Use tool schema to guess parameter
                tool = self.tool_cache[tool_name]
                schema = tool.get("inputSchema", {})
                required = schema.get("required", [])
                if required and len(arguments) == 0:
                    arguments[required[0]] = arg
        
        await self._execute_tool_call(tool_name, arguments)
    
    async def _execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]):
        """Execute a tool call and display results."""
        print(f"🚀 Calling {tool_name} with {arguments}")
        
        try:
            response = await self._call_mcp({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            })
            
            if "result" in response:
                self._display_result(response["result"])
            elif "error" in response:
                print(f"❌ Error: {response['error']['message']}")
            
        except Exception as e:
            print(f"❌ Tool call failed: {e}")
    
    def _display_result(self, result: Any):
        """Display tool call result in a nice format."""
        if isinstance(result, dict) and "content" in result:
            # MCP content format
            content = result["content"]
            for item in content:
                if item.get("type") == "text":
                    print("📄 Result:")
                    print(item["text"])
                elif item.get("type") == "image":
                    print(f"🖼️ Image: {item.get('url', 'No URL')}")
                else:
                    print(f"📦 Content: {json.dumps(item, indent=2)}")
        else:
            # Raw result
            print("📦 Result:")
            if isinstance(result, (dict, list)):
                print(json.dumps(result, indent=2))
            else:
                print(str(result))
    
    async def _test_tool(self, args: List[str]):
        """Test a tool with sample data."""
        if not args:
            print("❌ Usage: test <tool_name>")
            return
        
        tool_name = args[0]
        if tool_name not in self.tool_cache:
            print(f"❌ Unknown tool: {tool_name}")
            return
        
        tool = self.tool_cache[tool_name]
        schema = tool.get("inputSchema", {})
        
        print(f"🧪 Testing {tool_name}")
        print(f"📋 Description: {tool.get('description', 'No description')}")
        print(f"📊 Schema: {json.dumps(schema, indent=2)}")
        
        # Generate sample arguments
        sample_args = self._generate_sample_args(schema)
        print(f"🎲 Sample arguments: {sample_args}")
        
        # Ask user if they want to proceed
        try:
            confirm = input("Proceed with test? [y/N]: ").strip().lower()
            if confirm in ['y', 'yes']:
                await self._execute_tool_call(tool_name, sample_args)
        except KeyboardInterrupt:
            print("\n❌ Test cancelled")
    
    def _generate_sample_args(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate sample arguments based on schema."""
        args = {}
        props = schema.get("properties", {})
        
        for name, prop in props.items():
            prop_type = prop.get("type", "string")
            
            if prop_type == "string":
                if "example" in prop:
                    args[name] = prop["example"]
                elif name.lower() in ["jsonpath", "path"]:
                    args[name] = "$.tools[*].name"
                elif name.lower() in ["query", "search"]:
                    args[name] = "test query"
                else:
                    args[name] = f"sample_{name}"
            elif prop_type == "boolean":
                args[name] = False
            elif prop_type == "number":
                args[name] = 1
            elif prop_type == "array":
                args[name] = ["sample"]
            elif prop_type == "object":
                args[name] = {}
        
        return args
    
    async def _manage_onboarding(self, args: List[str]):
        """Manage onboarding instructions."""
        if not args:
            print("❌ Usage: onboard <identity> [instructions]")
            return
        
        identity = args[0]
        instructions = " ".join(args[1:]) if len(args) > 1 else None
        
        arguments = {"identity": identity}
        if instructions:
            arguments["instructions"] = instructions
        
        await self._execute_tool_call("onboarding", arguments)
    
    async def _show_status(self):
        """Show connection and tool status."""
        print("📊 MCP Browser Status")
        print()
        
        if self.client:
            print("🔗 Connection: Daemon")
        elif self.browser:
            print("🔗 Connection: Standalone")
        else:
            print("❌ Connection: None")
        
        print(f"🛠️ Tools cached: {len(self.tool_cache)}")
        print(f"📝 Command history: {len(self.command_history)}")
        
        if self.server_name:
            print(f"🎯 Server: {self.server_name}")
        
        # Show tool breakdown
        if self.tool_cache:
            meta_tools = [name for name in self.tool_cache if name.startswith("mcp_") or name == "onboarding"]
            regular_tools = [name for name in self.tool_cache if name not in meta_tools]
            
            print()
            print(f"🔍 Meta tools: {len(meta_tools)} ({', '.join(meta_tools)})")
            print(f"🛠️ Regular tools: {len(regular_tools)}")
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.client:
                await self.client.__aexit__(None, None, None)
            if self.browser:
                await self.browser.close()
        except Exception as e:
            self.logger.warning(f"Cleanup error: {e}")


async def main():
    """Main entry point for interactive mode."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Interactive MCP Browser")
    parser.add_argument("--server", help="MCP server name")
    parser.add_argument("--no-daemon", action="store_true", help="Don't use daemon")
    
    args = parser.parse_args()
    
    client = InteractiveMCPClient(
        server_name=args.server,
        use_daemon=not args.no_daemon
    )
    
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())