"""
Utility functions for MCP Browser.
"""

import sys
from typing import Any


def debug_print(message: str):
    """Print debug message to stderr."""
    print(message, file=sys.stderr, flush=True)


def debug_json(label: str, data: Any):
    """Print JSON data to stderr for debugging."""
    import json
    print(f"{label}: {json.dumps(data)}", file=sys.stderr, flush=True)