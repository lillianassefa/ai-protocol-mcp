#!/usr/bin/env python3
"""
Quick Demo Script for MCP Clients
Shows examples of connecting to and using MCP servers
"""

import asyncio
import json
from simple_test import tester

def print_json(data):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=2))

async def demo():
    """Run a quick demo"""
    print("🚀 MCP Client Demo")
    print("=" * 50)
    
    # 1. Health check
    print("\n1️⃣ Health Check:")
    health = await tester.health_check()
    print_json(health)
    
    # 2. Get GitHub tools
    print("\n2️⃣ GitHub Tools:")
    github_tools = await tester.get_tools("github")
    print_json(github_tools)
    
    # 3. Get Filesystem tools
    print("\n3️⃣ Filesystem Tools:")
    fs_tools = await tester.get_tools("filesystem")
    print_json(fs_tools)
    
    # 4. Test a simple filesystem operation
    print("\n4️⃣ Testing Filesystem List Directory:")
    fs_result = await tester.call_tool("filesystem", "list_directory", {"path": "/projects"})
    print_json(fs_result)
    
    # 5. Test GitHub search (if available)
    print("\n5️⃣ Testing GitHub Search:")
    github_result = await tester.call_tool("github", "search_repositories", {"query": "python"})
    print_json(github_result)
    
    print("\n✅ Demo completed!")

if __name__ == "__main__":
    asyncio.run(demo()) 