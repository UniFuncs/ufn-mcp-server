"""
UniFuncs MCP Server
===================
将 UniFuncs API 封装为 MCP 工具，让 Claude Code 具备强大的信息检索、研究分析、网页搜索和阅读能力。

使用方式:
    uvx unifuncs-mcp-server

或者在 MCP 配置中:
    {
        "mcpServers": {
            "unifuncs": {
                "type": "stdio",
                "command": "uvx",
                "args": ["unifuncs-mcp-server"],
                "env": {
                    "UNIFUNCS_API_KEY": "sk-你的Key"
                }
            }
        }
    }
"""

__version__ = "0.1.0"

from .server import main, mcp

__all__ = ["main", "mcp", "__version__"]
