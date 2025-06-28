#!/usr/bin/env python3
"""
Test suite for the enhanced interactive MCP client.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_browser.interactive_client import InteractiveMCPClient
from mcp_browser.proxy import MCPBrowser


class TestInteractiveMCPClient:
    """Test the interactive MCP client functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.client = InteractiveMCPClient(use_daemon=False)
        
    def test_initialization(self):
        """Test client initialization."""
        assert self.client.server_name is None
        assert self.client.use_daemon is False
        assert self.client.tool_cache == {}
        assert self.client.command_history == []
        
    def test_completer_commands(self):
        """Test tab completion for commands."""
        # Mock readline state
        with patch('readline.get_line_buffer', return_value='help'):
            matches = []
            state = 0
            while True:
                match = self.client._completer('hel', state)
                if match is None:
                    break
                matches.append(match)
                state += 1
            
            assert 'help' in matches
            
    def test_completer_tools(self):
        """Test tab completion includes tool names when cached."""
        # Setup tool cache
        self.client.tool_cache = {
            'Bash': {'name': 'Bash', 'description': 'Execute bash commands'},
            'mcp_discover': {'name': 'mcp_discover', 'description': 'Discover tools'}
        }
        
        with patch('readline.get_line_buffer', return_value='Bash'):
            matches = []
            state = 0
            while True:
                match = self.client._completer('Ba', state)
                if match is None:
                    break
                matches.append(match)
                state += 1
            
            assert 'Bash' in matches
    
    @pytest.mark.asyncio
    async def test_refresh_tools(self):
        """Test tool cache refresh functionality."""
        # Mock MCP browser
        mock_browser = AsyncMock()
        mock_browser.call.return_value = {
            "result": {
                "tools": [
                    {"name": "test_tool", "description": "Test tool"},
                    {"name": "another_tool", "description": "Another test tool"}
                ]
            }
        }
        self.client.browser = mock_browser
        
        await self.client._refresh_tools()
        
        assert len(self.client.tool_cache) == 2
        assert "test_tool" in self.client.tool_cache
        assert "another_tool" in self.client.tool_cache
        
    @pytest.mark.asyncio
    async def test_call_mcp_browser(self):
        """Test MCP call through browser."""
        mock_browser = AsyncMock()
        expected_response = {"result": {"test": "data"}}
        mock_browser.call.return_value = expected_response
        
        self.client.browser = mock_browser
        
        request = {"jsonrpc": "2.0", "id": 1, "method": "test"}
        response = await self.client._call_mcp(request)
        
        assert response == expected_response
        mock_browser.call.assert_called_once_with(request)
        
    @pytest.mark.asyncio
    async def test_call_mcp_client(self):
        """Test MCP call through daemon client."""
        mock_client = AsyncMock()
        expected_response = {"result": {"test": "data"}}
        mock_client.call.return_value = expected_response
        
        self.client.client = mock_client
        self.client.browser = None
        
        request = {"jsonrpc": "2.0", "id": 1, "method": "test"}
        response = await self.client._call_mcp(request)
        
        assert response == expected_response
        mock_client.call.assert_called_once_with(request)
        
    def test_generate_sample_args_string(self):
        """Test sample argument generation for string properties."""
        schema = {
            "properties": {
                "query": {"type": "string"},
                "jsonpath": {"type": "string"},
                "command": {"type": "string"}
            }
        }
        
        args = self.client._generate_sample_args(schema)
        
        assert args["jsonpath"] == "$.tools[*].name"
        assert args["query"] == "test query"
        assert args["command"] == "sample_command"
        
    def test_generate_sample_args_types(self):
        """Test sample argument generation for different types."""
        schema = {
            "properties": {
                "text": {"type": "string"},
                "enabled": {"type": "boolean"},
                "count": {"type": "number"},
                "items": {"type": "array"},
                "config": {"type": "object"}
            }
        }
        
        args = self.client._generate_sample_args(schema)
        
        assert isinstance(args["text"], str)
        assert isinstance(args["enabled"], bool)
        assert isinstance(args["count"], (int, float))
        assert isinstance(args["items"], list)
        assert isinstance(args["config"], dict)
        
    def test_generate_sample_args_examples(self):
        """Test sample argument generation uses examples when available."""
        schema = {
            "properties": {
                "query": {
                    "type": "string",
                    "example": "example query"
                }
            }
        }
        
        args = self.client._generate_sample_args(schema)
        assert args["query"] == "example query"
        
    @pytest.mark.asyncio
    async def test_execute_tool_call(self):
        """Test tool execution with proper result display."""
        mock_browser = AsyncMock()
        mock_browser.call.return_value = {
            "result": {
                "content": [
                    {"type": "text", "text": "Test result"}
                ]
            }
        }
        self.client.browser = mock_browser
        
        # Capture output
        with patch('builtins.print') as mock_print:
            await self.client._execute_tool_call("test_tool", {"arg": "value"})
        
        # Verify MCP call was made
        mock_browser.call.assert_called_once()
        call_args = mock_browser.call.call_args[0][0]
        assert call_args["method"] == "tools/call"
        assert call_args["params"]["name"] == "test_tool"
        assert call_args["params"]["arguments"] == {"arg": "value"}
        
        # Verify output was printed
        mock_print.assert_called()
        
    @pytest.mark.asyncio
    async def test_execute_tool_call_error(self):
        """Test tool execution error handling."""
        mock_browser = AsyncMock()
        mock_browser.call.return_value = {
            "error": {
                "code": -32603,
                "message": "Tool execution failed"
            }
        }
        self.client.browser = mock_browser
        
        with patch('builtins.print') as mock_print:
            await self.client._execute_tool_call("test_tool", {})
        
        # Check that error was printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Error:" in call for call in print_calls)
        
    def test_display_result_text_content(self):
        """Test display of text content results."""
        result = {
            "content": [
                {"type": "text", "text": "Hello, World!"}
            ]
        }
        
        with patch('builtins.print') as mock_print:
            self.client._display_result(result)
        
        # Verify text was printed
        calls = [call[0][0] for call in mock_print.call_args_list]
        assert "Hello, World!" in calls
        
    def test_display_result_image_content(self):
        """Test display of image content results."""
        result = {
            "content": [
                {"type": "image", "url": "http://example.com/image.png"}
            ]
        }
        
        with patch('builtins.print') as mock_print:
            self.client._display_result(result)
        
        # Verify image info was printed
        calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Image:" in call for call in calls)
        
    def test_display_result_raw_data(self):
        """Test display of raw result data."""
        result = {"key": "value", "number": 42}
        
        with patch('builtins.print') as mock_print:
            self.client._display_result(result)
        
        # Verify JSON was printed
        calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Result:" in call for call in calls)
        
    @pytest.mark.asyncio
    async def test_execute_command_help(self):
        """Test help command execution."""
        with patch('builtins.print') as mock_print:
            await self.client._execute_command("help")
        
        # Verify help was printed
        mock_print.assert_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("MCP Browser Interactive Commands" in call for call in print_calls)
        
    @pytest.mark.asyncio  
    async def test_execute_command_list(self):
        """Test list command execution."""
        # Setup tool cache
        self.client.tool_cache = {
            'test_tool': {'name': 'test_tool', 'description': 'A test tool'},
            'bash_tool': {'name': 'bash_tool', 'description': 'Bash execution tool'}
        }
        
        with patch('builtins.print') as mock_print:
            await self.client._execute_command("list bash")
        
        # Verify filtered tools were printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("bash_tool" in call for call in print_calls)
        
    @pytest.mark.asyncio
    async def test_execute_command_refresh(self):
        """Test refresh command execution."""
        mock_browser = AsyncMock()
        mock_browser.call.return_value = {
            "result": {"tools": [{"name": "new_tool", "description": "New tool"}]}
        }
        self.client.browser = mock_browser
        
        with patch('builtins.print') as mock_print:
            await self.client._execute_command("refresh")
        
        # Verify tool cache was updated
        assert "new_tool" in self.client.tool_cache
        
        # Verify refresh message was printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Tool cache refreshed" in call for call in print_calls)
        
    @pytest.mark.asyncio
    async def test_execute_command_unknown_tool(self):
        """Test handling of unknown direct tool calls."""
        with patch('builtins.print') as mock_print:
            await self.client._execute_command("unknown_tool arg1")
        
        # Verify error message was printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Unknown tool:" in call for call in print_calls)


