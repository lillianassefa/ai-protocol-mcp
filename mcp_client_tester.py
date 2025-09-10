"""
MCP Client Tester Script
Tests interaction with MCP servers and the proxy
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
import httpx
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MCPServer:
    """MCP Server configuration"""
    name: str
    url: str
    description: str

class MCPClientTester:
    """MCP Client for testing server interactions"""
    
    def __init__(self, proxy_url: str = "http://localhost:8000"):
        self.proxy_url = proxy_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_servers = [
            MCPServer("github", "http://localhost:8001", "GitHub MCP Server"),
            MCPServer("filesystem", "http://localhost:8002", "Filesystem MCP Server"),
            MCPServer("atlassian", "http://localhost:8003", "Atlassian MCP Server"),
        ]
    
    async def test_proxy_health(self) -> Dict[str, Any]:
        """Test proxy server health"""
        try:
            response = await self.client.get(f"{self.proxy_url}/health")
            response.raise_for_status()
            result = response.json()
            logger.info("✅ Proxy health check passed")
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"❌ Proxy health check failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_list_servers(self) -> Dict[str, Any]:
        """Test listing available servers"""
        try:
            response = await self.client.get(f"{self.proxy_url}/proxy/servers")
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Found {len(result.get('servers', {}))} servers")
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"❌ Failed to list servers: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_get_methods(self, server_name: str) -> Dict[str, Any]:
        """Test getting methods from a specific server"""
        try:
            response = await self.client.get(f"{self.proxy_url}/proxy/{server_name}/mcp/methods")
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Got methods from {server_name}")
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"❌ Failed to get methods from {server_name}: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_invoke_method(self, server_name: str, method_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Test invoking a method on a server"""
        try:
            payload = params or {}
            response = await self.client.post(
                f"{self.proxy_url}/proxy/{server_name}/mcp/{method_name}",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Successfully invoked {method_name} on {server_name}")
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"❌ Failed to invoke {method_name} on {server_name}: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_filesystem_operations(self) -> Dict[str, Any]:
        """Test filesystem server operations"""
        results = {}
        
        # Test list files
        logger.info("Testing filesystem list_files...")
        list_result = await self.test_invoke_method(
            "filesystem", 
            "list_files", 
            {"path": "/projects"}
        )
        results["list_files"] = list_result
        
        # Test read file (if we have a known file)
        logger.info("Testing filesystem read_file...")
        read_result = await self.test_invoke_method(
            "filesystem",
            "read_file",
            {"path": "/projects/README.md"}
        )
        results["read_file"] = read_result
        
        return results
    
    async def test_github_operations(self) -> Dict[str, Any]:
        """Test GitHub server operations"""
        results = {}
        
        # Test list repositories
        logger.info("Testing GitHub list_repositories...")
        list_repos_result = await self.test_invoke_method(
            "github",
            "list_repositories",
            {"owner": "octocat"}
        )
        results["list_repositories"] = list_repos_result
        
        # Test get user info
        logger.info("Testing GitHub get_user...")
        user_result = await self.test_invoke_method(
            "github",
            "get_user",
            {"username": "octocat"}
        )
        results["get_user"] = user_result
        
        return results
    
    async def test_atlassian_operations(self) -> Dict[str, Any]:
        """Test Atlassian server operations"""
        results = {}
        
        # Test list projects
        logger.info("Testing Atlassian list_projects...")
        projects_result = await self.test_invoke_method(
            "atlassian",
            "list_projects",
            {}
        )
        results["list_projects"] = projects_result
        
        # Test get issue
        logger.info("Testing Atlassian get_issue...")
        issue_result = await self.test_invoke_method(
            "atlassian",
            "get_issue",
            {"issue_key": "NEX-123"}
        )
        results["get_issue"] = issue_result
        
        return results
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling scenarios"""
        results = {}
        
        # Test invalid server
        logger.info("Testing invalid server...")
        invalid_server_result = await self.test_invoke_method(
            "invalid_server",
            "some_method",
            {}
        )
        results["invalid_server"] = invalid_server_result
        
        # Test invalid method
        logger.info("Testing invalid method...")
        invalid_method_result = await self.test_invoke_method(
            "filesystem",
            "invalid_method",
            {}
        )
        results["invalid_method"] = invalid_method_result
        
        return results
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results"""
        logger.info("🚀 Starting MCP Client comprehensive tests...")
        
        all_results = {
            "timestamp": asyncio.get_event_loop().time(),
            "tests": {}
        }
        
        # Test 1: Proxy health
        logger.info("\n📊 Testing proxy health...")
        all_results["tests"]["proxy_health"] = await self.test_proxy_health()
        
        # Test 2: List servers
        logger.info("\n📋 Testing server listing...")
        all_results["tests"]["list_servers"] = await self.test_list_servers()
        
        # Test 3: Get methods from each server
        logger.info("\n🔧 Testing method discovery...")
        methods_results = {}
        for server in self.test_servers:
            methods_results[server.name] = await self.test_get_methods(server.name)
        all_results["tests"]["get_methods"] = methods_results
        
        # Test 4: Filesystem operations
        logger.info("\n📁 Testing filesystem operations...")
        all_results["tests"]["filesystem_operations"] = await self.test_filesystem_operations()
        
        # Test 5: GitHub operations
        logger.info("\n🐙 Testing GitHub operations...")
        all_results["tests"]["github_operations"] = await self.test_github_operations()
        
        # Test 6: Atlassian operations
        logger.info("\n🎫 Testing Atlassian operations...")
        all_results["tests"]["atlassian_operations"] = await self.test_atlassian_operations()
        
        # Test 7: Error handling
        logger.info("\n⚠️ Testing error handling...")
        all_results["tests"]["error_handling"] = await self.test_error_handling()
        
        # Calculate summary
        total_tests = 0
        successful_tests = 0
        
        def count_results(results):
            nonlocal total_tests, successful_tests
            if isinstance(results, dict):
                if "success" in results:
                    total_tests += 1
                    if results["success"]:
                        successful_tests += 1
                else:
                    for value in results.values():
                        count_results(value)
        
        count_results(all_results["tests"])
        
        all_results["summary"] = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": total_tests - successful_tests,
            "success_rate": round((successful_tests / total_tests) * 100, 2) if total_tests > 0 else 0
        }
        
        logger.info(f"\n✅ Test Summary: {successful_tests}/{total_tests} tests passed ({all_results['summary']['success_rate']}%)")
        
        return all_results
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

