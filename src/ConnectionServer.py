from fastmcp import FastMCP
import asyncio
import subprocess
import json
import logging
import os
from typing import Dict, Any, Optional

from fastmcp.client.transports import StdioTransport
from fastmcp import Client, FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

configs = [
    {
        "name": "github",
        "command": "docker",
        "args": [
            "run",
            "-i",
            "--rm",
            "-e",
            "GITHUB_PERSONAL_ACCESS_TOKEN",
            "ghcr.io/github/github-mcp-server"
        ],
        "env": {
            "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN", "your-github-token-here")
        },
    },
    {
        "name": "filesystem",
        "command": "docker",
        "args": [
            "run",
            "-i",
            "--rm",
            "--mount", "type=bind,src=/home/lillian/,dst=/projects",
            "mcp/filesystem",
            "/projects"
        ],
        "env": {}  # No environment variables needed for filesystem
    },
    {
        "name": "atlassian",
        "command": "docker",
        "args": [
            "run",
            "-i",
            "--rm",
            "-e", "CONFLUENCE_URL",
            "-e", "CONFLUENCE_USERNAME", 
            "-e", "CONFLUENCE_API_TOKEN",
            "-e", "JIRA_URL",
            "-e", "JIRA_USERNAME",
            "-e", "JIRA_API_TOKEN",
            "ghcr.io/sooperset/mcp-atlassian:latest"
        ],
        "env": {
            "CONFLUENCE_URL": "your_confluence_url_here",
            "CONFLUENCE_USERNAME": "your_confluence_username_here",
            "CONFLUENCE_API_TOKEN": "your_confluence_token_here",
            "JIRA_URL": "your_jira_url_here", 
            "JIRA_USERNAME": "your_jira_username_here",
            "JIRA_API_TOKEN": "your_jira_token_here"
        }
    }
]

class UnifiedMCPServer:
    """Unified MCP Server that has access to all downstream servers"""
    
    def __init__(self):
        self.clients = {}
        self.server_configs = {config["name"]: config for config in configs}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize clients for all configured servers"""
        for server_name, config in self.server_configs.items():
            try:
                transport = StdioTransport(
                    command=config["command"],
                    args=config["args"],
                    env=config.get("env", {})
                )
                self.clients[server_name] = Client(transport)
                logger.info(f" Created client for {server_name} server")
            except Exception as e:
                logger.error(f"Failed to create client for {server_name}: {e}")
    
    async def test_all_connections(self) -> Dict[str, Any]:
        """Test connections to all servers"""
        results = {}
        
        for server_name, client in self.clients.items():
            try:
                async with client:
                    await client.ping()
                    results[server_name] = {
                        "status": "✅ Connected",
                        "transport": "stdio"
                    }
            except Exception as e:
                results[server_name] = {
                    "status": f" Connection failed: {str(e)}",
                    "transport": "stdio"
                }
        
        return {
            "servers": results,
            "total_servers": len(results),
            "connected_servers": [name for name, info in results.items() 
                                if "✅" in info["status"]]
        }
    
    async def get_server_tools(self, server_name: str) -> Dict[str, Any]:
        """Get tools from a specific server"""
        if server_name not in self.clients:
            return {"error": f"Server '{server_name}' not available"}
        
        try:
            client = self.clients[server_name]
            async with client:
                tools = await client.list_tools()
                
                tools_info = []
                for tool in tools:
                    tool_info = {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema,
                        "server": server_name
                    }
                    tools_info.append(tool_info)
                
                return {
                    "server": server_name,
                    "tools": tools_info,
                    "count": len(tools_info)
                }
                
        except Exception as e:
            logger.error(f"Error getting tools from {server_name}: {e}")
            return {"error": f"Failed to get tools from {server_name}: {str(e)}"}
    
    async def get_all_tools(self) -> Dict[str, Any]:
        """Get all tools from all servers"""
        all_tools = {}
        
        for server_name in self.clients.keys():
            server_tools = await self.get_server_tools(server_name)
            if "error" not in server_tools:
                all_tools[server_name] = server_tools
            else:
                all_tools[server_name] = {"error": server_tools["error"]}
        
        return {
            "servers": all_tools,
            "total_servers": len(all_tools),
            "total_tools": sum(len(server.get("tools", [])) 
                              for server in all_tools.values() 
                              if "error" not in server)
        }
    
    async def call_server_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool on a specific server"""
        if server_name not in self.clients:
            return {"error": f"Server '{server_name}' not available"}
        
        try:
            client = self.clients[server_name]
            async with client:
                result = await client.call_tool(tool_name, arguments or {})
                
                return {
                    "success": True,
                    "server": server_name,
                    "tool": tool_name,
                    "result": result
                }
                
        except Exception as e:
            logger.error(f"Error calling {tool_name} on {server_name}: {e}")
            return {
                "success": False,
                "error": f"Failed to call {tool_name} on {server_name}: {str(e)}",
                "server": server_name,
                "tool": tool_name
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all servers"""
        health_status = {}
        
        for server_name, client in self.clients.items():
            try:
                async with client:
                    await client.ping()
                    tools = await client.list_tools()
                    health_status[server_name] = {
                        "status": "✅ Healthy",
                        "tools_count": len(tools),
                        "transport": "stdio"
                    }
            except Exception as e:
                health_status[server_name] = {
                    "status": f"❌ Unhealthy: {str(e)}",
                    "tools_count": 0,
                    "transport": "stdio"
                }
        
        healthy_count = sum(1 for info in health_status.values() 
                           if "✅" in info["status"])
        
        return {
            "servers": health_status,
            "summary": {
                "healthy_servers": healthy_count,
                "total_servers": len(health_status),
                "health_percentage": round((healthy_count / len(health_status)) * 100, 1)
            }
        }

# Create the unified server instance
unified_server = UnifiedMCPServer()
server = FastMCP("Unified MCP Server")

@server.tool
async def test_connections() -> Dict[str, Any]:
    """Test connections to all configured servers"""
    return await unified_server.test_all_connections()

@server.tool
async def get_server_tools(server_name: str) -> Dict[str, Any]:
    """Get tools from a specific server"""
    return await unified_server.get_server_tools(server_name)

@server.tool
async def get_all_tools() -> Dict[str, Any]:
    """Get all tools from all servers"""
    return await unified_server.get_all_tools()

@server.tool
async def call_server_tool(server_name: str, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    """Call a tool on a specific server"""
    return await unified_server.call_server_tool(server_name, tool_name, arguments)

@server.tool
async def health_check() -> Dict[str, Any]:
    """Check health of all servers"""
    return await unified_server.health_check()

@server.tool
async def list_servers() -> Dict[str, Any]:
    """List all available servers"""
    return {
        "servers": list(unified_server.clients.keys()),
        "total": len(unified_server.clients),
        "configs": list(unified_server.server_configs.keys())
    }

@server.tool
async def get_server_info(server_name: str) -> Dict[str, Any]:
    """Get information about a specific server"""
    if server_name not in unified_server.server_configs:
        return {"error": f"Server '{server_name}' not configured"}
    
    config = unified_server.server_configs[server_name]
    return {
        "server_name": server_name,
        "command": config["command"],
        "args": config["args"],
        "has_env": bool(config.get("env")),
        "client_available": server_name in unified_server.clients
    }

if __name__ == "__main__":
    logger.info("Starting Unified MCP Server...")
    logger.info(f"Connected to {len(unified_server.clients)} downstream servers")
    
    # Run the server
    server.run()