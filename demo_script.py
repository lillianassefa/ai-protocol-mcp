#!/usr/bin/env python3
"""
Demo script to showcase the MCP implementation
Run this to test all components quickly
"""

import asyncio
import subprocess
import time
import requests
import json

def print_banner(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def test_proxy_server():
    print_banner("TESTING MCP PROXY SERVER")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8000/health", timeout=5)
        print("✅ Health Check:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"❌ Proxy server not running: {e}")
        print("Start it with: python mcp_proxy_server/proxy_server.py")
        return False
    
    try:
        # Test server listing
        response = requests.get("http://localhost:8000/proxy/servers", timeout=5)
        print("\n✅ Server Listing:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"❌ Server listing failed: {e}")
    
    return True

def test_rag_system():
    print_banner("TESTING RAG SYSTEM")
    
    try:
        from dev_assistant_agent.rag_setup import create_rag_system
        
        print("🔧 Setting up RAG system...")
        rag = create_rag_system("/home/lillian/Documents/projects/ai-protocol-mcp/mock_knowledge_base")
        
        print("✅ RAG system initialized")
        
        # Test queries
        test_queries = [
            "What is NEX-123 about?",
            "Tell me about login button issues",
            "What MCP servers are mentioned?"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: {query}")
            result = rag.query(query)
            if result["success"]:
                print(f"✅ Answer: {result['answer'][:200]}...")
            else:
                print(f"❌ Error: {result['error']}")
                
    except Exception as e:
        print(f"❌ RAG system test failed: {e}")

def show_file_structure():
    print_banner("PROJECT STRUCTURE")
    
    structure = """
ai-protocol-mcp/
├── mcp_proxy_server/           # MCP Proxy Gateway
│   ├── proxy_server.py         # Main proxy implementation  
│   ├── config.py               # Server configuration
│   ├── fastapi_app.py          # Web interface
│   └── simple_web_app.html     # Dashboard UI
├── dev_assistant_agent/        # RAG-enabled Agent
│   ├── agent.py                # Main agent logic
│   ├── rag_setup.py            # RAG system setup
│   └── run.py                  # CLI interface
├── tests/                      # Comprehensive test suite
│   ├── test_proxy_server.py    # Proxy server tests
│   └── test_agent.py           # Agent tests
├── docs/                       # Documentation
│   ├── protocols_understanding.md      # MCP/A2A concepts
│   ├── realtime_rag_notes.md          # Real-time RAG concepts
│   ├── advanced_mcp_concepts.md       # Enterprise patterns
│   └── ide_mcp_integration.md         # IDE setup guide
├── mock_knowledge_base/        # RAG knowledge base
└── mcp_client_tester.py        # Comprehensive client tester
    """
    print(structure)

def main():
    print_banner("MCP IMPLEMENTATION DEMO")
    print("This script demonstrates the key components of the MCP implementation")
    
    # Show project structure
    show_file_structure()
    
    # Test proxy server
    proxy_running = test_proxy_server()
    
    # Test RAG system
    test_rag_system()
    
    print_banner("DEMO COMPLETE")
    
    if proxy_running:
        print("🌐 Web Interface: http://localhost:8000")
        print("📚 API Docs: http://localhost:8000/docs")
        print("🏥 Health Check: http://localhost:8000/health")
    
    print("\n🚀 To run components manually:")
    print("1. Proxy Server: python mcp_proxy_server/proxy_server.py")
    print("2. Agent CLI: python dev_assistant_agent/run.py")
    print("3. Client Tester: python mcp_client_tester.py")
    print("4. Run Tests: python -m pytest tests/ -v")

if __name__ == "__main__":
    main()
