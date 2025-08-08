from fastmcp import FastMCP
import asyncio
import subprocess
import json
import logging
from typing import Dict, Any, Optional

from fastmcp.client.transports import StdioTransport

import asyncio
from fastmcp import Client, FastMCP

configs = [
    {
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
            "GITHUB_PERSONAL_ACCESS_TOKEN": "${input:github_token}"
        },
    },
     {  "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--mount", "type=bind,src=/home/lillian/,dst=/projects",
        "mcp/filesystem",
        "/projects"
      ]
    },
    {
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
    }
]

for config in configs:
    command = config["command"]
    args = config["args"]
    transport=StdioTransport(command, args)
    print("Created transport for", command)
    client = Client(transport)
    server = FastMCP("Custom Server")

async def main():
    async with client:
        result = await client.ping()    
     
        print(result)