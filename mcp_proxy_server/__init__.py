"""
MCP Proxy Server Package

A unified proxy server for routing MCP requests to multiple downstream servers.
"""

__version__ = "1.0.0"
__author__ = "MCP Proxy Team"

from .proxy_server import proxy_server, router, client_manager
from .config import MCP_SERVER_CONFIGS, PROXY_CONFIG, ROUTING_CONFIG

__all__ = [
    "proxy_server",
    "router", 
    "client_manager",
    "MCP_SERVER_CONFIGS",
    "PROXY_CONFIG",
    "ROUTING_CONFIG"
] 