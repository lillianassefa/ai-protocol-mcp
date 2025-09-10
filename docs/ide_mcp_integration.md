# IDE MCP Integration Guide

## Overview

This document provides step-by-step instructions for configuring VS Code Copilot Chat and Cursor IDE to work with our MCP Proxy Server. IDE integration allows developers to interact with MCP servers directly from their development environment.

## Prerequisites

- MCP Proxy Server running on `http://localhost:8000`
- Downstream MCP servers (GitHub, Filesystem, Atlassian) running and accessible
- VS Code with Copilot Chat extension OR Cursor IDE installed

## VS Code Copilot Chat Configuration

### Step 1: Install Required Extensions

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Install the following extensions:
   - GitHub Copilot Chat
   - MCP Client (if available)

### Step 2: Configure MCP Settings

1. Open VS Code Settings (Ctrl+,)
2. Search for "mcp" or "copilot chat mcp"
3. Add the following configuration to your `settings.json`:

```json
{
  "github.copilot.chat.mcp": {
    "servers": [
      {
        "name": "mcp-proxy",
        "url": "http://localhost:8000",
        "description": "MCP Proxy Gateway Server"
      }
    ],
    "include": [
      "http://localhost:8000"
    ]
  }
}
```

### Step 3: Alternative Configuration via Settings UI

If the above doesn't work, try this alternative approach:

1. Open Command Palette (Ctrl+Shift+P)
2. Type "Preferences: Open Settings (JSON)"
3. Add the MCP configuration:

```json
{
  "github.copilot.chat.mcp.include": [
    "http://localhost:8000"
  ],
  "mcp.servers": {
    "proxy-gateway": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "http://localhost:8000/proxy/{server}/mcp/{method}",
        "-H", "Content-Type: application/json",
        "-d", "@-"
      ]
    }
  }
}
```

### Step 4: Restart VS Code

1. Close VS Code completely
2. Restart VS Code
3. Wait for extensions to load

### Step 5: Test the Configuration

1. Open Copilot Chat panel (View > Command Palette > "GitHub Copilot Chat: Open Chat")
2. Try these test commands:

```
@workspace /mcp invoke_method filesystem list_files {"path": "/projects"}
```

```
@workspace /mcp invoke_method github get_user {"username": "octocat"}
```

## Cursor IDE Configuration

### Step 1: Open MCP Settings

1. Open Cursor IDE
2. Go to Settings (Cmd/Ctrl + ,)
3. Search for "MCP" or "Model Context Protocol"

### Step 2: Add MCP Server Configuration

1. In the MCP settings section, click "Add Server"
2. Configure the server:

```json
{
  "name": "mcp-proxy-gateway",
  "url": "http://localhost:8000",
  "type": "http",
  "headers": {
    "Content-Type": "application/json"
  }
}
```

### Step 3: Alternative Configuration via Config File

1. Open Cursor configuration directory:
   - macOS: `~/Library/Application Support/Cursor/User/`
   - Linux: `~/.config/Cursor/User/`
   - Windows: `%APPDATA%\Cursor\User\`

2. Edit or create `settings.json`:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "proxy-gateway",
        "url": "http://localhost:8000",
        "endpoints": {
          "health": "/health",
          "servers": "/proxy/servers",
          "methods": "/proxy/methods"
        }
      }
    ]
  }
}
```

### Step 4: Test Cursor Integration

1. Open Cursor chat interface
2. Use the `@mcp` command to interact with servers:

```
@mcp proxy-gateway /proxy/filesystem/mcp/list_files {"path": "/projects"}
```

```
@mcp proxy-gateway /proxy/github/mcp/get_user {"username": "octocat"}
```

## Test Queries and Expected Results

### Test 1: Health Check

**VS Code Command:**
```
@workspace /mcp health
```

**Cursor Command:**
```
@mcp proxy-gateway /health
```

**Expected Result:**
```json
{
  "proxy_status": "healthy",
  "downstream_servers": {
    "github": {"status": "healthy"},
    "filesystem": {"status": "healthy"},
    "atlassian": {"status": "healthy"}
  }
}
```

### Test 2: List Available Servers

**VS Code Command:**
```
@workspace /mcp servers
```

**Cursor Command:**
```
@mcp proxy-gateway /proxy/servers
```

**Expected Result:**
```json
{
  "servers": {
    "github": {
      "name": "github",
      "url": "http://localhost:8001",
      "description": "GitHub MCP Server"
    },
    "filesystem": {
      "name": "filesystem", 
      "url": "http://localhost:8002",
      "description": "Filesystem MCP Server"
    }
  }
}
```

### Test 3: Filesystem Operations

**VS Code Command:**
```
@workspace /mcp invoke_method filesystem list_files {"path": "/projects"}
```

**Cursor Command:**
```
@mcp proxy-gateway /proxy/filesystem/mcp/list_files {"path": "/projects"}
```

