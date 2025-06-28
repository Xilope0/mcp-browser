# MCP Browser

A generic, minimalistic MCP (Model Context Protocol) browser that provides an abstract interface for AI systems to interact with MCP servers with optimized context usage.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3+-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![AI Generated](https://img.shields.io/badge/AI-Generated-green.svg)](CLAUDE.md)

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
│   ├── DESIGN.md         # Architecture and design details
│   ├── WORKING_DIRECTORIES.md  # Working directory and process guide
│   └── ...
└── config/
    └── default.yaml      # Default configuration
```

**Important**: See [docs/WORKING_DIRECTORIES.md](docs/WORKING_DIRECTORIES.md) for detailed information about working directories, process architecture, and file path handling.

## Installation

```bash
# Clone the repository
git clone https://github.com/Xilope0/mcp-browser.git
cd mcp-browser

# Install in development mode
pip install -e .

# Or install directly from GitHub
pip install git+https://github.com/Xilope0/mcp-browser.git
```

## Quick Start

```bash
# Run enhanced interactive mode (NEW!)
./mcp-browser-interactive

# Run basic interactive mode
mcp-browser

# Run as MCP server (for chaining)
mcp-browser --mode server

# Connect to specific MCP server
mcp-browser --server claude-code

# Generate AI documentation
python setup.py aidocs
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

## Enhanced Interactive Mode

The new `./mcp-browser-interactive` provides a much better testing and exploration experience:

**Features:**
- **Tab completion** for commands and tool names
- **Command history** with readline support  
- **Smart argument parsing** with key=value syntax
- **Built-in help** and tool discovery
- **Test mode** to try tools with sample data
- **Direct tool calls** without verbose JSON-RPC syntax

**Interactive Commands:**
```bash
help                    # Show available commands
list [pattern]          # List tools (with optional filter)
discover <jsonpath>     # Explore using JSONPath
call <tool> key=value   # Call tool with arguments
test <tool>             # Test tool with sample data
<tool> key=value        # Direct tool call (shortcut)
onboard <identity>      # Manage onboarding instructions
status                  # Show connection status
```

**Example Session:**
```bash
mcp> list bash                              # Find bash-related tools
mcp> discover $.tools[*].name               # List all tool names  
mcp> test Bash                              # Test Bash tool
mcp> Bash command="ls -la"                  # Direct tool call
mcp> onboard Claude "Focus on code quality" # Set onboarding
```

## Design Principles

1. **Generic**: No tool-specific knowledge built into the browser
2. **Minimal**: Smallest possible API surface
3. **Efficient**: Optimized for minimal context usage
4. **Transparent**: Acts as a pass-through proxy with intelligent enhancements

## Contributing

This project is developed exclusively by AI assistants. See [CLAUDE.md](CLAUDE.md) for details about the AI-only development process.

If you're an AI assistant working on this project:
1. Read CLAUDE.md for development guidelines
2. Generate documentation with `python setup.py aidocs`
3. Test changes with the example scripts
4. Maintain context efficiency as the primary goal

## License

This project is licensed under the GNU General Public License v3.0 or later (GPLv3+) - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Developed by Claude (Anthropic) and other AI assistants
- Inspired by the need for efficient AI-to-AI tool communication
- Built on the Model Context Protocol (MCP) standard