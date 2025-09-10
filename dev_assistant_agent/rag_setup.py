"""
RAG Setup for Dev Assistant Agent
Implements document indexing and querying using LlamaIndex
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from llama_index.core import (
        VectorStoreIndex, 
        SimpleDirectoryReader, 
        StorageContext,
        load_index_from_storage
    )
    from llama_index.core.query_engine import QueryEngine
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.core import Settings
except ImportError:
    # Fallback for different llama-index versions
    try:
        from llama_index import (
            VectorStoreIndex,
            SimpleDirectoryReader,
            StorageContext,
            load_index_from_storage
        )
        from llama_index.query_engine import QueryEngine
        from llama_index.embeddings import HuggingFaceEmbedding
        from llama_index import Settings
    except ImportError:
        print("Warning: llama-index not installed. RAG functionality will be limited.")
        VectorStoreIndex = None
        SimpleDirectoryReader = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGSetup:
    """RAG setup and management class"""
    
    def __init__(self, knowledge_base_path: str, persist_dir: str = "./storage"):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.persist_dir = Path(persist_dir)
        self.index: Optional[VectorStoreIndex] = None
        self.query_engine: Optional[QueryEngine] = None
        
        # Ensure directories exist
        self.persist_dir.mkdir(exist_ok=True)
        
        # Configure embeddings
        self._setup_embeddings()
    
    def _setup_embeddings(self):
        """Setup embedding model"""
        try:
            # Use a lightweight, fast embedding model
            embed_model = HuggingFaceEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            Settings.embed_model = embed_model
            logger.info("✅ Configured HuggingFace embeddings")
        except Exception as e:
            logger.warning(f"Failed to configure HuggingFace embeddings: {e}")
            logger.info("Using default OpenAI embeddings")
    
    def load_documents(self) -> List[Any]:
        """Load documents from the knowledge base directory"""
        if not SimpleDirectoryReader:
            raise ImportError("llama-index not properly installed")
        
        if not self.knowledge_base_path.exists():
            raise FileNotFoundError(f"Knowledge base path does not exist: {self.knowledge_base_path}")
        
        logger.info(f"Loading documents from {self.knowledge_base_path}")
        
        # Load all documents recursively
        reader = SimpleDirectoryReader(
            input_dir=str(self.knowledge_base_path),
            recursive=True,
            exclude_hidden=True,
            file_extractor={
                ".md": "MarkdownReader",
                ".txt": "SimpleReader", 
                ".py": "SimpleReader",
                ".js": "SimpleReader",
                ".json": "JSONReader"
            }
        )
        
        documents = reader.load_data()
        logger.info(f"✅ Loaded {len(documents)} documents")
        
        return documents
    
    def create_index(self, documents: List[Any]) -> VectorStoreIndex:
        """Create vector index from documents"""
        if not VectorStoreIndex:
            raise ImportError("llama-index not properly installed")
        
        logger.info("Creating vector index...")
        
        # Create index
        index = VectorStoreIndex.from_documents(documents)
        
        # Persist index
        index.storage_context.persist(persist_dir=str(self.persist_dir))
        logger.info(f"✅ Index created and persisted to {self.persist_dir}")
        
        return index
    
    def load_existing_index(self) -> Optional[VectorStoreIndex]:
        """Load existing index from storage"""
        if not load_index_from_storage:
            return None
        
        try:
            storage_context = StorageContext.from_defaults(persist_dir=str(self.persist_dir))
            index = load_index_from_storage(storage_context)
            logger.info("✅ Loaded existing index from storage")
            return index
        except Exception as e:
            logger.info(f"No existing index found: {e}")
            return None
    
    def setup_rag(self, force_rebuild: bool = False) -> QueryEngine:
        """Setup complete RAG pipeline"""
        logger.info("🔧 Setting up RAG pipeline...")
        
        # Try to load existing index first
        if not force_rebuild:
            self.index = self.load_existing_index()
        
        # Create new index if needed
        if self.index is None:
            documents = self.load_documents()
            if not documents:
                raise ValueError("No documents loaded from knowledge base")
            
            self.index = self.create_index(documents)
        
        # Create query engine
        self.query_engine = self.index.as_query_engine(
            similarity_top_k=5,
            response_mode="compact"
        )
        
        logger.info("✅ RAG pipeline setup complete")
        return self.query_engine
    
    def query(self, question: str) -> Dict[str, Any]:
        """Query the RAG system"""
        if not self.query_engine:
            raise ValueError("RAG system not initialized. Call setup_rag() first.")
        
        logger.info(f"🔍 Querying RAG: {question}")
        
        try:
            response = self.query_engine.query(question)
            
            result = {
                "success": True,
                "question": question,
                "answer": str(response),
                "source_nodes": []
            }
            
            # Extract source information if available
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    source_info = {
                        "score": getattr(node, 'score', 0.0),
                        "text": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                        "metadata": getattr(node, 'metadata', {})
                    }
                    result["source_nodes"].append(source_info)
            
            logger.info("✅ RAG query successful")
            return result
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {
                "success": False,
                "question": question,
                "error": str(e)
            }
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the index"""
        if not self.index:
            return {"error": "Index not initialized"}
        
        try:
            # Get basic stats
            stats = {
                "index_type": type(self.index).__name__,
                "storage_dir": str(self.persist_dir),
                "knowledge_base_path": str(self.knowledge_base_path)
            }
            
            # Try to get document count
            if hasattr(self.index, 'docstore'):
                stats["document_count"] = len(self.index.docstore.docs)
            
            return stats
            
        except Exception as e:
            return {"error": f"Failed to get stats: {e}"}

def create_rag_system(knowledge_base_path: str, force_rebuild: bool = False) -> RAGSetup:
    """Factory function to create and setup RAG system"""
    rag_setup = RAGSetup(knowledge_base_path)
    rag_setup.setup_rag(force_rebuild=force_rebuild)
    return rag_setup

# Example usage and testing
if __name__ == "__main__":
    # Test the RAG setup
    knowledge_base = "/home/lillian/Documents/projects/ai-protocol-mcp/mock_knowledge_base"
    
    try:
        rag = create_rag_system(knowledge_base)
        
        # Test queries
        test_queries = [
            "What is NEX-123 about?",
            "Tell me about login button issues",
            "What MCP servers are mentioned in the documentation?",
            "Explain the commit_abc123 changes"
        ]
        
        print("🔍 Testing RAG System")
        print("="*50)
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            result = rag.query(query)
            
            if result["success"]:
                print(f"Answer: {result['answer']}")
                if result["source_nodes"]:
                    print(f"Sources: {len(result['source_nodes'])} documents")
            else:
                print(f"Error: {result['error']}")
        
        # Print stats
        print("\n📊 Index Statistics:")
        stats = rag.get_index_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
            
    except Exception as e:
        print(f"❌ RAG setup failed: {e}")
        print("Make sure llama-index is installed: pip install llama-index")
