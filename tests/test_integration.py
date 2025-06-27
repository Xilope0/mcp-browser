#!/usr/bin/env python3
"""
Integration tests for mcp-browser.

Tests the full JSON-RPC flow by piping commands and verifying responses.
"""

import json
import asyncio
import subprocess
import sys
import os
import pytest
from typing import Dict, Any, Optional


class JSONRPCTestClient:
    """Test client that pipes JSON-RPC commands to mcp-browser."""
    
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self.process = None
        
    async def __aenter__(self):
        """Start mcp-browser subprocess."""
        # Start mcp-browser as a subprocess in server mode
        self.process = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'mcp_browser', '--mode', 'server', '--no-builtin',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up subprocess."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request and get response."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method
        }
        if params:
            request["params"] = params
            
        # Send request
        request_bytes = (json.dumps(request) + '\n').encode()
        self.process.stdin.write(request_bytes)
        await self.process.stdin.drain()
        
        # Read response with timeout
        try:
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=self.timeout
            )
            return json.loads(response_line.decode())
        except asyncio.TimeoutError:
            # Check stderr for errors
            stderr = await self.process.stderr.read()
            raise TimeoutError(f"No response within {self.timeout}s. Stderr: {stderr.decode()}")


@pytest.mark.skip(reason="Integration tests require full server setup")
async def test_basic_flow():
    """Test basic JSON-RPC flow."""
    async with JSONRPCTestClient() as client:
        # First initialize the connection
        print("Initializing connection...")
        init_response = await client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        })
        assert init_response.get("result", {}).get("protocolVersion") == "2024-11-05"
        print("✓ Initialized successfully")
        
        # Test 1: List tools (should show sparse tools)
        print("Test 1: Listing tools...")
        response = await client.send_request("tools/list")
        assert response.get("jsonrpc") == "2.0"
        assert "result" in response
        tools = response["result"]["tools"]
        assert isinstance(tools, list)
        assert len(tools) == 3  # Sparse mode shows only 3 tools
        
        # Verify virtual tools are present
        tool_names = [t["name"] for t in tools]
        assert "mcp_discover" in tool_names
        assert "mcp_call" in tool_names
        assert "onboarding" in tool_names
        print(f"✓ Found {len(tools)} sparse tools: {tool_names}")
        
        # Test 2: Use mcp_discover to find all tools
        print("\nTest 2: Discovering all tools...")
        response = await client.send_request("tools/call", {
            "name": "mcp_discover",
            "arguments": {"query": "$.tools[*].name"}
        })
        assert "result" in response
        all_tool_names = response["result"]["content"][0]["text"]
        print(f"✓ Discovered tools: {all_tool_names}")
        
        # Test 3: Get description of a specific tool
        print("\nTest 3: Getting tool description...")
        response = await client.send_request("tools/call", {
            "name": "mcp_discover",
            "arguments": {"query": "$.tools[*].description"}
        })
        assert "result" in response
        descriptions = json.loads(response["result"]["content"][0]["text"])
        assert len(descriptions) > 0
        print(f"✓ Found {len(descriptions)} tool descriptions")
        
        # Test 4: Use the discovered tool
        print("\nTest 4: Using discovered tool...")
        response = await client.send_request("tools/call", {
            "name": "mcp_call",
            "arguments": {
                "tool": "screen::list",
                "arguments": {}
            }
        })
        assert "result" in response
        print(f"✓ screen::list response: {response['result']}")
        
        # Test 5: Use onboarding tool
        print("\nTest 5: Testing onboarding...")
        response = await client.send_request("tools/call", {
            "name": "onboarding",
            "arguments": {"identity": "test-bot"}
        })
        assert "result" in response
        onboarding_text = response["result"]["content"][0]["text"]
        assert "test-bot" in onboarding_text
        print(f"✓ Onboarding received personalized message")


@pytest.mark.skip(reason="Integration tests require full server setup")
async def test_error_handling():
    """Test error handling."""
    async with JSONRPCTestClient() as client:
        # Test invalid tool name
        print("\nTest 6: Testing error handling...")
        response = await client.send_request("tools/call", {
            "name": "nonexistent_tool",
            "arguments": {}
        })
        assert "error" in response
        print(f"✓ Got expected error: {response['error']['message']}")
        
        # Test invalid arguments
        response = await client.send_request("tools/call", {
            "name": "mcp_discover",
            "arguments": {"invalid_param": "value"}
        })
        assert "error" in response
        print(f"✓ Got expected error for invalid args: {response['error']['message']}")


async def main():
    """Run all integration tests."""
    print("Running MCP Browser Integration Tests")
    print("=" * 50)
    
    try:
        await test_basic_flow()
        await test_error_handling()
        print("\n" + "=" * 50)
        print("✅ All integration tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())