async def main():
    """Main function to run the MCP client tests"""
    tester = MCPClientTester()
    
    try:
        # Run comprehensive tests
        results = await tester.run_comprehensive_tests()
        
        # Save results to file
        with open("/home/lillian/Documents/projects/ai-protocol-mcp/docs/test_results.md", "w") as f:
            f.write("# MCP Client Test Results\n\n")
            f.write(f"**Test Date:** {asyncio.get_event_loop().time()}\n\n")
            f.write(f"**Summary:** {results['summary']['successful_tests']}/{results['summary']['total_tests']} tests passed ({results['summary']['success_rate']}%)\n\n")
            f.write("## Detailed Results\n\n")
            f.write("```json\n")
            f.write(json.dumps(results, indent=2))
            f.write("\n```\n")
        
        # Print summary
        print("\n" + "="*50)
        print("MCP CLIENT TEST SUMMARY")
        print("="*50)
        print(f"Total Tests: {results['summary']['total_tests']}")
        print(f"Successful: {results['summary']['successful_tests']}")
        print(f"Failed: {results['summary']['failed_tests']}")
        print(f"Success Rate: {results['summary']['success_rate']}%")
        print("="*50)
        
        # Show detailed results for failed tests
        if results['summary']['failed_tests'] > 0:
            print("\nFAILED TESTS:")
            def show_failures(results, path=""):
                if isinstance(results, dict):
                    if "success" in results and not results["success"]:
                        print(f"❌ {path}: {results.get('error', 'Unknown error')}")
                    else:
                        for key, value in results.items():
                            show_failures(value, f"{path}.{key}" if path else key)
            
            show_failures(results["tests"])
        
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())
