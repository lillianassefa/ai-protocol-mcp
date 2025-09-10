"""
Simple FastAPI App for LLM Orchestrator
Uses existing proxy server - much simpler!
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio
import logging
from contextlib import asynccontextmanager

# Import our simple orchestrator
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

# Pydantic models
class UserRequest(BaseModel):
    request: str

class ExecutionResult(BaseModel):
    success: bool
    server: Optional[str] = None
    tool: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None

# Global orchestrator client
orchestrator_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup the orchestrator client"""
    global orchestrator_client
    
    # Startup
    print("🧠 Starting Simple LLM Orchestrator FastAPI Server...")
    transport = StdioTransport("python", ["simple_llm_proxy.py"])
    orchestrator_client = Client(transport)
    
    try:
        # Test connection
        async with orchestrator_client:
            await orchestrator_client.ping()
            print("✅ Simple orchestrator connected successfully")
    except Exception as e:
        print(f"❌ Failed to connect to orchestrator: {e}")
        raise
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Simple LLM Orchestrator FastAPI Server...")
    orchestrator_client = None

# Create FastAPI app
app = FastAPI(
    title="Simple LLM Orchestrator API",
    description="Simple API for LLM-driven MCP tool orchestration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Main endpoint - Process user request with LLM
@app.post("/process", response_model=ExecutionResult)
async def process_user_request(request: UserRequest):
    """Process user request using LLM orchestration"""
    try:
        async with orchestrator_client:
            result = await orchestrator_client.call_tool("process_request", {"user_request": request.request})
            
            if "error" in result:
                return ExecutionResult(
                    success=False,
                    error=result["error"]
                )
            else:
                final_result = result.get("final_result", {})
                return ExecutionResult(
                    success=final_result.get("success", False),
                    server=final_result.get("server"),
                    tool=final_result.get("tool"),
                    result=final_result.get("result")
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/health")
async def health_check():
    """Check orchestrator health"""
    try:
        async with orchestrator_client:
            health = await orchestrator_client.call_tool("health_check")
            return {
                "api_status": "healthy",
                "orchestrator_health": health
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Orchestrator unavailable: {str(e)}")

# Discover servers
@app.get("/servers/discover")
async def discover_servers():
    """Discover all available servers"""
    try:
        async with orchestrator_client:
            result = await orchestrator_client.call_tool("discover_servers")
            return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get all tools
@app.get("/tools/all")
async def get_all_tools():
    """Get all tools from all servers"""
    try:
        async with orchestrator_client:
            result = await orchestrator_client.call_tool("get_all_tools")
            return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Simple HTML UI
@app.get("/", response_class=HTMLResponse)
async def get_ui():
    """Serve the simple UI"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple LLM Orchestrator</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .loading {
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <div id="app" class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold text-gray-800 mb-2">
                <i class="fas fa-brain text-purple-600"></i>
                Simple LLM Orchestrator
            </h1>
            <p class="text-gray-600 text-lg">AI-Powered MCP Tool Management (Simplified)</p>
        </div>

        <!-- Main Content -->
        <div class="max-w-4xl mx-auto">
            <!-- Request Panel -->
            <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
                <h2 class="text-2xl font-semibold text-gray-800 mb-4">
                    <i class="fas fa-comment-dots text-blue-600"></i>
                    Make a Request
                </h2>
                
                <div class="mb-4">
                    <label class="block text-sm font-medium text-gray-700 mb-2">Your Request:</label>
                    <textarea 
                        v-model="userRequest" 
                        placeholder="Describe what you want to do... (e.g., 'Create a GitHub issue about a bug', 'List files in my project', 'Read a specific file')"
                        class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        rows="4"
                    ></textarea>
                </div>
                
                <button 
                    @click="processRequest"
                    :disabled="isProcessing || !userRequest.trim()"
                    class="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                >
                    <i v-if="isProcessing" class="fas fa-spinner loading mr-2"></i>
                    <i v-else class="fas fa-magic mr-2"></i>
                    [[ isProcessing ? 'Processing...' : 'Process with AI' ]]
                </button>
            </div>

            <!-- Results Panel -->
            <div v-if="result" class="bg-white rounded-lg shadow-lg p-6">
                <h3 class="text-xl font-semibold text-gray-800 mb-4">
                    <i class="fas fa-chart-line text-green-600"></i>
                    Results
                </h3>
                
                <div v-if="result.success" class="space-y-4">
                    <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                        <div class="flex items-center">
                            <i class="fas fa-check-circle text-green-600 mr-2"></i>
                            <span class="font-semibold text-green-800">Success!</span>
                        </div>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                            <h4 class="font-semibold text-blue-800 mb-2">Server Used</h4>
                            <p class="text-blue-700">[[ result.server ]]</p>
                        </div>
                        <div class="bg-purple-50 border border-purple-200 rounded-lg p-4">
                            <h4 class="font-semibold text-purple-800 mb-2">Tool Used</h4>
                            <p class="text-purple-700">[[ result.tool ]]</p>
                        </div>
                    </div>
                    
                    <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
                        <h4 class="font-semibold text-gray-800 mb-2">Result</h4>
                        <pre class="text-sm text-gray-700 whitespace-pre-wrap">[[ JSON.stringify(result.result, null, 2) ]]</pre>
                    </div>
                </div>
                
                <div v-else class="bg-red-50 border border-red-200 rounded-lg p-4">
                    <div class="flex items-center">
                        <i class="fas fa-exclamation-circle text-red-600 mr-2"></i>
                        <span class="font-semibold text-red-800">Error</span>
                    </div>
                    <p class="text-red-700 mt-2">[[ result.error ]]</p>
                </div>
            </div>

            <!-- Quick Actions -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                <button @click="discoverServers" class="bg-blue-100 text-blue-700 py-3 px-4 rounded-lg hover:bg-blue-200 transition-colors">
                    <i class="fas fa-search mr-2"></i>
                    Discover Servers
                </button>
                
                <button @click="getAllTools" class="bg-green-100 text-green-700 py-3 px-4 rounded-lg hover:bg-green-200 transition-colors">
                    <i class="fas fa-tools mr-2"></i>
                    Get All Tools
                </button>
                
                <button @click="checkHealth" class="bg-red-100 text-red-700 py-3 px-4 rounded-lg hover:bg-red-200 transition-colors">
                    <i class="fas fa-heartbeat mr-2"></i>
                    Health Check
                </button>
            </div>
        </div>

        <!-- Footer -->
        <div class="text-center mt-12 text-gray-500">
            <p>Powered by FastMCP, OpenAI, and existing proxy server</p>
        </div>
    </div>

    <script>
        const { createApp } = Vue

        createApp({
            delimiters: ['[[', ']]'],
            data() {
                return {
                    userRequest: '',
                    isProcessing: false,
                    result: null
                }
            },
            methods: {
                async processRequest() {
                    if (!this.userRequest.trim()) return
                    
                    this.isProcessing = true
                    this.result = null
                    
                    try {
                        const response = await fetch('/process', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                request: this.userRequest
                            })
                        })
                        
                        const data = await response.json()
                        this.result = data
                    } catch (error) {
                        this.result = {
                            success: false,
                            error: 'Failed to process request: ' + error.message
                        }
                    } finally {
                        this.isProcessing = false
                    }
                },
                
                async checkHealth() {
                    try {
                        const response = await fetch('/health')
                        const data = await response.json()
                        console.log('Health:', data)
                        alert('Health check completed! Check console for details.')
                    } catch (error) {
                        console.error('Health check failed:', error)
                    }
                },
                
                async discoverServers() {
                    try {
                        const response = await fetch('/servers/discover')
                        const data = await response.json()
                        console.log('Discovered servers:', data)
                        alert('Servers discovered! Check console for details.')
                    } catch (error) {
                        console.error('Server discovery failed:', error)
                    }
                },
                
                async getAllTools() {
                    try {
                        const response = await fetch('/tools/all')
                        const data = await response.json()
                        console.log('All tools:', data)
                        alert('Tools retrieved! Check console for details.')
                    } catch (error) {
                        console.error('Tool retrieval failed:', error)
                    }
                }
            }
        }).mount('#app')
    </script>
</body>
</html>
    """

if __name__ == "__main__":
    import uvicorn
    
    print("🧠 Starting Simple LLM Orchestrator FastAPI Server...")
    print("🌐 Web UI: http://localhost:8007")
    print("📖 API Documentation: http://localhost:8003/docs")
    print("\n📋 Features:")
    print("- Simple web interface")
    print("- Uses existing proxy server")
    print("- LLM-powered tool selection")
    print("- No complex rewrites!")
    
    uvicorn.run(
        "simple_llm_fastapi:app",
        host="0.0.0.0",
        port=8007,
        reload=True,
        log_level="info"
    ) 