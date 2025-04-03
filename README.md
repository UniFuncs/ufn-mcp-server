# UniFuncs MCP Server

MCP Server for the UniFuncs API

## Setup

### API Key

Get a UniFuncs API Key:
https://unifuncs.com/account

### NPX

```json
{
    "mcpServers": {
        "unifuncs": {
            "command": "npx",
            "args": [
                "-y",
                "@unifuncs/ufn-mcp-server"
            ],
            "env": {
                "UNIFUNCS_API_KEY": "sk-**********"
            }
        }
    }
}
```
