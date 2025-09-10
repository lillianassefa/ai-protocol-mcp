"""
MCP Proxy Server with Dynamic Routing
Routes requests to different downstream MCP servers based on configurable rules
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from fastmcp import FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.server.proxy import ProxyClient
from fastmcp import Client

from config import MCP_SERVER_CONFIGS, PROXY_CONFIG, ROUTING_CONFIG

# Configure logging
logging.basicConfig(
    level=getattr(logging, PROXY_CONFIG["log_level"]),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPProxyRouter:
    """Handles routing logic for determining target server"""
    
    def __init__(self):
        self.strategy = ROUTING_CONFIG.get("routing_strategy", "prefix")
        self.delimiter = ROUTING_CONFIG.get("prefix_delimiter", "_")
        self.default_server = PROXY_CONFIG.get("default_server", "filesystem")
    
    def route_tool_call(self, tool_name: str, headers: Dict[str, str] = None) -> str:
        """Determine target server for a tool call"""
        if self.strategy == "prefix":
            return self._route_by_prefix(tool_name)
        elif self.strategy == "header":
            return self._route_by_header(headers)
        else:
            return self.default_server
    
    def route_resource_read(self, uri: str, headers: Dict[str, str] = None) -> str:
        """Determine target server for a resource read"""
        if self.strategy == "prefix":
            # Extract server from URI like "github://repo/issues"
            if "://" in uri:
                server_name = uri.split("://")[0]
                if server_name in MCP_SERVER_CONFIGS:
                    return server_name
        elif self.strategy == "header":
            return self._route_by_header(headers)
        
        return self.default_server
    
    def _route_by_prefix(self, tool_name: str) -> str:
        """Route based on tool name prefix (e.g., github_create_issue -> github)"""
        logger.info(f"Routing tool '{tool_name}' with delimiter '{self.delimiter}'")
        if self.delimiter in tool_name:
            prefix = tool_name.split(self.delimiter)[0]
            logger.info(f"Extracted prefix: '{prefix}' from tool '{tool_name}'")
            if prefix in MCP_SERVER_CONFIGS:
                logger.info(f"Found server '{prefix}' in config, routing to it")
                return prefix
            else:
                logger.warning(f"Prefix '{prefix}' not found in MCP_SERVER_CONFIGS: {list(MCP_SERVER_CONFIGS.keys())}")
        else:
            logger.info(f"No delimiter '{self.delimiter}' found in tool name '{tool_name}'")
        logger.info(f"Using default server: {self.default_server}")
        return self.default_server
    
    def _route_by_header(self, headers: Dict[str, str]) -> str:
        """Route based on HTTP header"""
        if headers:
            target = headers.get(ROUTING_CONFIG.get("header_name", "X-Target-MCP"))
            if target and target in MCP_SERVER_CONFIGS:
                return target
        return self.default_server

class MCPClientManager:
    """Manages connections to downstream MCP servers"""
    
    def __init__(self):
        self.clients: Dict[str, ProxyClient] = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize ProxyClient instances for each configured server"""
        for server_name, config in MCP_SERVER_CONFIGS.items():
            try:
                if config["transport"] == "stdio":
                    transport = StdioTransport(
                        command=config["command"],
                        args=config["args"],
                        env=config.get("env", {})
                    )
                    self.clients[server_name] = ProxyClient(transport)
                    logger.info(f"Initialized client for {server_name}")
                else:
                    logger.warning(f"Unsupported transport for {server_name}: {config['transport']}")
            except Exception as e:
                logger.error(f"Failed to initialize client for {server_name}: {e}")
    
    def get_client(self, server_name: str) -> Optional[ProxyClient]:
        """Get client for specified server"""
        return self.clients.get(server_name)
    
    def list_servers(self) -> List[str]:
        """List all available server names"""
        return list(self.clients.keys())

router = MCPProxyRouter()
client_manager = MCPClientManager()

proxy_server = FastMCP(PROXY_CONFIG["name"])

