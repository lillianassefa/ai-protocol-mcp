import os
import json

base = "mock_knowledge_base"
os.makedirs(base, exist_ok=True)

# Subdirectories
subdirs = ["code", "docs", "tickets"]
for sub in subdirs:
    os.makedirs(os.path.join(base, sub), exist_ok=True)

# ----------------------------
# JIRA Tickets JSON
# ----------------------------
jira_tickets = [
    {
        "ticket_id": "NEX-123",
        "summary": "Fix login button alignment on mobile",
        "description": "The login button is slightly off-center on screens smaller than 480px.",
        "status": "Done",
        "assignee": "dev_a",
        "reporter": "qa_b",
        "code_refs": ["commit_abc123", "PR #45"],
        "doc_refs": ["ui_guidelines.md", "login_feature.md"]
    },
    {
        "ticket_id": "NEX-456",
        "summary": "Implement MCP server for Task API",
        "description": "Wrap the internal Task Management API with an MCP server.",
        "status": "In Progress",
        "assignee": "protocol_eng_c",
        "reporter": "lead_eng",
        "code_refs": ["commit_def456", "PR #52"],
        "doc_refs": ["mcp_server_design.md", "task_api_spec.md"]
    },
    {
        "ticket_id": "NEX-789",
        "summary": "Research A2A security models",
        "description": "Investigate OAuth and other options for securing agent communication.",
        "status": "To Do",
        "assignee": None,
        "reporter": "arch_d",
        "code_refs": [],
        "doc_refs": ["a2a_spec.md"]
    }
]

with open(os.path.join(base, "jira_tickets.json"), "w") as f:
    json.dump(jira_tickets, f, indent=2)

# ----------------------------
# Code Snippets (commit_abc123.py, commit_def456.py)
# ----------------------------
code_files = {
    "commit_abc123.py": """# Fix for NEX-123: Adjusted login button CSS

def apply_mobile_styles(button_element):
    if screen_width < 480:
        button_element.style.marginLeft = 'auto'
        button_element.style.marginRight = 'auto'
    # ... other styles
""",
    "commit_def456.py": """# Implementation of MCP server for Task API

def start_task_mcp_server():
    print("Starting MCP server for Task API...")
"""
}

for filename, content in code_files.items():
    with open(os.path.join(base, "code", filename), "w") as f:
        f.write(content)

# ----------------------------
# Documentation Files
# ----------------------------
docs = {
    "login_feature.md": """# Login Feature Documentation

This document describes the user login flow.

## UI Elements

- Username field
- Password field
- Login Button (See ui_guidelines.md for styling)

## Known Issues

- Alignment on mobile (NEX-123)
""",
    "ui_guidelines.md": """# UI Guidelines

All buttons must be center-aligned on mobile devices.
""",
    "mcp_server_design.md": """# MCP Server Design

Outlines the architecture and logic behind the MCP server wrapping Task API.
""",
    "task_api_spec.md": """# Task API Specification

Provides endpoint details and expected payloads for internal task operations.
""",
    "a2a_spec.md": """# A2A Security Model Research

Explores OAuth 2.1, OpenID Connect and alternatives for agent-to-agent authentication.
"""
}

for filename, content in docs.items():
    with open(os.path.join(base, "docs", filename), "w") as f:
        f.write(content)

# ----------------------------
# JIRA Ticket Summaries (one .txt per ticket)
# ----------------------------
tickets = {
    "NEX-123.txt": """Ticket: NEX-123
Summary: Fix login button alignment on mobile
Description: The login button is slightly off-center on screens smaller than 480px.
Status: Done
Refs: commit_abc123, PR #45, ui_guidelines.md, login_feature.md
""",
    "NEX-456.txt": """Ticket: NEX-456
Summary: Implement MCP server for Task API
Description: Wrap the internal Task Management API with an MCP server.
Status: In Progress
Refs: commit_def456, PR #52, mcp_server_design.md, task_api_spec.md
""",
    "NEX-789.txt": """Ticket: NEX-789
Summary: Research A2A security models
Description: Investigate OAuth and other options for securing agent communication.
Status: To Do
Refs: a2a_spec.md
"""
}

for filename, content in tickets.items():
    with open(os.path.join(base, "tickets", filename), "w") as f:
        f.write(content)

print("✅ Official mock knowledge base created successfully.")
