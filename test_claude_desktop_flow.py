#!/usr/bin/env python3
"""
Test the exact Claude Desktop flow to identify the timeout issue.
"""

import asyncio
import json
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_server_mode_timeout():
    """Test server mode with proper timeout handling."""
    print("Testing Claude Desktop flow with timeout...")
    
    # Start mcp-browser in server mode
    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_browser", "--mode", "server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    try:
        # Send initialize request like Claude Desktop does
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
        
        print(f"Sending: {json.dumps(init_request)}")
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        
        # Wait for response with timeout
        response_received = False
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < 5.0:  # 5 second timeout
            try:
                # Non-blocking read
                line = proc.stdout.readline()
                if line:
                    response = json.loads(line.strip())
                    print(f"Received: {json.dumps(response, indent=2)}")
                    response_received = True
                    break
            except:
                await asyncio.sleep(0.1)
                continue
            
            await asyncio.sleep(0.1)
        
        if not response_received:
            print("ERROR: No response received within 5 seconds!")
            
            # Check stderr for errors
            stderr_output = proc.stderr.read()
            if stderr_output:
                print(f"STDERR: {stderr_output}")
        else:
            # Send initialized notification
            initialized = {
                "jsonrpc": "2.0",
                "method": "initialized"
            }
            print(f"\nSending: {json.dumps(initialized)}")
            proc.stdin.write(json.dumps(initialized) + "\n")
            proc.stdin.flush()
            
            # Test tools/list
            tools_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
            print(f"\nSending: {json.dumps(tools_request)}")
            proc.stdin.write(json.dumps(tools_request) + "\n")
            proc.stdin.flush()
            
            # Wait for tools response
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < 2.0:
                line = proc.stdout.readline()
                if line:
                    response = json.loads(line.strip())
                    print(f"Received: {json.dumps(response, indent=2)}")
                    break
                await asyncio.sleep(0.1)
            
    finally:
        proc.terminate()
        proc.wait()


async def test_with_logging():
    """Test with debug logging enabled."""
    print("\n\nTesting with debug logging...")
    
    # Start mcp-browser in server mode with debug
    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_browser", "--mode", "server", "--debug", "--log-file", "/tmp/mcp-test.log"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    try:
        # Send initialize
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
        
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        
        # Read with timeout
        await asyncio.sleep(1.0)
        
        # Try to read response
        output = proc.stdout.read()
        if output:
            print(f"STDOUT: {output}")
        
        stderr = proc.stderr.read() 
        if stderr:
            print(f"STDERR: {stderr}")
            
        # Check log file
        try:
            with open("/tmp/mcp-test.log", "r") as f:
                log_content = f.read()
                if log_content:
                    print(f"\nLOG FILE:\n{log_content}")
        except:
            pass
            
    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    asyncio.run(test_server_mode_timeout())
    asyncio.run(test_with_logging())