@proxy_server.tool
async def route_tool_call(tool_name: str, arguments: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
    """Route tool calls to appropriate downstream server"""
    target_server = router.route_tool_call(tool_name, headers)
    client = client_manager.get_client(target_server)
    
    if not client:
        error_msg = f"No client available for server: {target_server}"
        logger.error(error_msg)
        return {"error": error_msg, "available_servers": client_manager.list_servers()}
    
    try:
        logger.info(f"Routing tool '{tool_name}' to server '{target_server}'")
        
        # Strip the server prefix to get the actual tool name for the downstream server
        actual_tool_name = tool_name
        if tool_name.startswith(f"{target_server}_"):
            actual_tool_name = tool_name[len(f"{target_server}_"):]
            logger.info(f"Stripped prefix, actual tool name: '{actual_tool_name}'")
        
        # Create a regular client from the ProxyClient for the actual call
        if target_server in MCP_SERVER_CONFIGS:
            config = MCP_SERVER_CONFIGS[target_server]
            transport = StdioTransport(
                command=config["command"],
                args=config["args"],
                env=config.get("env", {})
            )
            actual_client = Client(transport)
            
            async with actual_client:
                result = await actual_client.call_tool(actual_tool_name, arguments or {})
                logger.info(f"Successfully called tool '{actual_tool_name}' on '{target_server}'")
                return {
                    "server": target_server,
                    "tool": actual_tool_name,
                    "result": result
                }
        else:
            raise Exception(f"Server config not found: {target_server}")
            
    except Exception as e:
        error_msg = f"Error calling tool '{tool_name}' on server '{target_server}': {str(e)}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "server": target_server,
            "tool": tool_name
        }

@proxy_server.tool
async def list_all_tools() -> Dict[str, Any]:
    """List all available tools from all downstream servers"""
    all_tools = {}
    
    for server_name, client in client_manager.clients.items():
        try:
            config = MCP_SERVER_CONFIGS[server_name]
            transport = StdioTransport(
                command=config["command"],
                args=config["args"],
                env=config.get("env", {})
            )
            actual_client = Client(transport)
            
            async with actual_client:
                tools = await actual_client.list_tools()
                all_tools[server_name] = [tool.name for tool in tools]
                logger.info(f"Listed {len(tools)} tools from {server_name}")
                
        except Exception as e:
            logger.error(f"Failed to list tools from {server_name}: {e}")
            all_tools[server_name] = f"Error: {str(e)}"
    
    return all_tools

@proxy_server.tool
async def get_server_status() -> Dict[str, Any]:
    """Get status of all downstream servers"""
    status = {}
    
    for server_name in client_manager.list_servers():
        try:
            config = MCP_SERVER_CONFIGS[server_name]
            transport = StdioTransport(
                command=config["command"],
                args=config["args"],
                env=config.get("env", {})
            )
            client = Client(transport)
            
            async with client:
                await client.ping()
                status[server_name] = "✅ Connected"
                
        except Exception as e:
            status[server_name] = f"❌ Error: {str(e)}"
    
    return status

@proxy_server.tool 
async def route_by_prefix(tool_prefix: str, tool_suffix: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    """Manually route a tool call by specifying prefix and suffix"""
    full_tool_name = f"{tool_prefix}_{tool_suffix}"
    
    # Call the route_tool_call function directly instead of trying to call it as a tool
    target_server = router.route_tool_call(full_tool_name)
    client = client_manager.get_client(target_server)
    
    if not client:
        return {
            "error": f"No client available for server: {target_server}",
            "tool_name": full_tool_name,
            "routed_to": target_server
        }
    
    try:
        logger.info(f"Routing tool '{full_tool_name}' to server '{target_server}'")
        
        # Create a regular client for the actual call
        if target_server in MCP_SERVER_CONFIGS:
            config = MCP_SERVER_CONFIGS[target_server]
            transport = StdioTransport(
                command=config["command"],
                args=config["args"],
                env=config.get("env", {})
            )
            actual_client = Client(transport)
            
            async with actual_client:
                result = await actual_client.call_tool(full_tool_name, arguments or {})
                logger.info(f"Successfully called tool '{full_tool_name}' on '{target_server}'")
                return {
                    "server": target_server,
                    "tool": full_tool_name,
                    "result": result
                }
        else:
            raise Exception(f"Server config not found: {target_server}")
            
    except Exception as e:
        error_msg = f"Error calling tool '{full_tool_name}' on server '{target_server}': {str(e)}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "server": target_server,
            "tool": full_tool_name
        }

