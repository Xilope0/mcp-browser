"""
MCP Browser - A generic, minimalistic MCP protocol interface.

Provides an abstract interface for AI systems to interact with MCP servers
with optimized context usage through sparse mode and on-demand tool discovery.

Copyright (C) 2024 Claude4Ξlope <xilope@esus.name>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from .proxy import MCPBrowser

__version__ = "0.2.0"
__author__ = "Claude4Ξlope"
__email__ = "xilope@esus.name"
__license__ = "GPLv3+"
__all__ = ["MCPBrowser"]