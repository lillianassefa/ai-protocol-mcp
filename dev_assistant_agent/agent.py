"""
Dev Assistant Agent with MCP Integration and RAG
Combines MCP proxy calls with RAG-based knowledge retrieval
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, Optional, List
import httpx
from dataclasses import dataclass
from .rag_setup import RAGSetup, create_rag_system

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MCPRequest:
    """MCP request structure"""
    server: str
    method: str
    params: Dict[str, Any]

class DevAssistantAgent:
    """Development Assistant Agent with MCP and RAG capabilities"""
    
    def __init__(self, 
                 proxy_url: str = "http://localhost:8000",
                 knowledge_base_path: str = "/home/lillian/Documents/projects/ai-protocol-mcp/mock_knowledge_base"):
        self.proxy_url = proxy_url
        self.knowledge_base_path = knowledge_base_path
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.rag_system: Optional[RAGSetup] = None
        
        # Initialize RAG system
        self._initialize_rag()
    
    def _initialize_rag(self):
        """Initialize the RAG system"""
        try:
            logger.info("🔧 Initializing RAG system...")
            self.rag_system = create_rag_system(self.knowledge_base_path)
            logger.info("✅ RAG system initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG system: {e}")
            self.rag_system = None
    
    def parse_user_query(self, query: str) -> Dict[str, Any]:
        """Parse user query to identify intent and extract parameters"""
        query_lower = query.lower()
        
        # Patterns for different types of requests
        patterns = {
            "github_issue": r"github.*issue.*#?(\d+)",
            "github_repo": r"github.*repo(?:sitory)?.*?([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)",
            "github_user": r"github.*user.*?([a-zA-Z0-9_-]+)",
            "file_list": r"list.*files?.*?(?:in|from)?\s*([^\s]+)",
            "file_read": r"read.*file.*?([^\s]+)",
            "jira_ticket": r"(?:jira|ticket).*?(NEX-\d+)",
            "general_info": r"(?:what|tell me|explain|describe).*?(.+)"
        }
        
        parsed = {
            "original_query": query,
            "intent": "general_info",
            "mcp_request": None,
            "rag_query": query,
            "parameters": {}
        }
        
        # Check each pattern
        for intent, pattern in patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                parsed["intent"] = intent
                parsed["parameters"]["match"] = match.group(1) if match.groups() else None
                break
        
        # Generate MCP request based on intent
        parsed["mcp_request"] = self._generate_mcp_request(parsed["intent"], parsed["parameters"])
        
        return parsed
    
    def _generate_mcp_request(self, intent: str, parameters: Dict[str, Any]) -> Optional[MCPRequest]:
        """Generate MCP request based on intent and parameters"""
        match_value = parameters.get("match")
        
        if intent == "github_issue" and match_value:
            return MCPRequest(
                server="github",
                method="get_issue",
                params={"issue_number": match_value}
            )
        
        elif intent == "github_repo" and match_value:
            owner, repo = match_value.split("/") if "/" in match_value else ("", match_value)
            return MCPRequest(
                server="github", 
                method="get_repository",
                params={"owner": owner, "repo": repo}
            )
        
        elif intent == "github_user" and match_value:
            return MCPRequest(
                server="github",
                method="get_user",
                params={"username": match_value}
            )
        
        elif intent == "file_list" and match_value:
            return MCPRequest(
                server="filesystem",
                method="list_files", 
                params={"path": match_value}
            )
        
        elif intent == "file_read" and match_value:
            return MCPRequest(
                server="filesystem",
                method="read_file",
                params={"path": match_value}
            )
        
        elif intent == "jira_ticket" and match_value:
            return MCPRequest(
                server="atlassian",
                method="get_issue",
                params={"issue_key": match_value}
            )
        
        return None
    
    async def call_mcp_via_proxy(self, mcp_request: MCPRequest) -> Dict[str, Any]:
        """Call MCP server via proxy"""
        try:
            url = f"{self.proxy_url}/proxy/{mcp_request.server}/mcp/{mcp_request.method}"
            
            logger.info(f"🔗 Calling MCP: {mcp_request.server}/{mcp_request.method}")
            
            response = await self.http_client.post(url, json=mcp_request.params)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ MCP call successful")
            
            return {
                "success": True,
                "server": mcp_request.server,
                "method": mcp_request.method,
                "data": result
            }
            
        except Exception as e:
            logger.error(f"❌ MCP call failed: {e}")
            return {
                "success": False,
                "server": mcp_request.server,
                "method": mcp_request.method,
                "error": str(e)
            }
    
    def query_rag_system(self, query: str) -> Dict[str, Any]:
        """Query the RAG system for relevant information"""
        if not self.rag_system:
            return {
                "success": False,
                "error": "RAG system not initialized"
            }
        
        try:
            logger.info(f"🔍 Querying RAG system: {query}")
            result = self.rag_system.query(query)
            logger.info("✅ RAG query successful")
            return result
        except Exception as e:
            logger.error(f"❌ RAG query failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def synthesize_response(self, user_query: str, mcp_result: Dict[str, Any], rag_result: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize final response from MCP and RAG results"""
        response = {
            "user_query": user_query,
            "mcp_result": mcp_result,
            "rag_result": rag_result,
            "synthesized_answer": "",
            "sources": []
        }
        
        # Build synthesized answer
        answer_parts = []
        
        # Add MCP information if available
        if mcp_result.get("success"):
            mcp_data = mcp_result.get("data", {})
            answer_parts.append(f"From {mcp_result['server']} server:")
            answer_parts.append(json.dumps(mcp_data, indent=2))
            response["sources"].append(f"MCP {mcp_result['server']} server")
        
        # Add RAG information if available
        if rag_result.get("success"):
            answer_parts.append("\nFrom knowledge base:")
            answer_parts.append(rag_result["answer"])
            
            # Add source documents
            for source in rag_result.get("source_nodes", []):
                source_info = source.get("metadata", {}).get("file_name", "Unknown document")
                if source_info not in response["sources"]:
                    response["sources"].append(source_info)
        
        # Handle cases where both failed
        if not mcp_result.get("success") and not rag_result.get("success"):
            answer_parts.append("I couldn't find information from either external tools or the knowledge base.")
            if mcp_result.get("error"):
                answer_parts.append(f"MCP Error: {mcp_result['error']}")
            if rag_result.get("error"):
                answer_parts.append(f"RAG Error: {rag_result['error']}")
        
        response["synthesized_answer"] = "\n".join(answer_parts)
        return response
    
    async def process_message(self, user_query: str) -> Dict[str, Any]:
        """Main message processing workflow"""
        logger.info(f"🎯 Processing user query: {user_query}")
        
        try:
            # Step 1: Parse the user query
            parsed = self.parse_user_query(user_query)
            logger.info(f"📝 Parsed intent: {parsed['intent']}")
            
            # Step 2: Execute MCP call if needed
            mcp_result = {"success": False, "message": "No MCP call needed"}
            if parsed["mcp_request"]:
                mcp_result = await self.call_mcp_via_proxy(parsed["mcp_request"])
            
            # Step 3: Query RAG system
            rag_result = self.query_rag_system(parsed["rag_query"])
            
            # Step 4: Synthesize response
            final_response = self.synthesize_response(user_query, mcp_result, rag_result)
            
            logger.info("✅ Message processing complete")
            return final_response
            
        except Exception as e:
            logger.error(f"❌ Message processing failed: {e}")
            return {
                "user_query": user_query,
                "error": str(e),
                "synthesized_answer": f"I encountered an error processing your request: {str(e)}"
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all components"""
        health = {
            "agent_status": "healthy",
            "components": {}
        }
        
        # Check MCP proxy
        try:
            response = await self.http_client.get(f"{self.proxy_url}/health")
            health["components"]["mcp_proxy"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "details": response.json() if response.status_code == 200 else f"Status: {response.status_code}"
            }
        except Exception as e:
            health["components"]["mcp_proxy"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check RAG system
        if self.rag_system:
            try:
                stats = self.rag_system.get_index_stats()
                health["components"]["rag_system"] = {
                    "status": "healthy",
                    "stats": stats
                }
            except Exception as e:
                health["components"]["rag_system"] = {
                    "status": "unhealthy", 
                    "error": str(e)
                }
        else:
            health["components"]["rag_system"] = {
                "status": "unhealthy",
                "error": "RAG system not initialized"
            }
        
        # Overall health
        unhealthy_components = [name for name, info in health["components"].items() 
                             if info["status"] != "healthy"]
        
        if unhealthy_components:
            health["agent_status"] = "degraded"
            health["unhealthy_components"] = unhealthy_components
        
        return health
    
    async def close(self):
        """Clean up resources"""
        await self.http_client.aclose()

# Example usage and testing
async def main():
    """Test the Dev Assistant Agent"""
    agent = DevAssistantAgent()
    
    # Test queries
    test_queries = [
        "Tell me about GitHub issue #123",
        "What is NEX-123 about?", 
        "List files in /projects",
        "Read file /projects/README.md",
        "Tell me about login button issues",
        "What MCP servers are available?"
    ]
    
    try:
        # Health check first
        print("🏥 Agent Health Check")
        print("="*50)
        health = await agent.health_check()
        print(json.dumps(health, indent=2))
        
        # Test queries
        print("\n🤖 Testing Agent Queries")
        print("="*50)
        
        for query in test_queries:
            print(f"\n👤 User: {query}")
            response = await agent.process_message(query)
            print(f"🤖 Agent: {response['synthesized_answer']}")
            
            if response.get("sources"):
                print(f"📚 Sources: {', '.join(response['sources'])}")
    
    except KeyboardInterrupt:
        print("\nAgent testing interrupted by user")
    except Exception as e:
        print(f"Agent testing failed: {e}")
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