class TestInteractiveMCPClientIntegration:
    """Integration tests for interactive client."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_mock(self):
        """Test a complete workflow with mocked dependencies."""
        client = InteractiveMCPClient(use_daemon=False)
        
        # Mock browser
        mock_browser = AsyncMock()
        
        # Mock tools/list response
        tools_response = {
            "result": {
                "tools": [
                    {
                        "name": "mcp_discover",
                        "description": "Discover tools",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "jsonpath": {"type": "string"}
                            },
                            "required": ["jsonpath"]
                        }
                    }
                ]
            }
        }
        
        # Mock discover response
        discover_response = {
            "result": {
                "content": [
                    {"type": "text", "text": '["mcp_discover", "mcp_call", "onboarding"]'}
                ]
            }
        }
        
        # Configure mock to return different responses based on call
        def mock_call(request):
            if request.get("method") == "tools/list":
                return tools_response
            elif (request.get("method") == "tools/call" and 
                  request.get("params", {}).get("name") == "mcp_discover"):
                return discover_response
            else:
                return {"error": {"code": -32601, "message": "Method not found"}}
        
        mock_browser.call.side_effect = mock_call
        client.browser = mock_browser
        
        # Test tool refresh
        await client._refresh_tools()
        assert "mcp_discover" in client.tool_cache
        
        # Test discovery command
        with patch('builtins.print'):
            await client._execute_command("discover $.tools[*].name")
        
        # Verify calls were made
        assert mock_browser.call.call_count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])