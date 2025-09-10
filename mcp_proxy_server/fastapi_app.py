"""
FastAPI wrapper for MCP Proxy Server
Provides HTTP REST API endpoints to access the MCP proxy functionality
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
import logging
from contextlib import asynccontextmanager

# Import our proxy components
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from config import MCP_SERVER_CONFIGS, PROXY_CONFIG

# Pydantic models for request/response
class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Optional[Dict[str, Any]] = {}
    headers: Optional[Dict[str, str]] = {}

class ToolCallResponse(BaseModel):
    success: bool
    server: Optional[str] = None
    tool: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None

class ServerStatus(BaseModel):
    server_name: str
    status: str
    response_time_ms: Optional[float] = None
    tools_count: Optional[int] = None

# Global proxy client
proxy_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup the proxy client"""
    global proxy_client
    
    # Startup
    print("🚀 Starting FastAPI MCP Proxy Server...")
    transport = StdioTransport("python", ["proxy_server.py"])
    proxy_client = Client(transport)
    
    try:
        async with proxy_client:
            await proxy_client.ping()
            print("✅ Proxy server connected successfully")
    except Exception as e:
        print(f"❌ Failed to connect to proxy server: {e}")
        raise
    
    yield
    proxy_client = None


app = FastAPI(
    title="MCP Proxy API",
    description="REST API for Model Context Protocol Proxy Server",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Check if the API and proxy server are healthy"""
    try:
        async with proxy_client:
            health_data = await proxy_client.call_tool("health_check")
            return {
                "api_status": "healthy",
                "proxy_status": health_data.get("summary", {}).get("overall_status", "unknown"),
                "details": health_data
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Proxy server unavailable: {str(e)}")

# Get available tools
@app.get("/tools")
async def list_tools():
    """List all available tools from all servers"""
    try:
        async with proxy_client:
            all_tools = await proxy_client.call_tool("list_all_tools")
            return {"success": True, "tools": all_tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get methods aggregation
@app.get("/methods")
async def get_methods():
    """Get aggregated methods from all downstream servers"""
    try:
        async with proxy_client:
            methods = await proxy_client.call_tool("get_methods")
            return {"success": True, "data": methods}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Server status
@app.get("/servers/status")
async def get_servers_status():
    """Get status of all downstream servers"""
    try:
        async with proxy_client:
            status = await proxy_client.call_tool("get_server_status")
            return {"success": True, "servers": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Proxy configuration
@app.get("/config")
async def get_proxy_config():
    """Get current proxy configuration"""
    try:
        async with proxy_client:
            config = await proxy_client.call_tool("list_proxy_config")
            return {"success": True, "config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Main tool calling endpoint
@app.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    """Call a tool through the proxy server"""
    try:
        async with proxy_client:
            result = await proxy_client.call_tool("route_tool_call", {
                "tool_name": request.tool_name,
                "arguments": request.arguments,
                "headers": request.headers
            })
            
            # Check if there was an error in the result
            if isinstance(result, dict) and "error" in result:
                return ToolCallResponse(
                    success=False,
                    error=result["error"],
                    server=result.get("server"),
                    tool=result.get("tool")
                )
            else:
                return ToolCallResponse(
                    success=True,
                    server=result.get("server"),
                    tool=result.get("tool"),
                    result=result.get("result")
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route by prefix endpoint
@app.post("/tools/route-by-prefix")
async def route_by_prefix(tool_prefix: str, tool_suffix: str, arguments: Optional[Dict[str, Any]] = None):
    """Route a tool call by specifying prefix and suffix"""
    try:
        async with proxy_client:
            result = await proxy_client.call_tool("route_by_prefix", {
                "tool_prefix": tool_prefix,
                "tool_suffix": tool_suffix,
                "arguments": arguments or {}
            })
            return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Test routing endpoint
@app.post("/tools/test-routing")
async def test_routing(tool_name: str):
    """Test routing logic without actually calling the tool"""
    try:
        async with proxy_client:
            result = await proxy_client.call_tool("test_routing", {"tool_name": tool_name})
            return {"success": True, "routing": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# GitHub-specific endpoints
@app.post("/github/create-issue")
async def github_create_issue(title: str, body: str, repo: Optional[str] = None):
    """Create a GitHub issue"""
    try:
        async with proxy_client:
            result = await proxy_client.call_tool("route_tool_call", {
                "tool_name": "github_create_issue",
                "arguments": {"title": title, "body": body, "repo": repo}
            })
            return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Filesystem-specific endpoints
@app.post("/filesystem/read-file")
async def filesystem_read_file(path: str):
    """Read a file from the filesystem"""
    try:
        async with proxy_client:
            result = await proxy_client.call_tool("route_tool_call", {
                "tool_name": "filesystem_read_file",
                "arguments": {"path": path}
            })
            return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/filesystem/list-files")
async def filesystem_list_files(path: str = "/"):
    """List files in a directory"""
    try:
        async with proxy_client:
            result = await proxy_client.call_tool("route_tool_call", {
                "tool_name": "filesystem_list_files", 
                "arguments": {"path": path}
            })
            return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Atlassian-specific endpoints
@app.post("/atlassian/create-ticket")
async def atlassian_create_ticket(title: str, description: str, issue_type: str = "Task"):
    """Create an Atlassian ticket"""
    try:
        async with proxy_client:
            result = await proxy_client.call_tool("route_tool_call", {
                "tool_name": "atlassian_create_ticket",
                "arguments": {"title": title, "description": description, "issue_type": issue_type}
            })
            return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    print("🌐 Starting FastAPI MCP Proxy Server...")
    print("📖 API Documentation will be available at: http://localhost:8000/docs")
    print("🔍 Alternative docs at: http://localhost:8000/redoc")
    
    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 