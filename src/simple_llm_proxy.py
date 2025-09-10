"""
Simple LLM Orchestrator - Uses existing proxy server
Just calls the proxy and lets LLM make decisions
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
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-key-here")
client = OpenAI(api_key=OPENAI_API_KEY)

class SimpleLLMOrchestrator:
    """Simple orchestrator that uses existing proxy server"""
    
    def __init__(self):
        # Connect to our existing proxy server (the one we built earlier)
        transport = StdioTransport("python", ["../mcp_proxy_server/proxy_server.py"])
        self.proxy_client = Client(transport)
        logger.info("Connected to existing proxy server")
    
    async def discover_servers(self) -> Dict[str, Any]:
        """Discover servers using existing proxy"""
        try:
            async with self.proxy_client:
                result = await self.proxy_client.call_tool("get_server_status")
                # Convert CallToolResult to dict if needed
                if hasattr(result, 'content'):
                    # If it's TextContent, try to parse as JSON
                    if hasattr(result.content, 'text'):
                        try:
                            return json.loads(result.content.text)
                        except json.JSONDecodeError:
                            return {"error": f"Failed to parse JSON: {result.content.text}"}
                    else:
                        return result.content
                elif hasattr(result, 'dict'):
                    return result.dict()
                elif hasattr(result, '__iter__'):
                    # If it's iterable, convert to list
                    return list(result)
                else:
                    # Try to convert to dict or return as is
                    try:
                        return dict(result)
                    except:
                        return {"result": str(result)}
        except Exception as e:
            logger.error(f"Error discovering servers: {e}")
            return {"error": str(e)}
    
    async def get_all_tools(self) -> Dict[str, Any]:
        """Get all tools using existing proxy"""
        try:
            async with self.proxy_client:
                result = await self.proxy_client.call_tool("list_all_tools")
                # Convert CallToolResult to dict if needed
                if hasattr(result, 'content'):
                    # If it's TextContent, try to parse as JSON
                    if hasattr(result.content, 'text'):
                        try:
                            return json.loads(result.content.text)
                        except json.JSONDecodeError:
                            return {"error": f"Failed to parse JSON: {result.content.text}"}
                    else:
                        return result.content
                elif hasattr(result, 'dict'):
                    return result.dict()
                elif hasattr(result, '__iter__'):
                    # If it's iterable, convert to list
                    return list(result)
                else:
                    # Try to convert to dict or return as is
                    try:
                        return dict(result)
                    except:
                        return {"result": str(result)}
        except Exception as e:
            logger.error(f"Error getting tools: {e}")
            return {"error": str(e)}
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call tool using existing proxy"""
        try:
            async with self.proxy_client:
                # Always add server prefix since LLM returns actual tool name
                full_tool_name = f"{server_name}_{tool_name}"
                logger.info(f"Calling proxy with tool: {full_tool_name}")
                
                result = await self.proxy_client.call_tool("route_tool_call", {
                    "tool_name": full_tool_name,  # Always add server prefix
                    "arguments": arguments or {}
                })
                
                # Debug: log the result type and content
                logger.info(f"Result type: {type(result)}")
                logger.info(f"Result content: {result}")
                
                # Convert CallToolResult to dict if needed
                if hasattr(result, 'content'):
                    # If it's TextContent, try to parse as JSON
                    if hasattr(result.content, 'text'):
                        try:
                            parsed_result = json.loads(result.content.text)
                            logger.info(f"Parsed JSON result: {parsed_result}")
                            return parsed_result
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse JSON: {result.content.text}")
                            return {"error": f"Failed to parse JSON: {result.content.text}"}
                    else:
                        logger.info(f"Returning content directly: {result.content}")
                        return result.content
                elif hasattr(result, 'dict'):
                    dict_result = result.dict()
                    logger.info(f"Converted to dict: {dict_result}")
                    return dict_result
                elif hasattr(result, '__iter__'):
                    # If it's iterable, convert to list
                    list_result = list(result)
                    logger.info(f"Converted to list: {list_result}")
                    return list_result
                else:
                    # Try to convert to dict or return as is
                    try:
                        dict_result = dict(result)
                        logger.info(f"Converted to dict via dict(): {dict_result}")
                        return dict_result
                    except Exception as e:
                        logger.warning(f"Could not convert result to dict: {e}")
                        return {"result": str(result)}
        except Exception as e:
            logger.error(f"Error calling tool: {e}")
            return {"error": str(e)}
    
    def ask_llm_to_choose_server_and_tool(self, user_request: str, all_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Ask LLM to choose server and tool in one go"""
        
        # Handle case where all_tools might be a list or have different structure
        if isinstance(all_tools, list):
            # If it's a list, extract the first element which should contain the data
            if len(all_tools) > 0:
                first_item = all_tools[0]
                # If it's TextContent, extract the text and parse as JSON
                if hasattr(first_item, 'text'):
                    try:
                        all_tools = json.loads(first_item.text)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON from TextContent: {first_item.text}")
                        return {
                            "server": "filesystem",
                            "tool": "list_directory",
                            "arguments": {"path": "/projects"}
                        }
                else:
                    all_tools = first_item
            else:
                logger.warning("all_tools is an empty list. Using fallback.")
                return {
                    "server": "filesystem",
                    "tool": "list_directory",
                    "arguments": {"path": "/projects"}
                }
        
        # Format available tools for LLM - show actual tool names
        tools_summary = ""
        for server_name, tools_list in all_tools.items():
            tools_summary += f"\n{server_name.upper()} SERVER:\n"
            for tool_name in tools_list:
                # Show the actual tool name (without prefix) to the LLM
                tools_summary += f"- {tool_name}\n"
        
        prompt = f"""
You are an AI assistant that helps choose the best MCP server and tool for user requests.

User request: {user_request}

Available tools:{tools_summary}

Based on the user request, choose the best server and tool. Respond with ONLY a JSON object like this:
{{"server": "server_name", "tool": "exact_tool_name_from_list", "arguments": {{"param1": "value1"}}}}

CRITICAL RULES:
1. Use the EXACT tool name from the list above (e.g., "search_repositories", "list_directory")
2. Do NOT add any prefixes - use the tool name exactly as shown
3. The tool name should be one of the options listed above
4. Choose the most appropriate server and tool for the user's request

Example correct response:
{{"server": "github", "tool": "search_repositories", "arguments": {{"query": "test"}}}}
"""

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that chooses the best MCP server and tool for user requests."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Debug: log the LLM response
            logger.info(f"LLM response: {response_text}")
            
            # Try to parse JSON response
            try:
                decision = json.loads(response_text)
                
                # Debug: log the parsed decision
                logger.info(f"Parsed decision: {decision}")
                
                # Clean up tool name if it has server prefix in the wrong format
                if "tool" in decision:
                    tool_name = decision["tool"]
                    
                    # Debug: log the original tool name
                    logger.info(f"Original tool name from LLM: {tool_name}")
                    
                    # Remove any server prefix that might be incorrectly included
                    if " SERVER_" in tool_name:
                        # Extract the part after "SERVER_"
                        tool_name = tool_name.split("SERVER_")[1]
                        decision["tool"] = tool_name
                        logger.info(f"Cleaned tool name: {tool_name}")
                    
                    # Validate that the tool name is a valid choice
                    server_name = decision.get('server', '')
                    if server_name and server_name in all_tools:
                        available_tools = all_tools[server_name]
                        if tool_name not in available_tools:
                            logger.warning(f"Tool '{tool_name}' not found in {server_name} server. Available: {available_tools}")
                            # Use first available tool as fallback
                            if available_tools:
                                decision["tool"] = available_tools[0]
                                logger.info(f"Using fallback tool: {available_tools[0]}")
                
                return decision
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {response_text}")
                # Fallback: choose filesystem server with correct tool name
                return {
                    "server": "filesystem",
                    "tool": "list_directory",
                    "arguments": {"path": "/projects"}
                }
                
        except Exception as e:
            logger.error(f"Error asking LLM: {e}")
            # Fallback
            return {
                "server": "filesystem",
                "tool": "list_directory",
                "arguments": {"path": "/projects"}
            }
    
    async def process_user_request(self, user_request: str) -> Dict[str, Any]:
        """Simple workflow: Get tools → LLM decides → Execute"""
        
        try:
            # Step 1: Get all tools from proxy
            logger.info("Step 1: Getting all tools from proxy...")
            all_tools = await self.get_all_tools()
            
            # Debug: log the structure
            logger.info(f"all_tools type: {type(all_tools)}")
            logger.info(f"all_tools content: {all_tools}")
            
            if "error" in all_tools:
                return {"error": f"Failed to get tools: {all_tools['error']}"}
            
            # Step 2: LLM chooses server and tool
            logger.info("Step 2: LLM choosing server and tool...")
            llm_decision = self.ask_llm_to_choose_server_and_tool(user_request, all_tools)
            
            server_name = llm_decision.get("server")
            tool_name = llm_decision.get("tool")
            arguments = llm_decision.get("arguments", {})
            
            if not server_name or not tool_name:
                return {"error": "LLM failed to choose server or tool"}
            
            # Step 3: Execute the tool
            logger.info(f"Step 3: Executing {tool_name} on {server_name}...")
            result = await self.call_tool(server_name, tool_name, arguments)
            
            logger.info(f"Tool execution completed. Result type: {type(result)}")
            
            return {
                "success": True,
                "workflow": {
                    "user_request": user_request,
                    "step1_all_tools": all_tools,
                    "step2_llm_decision": llm_decision,
                    "step3_execution_result": result
                },
                "final_result": result
            }
            
        except Exception as e:
            logger.error(f"Error processing user request: {e}")
            return {"error": f"Failed to process request: {str(e)}"}

# Create the simple orchestrator
orchestrator = SimpleLLMOrchestrator()
server = FastMCP("Simple LLM Orchestrator")

@server.tool
async def process_request(user_request: str) -> Dict[str, Any]:
    """Process user request using LLM orchestration"""
    return await orchestrator.process_user_request(user_request)

@server.tool
async def discover_servers() -> Dict[str, Any]:
    """Discover all available servers"""
    return await orchestrator.discover_servers()

@server.tool
async def get_all_tools() -> Dict[str, Any]:
    """Get all tools from all servers"""
    return await orchestrator.get_all_tools()

@server.tool
async def call_tool(server_name: str, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    """Call a tool on a specific server"""
    return await orchestrator.call_tool(server_name, tool_name, arguments)

@server.tool
async def health_check() -> Dict[str, Any]:
    """Check health of all servers"""
    try:
        async with orchestrator.proxy_client:
            health = await orchestrator.proxy_client.call_tool("health_check")
            # Convert CallToolResult to dict if needed
            if hasattr(health, 'content'):
                # If it's TextContent, try to parse as JSON
                if hasattr(health.content, 'text'):
                    try:
                        return json.loads(health.content.text)
                    except json.JSONDecodeError:
                        return {"error": f"Failed to parse JSON: {health.content.text}"}
                else:
                    return health.content
            elif hasattr(health, 'dict'):
                return health.dict()
            elif hasattr(health, '__iter__'):
                # If it's iterable, convert to list
                return list(health)
            else:
                # Try to convert to dict or return as is
                try:
                    return dict(health)
                except:
                    return {"result": str(health)}
    except Exception as e:
        return {"error": f"Health check failed: {str(e)}"}

if __name__ == "__main__":
    logger.info("🧠 Starting Simple LLM Orchestrator...")
    logger.info("📡 Using existing proxy server")
    
    # Run the server
    server.run() 