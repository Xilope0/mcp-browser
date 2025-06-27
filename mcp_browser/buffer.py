"""
JSON-RPC message buffering to ensure complete messages are processed.

Handles partial JSON messages and ensures atomic delivery of complete
JSON-RPC messages, critical for reliable MCP communication.
"""

import json
from typing import List, Optional


class JsonRpcBuffer:
    """Buffer for accumulating and extracting complete JSON-RPC messages."""
    
    def __init__(self):
        self.buffer = ""
    
    def append(self, data: str) -> List[dict]:
        """
        Append data to buffer and extract complete JSON-RPC messages.
        
        Args:
            data: Raw string data to append
            
        Returns:
            List of complete JSON-RPC message dictionaries
        """
        self.buffer += data
        messages = []
        
        # Extract complete JSON messages line by line
        lines = self.buffer.split('\n')
        
        # Keep the last incomplete line in the buffer
        self.buffer = lines[-1]
        
        # Process complete lines
        for line in lines[:-1]:
            line = line.strip()
            if not line:
                continue
                
            try:
                msg = json.loads(line)
                # Validate it's a proper JSON-RPC message
                if isinstance(msg, dict) and ('jsonrpc' in msg or 'method' in msg or 'id' in msg):
                    messages.append(msg)
            except json.JSONDecodeError:
                # Log or handle malformed JSON
                pass
        
        return messages
    
    def clear(self):
        """Clear the buffer."""
        self.buffer = ""