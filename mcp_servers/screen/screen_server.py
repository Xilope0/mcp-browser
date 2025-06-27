#!/usr/bin/env python3
"""
Screen MCP Server - GNU screen session management.

Provides tools for creating and managing persistent screen sessions,
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


class ScreenServer(BaseMCPServer):
    """MCP server for GNU screen management."""
    
    def __init__(self):
        super().__init__("screen-server", "1.0.0")
        self._register_tools()
        
    def _register_tools(self):
        """Register all screen management tools."""
        
        # Create session tool
        self.register_tool(
            name="create_session",
            description="Create a new screen session with optional initial command",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the screen session"
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
            description="Execute a command in an existing screen session",
            input_schema={
                "type": "object",
                "properties": {
                    "session": {
                        "type": "string",
                        "description": "Name of the screen session"
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
            description="Get recent output from a screen session (last 50 lines by default)",
            input_schema={
                "type": "object",
                "properties": {
                    "session": {
                        "type": "string",
                        "description": "Name of the screen session"
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
            description="List all active screen sessions",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        
        # Kill session
        self.register_tool(
            name="kill_session",
            description="Terminate a screen session",
            input_schema={
                "type": "object",
                "properties": {
                    "session": {
                        "type": "string",
                        "description": "Name of the screen session to kill"
                    }
                },
                "required": ["session"]
            }
        )
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle screen tool calls."""
        
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
        else:
            raise Exception(f"Unknown tool: {tool_name}")
    
    async def _create_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new screen session."""
        name = args["name"]
        command = args.get("command")
        
        # Check if session already exists
        check_result = await self._run_command(["screen", "-ls", name])
        if name in check_result.stdout:
            return self.content_text(f"Session '{name}' already exists")
        
        # Create session
        cmd = ["screen", "-dmS", name]
        if command:
            cmd.extend(["bash", "-c", command])
        
        result = await self._run_command(cmd)
        
        if result.returncode == 0:
            return self.content_text(f"Created screen session '{name}'" + 
                                   (f" running '{command}'" if command else ""))
        else:
            return self.content_text(f"Failed to create session: {result.stderr}")
    
    async def _execute_command(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command in a screen session."""
        session = args["session"]
        command = args["command"]
        
        # Send command to screen session
        # Note: We need to send the command followed by Enter
        cmd = ["screen", "-S", session, "-X", "stuff", f"{command}\n"]
        
        result = await self._run_command(cmd)
        
        if result.returncode == 0:
            return self.content_text(f"Executed command in session '{session}'")
        else:
            return self.content_text(f"Failed to execute command: {result.stderr}")
    
    async def _peek_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent output from a screen session."""
        session = args["session"]
        lines = args.get("lines", 50)
        
        # Create temporary file for hardcopy
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Get hardcopy of screen
            cmd = ["screen", "-S", session, "-X", "hardcopy", tmp_path]
            result = await self._run_command(cmd)
            
            if result.returncode != 0:
                return self.content_text(f"Failed to peek at session: {result.stderr}")
            
            # Read the output
            with open(tmp_path, 'r') as f:
                content = f.read()
            
            # Get last N lines
            output_lines = content.strip().split('\n')
            if len(output_lines) > lines:
                output_lines = output_lines[-lines:]
            
            output = '\n'.join(output_lines)
            
            return self.content_text(output if output else "(No output)")
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    async def _list_sessions(self) -> Dict[str, Any]:
        """List all active screen sessions."""
        result = await self._run_command(["screen", "-ls"])
        
        if "No Sockets found" in result.stdout:
            return self.content_text("No active screen sessions")
        
        # Parse screen list output
        lines = result.stdout.strip().split('\n')
        sessions = []
        
        for line in lines:
            if '\t' in line and '(' in line:
                # Extract session info
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    session_info = parts[0]
                    status = parts[1].strip('()')
                    sessions.append(f"{session_info} - {status}")
        
        if sessions:
            output = "Active screen sessions:\n" + '\n'.join(sessions)
        else:
            output = "No active screen sessions"
        
        return self.content_text(output)
    
    async def _kill_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Kill a screen session."""
        session = args["session"]
        
        cmd = ["screen", "-S", session, "-X", "quit"]
        result = await self._run_command(cmd)
        
        if result.returncode == 0:
            return self.content_text(f"Killed screen session '{session}'")
        else:
            return self.content_text(f"Failed to kill session: {result.stderr}")
    
    async def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        return await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True
        )


if __name__ == "__main__":
    # Check if screen is installed
    try:
        subprocess.run(["screen", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: GNU screen is not installed", file=sys.stderr)
        print("Install it with: sudo apt-get install screen", file=sys.stderr)
        sys.exit(1)
    
    # Run the server
    server = ScreenServer()
    asyncio.run(server.run())