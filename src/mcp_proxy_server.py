from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import httpx
import json
import logging
import subprocess
import asyncio
from urllib.parse import urljoin
from httpx import AsyncClient, ASGITransport

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Proxy Server")

# Configuration for downstream MCP servers
MCP_SERVERS = {
    "filesystem": "stdio",  # Filesystem MCP server uses stdio
    "github": "http://localhost:8002",      # GitHub MCP server
    "gdrive": "http://localhost:8003",      # Google Drive MCP server
    "atlassian": "http://localhost:8004",   # Atlassian MCP server
}

class MCPRequest(BaseModel):
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPProxy:
    def __init__(self, servers: Dict[str, str]):
        self.servers = servers
        self.client = httpx.AsyncClient()
        self.filesystem_process = None
        self.filesystem_stdin = None
        self.filesystem_stdout = None

    async def get_target_server(self, path: str) -> tuple[str, str]:
        """Determine target server from path and return server URL and remaining path."""
        parts = path.strip('/').split('/')
        if not parts:
            raise HTTPException(status_code=400, detail="Invalid path")
        
        server_key = parts[0]
        if server_key not in self.servers:
            raise HTTPException(status_code=404, detail=f"Unknown MCP server: {server_key}")
        
        remaining_path = '/'.join(parts[1:])
        return self.servers[server_key], remaining_path

    async def start_filesystem_server(self):
        """Start the filesystem server process if not already running."""
        if self.filesystem_process is None:
            try:
                # Start the filesystem server process
                self.filesystem_process = subprocess.Popen(
                    ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/home/lillian/Documents/projects"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                self.filesystem_stdin = self.filesystem_process.stdin
                self.filesystem_stdout = self.filesystem_process.stdout
                logger.info("Started filesystem MCP server")
            except Exception as e:
                logger.error(f"Failed to start filesystem server: {e}")
                raise HTTPException(status_code=500, detail="Failed to start filesystem server")

    async def forward_request(self, server_url: str, path: str, request: MCPRequest) -> Dict[str, Any]:
        """Forward request to target MCP server."""
        try:
            if server_url == "stdio":
                # Handle stdio communication for filesystem server
                await self.start_filesystem_server()
                
                # Send request to filesystem server
                request_json = json.dumps({
                    "jsonrpc": "2.0",
                    "method": request.method,
                    "params": request.params or {},
                    "id": 1
                })
                self.filesystem_stdin.write(request_json + "\n")
                self.filesystem_stdin.flush()
                
                # Read response from filesystem server
                response_line = self.filesystem_stdout.readline()
                if not response_line:
                    raise Exception("No response from filesystem server")
                
                response = json.loads(response_line)
                if "error" in response:
                    return {
                        "error": {
                            "code": "SERVER_ERROR",
                            "message": response["error"].get("message", "Unknown error")
                        }
                    }
                return response.get("result", {})
            else:
                # Handle HTTP communication for other servers
                url = urljoin(server_url, path)
                logger.info(f"Forwarding request to {url}")
                
                response = await self.client.post(
                    url,
                    json=request.model_dump(),
                    timeout=30.0
                )
                response.raise_for_status()
                return await response.json()
        except httpx.ConnectError:
            logger.error(f"Cannot connect to server at {server_url}")
            return {
                "error": {
                    "code": "SERVER_UNAVAILABLE",
                    "message": f"The MCP server at {server_url} is not running. Please start the server and try again."
                }
            }
        except httpx.HTTPError as e:
            logger.error(f"Error forwarding request: {str(e)}")
            return {
                "error": {
                    "code": "HTTP_ERROR",
                    "message": f"Error forwarding request: {str(e)}"
                }
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                "error": {
                    "code": "UNKNOWN_ERROR",
                    "message": str(e)
                }
            }

proxy = MCPProxy(MCP_SERVERS)

@app.post("/{path:path}")
async def proxy_request(path: str, request: MCPRequest):
    """Handle incoming MCP requests and route them to appropriate servers."""
    try:
        server_url, remaining_path = await proxy.get_target_server(path)
        result = await proxy.forward_request(server_url, remaining_path, request)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 