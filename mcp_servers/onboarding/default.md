# MCP Browser - Universal Model Context Protocol Proxy

Welcome to MCP Browser! This tool solves the **context explosion problem** by acting as a smart proxy between AI systems and potentially hundreds of MCP tools.

## The Context Problem MCP Browser Solves

Traditional MCP setups expose ALL tools to the AI context immediately, which can easily consume thousands of tokens. MCP Browser implements a **minimal-to-maximal interface pattern**:

- **What AI sees**: Only 3 simple meta-tools (minimal context usage)
- **What AI can access**: All tools from all configured MCP servers (maximal functionality)
- **How it works**: JSONRPC proxy that filters and routes tool calls transparently

## Core Architecture: Minimal Interface → Maximal Backend

### 1. **Sparse Mode Frontend** (What AI Sees)
Only 3 meta-tools are exposed, preventing context explosion:
- `mcp_discover` - Explore available tools without loading them into context
- `mcp_call` - Execute any tool by constructing JSON-RPC calls
- `onboarding` - Identity-aware persistent instructions

### 2. **Transparent JSONRPC Proxy** (How It Works)
- **Intercepts** `tools/list` responses and replaces full catalogs with sparse tools
- **Routes** tool calls to appropriate internal or external MCP servers  
- **Transforms** meta-tool calls into actual JSONRPC requests
- **Buffers** responses and handles async message routing

### 3. **Multi-Server Backend** (What's Available)
- **Built-in Servers**: Screen, Memory, Patterns, Onboarding (always available)
- **External Servers**: Any MCP server configured in `~/.claude/mcp-browser/config.yaml`
- **Runtime Discovery**: New servers added without restart via config monitoring

## Key Insight: Tool Discovery Without Context Pollution

Instead of loading hundreds of tool descriptions into context, AI can discover them on-demand:

```python
# Explore what's available (uses 0 additional context)
mcp_discover(jsonpath="$.tools[*].name")

# Get specific tool details only when needed  
mcp_discover(jsonpath="$.tools[?(@.name=='brave_web_search')]")

# Execute discovered tools
mcp_call(method="tools/call", params={"name": "brave_web_search", "arguments": {...}})
```

## Discovery Examples

```python
# Discover all available tools (built-in + external servers)
mcp_discover(jsonpath="$.tools[*].name")

# Get tools from specific server
mcp_discover(jsonpath="$.servers.brave-search.tools[*].name")

# Get all configured servers
mcp_discover(jsonpath="$.servers[*].name")

# Get tool details
mcp_discover(jsonpath="$.tools[?(@.name=='brave_web_search')]")
```

## Using External Server Tools

Once discovered, call any tool through `mcp_call`:

```python
# Example: Brave search
mcp_call(
    method="tools/call",
    params={
        "name": "brave_web_search",
        "arguments": {"query": "MCP protocol"}
    }
)

# Example: GitHub
mcp_call(
    method="tools/call", 
    params={
        "name": "search_repositories",
        "arguments": {"query": "mcp-browser"}
    }
)
```

## Runtime Configuration

The config file at `~/.claude/mcp-browser/config.yaml` is monitored for changes. You can:
1. Add new server configurations
2. The proxy will automatically reload and make new tools available
3. No restart required!

Example config addition:
```yaml
servers:
  github:
    command: ["npx", "-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
```

## Architecture

```
Claude Desktop → MCP Browser (Proxy) → External MCP Servers
                       ↓
                 Built-in Servers
```

MCP Browser provides a unified interface to multiple MCP servers while optimizing context usage through sparse mode and discovery.