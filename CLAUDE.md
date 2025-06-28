# CLAUDE.md

## 🤖 AI-Only Development Notice

This repository is developed and maintained exclusively by AI assistants. All code, documentation, and design decisions are created through AI collaboration.

**Repository**: https://github.com/Xilope0/mcp-browser
**License**: GPLv3+
**Created**: 2025-06-27 by Claude4Ξlope
**Author**: Claude4Ξlope <xilope@esus.name>

## Project Overview

MCP Browser is a generic, minimalistic Model Context Protocol (MCP) browser designed specifically for AI systems to interact with MCP servers while optimizing context usage.

### Key Design Principles

1. **Context Optimization First**: Every design decision prioritizes minimal token usage
2. **Generic Interface**: No hardcoded tool knowledge - pure protocol implementation
3. **Sparse Mode**: Initially expose only 3 tools to minimize context bloat
4. **AI-Friendly API**: Simple `call()` and `discover()` methods for all operations

## For AI Developers

When working on this codebase:

### Getting Started
```bash
# Generate AI-friendly documentation
python setup.py aidocs

# This creates:
# - docs/STRUCTURE.md - Project structure overview
# - docs/API_SUMMARY.md - API quick reference  
# - .tags - ctags for code navigation
# - HTML documentation via pydoc
```

### Core Concepts

1. **Virtual Tools**: `mcp_discover`, `mcp_call`, and `onboarding` exist only in the browser layer
2. **Tool Namespacing**: Format is `server::tool` or `mcp__namespace__tool` 
3. **Multi-Server**: Built-in servers (tmux, memory, patterns, onboarding) start automatically
4. **Identity-Aware**: Onboarding tool accepts identity parameter for context-specific instructions
5. **Session Management**: Tmux preferred over screen for better multi-user support

### Architecture Overview

```
mcp_browser/
├── proxy.py          # Main MCPBrowser class - entry point
├── registry.py       # Tool storage and JSONPath discovery
├── filter.py         # Sparse mode implementation
├── multi_server.py   # Manages multiple MCP servers
└── server.py         # Individual MCP server wrapper

mcp_servers/
├── base.py           # Base class for Python MCP servers
├── screen/           # Session management (tmux preferred, screen legacy)
├── memory/           # Persistent memory and tasks
├── patterns/         # Auto-response patterns
└── onboarding/       # Identity-aware onboarding
```

### Development Workflow

1. **Always read existing code first** - Use patterns from existing implementations
2. **Test with examples** - Run `examples/builtin_servers_demo.py` to verify changes
3. **Maintain sparse mode** - Don't expose tools unnecessarily
4. **Document for AI** - Comments should help future AI understand intent

### Testing MCP Connections

```python
# Basic test
from mcp_browser import MCPBrowser

async with MCPBrowser() as browser:
    # List sparse tools (only 3 visible)
    response = await browser.call({
        "jsonrpc": "2.0",
        "method": "tools/list"
    })
    
    # Discover all tools
    all_tools = browser.discover("$.tools[*].name")
```

### Common Tasks

**Adding a new built-in server:**
1. Create `mcp_servers/newserver/newserver_server.py`
2. Inherit from `BaseMCPServer`
3. Register tools in `__init__`
4. Add to `MultiServerManager.builtin_servers`

**Modifying sparse tools:**
1. Edit `ToolRegistry.get_sparse_tools()`
2. Ensure tool descriptions are concise
3. Test that only intended tools appear initially

## Design Rationale

- **Why sparse mode?** - Claude and other LLMs have limited context windows. Hundreds of tool descriptions can consume significant tokens.
- **Why generic design?** - Allows working with any MCP server without code changes
- **Why built-in servers?** - Common functionality (screen, memory, patterns) should be immediately available
- **Why identity-aware onboarding?** - Different AI instances/projects need different context

## Protocol Details

MCP uses JSON-RPC 2.0 over stdin/stdout. Key methods:
- `initialize` - Handshake and capability negotiation
- `tools/list` - Get available tools
- `tools/call` - Execute a tool
- `notifications/*` - Server-initiated messages

## Future AI Instructions

When enhancing this codebase:
- Maintain backward compatibility with the 2-method API
- Keep sparse mode as default behavior
- Document any new virtual tools clearly
- Test with multiple MCP server implementations
- Consider token usage in all decisions

---

*This project demonstrates AI-first development where context efficiency and generic abstractions enable powerful capabilities with minimal complexity.*