"""
Run script for Dev Assistant Agent
Provides CLI interface for interacting with the agent
"""

import asyncio
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from dev_assistant_agent.agent import DevAssistantAgent

class AgentCLI:
    """Command Line Interface for the Dev Assistant Agent"""
    
    def __init__(self):
        self.agent = None
        self.running = True
    
    async def start(self):
        """Start the agent CLI"""
        print("🚀 Starting Dev Assistant Agent CLI")
        print("="*50)
        
        # Initialize agent
        try:
            self.agent = DevAssistantAgent()
            print("✅ Agent initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize agent: {e}")
            return
        
        # Health check
        print("\n🏥 Performing health check...")
        health = await self.agent.health_check()
        print(f"Agent Status: {health['agent_status']}")
        
        for component, info in health['components'].items():
            status_emoji = "✅" if info['status'] == 'healthy' else "❌"
            print(f"{status_emoji} {component}: {info['status']}")
        
        # Start interactive loop
        await self.interactive_loop()
    
    async def interactive_loop(self):
        """Main interactive loop"""
        print("\n💬 Interactive Mode Started")
        print("Type 'help' for commands, 'quit' to exit")
        print("-" * 50)
        
        while self.running:
            try:
                # Get user input
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                elif user_input.lower() == 'help':
                    self.show_help()
                elif user_input.lower() == 'health':
                    await self.show_health()
                elif user_input.lower() == 'examples':
                    self.show_examples()
                elif user_input.lower() == 'clear':
                    print("\033[2J\033[H")  # Clear screen
                else:
                    # Process as agent query
                    await self.process_query(user_input)
            
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except EOFError:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    async def process_query(self, query: str):
        """Process user query through the agent"""
        print("🤖 Processing...")
        
        try:
            response = await self.agent.process_message(query)
            
            print(f"\n🤖 Agent: {response['synthesized_answer']}")
            
            # Show sources if available
            if response.get('sources'):
                print(f"\n📚 Sources: {', '.join(response['sources'])}")
            
            # Show debug info if verbose
            if '--debug' in sys.argv:
                print(f"\n🔧 Debug Info:")
                print(f"MCP Success: {response.get('mcp_result', {}).get('success', 'N/A')}")
                print(f"RAG Success: {response.get('rag_result', {}).get('success', 'N/A')}")
        
        except Exception as e:
            print(f"❌ Failed to process query: {e}")
    
    def show_help(self):
        """Show help information"""
        help_text = """
🆘 Available Commands:
- help          Show this help message
- health        Show agent health status
- examples      Show example queries
- clear         Clear the screen
- quit/exit/q   Exit the program

📝 Example Queries:
- "Tell me about GitHub issue #123"
- "What is NEX-123 about?"
- "List files in /projects"
- "Read file /projects/README.md" 
- "Tell me about login button issues"
- "What MCP servers are available?"

💡 Tips:
- The agent combines information from MCP servers and local knowledge base
- Use specific references (like NEX-123) for better results
- File paths should be absolute or relative to the filesystem server root
        """
        print(help_text)
    
    async def show_health(self):
        """Show detailed health information"""
        print("🏥 Checking agent health...")
        
        try:
            health = await self.agent.health_check()
            print(f"\n📊 Agent Status: {health['agent_status']}")
            
            print("\n🔧 Component Details:")
            for component, info in health['components'].items():
                status_emoji = "✅" if info['status'] == 'healthy' else "❌"
                print(f"\n{status_emoji} {component.upper()}:")
                print(f"   Status: {info['status']}")
                
                if 'error' in info:
                    print(f"   Error: {info['error']}")
                
                if 'stats' in info:
                    for key, value in info['stats'].items():
                        print(f"   {key}: {value}")
        
        except Exception as e:
            print(f"❌ Health check failed: {e}")
    
    def show_examples(self):
        """Show example queries with explanations"""
        examples = [
            {
                "query": "Tell me about GitHub issue #123",
                "explanation": "Queries GitHub MCP server for issue information"
            },
            {
                "query": "What is NEX-123 about?", 
                "explanation": "Searches knowledge base for JIRA ticket information"
            },
            {
                "query": "List files in /projects",
                "explanation": "Uses filesystem MCP server to list directory contents"
            },
            {
                "query": "Tell me about login button issues",
                "explanation": "Searches knowledge base for relevant documentation"
            },
            {
                "query": "Read file /projects/README.md",
                "explanation": "Uses filesystem MCP server to read file contents"
            }
        ]
        
        print("\n📚 Example Queries:")
        print("=" * 50)
        
        for i, example in enumerate(examples, 1):
            print(f"\n{i}. {example['query']}")
            print(f"   💡 {example['explanation']}")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.agent:
            await self.agent.close()
        print("🧹 Cleanup complete")

async def main():
    """Main function"""
    cli = AgentCLI()
    
    try:
        await cli.start()
    except Exception as e:
        print(f"❌ CLI failed: {e}")
    finally:
        await cli.cleanup()

if __name__ == "__main__":
    # Check for help flag
    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
Dev Assistant Agent CLI

Usage: python run.py [options]

Options:
  --debug    Show debug information
  --help     Show this help message

The agent combines MCP server calls with RAG-based knowledge retrieval
to answer questions about your development environment.
        """)
        sys.exit(0)
    
    # Run the CLI
    asyncio.run(main())
