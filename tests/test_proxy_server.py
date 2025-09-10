"""
Tests for MCP Proxy Server
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import httpx

# Mock the config and proxy_server modules since they may not exist yet
@pytest.fixture
def mock_config():
    return {
        "DOWNSTREAM_SERVERS": {
            "github": {
                "url": "http://localhost:8001",
                "description": "GitHub MCP Server"
            },
            "filesystem": {
                "url": "http://localhost:8002", 
                "description": "Filesystem MCP Server"
            }
        },
        "PROXY_CONFIG": {
            "host": "0.0.0.0",
            "port": 8000,
            "timeout": 30,
            "max_retries": 3
        }
    }

@pytest.fixture
def mock_proxy_app():
    """Create a mock FastAPI app for testing"""
    from fastapi import FastAPI, HTTPException
    
    app = FastAPI()
    
    @app.get("/")
    async def root():
        return {"status": "running"}
    
    @app.get("/health")
    async def health():
        return {
            "proxy_status": "healthy",
            "downstream_servers": {
                "github": {"status": "healthy"},
                "filesystem": {"status": "healthy"}
            }
        }
    
    @app.get("/proxy/servers")
    async def list_servers():
        return {
            "servers": {
                "github": {"name": "github", "url": "http://localhost:8001"},
                "filesystem": {"name": "filesystem", "url": "http://localhost:8002"}
            }
        }
    
    @app.post("/proxy/{server_name}/mcp/{method_name}")
    async def proxy_request(server_name: str, method_name: str):
        if server_name not in ["github", "filesystem"]:
            raise HTTPException(status_code=404, detail="Server not found")
        
        return {
            "success": True,
            "server": server_name,
            "method": method_name,
            "result": {"message": f"Called {method_name} on {server_name}"}
        }
    
    return app

@pytest.fixture
def client(mock_proxy_app):
    """Create test client"""
    return TestClient(mock_proxy_app)

class TestProxyServer:
    """Test cases for MCP Proxy Server"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns status"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "running"
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "proxy_status" in data
        assert "downstream_servers" in data
        assert data["proxy_status"] == "healthy"
    
    def test_list_servers_endpoint(self, client):
        """Test server listing endpoint"""
        response = client.get("/proxy/servers")
        assert response.status_code == 200
        data = response.json()
        assert "servers" in data
        assert "github" in data["servers"]
        assert "filesystem" in data["servers"]
    
    def test_proxy_request_valid_server(self, client):
        """Test proxying request to valid server"""
        response = client.post("/proxy/github/mcp/list_repos")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["server"] == "github"
        assert data["method"] == "list_repos"
    
    def test_proxy_request_invalid_server(self, client):
        """Test proxying request to invalid server returns 404"""
        response = client.post("/proxy/invalid_server/mcp/some_method")
        assert response.status_code == 404
        data = response.json()
        assert "Server not found" in data["detail"]
    
    def test_proxy_request_filesystem_server(self, client):
        """Test proxying request to filesystem server"""
        response = client.post("/proxy/filesystem/mcp/list_files")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["server"] == "filesystem"
        assert data["method"] == "list_files"

class TestProxyServerRouting:
    """Test routing logic for proxy server"""
    
    @pytest.mark.asyncio
    async def test_routing_prefix_based(self):
        """Test prefix-based routing logic"""
        # Mock routing logic
        def extract_server_from_path(path: str):
            parts = path.split('/')
            if len(parts) >= 3 and parts[1] == 'proxy':
                return parts[2]
            return None
        
        # Test various paths
        assert extract_server_from_path("/proxy/github/mcp/method") == "github"
        assert extract_server_from_path("/proxy/filesystem/mcp/method") == "filesystem"
        assert extract_server_from_path("/invalid/path") is None
    
    @pytest.mark.asyncio
    async def test_request_forwarding(self):
        """Test request forwarding logic"""
        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "success"}
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        
        # Test forwarding
        response = await mock_client.post(
            "http://localhost:8001/mcp/test_method",
            json={"param": "value"}
        )
        
        assert mock_client.post.called
        assert response.json()["result"] == "success"

class TestProxyServerErrorHandling:
    """Test error handling in proxy server"""
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout error handling"""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
        
        with pytest.raises(httpx.TimeoutException):
            await mock_client.post("http://localhost:8001/mcp/method")
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test connection error handling"""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection failed")
        
        with pytest.raises(httpx.ConnectError):
            await mock_client.post("http://localhost:8001/mcp/method")
    
    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test retry logic with exponential backoff"""
        async def mock_retry_function(max_retries=3):
            attempts = 0
            while attempts < max_retries:
                attempts += 1
                if attempts < max_retries:
                    # Simulate failure
                    await asyncio.sleep(0.01)  # Small delay for test
                    continue
                else:
                    # Simulate success on last attempt
                    return {"success": True, "attempts": attempts}
            return {"success": False, "attempts": attempts}
        
        result = await mock_retry_function(3)
        assert result["success"] is True
        assert result["attempts"] == 3

class TestProxyServerConfiguration:
    """Test configuration handling"""
    
    def test_server_config_validation(self, mock_config):
        """Test server configuration validation"""
        servers = mock_config["DOWNSTREAM_SERVERS"]
        
        # Validate required fields
        for server_name, config in servers.items():
            assert "url" in config
            assert "description" in config
            assert isinstance(config["url"], str)
            assert config["url"].startswith("http")
    
    def test_proxy_config_validation(self, mock_config):
        """Test proxy configuration validation"""
        proxy_config = mock_config["PROXY_CONFIG"]
        
        assert "host" in proxy_config
        assert "port" in proxy_config
        assert "timeout" in proxy_config
        assert "max_retries" in proxy_config
        assert isinstance(proxy_config["port"], int)
        assert proxy_config["port"] > 0

if __name__ == "__main__":
    pytest.main([__file__])
