#!/usr/bin/env python3
"""
Simple unit tests that don't require server startup.
"""

import pytest
from mcp_browser.registry import ToolRegistry
from mcp_browser.filter import MessageFilter, VirtualToolHandler


def test_tool_registry():
    """Test basic tool registry functionality."""
    registry = ToolRegistry()
    
    # Add some tools
    tools = [
        {"name": "tool1", "description": "First tool"},
        {"name": "tool2", "description": "Second tool"}
    ]
    registry.update_tools(tools)
    
    # Test retrieval
    assert registry.get_tool("tool1")["description"] == "First tool"
    assert registry.get_all_tool_names() == ["tool1", "tool2"]
    
    # Test JSONPath discovery
    assert registry.discover("$.tools[*].name") == ["tool1", "tool2"]
    assert registry.discover("$.tools[0].name") == "tool1"
    
    print("✓ Tool registry tests passed")


def test_sparse_mode():
    """Test sparse mode functionality."""
    registry = ToolRegistry()
    registry.update_tools([
        {"name": "tool1", "description": "Tool 1"},
        {"name": "tool2", "description": "Tool 2"},
        {"name": "tool3", "description": "Tool 3"},
        {"name": "tool4", "description": "Tool 4"},
        {"name": "tool5", "description": "Tool 5"}
    ])
    
    # Get sparse tools
    sparse = registry.get_sparse_tools()
    assert len(sparse) == 3
    assert sparse[0]["name"] == "mcp_discover"
    assert sparse[1]["name"] == "mcp_call"
    assert sparse[2]["name"] == "onboarding"
    
    # Check tool count in description
    assert "5 hidden tools" in sparse[0]["description"]
    
    print("✓ Sparse mode tests passed")


def test_message_filter():
    """Test message filtering."""
    registry = ToolRegistry()
    filter = MessageFilter(registry, sparse_mode=True)
    
    # Test tools/list response filtering
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {"name": "tool1", "description": "Tool 1"},
                {"name": "tool2", "description": "Tool 2"}
            ]
        }
    }
    
    filtered = filter.filter_incoming(message)
    assert filtered is not None
    assert len(filtered["result"]["tools"]) == 3  # Sparse tools
    assert filtered["result"]["tools"][0]["name"] == "mcp_discover"
    
    print("✓ Message filter tests passed")


if __name__ == "__main__":
    test_tool_registry()
    test_sparse_mode()
    test_message_filter()
    print("\n✅ All simple tests passed!")