@proxy_server.tool
async def list_proxy_config() -> Dict[str, Any]:
    """List current proxy configuration"""
    return {
        "proxy_config": PROXY_CONFIG,
        "routing_config": ROUTING_CONFIG,
        "available_servers": list(MCP_SERVER_CONFIGS.keys()),
        "active_clients": client_manager.list_servers()
    }

@proxy_server.tool
async def get_methods() -> Dict[str, Any]:
    """Aggregate get_methods from all downstream servers"""
    aggregated_methods = {}
    
    for server_name in client_manager.list_servers():
        try:
            config = MCP_SERVER_CONFIGS[server_name]
            transport = StdioTransport(
                command=config["command"],
                args=config["args"],
                env=config.get("env", {})
            )
            client = Client(transport)
            
            async with client:
                # Get tools (methods) from each server
                tools = await client.list_tools()
                methods = []
                
                for tool in tools:
                    method_info = {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    }
                    methods.append(method_info)
                
                aggregated_methods[server_name] = {
                    "methods": methods,
                    "count": len(methods),
                    "status": "✅ Available"
                }
                
                logger.info(f"Aggregated {len(methods)} methods from {server_name}")
                
        except Exception as e:
            logger.error(f"Failed to get methods from {server_name}: {e}")
            aggregated_methods[server_name] = {
                "methods": [],
                "count": 0,
                "status": f"❌ Error: {str(e)}"
            }
    
    return {
        "servers": aggregated_methods,
        "total_servers": len(aggregated_methods),
        "total_methods": sum(server.get("count", 0) for server in aggregated_methods.values())
    }

@proxy_server.tool
async def test_routing(tool_name: str) -> Dict[str, Any]:
    """Test routing logic without actually calling the tool"""
    target_server = router.route_tool_call(tool_name)
    
    return {
        "tool_name": tool_name,
        "routed_to": target_server,
        "routing_strategy": router.strategy,
        "available_servers": list(MCP_SERVER_CONFIGS.keys()),
        "is_valid_server": target_server in MCP_SERVER_CONFIGS
    }

@proxy_server.tool
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check of proxy and all downstream servers"""
    health_status = {
        "proxy_server": {
            "status": "✅ Running",
            "name": PROXY_CONFIG["name"],
            "routing_strategy": router.strategy,
            "timestamp": asyncio.get_event_loop().time()
        },
        "downstream_servers": {}
    }
    
    # Check each downstream server
    for server_name in client_manager.list_servers():
        try:
            config = MCP_SERVER_CONFIGS[server_name]
            transport = StdioTransport(
                command=config["command"],
                args=config["args"],
                env=config.get("env", {})
            )
            client = Client(transport)
            
            start_time = asyncio.get_event_loop().time()
            async with client:
                await client.ping()
                tools = await client.list_tools()
                
            response_time = asyncio.get_event_loop().time() - start_time
            
            health_status["downstream_servers"][server_name] = {
                "status": "✅ Healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "tools_count": len(tools),
                "transport": config["transport"]
            }
            
        except Exception as e:
            health_status["downstream_servers"][server_name] = {
                "status": f"❌ Unhealthy: {str(e)}",
                "response_time_ms": None,
                "tools_count": 0,
                "transport": config.get("transport", "unknown")
            }
    
    # Calculate overall health
    healthy_servers = sum(1 for server in health_status["downstream_servers"].values() 
                         if "✅" in server["status"])
    total_servers = len(health_status["downstream_servers"])
    
    health_status["summary"] = {
        "healthy_servers": healthy_servers,
        "total_servers": total_servers,
        "health_percentage": round((healthy_servers / total_servers) * 100, 1) if total_servers > 0 else 0,
        "overall_status": "✅ Healthy" if healthy_servers == total_servers else "⚠️ Partial" if healthy_servers > 0 else "❌ Unhealthy"
    }
    
    return health_status

if __name__ == "__main__":
    logger.info(f"Starting {PROXY_CONFIG['name']}")
    logger.info(f"Available servers: {list(MCP_SERVER_CONFIGS.keys())}")
    logger.info(f"Routing strategy: {ROUTING_CONFIG.get('routing_strategy', 'prefix')}")
    
    # Run the proxy server
    proxy_server.run() 