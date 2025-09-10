"""
Configuration for MCP Proxy Server
Maps routing keys to downstream MCP server configurations
"""

from typing import Dict, Any

# Mapping from routing key to downstream MCP server configuration
MCP_SERVER_CONFIGS = {
    "github": {
        "command": "docker",
        "args": [
            "run",
            "-i",
            "--rm",
            "-e",
            "GITHUB_PERSONAL_ACCESS_TOKEN",
            "ghcr.io/github/github-mcp-server"
        ],
        "env": {
            "GITHUB_PERSONAL_ACCESS_TOKEN": "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"
        },
        "transport": "stdio"
    },
    "filesystem": {
        "command": "docker",
        "args": [
            "run",
            "-i",
            "--rm",
            "--mount", "type=bind,src=/home/lillian/,dst=/projects",
            "mcp/filesystem",
            "/projects"
        ],
        "env": {},
        "transport": "stdio"
    },
    "atlassian": {
        "command": "docker",
        "args": [
            "run",
            "-i",
            "--rm",
            "-e", "CONFLUENCE_URL",
            "-e", "CONFLUENCE_USERNAME",
            "-e", "CONFLUENCE_API_TOKEN", 
            "-e", "JIRA_URL",
            "-e", "JIRA_USERNAME",
            "-e", "JIRA_API_TOKEN",
            "ghcr.io/sooperset/mcp-atlassian:latest"
        ],
        "env": {
            "CONFLUENCE_URL": "your_confluence_url_here",
            "CONFLUENCE_USERNAME": "your_confluence_username_here",
            "CONFLUENCE_API_TOKEN": "your_confluence_token_here",
            "JIRA_URL": "your_jira_url_here",
            "JIRA_USERNAME": "your_jira_username_here", 
            "JIRA_API_TOKEN": "your_jira_token_here"
        },
        "transport": "stdio"
    }
}

PROXY_CONFIG = {
    "name": "Unified MCP Proxy Server",
    "routing_strategy": "prefix", 
    "default_server": "filesystem", 
    "enable_logging": True,
    "log_level": "INFO"
}

ROUTING_CONFIG = {
    "prefix_delimiter": "_", 
    "header_name": "X-Target-MCP",  
    "path_prefix": "/mcp",  
} 