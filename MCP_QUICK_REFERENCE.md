# MCP Quick Reference for Fresh Claude Instances

## 🔗 MCP Interface Access

**Status**: ✅ mcp-browser is configured and running
- **Claude Desktop** → **mcp-browser** → **27 tools from 7 servers**
- **Config**: `/home/claude/.claude/mcp-browser/config.yaml`
- **Tools**: Built-in servers (screen, memory, patterns, onboarding) + external (claude-code, brave-search, filesystem, github)

## 🚀 Quick MCP Commands

### Discovery (Context-Safe)
```python
# List all available tool names (27 total)
mcp_discover(jsonpath="$.tools[*].name")

# Find memory-related tools (regex support)
mcp_discover(jsonpath="$.tools[?(@.name =~ /memory|task|pattern/i)]")

# Get server information
mcp_discover(jsonpath="$.servers[*].name")

# Get claude-code tools specifically
mcp_discover(jsonpath="$.servers['claude-code'].tools[*].name")
```

### Tool Execution
```python
# Call any discovered tool
mcp_call(
    method="tools/call",
    params={
        "name": "task_list", 
        "arguments": {"status": "pending"}
    }
)

# Call claude-code tools
mcp_call(
    method="tools/call",
    params={
        "name": "claude-code::read_file",
        "arguments": {"path": "/path/to/file.py"}
    }
)
```

## 🧠 Memory & Handoff System

### Get Current Context
```bash
cmem handoff           # Quick context summary
cmem task list         # Active tasks
cmem pattern list      # Available patterns
```

### Essential Memory Tools (via MCP)
- `task_add` - Add new tasks with priority/assignee
- `task_update` - Update task status
- `memory_summary` - Get project overview
- `knowledge_add` - Store information
- `pattern_add` - Record learning patterns

## 🛠️ Built-in MCP Tools Available

**Screen Management (8 tools)**:
- `create_session`, `execute`, `peek`, `list_sessions`, `kill_session`

**Memory & Tasks (10 tools)**:
- `task_add`, `task_list`, `task_update`, `decision_add`, `pattern_add`

**Auto-Response Patterns (5 tools)**:
- `add_pattern`, `list_patterns`, `test_pattern`

**Identity & Onboarding (4 tools)**:
- `onboarding`, `onboarding_list`, `onboarding_export`

## 🎯 Current Project Context

**Location**: `/mnt/data/claude/claude` (bind mounted from `/home/claude`)
**Active Projects**: 
- `mcp-browser` (✅ Working, integrated)
- `xilope` (🔄 In development - XDG config system needed)

**Memory Storage**: `/mnt/data/claude/claude/.mcp-memory/`
**cmem Wrapper**: `/mnt/data/claude/claude/bin/cmem` → `/usr/local/bin/cmem`

## 🔧 For Fresh Claude Instances

1. **Read this file** for MCP context
2. **Run `cmem handoff`** for session continuity  
3. **Use `mcp_discover`** to explore available tools
4. **Check `CLAUDE.md`** for project-specific instructions
5. **Access Xilope onboarding**: `onboarding(identity="xilope_production")`

## 📚 Documentation Locations

- **Handoff Guide**: `/home/claude/claude-utils/mcp-browser/HANDOFF_INSTRUCTIONS.md`
- **Xilope Production**: `/home/claude/claude-utils/mcp-browser/mcp_servers/onboarding/xilope_production.md`
- **MCP Config**: `/home/claude/.claude/mcp-browser/config.yaml`
- **Memory Files**: `/mnt/data/claude/claude/.mcp-memory/default/`

## ⚡ Generate Complete API Docs

```bash
cd /home/claude/claude-utils/mcp-browser
python setup.py gen_apidoc
# Creates: mcp_api_documentation.json (27 tools, 7 servers documented)
```

This provides **complete MCP ecosystem access** with persistent memory across Claude sessions.