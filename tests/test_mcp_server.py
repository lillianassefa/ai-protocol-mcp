import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from src.mcp_proxy_server import app, MCPProxy, MCPRequest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

client = TestClient(app)

# Mock responses for different servers
MOCK_GITHUB_RESPONSE = {
    "result": {
        "methods": [
            "get_user_info",
            "list_repositories",
            "create_issue",
            "update_issue"
        ]
    }
}

MOCK_FILESYSTEM_RESPONSE = {
    "result": {
        "files": [
            "test_file.txt",
            "config.json"
        ]
    }
}

MOCK_GDRIVE_RESPONSE = {
    "result": {
        "files": [
            {
                "id": "doc1",
                "name": "Test Document",
                "type": "document"
            }
        ]
    }
}

@pytest.fixture
def mock_httpx_client():
    with patch('httpx.AsyncClient') as mock:
        mock_client = AsyncMock()
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_subprocess():
    with patch('subprocess.Popen') as mock:
        process = MagicMock()
        process.stdin = MagicMock()
        process.stdout = MagicMock()
        mock.return_value = process
        yield mock

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_get_target_server():
    """Test server target resolution."""
    proxy = MCPProxy({
        "github": "http://localhost:8002",
        "filesystem": "stdio",
        "gdrive": "http://localhost:8003"
    })
    
    # Test valid server
    server_url, path = await proxy.get_target_server("github/test")
    assert server_url == "http://localhost:8002"
    assert path == "test"
    
    # Test invalid server
    with pytest.raises(Exception):
        await proxy.get_target_server("invalid/test")

@pytest.mark.asyncio
async def test_forward_request_github(mock_httpx_client):
    """Test forwarding requests to GitHub server."""
    mock_response = AsyncMock()
    mock_response.json.return_value = MOCK_GITHUB_RESPONSE
    mock_response.raise_for_status = AsyncMock()
    mock_httpx_client.post.return_value = mock_response

    proxy = MCPProxy({"github": "http://localhost:8002"})
    request = MCPRequest(method="get_methods")

    result = await proxy.forward_request("http://localhost:8002", "test", request)
    assert result == MOCK_GITHUB_RESPONSE

@pytest.mark.asyncio
async def test_forward_request_filesystem(mock_subprocess):
    """Test forwarding requests to filesystem server."""
    mock_process = mock_subprocess.return_value
    mock_process.stdout.readline.return_value = json.dumps(MOCK_FILESYSTEM_RESPONSE)
    
    proxy = MCPProxy({"filesystem": "stdio"})
    request = MCPRequest(method="list_files", params={"path": "./"})
    
    result = await proxy.forward_request("stdio", "", request)
    assert result == MOCK_FILESYSTEM_RESPONSE["result"]

def test_proxy_request_github():
    """Test proxy request to GitHub server."""
    with patch('src.mcp_proxy_server.proxy.forward_request') as mock_forward:
        mock_forward.return_value = MOCK_GITHUB_RESPONSE
        
        response = client.post(
            "/github/test",
            json={"method": "get_methods"}
        )
        assert response.status_code == 200
        assert response.json() == MOCK_GITHUB_RESPONSE

def test_proxy_request_invalid_server():
    """Test proxy request to invalid server."""
    response = client.post(
        "/invalid/test",
        json={"method": "get_methods"}
    )
    assert response.status_code == 404

def test_proxy_request_invalid_method():
    """Test proxy request with invalid method."""
    response = client.post(
        "/github/test",
        json={"method": "invalid_method"}
    )
    assert response.status_code == 200
    assert "error" in response.json()

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in proxy server."""
    proxy = MCPProxy({"github": "http://localhost:8002"})
    
    # Test connection error
    with patch('httpx.AsyncClient.post', side_effect=Exception("Connection error")):
        result = await proxy.forward_request(
            "http://localhost:8002",
            "test",
            MCPRequest(method="get_methods")
        )
        assert "error" in result
        assert result["error"]["code"] == "UNKNOWN_ERROR"

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test handling of concurrent requests."""
    transport = ASGITransport(app=app)
    async def make_request():
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/github/test",
                json={"method": "get_methods"}
            )
            return response.json()
    tasks = [make_request() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    assert all("result" in result or "error" in result for result in results) 