# Working Directories and Process Architecture

This document clarifies the working directory expectations and process architecture for MCP Browser.

## Overview

MCP Browser involves multiple processes with different roles:

1. **Your Application** (AI client)
2. **MCP Browser** (Python library)
3. **MCP Server** (subprocess, e.g., claude mcp serve)

## Process Architecture

```
┌─────────────────────────────────────┐
│ Your Application Process            │
│ Working Dir: /your/project          │
│                                     │
│  ┌─────────────────────────────┐    │
│  │ MCP Browser Library         │    │
│  │ (imported Python module)    │    │
│  └──────────┬──────────────────┘    │
│             │ spawns               │
└─────────────┼──────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│ MCP Server Process                  │
│ Working Dir: /your/project          │
│ (inherits from parent)              │
│                                     │
│ Examples:                           │
│ - claude mcp serve                  │
│ - python -m my_mcp_server           │
└─────────────────────────────────────┘
```

## Working Directory Guidelines

### 1. Running MCP Browser

When you use MCP Browser, it runs in your application's process:

```bash
# Run from your project directory
cd /path/to/your/project
python your_script.py
```

### 2. MCP Server Working Directory

MCP servers spawned by MCP Browser inherit the working directory:

```python
# If you run this from /home/user/myproject
async with MCPBrowser() as browser:
    # The MCP server process will have working directory: /home/user/myproject
    pass
```

### 3. File Path Recommendations

**Always use absolute paths** when passing file arguments to tools:

```python
# Good - absolute path
await browser.call({
    "method": "tools/call",
    "params": {
        "name": "Read",
        "arguments": {
            "file_path": "/home/user/myproject/data.txt"
        }
    }
})

# Bad - relative path (may not work as expected)
await browser.call({
    "method": "tools/call",
    "params": {
        "name": "Read",
        "arguments": {
            "file_path": "data.txt"  # Avoid this!
        }
    }
})
```

### 4. Configuration File Locations

MCP Browser looks for configuration in these locations (in order):

1. Command-line specified: `--config /path/to/config.yaml`
2. Project directory: `./.mcp-browser/config.yaml`
3. User home: `~/.mcp-browser/config.yaml`
4. Built-in defaults

## Common Scenarios

### Scenario 1: Testing Claude Connection

```bash
# Working directory matters!
cd /path/to/mcp-browser
python test_claude_connection.py

# The test will:
# 1. Run from /path/to/mcp-browser
# 2. Search for claude binary in PATH
# 3. Spawn claude process with same working directory
# 4. Create test files in system temp directory
```

### Scenario 2: Using in Your Project

```python
# your_project/main.py
import os
from pathlib import Path
from mcp_browser import MCPBrowser

# Always know your working directory
print(f"Working directory: {os.getcwd()}")
project_root = Path(__file__).parent

async def main():
    async with MCPBrowser() as browser:
        # Read file using absolute path
        file_path = project_root / "data" / "input.txt"
        response = await browser.call({
            "method": "tools/call",
            "params": {
                "name": "Read",
                "arguments": {
                    "file_path": str(file_path.absolute())
                }
            }
        })
```

### Scenario 3: Running as MCP Server

When MCP Browser runs in server mode, it still maintains the same architecture:

```bash
# Terminal 1: Run MCP Browser as server
cd /path/to/your/project
mcp-browser --mode server

# Terminal 2: Connect to it
# The MCP Browser server can spawn other MCP servers as needed
```

## Environment Variables

### Finding Claude Binary

Set `CLAUDE_PATH` if claude is not in your PATH:

```bash
export CLAUDE_PATH=/custom/location/claude
python test_claude_connection.py
```

### MCP Server Environment

MCP servers inherit environment variables from MCP Browser:

```yaml
# config.yaml
servers:
  my_server:
    command: ["my-mcp-server"]
    env:
      # These are added to the inherited environment
      API_KEY: "${API_KEY}"
      WORKING_DIR: "${PWD}"  # Explicitly pass working directory if needed
```

## Troubleshooting

### Issue: "File not found" errors

**Solution**: Use absolute paths
```python
# Instead of:
"file_path": "data.txt"

# Use:
"file_path": os.path.abspath("data.txt")
# or
"file_path": str(Path("data.txt").absolute())
```

### Issue: Claude binary not found

**Solution**: Check these locations:
1. Is claude in your PATH? `which claude`
2. Set CLAUDE_PATH: `export CLAUDE_PATH=/path/to/claude`
3. Check standard locations: `/usr/local/bin`, `~/.local/bin`

### Issue: Wrong working directory

**Solution**: Always check and set explicitly:
```python
import os
print(f"Current working directory: {os.getcwd()}")

# Change if needed
os.chdir("/desired/working/directory")
```

## Best Practices

1. **Document working directory requirements** in your scripts
2. **Use absolute paths** for all file operations
3. **Check working directory** at the start of your scripts
4. **Set CLAUDE_PATH** in your environment if claude is not in PATH
5. **Test from the correct directory** - where your code will actually run

## Example: Complete Setup

```bash
# 1. Set up environment (add to ~/.bashrc or ~/.zshrc)
export CLAUDE_PATH=/usr/local/bin/claude
export MCP_BROWSER_CONFIG=~/.mcp-browser/config.yaml

# 2. Create test script with clear documentation
cat > test_mcp.py << 'EOF'
#!/usr/bin/env python3
"""
Test MCP Browser functionality.

Working Directory: Run from your project root
Required: claude must be in PATH or CLAUDE_PATH set
"""
import os
from pathlib import Path

print(f"Working directory: {os.getcwd()}")
print(f"Script location: {Path(__file__).resolve()}")

# ... rest of your code ...
EOF

# 3. Run from correct directory
cd /path/to/your/project
python test_mcp.py
```