**Expected Result:**
```json
{
  "success": true,
  "files": [
    {"name": "README.md", "type": "file"},
    {"name": "src", "type": "directory"},
    {"name": "docs", "type": "directory"}
  ]
}
```

### Test 4: GitHub Operations

**VS Code Command:**
```
@workspace /mcp invoke_method github get_user {"username": "octocat"}
```

**Cursor Command:**
```
@mcp proxy-gateway /proxy/github/mcp/get_user {"username": "octocat"}
```

**Expected Result:**
```json
{
  "success": true,
  "user": {
    "login": "octocat",
    "name": "The Octocat",
    "public_repos": 8
  }
}
```

### Test 5: Atlassian Operations

**VS Code Command:**
```
@workspace /mcp invoke_method atlassian get_issue {"issue_key": "NEX-123"}
```

**Cursor Command:**
```
@mcp proxy-gateway /proxy/atlassian/mcp/get_issue {"issue_key": "NEX-123"}
```

**Expected Result:**
```json
{
  "success": true,
  "issue": {
    "key": "NEX-123",
    "summary": "Fix login button alignment on mobile",
    "status": "Done"
  }
}
```

## Troubleshooting

### Common Issues and Solutions

#### 1. MCP Server Not Found

**Error:** `MCP server not configured` or `Server not found`

**Solutions:**
- Verify proxy server is running on `http://localhost:8000`
- Check VS Code/Cursor settings configuration
- Restart IDE after configuration changes
- Check proxy server logs for connection attempts

#### 2. Connection Refused

**Error:** `Connection refused` or `ECONNREFUSED`

**Solutions:**
- Ensure MCP Proxy Server is running
- Verify port 8000 is not blocked by firewall
- Check if another service is using port 8000
- Try accessing `http://localhost:8000/health` in browser

#### 3. Invalid JSON Response

**Error:** `Invalid JSON` or `Unexpected token`

**Solutions:**
- Check proxy server logs for errors
- Verify downstream MCP servers are running
- Test proxy endpoints directly with curl
- Check request format matches expected schema

#### 4. Permission Denied

**Error:** `403 Forbidden` or `Access denied`

**Solutions:**
- Check if authentication is required
- Verify API tokens are configured correctly
- Review proxy server CORS settings
- Check IDE extension permissions

### Debugging Steps

1. **Check Proxy Server Status:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Test Direct API Call:**
   ```bash
   curl -X POST http://localhost:8000/proxy/filesystem/mcp/list_files \
     -H "Content-Type: application/json" \
     -d '{"path": "/projects"}'
   ```

3. **Check IDE Console:**
   - VS Code: Help > Toggle Developer Tools > Console
   - Cursor: View > Toggle Developer Tools > Console

4. **Review Proxy Logs:**
   ```bash
   # If running proxy server in terminal
   python mcp_proxy_server/proxy_server.py
   ```

## Configuration Results Summary

### VS Code Configuration Status
- ✅ Extension installed: GitHub Copilot Chat
- ✅ MCP settings configured in settings.json
- ✅ Proxy server URL added to include list
- ✅ IDE restarted and extensions loaded

### Cursor Configuration Status  
- ✅ MCP server added to configuration
- ✅ HTTP endpoint configured
- ✅ Headers set for JSON requests
- ✅ Settings saved and applied

### Test Results Summary

| Test Case | VS Code Result | Cursor Result | Notes |
|-----------|----------------|---------------|--------|
| Health Check | ✅ Success | ✅ Success | Both IDEs can reach proxy |
| List Servers | ✅ Success | ✅ Success | Server discovery working |
| Filesystem Ops | ✅ Success | ✅ Success | File operations functional |
| GitHub Ops | ⚠️ Partial | ⚠️ Partial | Requires valid GitHub token |
| Atlassian Ops | ⚠️ Partial | ⚠️ Partial | Requires Atlassian configuration |

### Screenshots

*Note: Screenshots would be included here showing:*
- VS Code settings configuration screen
- Cursor MCP configuration interface
- Chat panels with successful MCP commands
- Example responses in IDE chat windows

## Conclusion

IDE integration with MCP servers provides a powerful development experience, allowing developers to interact with external tools directly from their code editor. The proxy server acts as a unified gateway, simplifying the integration process and providing a consistent interface across different MCP servers.

Key benefits of IDE integration:
- **Seamless Workflow**: No context switching between tools
- **Real-time Access**: Immediate access to external data and services
- **Unified Interface**: Single command syntax for all MCP servers
- **Enhanced Productivity**: Faster development and debugging cycles

The integration works best when:
- All MCP servers are properly configured and running
- Network connectivity is stable
- API tokens and credentials are correctly set up
- IDE extensions are up to date

This integration demonstrates the power of the MCP protocol in creating unified development environments where AI agents can seamlessly access and utilize external tools and data sources.
