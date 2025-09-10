"""
LLM Orchestrator with OpenAI Integration
Uses OpenAI to make intelligent decisions about server and tool selection
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from openai import OpenAI
from fastmcp import FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp import Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI configuration
OPENAI_API_KEY = "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"
client = OpenAI(api_key=OPENAI_API_KEY)

# Server configurations
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
            "GITHUB_PERSONAL_ACCESS_TOKEN": "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"
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
        "env": {}
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

class LLMOrchestrator:
    """Orchestrates MCP servers using OpenAI for decision making"""
    
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
                logger.info(f"Created client for {server_name} server")
            except Exception as e:
                logger.error(f"Failed to create client for {server_name}: {e}")
    
    async def discover_servers(self) -> Dict[str, Any]:
        """Discover all available servers"""
        results = {}
        
        for server_name, client in self.clients.items():
            try:
                async with client:
                    await client.ping()
                    results[server_name] = {
                        "status": "✅ Available",
                        "transport": "stdio"
                    }
            except Exception as e:
                results[server_name] = {
                    "status": f"❌ Unavailable: {str(e)}",
                    "transport": "stdio"
                }
        
        return {
            "servers": results,
            "total_servers": len(results),
            "available_servers": [name for name, info in results.items() 
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
    
    def ask_llm_to_choose_server(self, user_request: str, available_servers: List[str]) -> str:
        """Ask LLM to choose the best server for the user request"""
        prompt = f"""
You are an AI assistant that helps choose the best MCP server for a user's request.

Available servers: {', '.join(available_servers)}

User request: {user_request}

Based on the user request, which server would be most appropriate? Choose from: {', '.join(available_servers)}

Respond with ONLY the server name, nothing else.
"""

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that chooses the best MCP server for user requests."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            chosen_server = response.choices[0].message.content.strip().lower()
            
            # Validate the choice
            if chosen_server in available_servers:
                return chosen_server
            else:
                # Default to filesystem if LLM choice is invalid
                return "filesystem"
                
        except Exception as e:
            logger.error(f"Error asking LLM to choose server: {e}")
            return "filesystem"  # Default fallback
    
    def ask_llm_to_choose_tool(self, user_request: str, server_name: str, available_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ask LLM to choose the best tool for the user request"""
        
        # Format tools for LLM
        tools_description = ""
        for tool in available_tools:
            tools_description += f"- {tool['name']}: {tool['description']}\n"
        
        prompt = f"""
You are an AI assistant that helps choose the best MCP tool for a user's request.

Server: {server_name}
User request: {user_request}

Available tools:
{tools_description}

Based on the user request, which tool would be most appropriate? 
Respond with ONLY the tool name, nothing else.
"""

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that chooses the best MCP tool for user requests."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.1
            )
            
            chosen_tool_name = response.choices[0].message.content.strip()
            
            # Find the chosen tool
            for tool in available_tools:
                if tool['name'] == chosen_tool_name:
                    return tool
            
            # If not found, return the first tool
            return available_tools[0] if available_tools else None
                
        except Exception as e:
            logger.error(f"Error asking LLM to choose tool: {e}")
            return available_tools[0] if available_tools else None
    
    def ask_llm_for_arguments(self, user_request: str, tool_info: Dict[str, Any]) -> Dict[str, Any]:
        """Ask LLM to generate appropriate arguments for the tool"""
        
        prompt = f"""
You are an AI assistant that generates appropriate arguments for MCP tools.

User request: {user_request}
Tool: {tool_info['name']}
Tool description: {tool_info['description']}
Tool input schema: {json.dumps(tool_info['inputSchema'], indent=2)}

Based on the user request and tool schema, generate appropriate arguments for this tool.
Respond with ONLY a JSON object containing the arguments, nothing else.
"""

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates appropriate arguments for MCP tools."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            arguments_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            try:
                arguments = json.loads(arguments_text)
                return arguments
            except json.JSONDecodeError:
                # Return empty dict if JSON parsing fails
                return {}
                
        except Exception as e:
            logger.error(f"Error asking LLM for arguments: {e}")
            return {}
    
    async def process_user_request(self, user_request: str) -> Dict[str, Any]:
        """Complete workflow: Discover → LLM chooses server → Get tools → LLM chooses tool → Execute"""
        
        try:
            # Step 1: Discover servers
            logger.info("Step 1: Discovering servers...")
            servers_info = await self.discover_servers()
            available_servers = servers_info["available_servers"]
            
            if not available_servers:
                return {"error": "No servers available"}
            
            # Step 2: LLM chooses server
            logger.info("Step 2: LLM choosing server...")
            chosen_server = self.ask_llm_to_choose_server(user_request, available_servers)
            
            # Step 3: Get tools from chosen server
            logger.info(f"Step 3: Getting tools from {chosen_server}...")
            server_tools = await self.get_server_tools(chosen_server)
            
            if "error" in server_tools:
                return {"error": f"Failed to get tools from {chosen_server}: {server_tools['error']}"}
            
            available_tools = server_tools.get("tools", [])
            if not available_tools:
                return {"error": f"No tools available on {chosen_server}"}
            
            # Step 4: LLM chooses tool
            logger.info("Step 4: LLM choosing tool...")
            chosen_tool = self.ask_llm_to_choose_tool(user_request, chosen_server, available_tools)
            
            if not chosen_tool:
                return {"error": "LLM failed to choose a tool"}
            
            # Step 5: LLM generates arguments
            logger.info("Step 5: LLM generating arguments...")
            arguments = self.ask_llm_for_arguments(user_request, chosen_tool)
            
            # Step 6: Execute the tool
            logger.info(f"Step 6: Executing {chosen_tool['name']} on {chosen_server}...")
            result = await self.call_server_tool(chosen_server, chosen_tool['name'], arguments)
            
            return {
                "success": True,
                "workflow": {
                    "user_request": user_request,
                    "step1_discovered_servers": servers_info,
                    "step2_llm_chose_server": chosen_server,
                    "step3_server_tools": server_tools,
                    "step4_llm_chose_tool": chosen_tool,
                    "step5_llm_generated_arguments": arguments,
                    "step6_execution_result": result
                },
                "final_result": result
            }
            
        except Exception as e:
            logger.error(f"Error processing user request: {e}")
            return {"error": f"Failed to process request: {str(e)}"}

# Create the orchestrator
orchestrator = LLMOrchestrator()
server = FastMCP("LLM Orchestrator with OpenAI")

@server.tool
async def process_request(user_request: str) -> Dict[str, Any]:
    """Process user request using LLM orchestration"""
    return await orchestrator.process_user_request(user_request)

@server.tool
async def discover_servers() -> Dict[str, Any]:
    """Discover all available servers"""
    return await orchestrator.discover_servers()

@server.tool
async def get_server_tools(server_name: str) -> Dict[str, Any]:
    """Get tools from a specific server"""
    return await orchestrator.get_server_tools(server_name)

@server.tool
async def call_server_tool(server_name: str, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    """Call a tool on a specific server"""
    return await orchestrator.call_server_tool(server_name, tool_name, arguments)

@server.tool
async def health_check() -> Dict[str, Any]:
    """Check health of all servers"""
    health_status = {}
    
    for server_name, client in orchestrator.clients.items():
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

if __name__ == "__main__":
    logger.info("�� Starting LLM Orchestrator with OpenAI...")
    logger.info(f"📡 Connected to {len(orchestrator.clients)} downstream servers")
    
    # Run the server
    server.run()