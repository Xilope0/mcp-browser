"""
MCP Browser - A generic, minimalistic MCP protocol interface.

Provides an abstract interface for AI systems to interact with MCP servers
with optimized context usage through sparse mode and on-demand tool discovery.
"""

from .proxy import MCPBrowser

__version__ = "0.1.0"
__all__ = ["MCPBrowser"]