#!/usr/bin/env python3
"""
Onboarding MCP Server - Identity-aware onboarding management.

Provides personalized onboarding experiences where AI instances can
leave instructions for future contexts based on identity.
"""

import os
import sys
import json
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from base import BaseMCPServer


class OnboardingServer(BaseMCPServer):
    """MCP server for identity-aware onboarding."""
    
    def __init__(self):
        super().__init__("onboarding-server", "1.0.0")
        self.onboarding_dir = Path.home() / ".mcp-onboarding"
        self.onboarding_dir.mkdir(exist_ok=True)
        self._register_tools()
    
    def _register_tools(self):
        """Register onboarding tools."""
        
        self.register_tool(
            name="onboarding",
            description="Get or set onboarding instructions for a specific identity",
            input_schema={
                "type": "object",
                "properties": {
                    "identity": {
                        "type": "string",
                        "description": "The identity to get/set onboarding for (e.g., 'Claude', 'Assistant', project name)"
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Optional: New onboarding instructions to set. If not provided, retrieves existing."
                    },
                    "append": {
                        "type": "boolean",
                        "description": "If true, append to existing instructions instead of replacing",
                        "default": False
                    }
                },
                "required": ["identity"]
            }
        )
        
        self.register_tool(
            name="onboarding_list",
            description="List all available onboarding identities",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        
        self.register_tool(
            name="onboarding_delete",
            description="Delete onboarding for a specific identity",
            input_schema={
                "type": "object",
                "properties": {
                    "identity": {
                        "type": "string",
                        "description": "The identity to delete onboarding for"
                    }
                },
                "required": ["identity"]
            }
        )
        
        self.register_tool(
            name="onboarding_export",
            description="Export all onboarding data",
            input_schema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["json", "markdown"],
                        "default": "markdown"
                    }
                }
            }
        )
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle onboarding tool calls."""
        
        if tool_name == "onboarding":
            return await self._handle_onboarding(arguments)
        elif tool_name == "onboarding_list":
            return await self._list_identities()
        elif tool_name == "onboarding_delete":
            return await self._delete_onboarding(arguments)
        elif tool_name == "onboarding_export":
            return await self._export_onboarding(arguments)
        else:
            raise Exception(f"Unknown tool: {tool_name}")
    
    async def _handle_onboarding(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get or set onboarding for an identity."""
        identity = self._sanitize_identity(args["identity"])
        instructions = args.get("instructions")
        append = args.get("append", False)
        
        onboarding_file = self.onboarding_dir / f"{identity}.json"
        
        if instructions is None:
            # Get mode - retrieve existing onboarding
            if onboarding_file.exists():
                with open(onboarding_file) as f:
                    data = json.load(f)
                
                content = self._format_onboarding(identity, data)
                return self.content_text(content)
            else:
                # Try to load predefined markdown files first
                predefined_file = Path(__file__).parent / f"{identity}.md"
                if predefined_file.exists():
                    with open(predefined_file) as f:
                        predefined_content = f.read()
                    
                    return self.content_text(predefined_content)
                
                # Try to load default onboarding
                default_file = Path(__file__).parent / "default.md"
                if default_file.exists():
                    with open(default_file) as f:
                        default_content = f.read()
                    
                    return self.content_text(default_content)
                else:
                    return self.content_text(
                        f"# Onboarding for {identity}\n\n"
                        f"No onboarding instructions found.\n\n"
                        f"To add onboarding, use:\n"
                        f"onboarding(identity='{identity}', instructions='Your instructions here')"
                    )
        else:
            # Set mode - store new onboarding
            if onboarding_file.exists() and append:
                with open(onboarding_file) as f:
                    data = json.load(f)
                
                # Append to history
                data["history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "instructions": instructions
                })
                data["current"] = data["current"] + "\n\n" + instructions
                data["updated_at"] = datetime.now().isoformat()
            else:
                # Create new or replace
                data = {
                    "identity": identity,
                    "current": instructions,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "history": [{
                        "timestamp": datetime.now().isoformat(),
                        "instructions": instructions
                    }]
                }
            
            with open(onboarding_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return self.content_text(
                f"Onboarding {'appended' if append else 'set'} for {identity}.\n\n"
                f"Instructions:\n{instructions}"
            )
    
    async def _list_identities(self) -> Dict[str, Any]:
        """List all available identities."""
        identities = []
        
        for file in self.onboarding_dir.glob("*.json"):
            identity = file.stem
            with open(file) as f:
                data = json.load(f)
            
            created = data.get("created_at", "Unknown")
            updated = data.get("updated_at", created)
            history_count = len(data.get("history", []))
            
            identities.append(
                f"- **{identity}**: Created {created[:10]}, "
                f"Updated {updated[:10]}, {history_count} revision(s)"
            )
        
        if not identities:
            return self.content_text("No onboarding identities found.")
        
        return self.content_text(
            "# Available Onboarding Identities\n\n" + 
            "\n".join(identities)
        )
    
    async def _delete_onboarding(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete onboarding for an identity."""
        identity = self._sanitize_identity(args["identity"])
        onboarding_file = self.onboarding_dir / f"{identity}.json"
        
        if not onboarding_file.exists():
            return self.content_text(f"No onboarding found for {identity}")
        
        onboarding_file.unlink()
        return self.content_text(f"Deleted onboarding for {identity}")
    
    async def _export_onboarding(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Export all onboarding data."""
        format_type = args.get("format", "markdown")
        
        all_data = {}
        for file in self.onboarding_dir.glob("*.json"):
            identity = file.stem
            with open(file) as f:
                all_data[identity] = json.load(f)
        
        if format_type == "json":
            return self.content_text(json.dumps(all_data, indent=2))
        else:
            # Markdown format
            lines = ["# All Onboarding Data\n"]
            
            for identity, data in all_data.items():
                lines.append(f"## {identity}\n")
                lines.append(f"**Created**: {data.get('created_at', 'Unknown')}")
                lines.append(f"**Updated**: {data.get('updated_at', 'Unknown')}")
                lines.append(f"\n### Current Instructions\n")
                lines.append(data.get('current', 'No instructions'))
                
                if data.get('history') and len(data['history']) > 1:
                    lines.append(f"\n### History ({len(data['history'])} revisions)\n")
                    for i, entry in enumerate(data['history']):
                        lines.append(f"#### Revision {i+1} - {entry['timestamp'][:10]}")
                        lines.append(entry['instructions'])
                        lines.append("")
                
                lines.append("\n---\n")
            
            return self.content_text("\n".join(lines))
    
    def _sanitize_identity(self, identity: str) -> str:
        """Sanitize identity string for filesystem use."""
        # Replace problematic characters
        return identity.replace("/", "_").replace("\\", "_").replace(":", "_")
    
    def _format_onboarding(self, identity: str, data: Dict[str, Any]) -> str:
        """Format onboarding data for display."""
        lines = [
            f"# Onboarding for {identity}",
            f"",
            f"**Created**: {data.get('created_at', 'Unknown')}",
            f"**Updated**: {data.get('updated_at', 'Unknown')}",
            f"**Revisions**: {len(data.get('history', []))}",
            f"",
            f"## Instructions",
            f"",
            data.get('current', 'No instructions set.'),
            f"",
            f"---",
            f"",
            f"*To update these instructions, use:*",
            f"`onboarding(identity='{identity}', instructions='New instructions', append=True/False)`"
        ]
        
        return "\n".join(lines)


if __name__ == "__main__":
    server = OnboardingServer()
    asyncio.run(server.run())