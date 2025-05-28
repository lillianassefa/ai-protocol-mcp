import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional

class MCPClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_methods(self, server: str = None) -> Dict[str, Any]:
        """Get available methods from the MCP server."""
        path = f"{server}/mcp/get_methods" if server else "mcp/get_methods"
        async with self.session.get(f"{self.base_url}/{path}") as response:
            return await response.json()

    async def invoke_method(self, method_name: str, params: Optional[Dict[str, Any]] = None, server: str = None) -> Dict[str, Any]:
        """Invoke a method on the MCP server."""
        payload = {
            "method": method_name,
            "params": params or {}
        }
        path = f"{server}/mcp/invoke_method" if server else "mcp/invoke_method"
        async with self.session.post(f"{self.base_url}/{path}", json=payload) as response:
            return await response.json()

async def main():
    # Example usage with our MCP proxy server
    server_url = "http://localhost:8000"  # Our proxy server
    
    async with MCPClient(server_url) as client:
        try:
            # Test filesystem server
            print("\nTesting filesystem server...")
            result = await client.invoke_method("list_files", {"path": "./"}, server="filesystem")
            print("Filesystem result:", json.dumps(result, indent=2))

            # Test github server
            print("\nTesting github server...")
            result = await client.invoke_method("get_user_info", {"username": "test"}, server="github")
            print("GitHub result:", json.dumps(result, indent=2))

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 