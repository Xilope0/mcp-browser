# Xilope Production Environment - MCP Browser Guide

Welcome to Xilope's production MCP Browser setup! This environment provides integrated access to both MCP tools and the Claude Memory (cmem) system.

## Production Architecture

### Memory Storage Integration
- **Local Storage**: `/mnt/data/claude/claude/.mcp-memory/`
- **cmem Integration**: Bidirectional sync via `/mnt/data/claude/claude/bin/cmem`
- **Identity-Based**: Each project gets separate memory space
- **Persistent**: Memory survives across AI assistant sessions

### Built-in Servers Available
1. **Memory Server** (`builtin:memory::`):
   - `task_add`, `task_list`, `task_update` - Task management with cmem sync
   - `decision_add` - Decision tracking with reasoning
   - `pattern_add`, `pattern_resolve` - Learning pattern management
   - `knowledge_add`, `knowledge_get` - Fact storage and retrieval
   - `project_switch` - Switch between project contexts
   - `memory_summary` - Get overview of stored information

2. **Screen Server** (`builtin:screen::`):
   - `create_session`, `execute`, `peek` - GNU screen management
   - `list_sessions`, `kill_session` - Session lifecycle
   - `enable_multiuser`, `attach_multiuser`, `add_user` - Collaboration

3. **Pattern Server** (`builtin:patterns::`):
   - `add_pattern`, `list_patterns` - Auto-response pattern management
   - `test_pattern`, `execute_pattern` - Pattern execution

4. **Onboarding Server** (`builtin:onboarding::`):
   - `onboarding` - Identity-aware instructions
   - `onboarding_list`, `onboarding_delete`, `onboarding_export` - Management

## Production Workflows

### Starting a Session
```python
# Check what servers are available
mcp_discover(jsonpath="$.servers[*].name")

# List all memory tools for task management
mcp_discover(jsonpath="$.tools[?(@.name =~ /memory|task/)]")

# Check current project context
mcp_call(
    method="tools/call",
    params={
        "name": "builtin:memory::memory_summary",
        "arguments": {}
    }
)
```

### Task Management with cmem Sync
```python
# Add a new task (automatically syncs to cmem)
mcp_call(
    method="tools/call",
    params={
        "name": "builtin:memory::task_add",
        "arguments": {
            "content": "Implement feature X",
            "priority": "high",
            "assignee": "next-ai"
        }
    }
)

# List active tasks
mcp_call(
    method="tools/call", 
    params={
        "name": "builtin:memory::task_list",
        "arguments": {"status": "pending"}
    }
)

# Update task status (syncs completion to cmem)
mcp_call(
    method="tools/call",
    params={
        "name": "builtin:memory::task_update", 
        "arguments": {
            "task_id": "abc123",
            "status": "completed"
        }
    }
)
```

### Decision and Pattern Management
```python
# Record important decisions (synced to cmem)
mcp_call(
    method="tools/call",
    params={
        "name": "builtin:memory::decision_add",
        "arguments": {
            "choice": "Use Docker for deployment",
            "reasoning": "Simplifies environment management",
            "alternatives": ["Native install", "VM deployment"]
        }
    }
)

# Add learning patterns (synced to cmem)
mcp_call(
    method="tools/call",
    params={
        "name": "builtin:memory::pattern_add",
        "arguments": {
            "pattern": "Always test before commit",
            "description": "Run full test suite before any git commit",
            "priority": "high"
        }
    }
)
```

### Screen Session Management
```python
# Create a development session
mcp_call(
    method="tools/call",
    params={
        "name": "builtin:screen::create_session", 
        "arguments": {
            "session_name": "development",
            "working_directory": "/mnt/data/claude/claude"
        }
    }
)

# Execute commands in session
mcp_call(
    method="tools/call",
    params={
        "name": "builtin:screen::execute",
        "arguments": {
            "session_name": "development",
            "command": "git status"
        }
    }
)

# Peek at session output
mcp_call(
    method="tools/call",
    params={
        "name": "builtin:screen::peek",
        "arguments": {"session_name": "development"}
    }
)
```

### Project Context Switching
```python
# Switch to different project memory space
mcp_call(
    method="tools/call",
    params={
        "name": "builtin:memory::project_switch",
        "arguments": {"project_name": "mcp-browser"}
    }
)

# Use onboarding for project-specific instructions
mcp_call(
    method="tools/call",
    params={
        "name": "builtin:onboarding::onboarding",
        "arguments": {
            "identity": "mcp-browser",
            "instructions": "Focus on context optimization and AI-first development"
        }
    }
)
```

## cmem Integration Details

### Memory Storage Structure
```
/mnt/data/claude/claude/.mcp-memory/
├── default/                    # Default project space
│   ├── tasks.json             # Task storage
│   ├── decisions.json         # Decision history  
│   ├── patterns.json          # Learning patterns
│   └── knowledge.json         # Knowledge base
├── mcp-browser/               # Project-specific space
└── [other-projects]/          # Additional projects
```

### cmem Wrapper
- **Location**: `/mnt/data/claude/claude/bin/cmem`
- **Function**: Wraps `/usr/local/bin/cmem` with proper directory context
- **Integration**: Automatic bidirectional sync with MCP memory server
- **Commands**: `cmem handoff`, `cmem task add`, `cmem pattern add`, etc.

### Sync Behavior
- **Automatic**: All memory operations sync to cmem in background
- **Graceful**: If cmem unavailable, operations continue locally
- **Identity-Aware**: Each project gets separate cmem context
- **Bidirectional**: Changes in either system propagate to the other

## Production Best Practices

1. **Always check memory summary** at start of session
2. **Use task management** to track work across AI sessions  
3. **Record decisions** with reasoning for future reference
4. **Create patterns** to capture effective approaches
5. **Switch project contexts** when working on different codebases
6. **Use screen sessions** for persistent development environments

## Error Handling

If cmem sync fails:
- Operations continue with local storage
- Sync retries automatically when cmem becomes available
- No data loss occurs during temporary cmem unavailability

This production setup ensures seamless AI assistant transitions while maintaining full project context and memory across sessions.