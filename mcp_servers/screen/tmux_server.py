#!/usr/bin/env python3
"""
Tmux MCP Server - tmux session management.

Provides tools for creating and managing persistent tmux sessions,
useful for long-running processes and maintaining shell state.
"""

import os
import sys
import asyncio
import subprocess
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from base import BaseMCPServer


class TmuxServer(BaseMCPServer):
    """MCP server for tmux management."""
    
    def __init__(self):
        super().__init__("tmux-server", "1.0.0")
        self._register_tools()
        
    def _register_tools(self):
        """Register all tmux management tools."""
        
        # Create session tool
        self.register_tool(
            name="create_session",
            description="Create a new tmux session with optional initial command",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the tmux session"
                    },
                    "command": {
                        "type": "string",
                        "description": "Optional command to run in the session"
                    }
                },
                "required": ["name"]
            }
        )
        
        # Execute command tool
        self.register_tool(
            name="execute",
            description="Execute a command in an existing tmux session",
            input_schema={
                "type": "object",
                "properties": {
                    "session": {
                        "type": "string",
                        "description": "Name of the tmux session"
                    },
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    }
                },
                "required": ["session", "command"]
            }
        )
        
        # Peek at session output
        self.register_tool(
            name="peek",
            description="Get recent output from a tmux session (last 50 lines by default)",
            input_schema={
                "type": "object",
                "properties": {
                    "session": {
                        "type": "string",
                        "description": "Name of the tmux session"
                    },
                    "lines": {
                        "type": "integer",
                        "description": "Number of lines to retrieve (default: 50)",
                        "default": 50
                    }
                },
                "required": ["session"]
            }
        )
        
        # List sessions
        self.register_tool(
            name="list_sessions",
            description="List all active tmux sessions",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        
        # Kill session
        self.register_tool(
            name="kill_session",
            description="Terminate a tmux session",
            input_schema={
                "type": "object",
                "properties": {
                    "session": {
                        "type": "string",
                        "description": "Name of the tmux session to kill"
                    }
                },
                "required": ["session"]
            }
        )
        
        # Attach to session (provides instructions)
        self.register_tool(
            name="attach_session",
            description="Provide instructions for attaching to a tmux session",
            input_schema={
                "type": "object",
                "properties": {
                    "session": {
                        "type": "string",
                        "description": "Name of the tmux session"
                    }
                },
                "required": ["session"]
            }
        )
        
        # Share session (tmux supports multiple clients by default)
        self.register_tool(
            name="share_session",
            description="Get instructions for sharing a tmux session with other users",
            input_schema={
                "type": "object",
                "properties": {
                    "session": {
                        "type": "string",
                        "description": "Name of the tmux session"
                    }
                },
                "required": ["session"]
            }
        )
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tmux tool calls."""
        
        if tool_name == "create_session":
            return await self._create_session(arguments)
        elif tool_name == "execute":
            return await self._execute_command(arguments)
        elif tool_name == "peek":
            return await self._peek_session(arguments)
        elif tool_name == "list_sessions":
            return await self._list_sessions()
        elif tool_name == "kill_session":
            return await self._kill_session(arguments)
        elif tool_name == "attach_session":
            return await self._attach_session(arguments)
        elif tool_name == "share_session":
            return await self._share_session(arguments)
        else:
            raise Exception(f"Unknown tool: {tool_name}")
    
    async def _create_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new tmux session."""
        name = args["name"]
        command = args.get("command")
        
        # Check if session already exists
        check_result = await self._run_command(["tmux", "list-sessions", "-F", "#{session_name}"])
        if check_result.returncode == 0 and name in check_result.stdout.split('\n'):
            return self.content_text(f"Session '{name}' already exists")
        
        # Create session
        cmd = ["tmux", "new-session", "-d", "-s", name]
        if command:
            cmd.append(command)
        
        result = await self._run_command(cmd)
        
        if result.returncode == 0:
            return self.content_text(f"Created tmux session '{name}'" + 
                                   (f" running '{command}'" if command else ""))
        else:
            return self.content_text(f"Failed to create session: {result.stderr}")
    
    async def _execute_command(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command in a tmux session."""
        session = args["session"]
        command = args["command"]
        
        # Send command to tmux session
        cmd = ["tmux", "send-keys", "-t", session, command, "Enter"]
        
        result = await self._run_command(cmd)
        
        if result.returncode == 0:
            return self.content_text(f"Executed command in session '{session}'")
        else:
            return self.content_text(f"Failed to execute command: {result.stderr}")
    
    async def _peek_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent output from a tmux session."""
        session = args["session"]
        lines = args.get("lines", 50)
        
        # Get pane content from tmux
        cmd = ["tmux", "capture-pane", "-t", session, "-p"]
        
        result = await self._run_command(cmd)
        
        if result.returncode != 0:
            return self.content_text(f"Failed to peek at session: {result.stderr}")
        
        # Clean ANSI escape sequences
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        content = ansi_escape.sub('', result.stdout)
        
        # Get last N lines
        output_lines = content.strip().split('\n')
        if len(output_lines) > lines:
            output_lines = output_lines[-lines:]
        
        output = '\n'.join(output_lines)
        
        return self.content_text(output if output else "(No output)")
    
    async def _list_sessions(self) -> Dict[str, Any]:
        """List all active tmux sessions."""
        result = await self._run_command(["tmux", "list-sessions", "-F", "#{session_name}: #{?session_attached,attached,not attached} (#{session_windows} windows)"])
        
        if result.returncode != 0:
            if "no server running" in result.stderr.lower():
                return self.content_text("No tmux server running (no active sessions)")
            else:
                return self.content_text(f"Error listing sessions: {result.stderr}")
        
        if result.stdout.strip():
            output = "Active tmux sessions:\n" + result.stdout.strip()
        else:
            output = "No active tmux sessions"
        
        return self.content_text(output)
    
    async def _kill_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Kill a tmux session."""
        session = args["session"]
        
        cmd = ["tmux", "kill-session", "-t", session]
        result = await self._run_command(cmd)
        
        if result.returncode == 0:
            return self.content_text(f"Killed tmux session '{session}'")
        else:
            return self.content_text(f"Failed to kill session: {result.stderr}")
    
    async def _attach_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Provide instructions for attaching to a tmux session."""
        session = args["session"]
        
        # Check if session exists
        check_result = await self._run_command(["tmux", "list-sessions", "-F", "#{session_name}"])
        if check_result.returncode != 0 or session not in check_result.stdout.split('\n'):
            return self.content_text(f"Session '{session}' not found")
        
        # Provide attach command
        attach_cmd = f"tmux attach-session -t {session}"
        
        return self.content_text(f"To attach to session '{session}', run: {attach_cmd}")
    
    async def _share_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get instructions for sharing a tmux session."""
        session = args["session"]
        
        # Check if session exists
        check_result = await self._run_command(["tmux", "list-sessions", "-F", "#{session_name}"])
        if check_result.returncode != 0 or session not in check_result.stdout.split('\n'):
            return self.content_text(f"Session '{session}' not found")
        
        instructions = f"""To share tmux session '{session}':

1. Multiple users can attach simultaneously:
   tmux attach-session -t {session}

2. For read-only access:
   tmux attach-session -t {session} -r

3. To create a new session attached to the same windows:
   tmux new-session -t {session}

Note: tmux supports multiple clients by default - no special setup needed!"""
        
        return self.content_text(instructions)
    
    async def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        return await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True
        )


if __name__ == "__main__":
    # Check if tmux is installed
    try:
        subprocess.run(["tmux", "-V"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: tmux is not installed", file=sys.stderr)
        print("Install it with: sudo apt-get install tmux", file=sys.stderr)
        sys.exit(1)
    
    # Run the server
    server = TmuxServer()
    asyncio.run(server.run())