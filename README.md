# MCP Browser

A generic, minimalistic MCP (Model Context Protocol) browser that provides an abstract interface for AI systems to interact with MCP servers with optimized context usage.

## Overview

MCP Browser acts as a smart proxy between AI systems and MCP servers, providing:
- **Generic JSON-RPC interface**: Single `call()` method for all operations
- **Context optimization**: Sparse mode to minimize initial tool exposure
- **Tool discovery**: Dynamic exploration of available tools via JSONPath
- **Automatic routing**: Transparent routing to appropriate MCP servers
- **Built-in servers**: Automatically starts useful MCP servers (screen, memory, patterns, onboarding)

## Key Features

1. **Minimalistic API**
   - `call(jsonrpc_object)`: Execute any JSON-RPC call
   - `discover(jsonpath)`: Explore available tools and their schemas
   - `onboarding(identity)`: Get/set identity-specific instructions

2. **Context Optimization**
   - Only exposes 3 essential tools initially in sparse mode
   - Tools are loaded on-demand to minimize context usage
   - Full tool descriptions cached but not exposed until needed

3. **Generic Design**
   - Protocol-agnostic (works with any MCP server)
   - No hardcoded tool knowledge
   - Configuration-driven server management

4. **Built-in Servers**
   - **Screen**: GNU screen session management for persistent processes
   - **Memory**: Project memory, tasks, decisions, and knowledge management
   - **Patterns**: Auto-response pattern management for automation
   - **Onboarding**: Identity-aware onboarding for AI contexts

## Architecture

```
mcp-browser/
├── mcp_browser/
│   ├── __init__.py
│   ├── proxy.py          # Main MCP proxy
│   ├── server.py         # MCP server management
│   ├── multi_server.py   # Multi-server manager
│   ├── registry.py       # Tool registry and discovery
│   ├── filter.py         # Message filtering and sparse mode
│   ├── buffer.py         # JSON-RPC message buffering
│   └── config.py         # Configuration management
├── mcp_servers/          # Built-in MCP servers
│   ├── base.py           # Base server implementation
│   ├── screen/           # Screen session management
│   ├── memory/           # Memory and context management
│   ├── pattern_manager/  # Pattern automation
│   └── onboarding/       # Identity-aware onboarding
├── tests/
├── docs/
└── config/
    └── default.yaml      # Default configuration
```

## Usage

```python
from mcp_browser import MCPBrowser

# Initialize browser (built-in servers start automatically)
async with MCPBrowser() as browser:
    # Execute any JSON-RPC call
    response = await browser.call({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    })
    
    # Discover tool details
    tool_info = browser.discover("$.tools[?(@.name=='Bash')]")
    
    # Use identity-aware onboarding
    response = await browser.call({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "onboarding",
            "arguments": {
                "identity": "MyProject",
                "instructions": "Remember to focus on code quality"
            }
        }
    })
```

## Sparse Mode

In sparse mode (default), only 3 tools are initially visible:
1. **mcp_discover**: Explore available tools using JSONPath
2. **mcp_call**: Execute any tool by name
3. **onboarding**: Get/set identity-specific instructions

All other tools (potentially hundreds) are hidden but fully accessible through these meta-tools.

## Design Principles

1. **Generic**: No tool-specific knowledge built into the browser
2. **Minimal**: Smallest possible API surface
3. **Efficient**: Optimized for minimal context usage
4. **Transparent**: Acts as a pass-through proxy with intelligent enhancements