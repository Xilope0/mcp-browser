"""
AI-optimized usage example for MCP Browser.

Shows how an AI system would use MCP Browser with minimal context usage.
Only two methods are needed: call() for execution and discover() for exploration.
"""

import asyncio
import json
from mcp_browser import MCPBrowser


class AIAssistant:
    """Example AI assistant using MCP Browser."""
    
    def __init__(self):
        self.browser = None
        self.discovered_tools = {}
        
    async def initialize(self):
        """Initialize connection to MCP server."""
        self.browser = MCPBrowser()
        await self.browser.initialize()
        
        # In sparse mode, only 2 tools are visible initially:
        # - mcp_discover: For exploring available tools
        # - mcp_call: For executing any tool
        
    async def execute_user_request(self, user_request: str):
        """Process a user request using MCP tools."""
        print(f"User: {user_request}\n")
        
        # Example: User wants to run a bash command
        if "run command" in user_request.lower():
            # First, discover if Bash tool exists
            bash_tools = self.browser.discover("$.tools[?(@.name=='Bash')]")
            
            if not bash_tools:
                print("AI: Bash tool not available on this MCP server.")
                return
                
            # Get the tool schema (cached after first discovery)
            bash_schema = bash_tools[0] if isinstance(bash_tools, list) else bash_tools
            print(f"AI: Found Bash tool. Schema: {bash_schema['name']}")
            
            # Execute the command using mcp_call
            response = await self.browser.call({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "mcp_call",
                    "arguments": {
                        "method": "tools/call",
                        "params": {
                            "name": "Bash",
                            "arguments": {
                                "command": "echo 'Hello from AI-optimized MCP Browser!'",
                                "description": "Test echo command"
                            }
                        }
                    }
                }
            })
            
            if "result" in response:
                result = response["result"]
                print(f"AI: Command executed successfully.")
                if isinstance(result, dict) and "content" in result:
                    content = result["content"][0]["text"]
                    print(f"Output: {content}")
            else:
                print(f"AI: Error: {response.get('error', {}).get('message')}")
                
        # Example: User wants to see available tools
        elif "what tools" in user_request.lower():
            # Use discover to get all tool names efficiently
            tool_names = self.browser.discover("$.tools[*].name")
            
            if tool_names:
                print(f"AI: I have access to {len(tool_names)} tools:")
                for name in tool_names[:10]:  # Show first 10
                    print(f"  - {name}")
                if len(tool_names) > 10:
                    print(f"  ... and {len(tool_names) - 10} more")
            else:
                print("AI: No tools found on this MCP server.")
                
    async def close(self):
        """Close the MCP connection."""
        if self.browser:
            await self.browser.close()


async def main():
    """Demonstrate AI-optimized MCP usage."""
    print("=== AI-Optimized MCP Browser Usage ===\n")
    print("Key insight: Only 2 methods needed for full MCP access:")
    print("- browser.call(jsonrpc_object) - Execute any operation")
    print("- browser.discover(jsonpath) - Explore available tools")
    print("\nThis minimizes context usage while maintaining full functionality.\n")
    print("-" * 50 + "\n")
    
    assistant = AIAssistant()
    await assistant.initialize()
    
    # Simulate user requests
    await assistant.execute_user_request("What tools do you have?")
    print("\n" + "-" * 50 + "\n")
    
    await assistant.execute_user_request("Run command to show current directory")
    print("\n" + "-" * 50 + "\n")
    
    await assistant.close()


if __name__ == "__main__":
    asyncio.run(main())