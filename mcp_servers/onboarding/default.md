# MCP Browser - Universal Model Context Protocol Proxy

Welcome to MCP Browser! This tool acts as a proxy between AI systems and MCP servers, providing:

## Core Capabilities

### 1. **Proxy Mode**
MCP Browser acts as a transparent proxy to external MCP servers configured in `~/.claude/mcp-browser/config.yaml`. You can:
- Connect to any MCP server (filesystem, brave-search, github, etc.)
- Add new servers at runtime without restarting
- Access all tools from configured servers through the proxy

### 2. **Built-in Tools**
Always available, regardless of external servers:
- **Screen Management** - Create/manage GNU screen sessions
- **Memory & Tasks** - Persistent memory and task tracking
- **Pattern Manager** - Auto-response patterns
- **Onboarding** - Context-specific instructions (this tool)

### 3. **Sparse Mode Optimization**
To minimize context usage, only 3 meta-tools are shown initially:
- `mcp_discover` - Discover all available tools using JSONPath
- `mcp_call` - Execute any tool by constructing JSON-RPC calls
- `onboarding` - Get/set identity-specific instructions

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