#!/usr/bin/env python3
"""
Test MCP Protocol flow to understand and verify the initialization handshake.

This test will:
1. Create a minimal MCP server that logs all interactions
2. Create an MCP browser client
3. Verify the complete initialization flow
4. Test tools/list and tools/call
"""

import asyncio
import json
import sys
import os
import tempfile
from pathlib import Path

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_browser import MCPBrowser
from mcp_browser.daemon import MCPBrowserDaemon, MCPBrowserClient, get_socket_path


def log_test(msg):
    """Log test messages with timestamp."""
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {msg}")


async def test_direct_initialization():
    """Test direct initialization without daemon."""
    log_test("=== TEST 1: Direct Initialization ===")
    
    # Create browser with correct config
    browser = MCPBrowser(enable_builtin_servers=True)
    
    try:
        log_test("Initializing browser...")
        await browser.initialize()
        log_test("✓ Browser initialized successfully")
        
        # Test tools/list
        log_test("Calling tools/list...")
        response = await browser.call({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        })
        
        if "result" in response:
            tools = response["result"].get("tools", [])
            log_test(f"✓ Got {len(tools)} tools: {[t['name'] for t in tools]}")
        else:
            log_test(f"✗ Error in tools/list: {response}")
            
    except Exception as e:
        log_test(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser.close()


async def test_daemon_initialization():
    """Test initialization through daemon."""
    log_test("\n=== TEST 2: Daemon Initialization ===")
    
    # Use a temporary socket
    with tempfile.TemporaryDirectory() as tmpdir:
        socket_path = Path(tmpdir) / "test-mcp.sock"
        
        # Create browser and daemon
        browser = MCPBrowser(enable_builtin_servers=True)
        daemon = MCPBrowserDaemon(browser, socket_path)
        
        # Start daemon in background
        daemon_task = asyncio.create_task(daemon.start())
        
        try:
            # Give daemon time to start
            await asyncio.sleep(0.1)
            
            # Connect as client
            async with MCPBrowserClient(socket_path) as client:
                log_test("Connected to daemon")
                
                # Send initialize - this should be handled by the proxy
                log_test("Sending initialize request...")
                init_request = {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "test-client",
                            "version": "1.0.0"
                        }
                    }
                }
                
                response = await client.call(init_request)
                log_test(f"Initialize response: {json.dumps(response, indent=2)}")
                
                # Check response
                if "result" in response:
                    result = response["result"]
                    if result.get("protocolVersion") == "2024-11-05":
                        log_test("✓ Got correct protocol version")
                    else:
                        log_test(f"✗ Wrong protocol version: {result.get('protocolVersion')}")
                else:
                    log_test(f"✗ Error in initialize: {response}")
                
                # Test tools/list
                log_test("\nSending tools/list request...")
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list"
                }
                
                response = await client.call(tools_request)
                if "result" in response:
                    tools = response["result"].get("tools", [])
                    log_test(f"✓ Got {len(tools)} tools: {[t['name'] for t in tools]}")
                else:
                    log_test(f"✗ Error in tools/list: {response}")
                    
        finally:
            # Stop daemon
            await daemon.stop()
            daemon_task.cancel()
            try:
                await daemon_task
            except asyncio.CancelledError:
                pass


async def test_server_mode_initialization():
    """Test server mode (stdin/stdout) initialization."""
    log_test("\n=== TEST 3: Server Mode Initialization ===")
    
    # This simulates what Claude Desktop does
    browser = MCPBrowser(enable_builtin_servers=True)
    await browser.initialize()
    
    # Simulate initialize request from Claude Desktop
    init_request = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "claude-desktop",
                "version": "0.7.2"
            }
        }
    }
    
    log_test("Processing initialize request from Claude Desktop...")
    response = await browser.call(init_request)
    log_test(f"Response: {json.dumps(response, indent=2)}")
    
    # Check if we need to send initialized notification
    if "result" in response:
        log_test("✓ Initialize successful")
        
        # Claude Desktop would send initialized notification
        initialized_notif = {
            "jsonrpc": "2.0",
            "method": "initialized"
        }
        log_test("Sending initialized notification...")
        # Notifications don't expect responses
        await browser.call(initialized_notif)
        
        # Now test tools/list
        tools_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
        response = await browser.call(tools_request)
        if "result" in response:
            tools = response["result"].get("tools", [])
            log_test(f"✓ Got {len(tools)} tools in sparse mode")
        else:
            log_test(f"✗ Error in tools/list: {response}")
    
    await browser.close()


async def test_double_handshake_issue():
    """Test the specific issue: Claude Desktop -> mcp-browser -> MCP servers."""
    log_test("\n=== TEST 4: Double Handshake Issue ===")
    
    # When Claude Desktop connects to mcp-browser in server mode:
    # 1. Claude Desktop sends initialize to mcp-browser
    # 2. mcp-browser should respond with its capabilities
    # 3. mcp-browser internally initializes connections to MCP servers
    # 4. But it should NOT forward the initialize request to MCP servers
    
    browser = MCPBrowser(enable_builtin_servers=True)
    
    # The browser should initialize its internal servers first
    log_test("Browser initializing internal servers...")
    await browser.initialize()
    
    # Now simulate Claude Desktop connecting
    init_from_claude = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "claude-desktop",
                "version": "0.7.2"
            }
        }
    }
    
    log_test("Claude Desktop sends initialize...")
    response = await browser.call(init_from_claude)
    
    if "result" in response:
        log_test("✓ mcp-browser responded to initialize")
        log_test(f"  Protocol: {response['result'].get('protocolVersion')}")
        log_test(f"  Server: {response['result'].get('serverInfo', {}).get('name')}")
    else:
        log_test(f"✗ Error: {response}")
    
    await browser.close()


async def main():
    """Run all tests."""
    log_test("Starting MCP Protocol Tests")
    log_test("=" * 60)
    
    # Run tests
    await test_direct_initialization()
    await test_daemon_initialization()
    await test_server_mode_initialization()
    await test_double_handshake_issue()
    
    log_test("\n" + "=" * 60)
    log_test("Tests completed!")


if __name__ == "__main__":
    asyncio.run(main())