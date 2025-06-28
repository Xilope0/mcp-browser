#!/usr/bin/env python3
"""
Memory MCP Server - Persistent memory and context management.

Provides tools for managing project memory, tasks, decisions, patterns,
and knowledge across sessions.
"""

import os
import sys
import json
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field
from uuid import uuid4

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from base import BaseMCPServer


@dataclass
class Task:
    id: str
    content: str
    status: str = "pending"  # pending, in_progress, completed
    priority: str = "medium"  # low, medium, high
    assignee: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


@dataclass
class Decision:
    id: str
    choice: str
    reasoning: str
    alternatives: List[str]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Pattern:
    id: str
    pattern: str
    description: str
    priority: str = "medium"
    effectiveness: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved: bool = False
    solution: Optional[str] = None


class MemoryServer(BaseMCPServer):
    """MCP server for memory and context management with cmem integration."""
    
    def __init__(self, identity: str = "default"):
        super().__init__("memory-server", "1.0.0")
        self.memory_dir = Path.home() / ".mcp-memory"
        self.memory_dir.mkdir(exist_ok=True)
        self.current_project = identity
        self.cmem_integration = self._setup_cmem_integration()
        self._register_tools()
        self._load_memory()
    
    def _register_tools(self):
        """Register all memory management tools."""
        
        # Task management
        self.register_tool(
            name="task_add",
            description="Add a new task to the current project",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Task description"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "assignee": {"type": "string", "description": "Optional assignee"}
                },
                "required": ["content"]
            }
        )
        
        self.register_tool(
            name="task_list",
            description="List tasks with optional status filter",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}
                }
            }
        )
        
        self.register_tool(
            name="task_update",
            description="Update task status",
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}
                },
                "required": ["task_id", "status"]
            }
        )
        
        # Decision tracking
        self.register_tool(
            name="decision_add",
            description="Record a decision with reasoning",
            input_schema={
                "type": "object",
                "properties": {
                    "choice": {"type": "string", "description": "The decision made"},
                    "reasoning": {"type": "string", "description": "Why this choice"},
                    "alternatives": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["choice", "reasoning", "alternatives"]
            }
        )
        
        # Pattern management
        self.register_tool(
            name="pattern_add",
            description="Add a pattern or recurring issue",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "effectiveness": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["pattern", "description"]
            }
        )
        
        self.register_tool(
            name="pattern_resolve",
            description="Mark a pattern as resolved with solution",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern_id": {"type": "string"},
                    "solution": {"type": "string"}
                },
                "required": ["pattern_id", "solution"]
            }
        )
        
        # Knowledge management
        self.register_tool(
            name="knowledge_add",
            description="Store knowledge or information",
            input_schema={
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                    "category": {"type": "string"}
                },
                "required": ["key", "value"]
            }
        )
        
        self.register_tool(
            name="knowledge_get",
            description="Retrieve knowledge by key or category",
            input_schema={
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "category": {"type": "string"}
                }
            }
        )
        
        # Project management
        self.register_tool(
            name="project_switch",
            description="Switch to a different project context",
            input_schema={
                "type": "object",
                "properties": {
                    "project": {"type": "string"}
                },
                "required": ["project"]
            }
        )
        
        # Summary and stats
        self.register_tool(
            name="memory_summary",
            description="Get a summary of current project memory",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
    
    def _load_memory(self):
        """Load memory for current project."""
        self.project_dir = self.memory_dir / self.current_project
        self.project_dir.mkdir(exist_ok=True)
        
        # Load data files
        self.tasks = self._load_json("tasks.json", {})
        self.decisions = self._load_json("decisions.json", {})
        self.patterns = self._load_json("patterns.json", {})
        self.knowledge = self._load_json("knowledge.json", {})
    
    def _setup_cmem_integration(self) -> bool:
        """Setup integration with cmem by creating identity-specific directories."""
        try:
            # Check if cmem is available
            import subprocess
            result = subprocess.run(['cmem', 'stats'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return False
            
            # Create identity-specific directory
            identity_dir = self.memory_dir / self.current_project
            identity_dir.mkdir(exist_ok=True)
            
            # Check if we should symlink to cmem storage
            claude_dir = Path.home() / ".claude"
            if claude_dir.exists():
                # Try to find cmem session data
                cmem_session_dirs = list(claude_dir.glob("sessions/*/"))
                if cmem_session_dirs:
                    # Use the most recent session
                    latest_session = max(cmem_session_dirs, key=lambda p: p.stat().st_mtime)
                    
                    # Create symlinks for task/pattern/decision integration
                    self._create_cmem_bridges(identity_dir, latest_session)
                    return True
            
            return False
        except Exception as e:
            # Fail silently - cmem integration is optional
            return False
    
    def _create_cmem_bridges(self, identity_dir: Path, session_dir: Path):
        """Create bridge files to sync with cmem."""
        # Create bridge files that can sync with cmem format
        bridge_dir = identity_dir / "cmem_bridge"
        bridge_dir.mkdir(exist_ok=True)
        
        # Store reference to cmem session for potential sync
        bridge_info = {
            "session_dir": str(session_dir),
            "last_sync": datetime.now().isoformat(),
            "integration_active": True
        }
        
        with open(bridge_dir / "info.json", 'w') as f:
            json.dump(bridge_info, f, indent=2)
    
    def _load_json(self, filename: str, default: Any) -> Any:
        """Load JSON file or return default."""
        filepath = self.project_dir / filename
        if filepath.exists():
            with open(filepath) as f:
                return json.load(f)
        return default
    
    def _save_json(self, filename: str, data: Any):
        """Save data to JSON file."""
        filepath = self.project_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory tool calls."""
        
        if tool_name == "task_add":
            return await self._task_add(arguments)
        elif tool_name == "task_list":
            return await self._task_list(arguments)
        elif tool_name == "task_update":
            return await self._task_update(arguments)
        elif tool_name == "decision_add":
            return await self._decision_add(arguments)
        elif tool_name == "pattern_add":
            return await self._pattern_add(arguments)
        elif tool_name == "pattern_resolve":
            return await self._pattern_resolve(arguments)
        elif tool_name == "knowledge_add":
            return await self._knowledge_add(arguments)
        elif tool_name == "knowledge_get":
            return await self._knowledge_get(arguments)
        elif tool_name == "project_switch":
            return await self._project_switch(arguments)
        elif tool_name == "memory_summary":
            return await self._memory_summary()
        else:
            raise Exception(f"Unknown tool: {tool_name}")
    
    async def _task_add(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new task."""
        task = Task(
            id=str(uuid4()),
            content=args["content"],
            priority=args.get("priority", "medium"),
            assignee=args.get("assignee")
        )
        
        self.tasks[task.id] = asdict(task)
        self._save_json("tasks.json", self.tasks)
        
        # Try to sync with cmem if integration is active
        await self._sync_task_to_cmem(task, "add")
        
        return self.content_text(f"Added task: {task.id[:8]} - {task.content}")
    
    async def _task_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List tasks."""
        status_filter = args.get("status")
        
        tasks = []
        for task_id, task in self.tasks.items():
            if status_filter and task["status"] != status_filter:
                continue
            tasks.append(f"[{task['status']}] {task_id[:8]} - {task['content']} ({task['priority']})")
        
        if not tasks:
            return self.content_text("No tasks found")
        
        return self.content_text("Tasks:\n" + "\n".join(tasks))
    
    async def _task_update(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update task status."""
        task_id = args["task_id"]
        new_status = args["status"]
        
        # Find task by ID or partial ID
        full_id = None
        for tid in self.tasks:
            if tid.startswith(task_id):
                full_id = tid
                break
        
        if not full_id:
            return self.content_text(f"Task {task_id} not found")
        
        self.tasks[full_id]["status"] = new_status
        if new_status == "completed":
            self.tasks[full_id]["completed_at"] = datetime.now().isoformat()
            # Sync completion to cmem
            task_obj = Task(**self.tasks[full_id])
            await self._sync_task_to_cmem(task_obj, "complete")
        
        self._save_json("tasks.json", self.tasks)
        
        return self.content_text(f"Updated task {full_id[:8]} to {new_status}")
    
    async def _decision_add(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Record a decision."""
        decision = Decision(
            id=str(uuid4()),
            choice=args["choice"],
            reasoning=args["reasoning"],
            alternatives=args["alternatives"]
        )
        
        self.decisions[decision.id] = asdict(decision)
        self._save_json("decisions.json", self.decisions)
        
        # Try to sync with cmem
        await self._sync_decision_to_cmem(decision)
        
        return self.content_text(f"Recorded decision: {decision.choice}")
    
    async def _pattern_add(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a pattern."""
        pattern = Pattern(
            id=str(uuid4()),
            pattern=args["pattern"],
            description=args["description"],
            priority=args.get("priority", "medium"),
            effectiveness=args.get("effectiveness", 0.5)
        )
        
        self.patterns[pattern.id] = asdict(pattern)
        self._save_json("patterns.json", self.patterns)
        
        # Try to sync with cmem
        await self._sync_pattern_to_cmem(pattern, "add")
        
        return self.content_text(f"Added pattern: {pattern.pattern}")
    
    async def _pattern_resolve(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a pattern."""
        pattern_id = args["pattern_id"]
        solution = args["solution"]
        
        # Find pattern by ID or partial ID
        full_id = None
        for pid in self.patterns:
            if pid.startswith(pattern_id):
                full_id = pid
                break
        
        if not full_id:
            return self.content_text(f"Pattern {pattern_id} not found")
        
        self.patterns[full_id]["resolved"] = True
        self.patterns[full_id]["solution"] = solution
        
        self._save_json("patterns.json", self.patterns)
        
        return self.content_text(f"Resolved pattern with: {solution}")
    
    async def _knowledge_add(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Store knowledge."""
        key = args["key"]
        value = args["value"]
        category = args.get("category", "general")
        
        if category not in self.knowledge:
            self.knowledge[category] = {}
        
        self.knowledge[category][key] = {
            "value": value,
            "created_at": datetime.now().isoformat()
        }
        
        self._save_json("knowledge.json", self.knowledge)
        
        return self.content_text(f"Stored knowledge: {key} in {category}")
    
    async def _knowledge_get(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve knowledge."""
        key = args.get("key")
        category = args.get("category")
        
        results = []
        
        if key:
            # Search for specific key across categories
            for cat, items in self.knowledge.items():
                if key in items:
                    results.append(f"[{cat}] {key}: {items[key]['value']}")
        elif category:
            # Get all items in category
            if category in self.knowledge:
                for k, v in self.knowledge[category].items():
                    results.append(f"{k}: {v['value']}")
        else:
            # List all categories
            for cat in self.knowledge:
                results.append(f"Category: {cat} ({len(self.knowledge[cat])} items)")
        
        if not results:
            return self.content_text("No knowledge found")
        
        return self.content_text("\n".join(results))
    
    async def _project_switch(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Switch project context."""
        self.current_project = args["project"]
        self._load_memory()
        
        return self.content_text(f"Switched to project: {self.current_project}")
    
    async def _memory_summary(self) -> Dict[str, Any]:
        """Get memory summary."""
        # Count items by status
        task_stats = {"pending": 0, "in_progress": 0, "completed": 0}
        for task in self.tasks.values():
            task_stats[task["status"]] += 1
        
        pattern_stats = {"resolved": 0, "unresolved": 0}
        for pattern in self.patterns.values():
            if pattern["resolved"]:
                pattern_stats["resolved"] += 1
            else:
                pattern_stats["unresolved"] += 1
        
        summary = f"""Memory Summary for Project: {self.current_project}

Tasks:
  - Pending: {task_stats['pending']}
  - In Progress: {task_stats['in_progress']}
  - Completed: {task_stats['completed']}
  
Decisions: {len(self.decisions)}

Patterns:
  - Resolved: {pattern_stats['resolved']}
  - Unresolved: {pattern_stats['unresolved']}
  
Knowledge Categories: {len(self.knowledge)}
Total Knowledge Items: {sum(len(items) for items in self.knowledge.values())}
"""
        
        return self.content_text(summary)
    
    async def _sync_task_to_cmem(self, task: Task, action: str):
        """Sync task with cmem if integration is active."""
        if not self.cmem_integration:
            return
        
        try:
            import subprocess
            import asyncio
            
            if action == "add":
                # Map our priority to cmem priority
                priority_map = {"low": "low", "medium": "medium", "high": "high"}
                cmem_priority = priority_map.get(task.priority, "medium")
                
                # Add task to cmem
                cmd = ['cmem', 'task', 'add', task.content, '--priority', cmem_priority]
                if task.assignee:
                    cmd.extend(['--assignee', task.assignee])
                
                result = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
            elif action == "complete":
                # Try to find and complete corresponding cmem task
                # This is best-effort since we don't have direct ID mapping
                cmd = ['cmem', 'task', 'complete', task.content[:50]]  # Use content prefix
                result = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
        
        except Exception:
            # Fail silently - cmem sync is optional
            pass
    
    async def _sync_pattern_to_cmem(self, pattern: Pattern, action: str):
        """Sync pattern with cmem if integration is active."""
        if not self.cmem_integration:
            return
        
        try:
            import subprocess
            import asyncio
            
            if action == "add":
                # Add pattern to cmem
                cmd = ['cmem', 'pattern', 'add', pattern.pattern, pattern.description]
                if pattern.priority != "medium":
                    cmd.extend(['--priority', pattern.priority])
                
                result = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
        
        except Exception:
            # Fail silently - cmem sync is optional
            pass
    
    async def _sync_decision_to_cmem(self, decision: Decision):
        """Sync decision with cmem if integration is active."""
        if not self.cmem_integration:
            return
        
        try:
            import subprocess
            import asyncio
            
            # Add decision to cmem
            alternatives_str = ', '.join(decision.alternatives)
            cmd = ['cmem', 'decision', decision.choice, decision.reasoning, alternatives_str]
            
            result = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
        
        except Exception:
            # Fail silently - cmem sync is optional
            pass


if __name__ == "__main__":
    server = MemoryServer()
    asyncio.run(server.run())