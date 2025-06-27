# MCP Browser v0.1.0 Release Notes

## Initial Release - 2025-06-27

### Overview
MCP Browser is a generic, minimalistic Model Context Protocol browser designed for AI systems to interact with MCP servers while optimizing context usage.

### Key Features
- **Minimal API**: Just two methods - `call()` and `discover()`
- **Sparse Mode**: Initially exposes only 3 tools to minimize context usage
- **Built-in Servers**: 4 useful MCP servers included
  - Screen: GNU screen session management
  - Memory: Persistent project memory
  - Patterns: Auto-response patterns
  - Onboarding: Identity-aware instructions
- **Multi-Server Support**: Connect to multiple MCP servers simultaneously
- **JSONPath Discovery**: Explore tools dynamically

### Technical Details
- Written in Python 3.8+
- Async/await architecture
- JSON-RPC 2.0 protocol
- Configurable via YAML

### Installation
```bash
pip install git+https://github.com/Xilope0/mcp-browser.git
```

### License
GPLv3+ - GNU General Public License v3.0 or later

### Author
Claude4Ξlope <xilope@esus.name>

### Note
This project is developed exclusively by AI assistants. See CLAUDE.md for details.