# MCP Browser Design Documentation

## Overview

MCP Browser is a generic, minimalistic proxy for the Model Context Protocol (MCP) that provides an abstract interface optimized for AI systems. It acts as an intelligent intermediary between AI clients and MCP servers, implementing context optimization strategies inspired by claude-composer.

### Process Architecture

- **MCP Browser**: Python library that runs in your application process
- **MCP Server**: Separate subprocess spawned by MCP Browser (e.g., `claude mcp serve`)
- **Working Directory**: MCP servers inherit the working directory from where MCP Browser is initialized
- **File Paths**: Always use absolute paths when passing file arguments to tools

## Design Principles

### 1. **Minimalism**
- Only two public methods: `call()` and `discover()`
- No tool-specific knowledge built into the browser
- Generic JSON-RPC interface for all operations

### 2. **Context Optimization**
- Sparse mode reduces initial tool exposure from potentially hundreds to just 2
- Tools are discovered on-demand using JSONPath queries
- Full functionality maintained while minimizing token usage

### 3. **Transparency**
- Acts as a pass-through proxy with intelligent enhancements
- Preserves full MCP protocol compatibility
- No modification of actual tool functionality

### 4. **Genericity**
- Works with any MCP server without modification
- Configuration-driven server management
- Protocol-agnostic design

## Architecture

### Core Components

```
┌─────────────────┐
│   AI Client     │  <- Your AI application (runs in your project directory)
│  (uses 2 methods)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   MCP Browser   │  <- Python library (runs in same process as client)
│  ┌───────────┐  │
│  │   Proxy   │  │
│  ├───────────┤  │
│  │  Registry │  │
│  ├───────────┤  │
│  │  Filter   │  │
│  └───────────┘  │
└────────┬────────┘
         │ (spawns subprocess)
         ▼
┌─────────────────┐
│   MCP Server    │  <- Separate process (e.g., claude mcp serve)
│  (any server)   │     Working directory: inherits from MCP Browser
└─────────────────┘
```

### Component Responsibilities

1. **Proxy (`proxy.py`)**
   - Main entry point and API
   - Manages MCP server lifecycle
   - Routes messages between client and server
   - Handles virtual tool calls

2. **Registry (`registry.py`)**
   - Stores full tool descriptions
   - Provides JSONPath-based discovery
   - Generates sparse tool list

3. **Filter (`filter.py`)**
   - Intercepts and modifies messages
   - Implements sparse mode transformation
   - Handles virtual tool responses

4. **Server (`server.py`)**
   - Spawns and manages MCP server process
   - Handles bidirectional communication
   - Manages request/response correlation

5. **Buffer (`buffer.py`)**
   - Ensures atomic JSON-RPC message delivery
   - Handles partial message buffering

## Sparse Mode Operation

### Initial State
When a client requests `tools/list`, instead of returning all tools:

```json
{
  "result": {
    "tools": [
      {"name": "tool1", "description": "..."},
      {"name": "tool2", "description": "..."},
      ... // potentially hundreds more
    ]
  }
}
```

### Sparse Response
The browser returns only meta-tools:

```json
{
  "result": {
    "tools": [
      {
        "name": "mcp_discover",
        "description": "Discover available tools using JSONPath. 150 tools available.",
        "inputSchema": {...}
      },
      {
        "name": "mcp_call", 
        "description": "Execute any MCP tool by constructing a JSON-RPC call.",
        "inputSchema": {...}
      }
    ]
  }
}
```

### Tool Discovery Flow

1. Client uses `mcp_discover` to explore tools:
   ```python
   # Working directory: your project root
   # Process: AI client using MCP Browser
   browser.discover("$.tools[?(@.name contains 'file')]")
   # Returns all file-related tools
   ```

2. Client uses `mcp_call` to execute any tool:
   ```python
   # Working directory: your project root
   # Process: AI client -> MCP Browser -> MCP Server
   await browser.call({
     "method": "tools/call",
     "params": {
       "name": "mcp_call",
       "arguments": {
         "method": "tools/call",
         "params": {
           "name": "Read",
           "arguments": {
             "file_path": "/absolute/path/to/file.txt"  # Always use absolute paths
           }
         }
       }
     }
   })
   ```

## Message Flow

### Standard Tool Call
```
Client -> Browser: tools/call(mcp_call, {method: "tools/call", params: {...}})
Browser -> Server: tools/call(ActualTool, {...})
Server -> Browser: Result
Browser -> Client: Result
```

### Discovery Call
```
Client -> Browser: tools/call(mcp_discover, {jsonpath: "$.tools[*].name"})
Browser: Process locally using registry
Browser -> Client: ["tool1", "tool2", ...]
```

## Configuration System

### Hierarchical Loading
1. Command-line arguments (highest priority)
2. Project configuration (`.mcp-browser/config.yaml`)
3. User configuration (`~/.mcp-browser/config.yaml`)
4. Default configuration (lowest priority)

### Server Configuration
```yaml
# File location: ~/.mcp-browser/config.yaml or .mcp-browser/config.yaml
# Working directory: Configuration is loaded relative to where you run MCP Browser

servers:
  my_server:
    command: ["python", "-m", "my_mcp_server"]
    args: ["--port", "8080"]
    env:
      API_KEY: "${API_KEY}"
    description: "My custom MCP server"
    # Note: Server process inherits working directory from MCP Browser
```

## Key Innovations

### 1. **Virtual Tool Pattern**
Instead of modifying the MCP protocol, we inject virtual tools that exist only in the browser layer. These tools (`mcp_discover`, `mcp_call`) provide meta-functionality for tool discovery and execution.

### 2. **JSONPath Discovery**
Using JSONPath for tool discovery provides a flexible, powerful query language that AI systems can easily use to explore available functionality.

### 3. **Transparent Routing**
The `mcp_call` tool acts as a universal router, allowing execution of any tool without needing to expose all tools initially.

### 4. **Context Budget**
By reducing initial tool exposure from O(n) to O(1), we dramatically reduce context usage while maintaining full functionality.

## Comparison with Claude Composer

| Feature | Claude Composer | MCP Browser |
|---------|----------------|-------------|
| Language | TypeScript | Python |
| Target | Claude Code CLI | Generic AI systems |
| API | CLI wrapper | Library API |
| Tools | Hardcoded meta-tools | Generic virtual tools |
| Discovery | get_tool_description | JSONPath queries |
| Router | use_tool | mcp_call |
| Config | YAML toolsets | YAML servers |

## Future Enhancements

1. **Caching Layer**: Cache tool responses and descriptions
2. **Multi-Server Support**: Route to multiple MCP servers
3. **Streaming Support**: Handle streaming responses
4. **Tool Namespacing**: Automatic namespace management
5. **Metrics**: Usage statistics and performance monitoring