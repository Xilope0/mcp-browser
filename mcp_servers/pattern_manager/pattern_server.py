#!/usr/bin/env python3
"""
Pattern Manager MCP Server - Auto-response pattern management.

Manages custom patterns for automating repetitive interactions,
with support for placeholders and command execution.
"""

import os
import sys
import json
import asyncio
import subprocess
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from base import BaseMCPServer


class PatternServer(BaseMCPServer):
    """MCP server for pattern management."""
    
    def __init__(self):
        super().__init__("pattern-server", "1.0.0")
        self.patterns_file = Path.home() / ".mcp-patterns" / "patterns.json"
        self.patterns_file.parent.mkdir(exist_ok=True)
        self.patterns: Dict[str, Dict[str, Any]] = self._load_patterns()
        self._register_tools()
    
    def _register_tools(self):
        """Register pattern management tools."""
        
        self.register_tool(
            name="add_pattern",
            description="Add a new auto-response pattern",
            input_schema={
                "type": "object",
                "properties": {
                    "trigger": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of strings that must appear in sequence"
                    },
                    "response": {
                        "type": ["string", "array"],
                        "description": "Response text or array of responses"
                    },
                    "description": {
                        "type": "string",
                        "description": "Human-readable description of the pattern"
                    }
                },
                "required": ["trigger", "response"]
            }
        )
        
        self.register_tool(
            name="list_patterns",
            description="List all active patterns",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        
        self.register_tool(
            name="remove_pattern",
            description="Remove a pattern by ID",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern_id": {
                        "type": "string",
                        "description": "ID of the pattern to remove"
                    }
                },
                "required": ["pattern_id"]
            }
        )
        
        self.register_tool(
            name="test_pattern",
            description="Test if text matches a pattern",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to test against patterns"
                    },
                    "pattern_id": {
                        "type": "string",
                        "description": "Optional specific pattern to test"
                    }
                }
            }
        )
        
        self.register_tool(
            name="execute_pattern",
            description="Execute a pattern's response (for testing)",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern_id": {
                        "type": "string",
                        "description": "ID of the pattern to execute"
                    },
                    "context": {
                        "type": "object",
                        "description": "Optional context variables for placeholders"
                    }
                }
            }
        )
    
    def _load_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load patterns from file."""
        if self.patterns_file.exists():
            with open(self.patterns_file) as f:
                return json.load(f)
        return {}
    
    def _save_patterns(self):
        """Save patterns to file."""
        with open(self.patterns_file, 'w') as f:
            json.dump(self.patterns, f, indent=2)
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pattern tool calls."""
        
        if tool_name == "add_pattern":
            return await self._add_pattern(arguments)
        elif tool_name == "list_patterns":
            return await self._list_patterns()
        elif tool_name == "remove_pattern":
            return await self._remove_pattern(arguments)
        elif tool_name == "test_pattern":
            return await self._test_pattern(arguments)
        elif tool_name == "execute_pattern":
            return await self._execute_pattern(arguments)
        else:
            raise Exception(f"Unknown tool: {tool_name}")
    
    async def _add_pattern(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new pattern."""
        pattern_id = str(uuid4())[:8]
        
        pattern = {
            "id": pattern_id,
            "trigger": args["trigger"],
            "response": args["response"],
            "description": args.get("description", ""),
            "created_at": asyncio.get_event_loop().time()
        }
        
        self.patterns[pattern_id] = pattern
        self._save_patterns()
        
        return self.content_text(
            f"Added pattern {pattern_id}:\n"
            f"Trigger: {' -> '.join(args['trigger'])}\n"
            f"Response: {args['response']}"
        )
    
    async def _list_patterns(self) -> Dict[str, Any]:
        """List all patterns."""
        if not self.patterns:
            return self.content_text("No patterns defined")
        
        lines = ["Active patterns:"]
        for pid, pattern in self.patterns.items():
            trigger_str = " -> ".join(pattern["trigger"])
            response_str = str(pattern["response"])
            if len(response_str) > 50:
                response_str = response_str[:47] + "..."
            
            lines.append(f"\n[{pid}] {pattern.get('description', 'No description')}")
            lines.append(f"  Trigger: {trigger_str}")
            lines.append(f"  Response: {response_str}")
        
        return self.content_text("\n".join(lines))
    
    async def _remove_pattern(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Remove a pattern."""
        pattern_id = args["pattern_id"]
        
        if pattern_id not in self.patterns:
            return self.content_text(f"Pattern {pattern_id} not found")
        
        pattern = self.patterns.pop(pattern_id)
        self._save_patterns()
        
        return self.content_text(f"Removed pattern {pattern_id}")
    
    async def _test_pattern(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Test if text matches patterns."""
        text = args["text"]
        specific_id = args.get("pattern_id")
        
        matches = []
        
        if specific_id:
            # Test specific pattern
            if specific_id in self.patterns:
                pattern = self.patterns[specific_id]
                if self._matches_pattern(text, pattern["trigger"]):
                    matches.append(f"Pattern {specific_id} matches!")
                else:
                    matches.append(f"Pattern {specific_id} does not match")
            else:
                return self.content_text(f"Pattern {specific_id} not found")
        else:
            # Test all patterns
            for pid, pattern in self.patterns.items():
                if self._matches_pattern(text, pattern["trigger"]):
                    matches.append(f"Pattern {pid} matches: {pattern.get('description', '')}")
        
        if not matches:
            return self.content_text("No patterns match the text")
        
        return self.content_text("\n".join(matches))
    
    async def _execute_pattern(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a pattern's response."""
        pattern_id = args["pattern_id"]
        context = args.get("context", {})
        
        if pattern_id not in self.patterns:
            return self.content_text(f"Pattern {pattern_id} not found")
        
        pattern = self.patterns[pattern_id]
        response = pattern["response"]
        
        # Process response
        processed = await self._process_response(response, context)
        
        return self.content_text(f"Pattern response:\n{processed}")
    
    def _matches_pattern(self, text: str, trigger: List[str]) -> bool:
        """Check if text matches a trigger pattern."""
        # Simple implementation: check if all trigger strings appear in order
        position = 0
        for trigger_part in trigger:
            index = text.find(trigger_part, position)
            if index == -1:
                return False
            position = index + len(trigger_part)
        return True
    
    async def _process_response(self, response: Any, context: Dict[str, Any]) -> str:
        """Process a response, handling special commands and placeholders."""
        if isinstance(response, list):
            # Process each item in array
            processed = []
            for item in response:
                processed.append(await self._process_single_response(item, context))
            return "\n".join(processed)
        else:
            return await self._process_single_response(response, context)
    
    async def _process_single_response(self, response: str, context: Dict[str, Any]) -> str:
        """Process a single response string."""
        # Handle special commands
        
        # __CALL_TOOL_<command>_<args>
        if response.startswith("__CALL_TOOL_"):
            parts = response[12:].split("_", 1)
            if len(parts) >= 1:
                command = parts[0]
                args = parts[1] if len(parts) > 1 else ""
                
                try:
                    result = subprocess.run(
                        [command] + (args.split() if args else []),
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr}"
                except Exception as e:
                    return f"Error executing command: {e}"
        
        # __DELAY_<ms>
        if response.startswith("__DELAY_"):
            try:
                ms = int(response[8:])
                await asyncio.sleep(ms / 1000)
                return f"[Delayed {ms}ms]"
            except:
                pass
        
        # Replace placeholders with context values
        for key, value in context.items():
            response = response.replace(f"{{{key}}}", str(value))
        
        return response


if __name__ == "__main__":
    server = PatternServer()
    asyncio.run(server.run())