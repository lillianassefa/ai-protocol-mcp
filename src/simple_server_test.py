#!/usr/bin/env python3
"""
Simple test file for the MCP proxy server
"""

import asyncio
import json
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

# Connect to the existing proxy server
transport = StdioTransport("python", ["../mcp_proxy_server/proxy_server.py"])
client = Client(transport)

async def test_server():
    """Test the proxy server"""
    
    print("Testing MCP Proxy Server...")
    
    async with client:
        # Test 1: Get server status
        print("\n1. Testing server status:")
        result = await client.call_tool("get_server_status")
        print(json.dumps(result, indent=2))
        
        # Test 2: Get all tools
        print("\n2. Testing get all tools:")
        result = await client.call_tool("list_all_tools")
        print(json.dumps(result, indent=2))
        
        # Test 3: Test routing
        print("\n3. Testing routing:")
        result = await client.call_tool("route_tool_call", {
            "tool_name": "filesystem_list_directory",
            "arguments": {"path": "/projects"}
        })
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test_server()) 