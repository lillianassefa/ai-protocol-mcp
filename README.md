# AI Protocol MCP Implementation

This project implements a Model Context Protocol (MCP) Proxy Gateway Server that enables AI agents to interact with various external tools and services through a standardized interface.

## Project Overview

The MCP Proxy Gateway Server acts as a middleware that:
- Standardizes communication between AI agents and external tools
- Provides a unified interface for accessing various services
- Handles authentication and authorization
- Manages tool-specific configurations

## Features

- MCP Protocol Implementation
- Proxy Gateway Server
- Client Testing Script
- Comprehensive Documentation
- Mock Knowledge Base for Testing

## Prerequisites

- Python 3.8+
- pip (Python package manager)
- Git

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-protocol-mcp.git
cd ai-protocol-mcp
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Starting the MCP Proxy Server

```bash
python src/mcp_proxy_server.py
```

The server will start on `http://localhost:8000` by default.

### Running the Client Tester

```bash
python src/mcp_client_tester.py
```

This will run a series of tests against the MCP server, including:
- Method discovery
- Basic method invocation
- Error handling tests

## Project Structure

```
ai-protocol-mcp/
├── src/
│   ├── mcp_proxy_server.py    # Main MCP server implementation
│   └── mcp_client_tester.py   # Client testing script
├── docs/
│   ├── protocols_understanding.md    # Protocol documentation
│   └── mcp_server_exploration.md     # Server exploration findings
├── tests/
│   └── test_mcp_server.py     # Unit tests
├── mock_knowledge_base/       # Mock data for testing
└── requirements.txt          # Project dependencies
```

## Testing

Run the test suite:
```bash
python -m pytest tests/
```

### Test Results

![MCP Server Test Results]
![Screenshot from 2025-05-29 00-01-48](https://github.com/user-attachments/assets/70125c14-4389-403e-91d8-9da3aa54ff51)


**Test Results:** All tests for the MCP Proxy Gateway Server are passing, demonstrating robust functionality and error handling. Coverage for the main server code is at 85%, ensuring reliability for production use.

## Documentation

- [Protocol Understanding](docs/protocols_understanding.md)
- [Server Exploration](docs/mcp_server_exploration.md)


## License

This project is licensed under the MIT License - see the LICENSE file for details.
