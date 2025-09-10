#!/usr/bin/env python3
"""
Quick Demo Script for MCP Clients
Shows examples of connecting to and using MCP servers
"""

import asyncio
import json
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

# Server configurations
SERVERS = {
    "github": {
        "command": "docker",
        "args": [
            "run", "-i", "--rm",
            "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
            "ghcr.io/github/github-mcp-server"
        ],
        "env": {
            "GITHUB_PERSONAL_ACCESS_TOKEN": "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"
        }
    },
    "filesystem": {
        "command": "docker",
        "args": [
            "run", "-i", "--rm",
            "--mount", "type=bind,src=/home/lillian/,dst=/projects",
            "mcp/filesystem", "/projects"
        ],
        "env": {}
    }
}

async def test_server(server_name, config):
    """Test a specific server"""
    try:
        transport = StdioTransport(
            command=config["command"],
            args=config["args"],
            env=config.get("env", {})
        )
        client = Client(transport)
        
        async with client:
            # Test connection
            await client.ping()
            print(f"✅ {server_name} connected")
            
            # Get tools
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]
            print(f"🛠️ {server_name} tools: {tool_names}")
            
            # Test a simple tool
            if server_name == "filesystem":
                result = await client.call_tool("list_directory", {"path": "/projects"})
                print(f" {server_name} test result: {result}")
            
    except Exception as e:
        print(f"{server_name} error: {e}")

def print_json(data):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=2))

async def demo():
    """Run a quick demo"""
    print("MCP Client Demo")
    print("=" * 50)
    
    # Test each server
    for server_name, config in SERVERS.items():
        print(f"\nTesting {server_name}:")
        await test_server(server_name, config)
    
    print("\nDemo completed!")

if __name__ == "__main__":
    asyncio.run(demo()) 