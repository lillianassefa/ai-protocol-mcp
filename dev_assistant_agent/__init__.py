"""
Dev Assistant Agent Package
RAG-enabled agent with MCP integration
"""

from .agent import DevAssistantAgent
from .rag_setup import RAGSetup, create_rag_system

__version__ = "1.0.0"
__all__ = ["DevAssistantAgent", "RAGSetup", "create_rag_system"]
