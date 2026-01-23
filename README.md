# UniFuncs MCP Server

将 [UniFuncs](https://unifuncs.com) API 封装为 MCP 工具，让 Claude Code 具备强大的信息检索、研究分析、网页搜索和阅读能力。

## 功能特点

| 工具 | API | 模型/类型 | 用途 |
|------|-----|-----------|------|
| **deep_search** | 深度搜索 | S2 / S1 | 高速、准确、全面搜索信息 |
| **deep_research** | 深度研究 | U2 / U1 / U1-Pro | 深度分析、万字报告、专业研究 |
| **web_search** | 网页搜索 | Web API | 实时搜索、获取搜索结果列表 |
| **web_reader** | 网页阅读 | Web API | 提取网页正文、阅读文章内容 |

## 快速开始

### 方式一：使用 uvx（推荐）

无需下载安装，直接配置即可使用！

**1. 获取 API Key**

前往 [UniFuncs 账户页面](https://unifuncs.com/account) 获取您的 API Key。

**2. 配置 Claude Code**

编辑 `~/.claude/claude_desktop_config.json` 或项目目录下的 `.mcp.json`：

```json
{
  "mcpServers": {
    "unifuncs": {
      "type": "stdio",
      "command": "uvx",
      "args": ["unifuncs-mcp-server"],
      "env": {
        "UNIFUNCS_API_KEY": "sk-你的API Key"
      }
    }
  }
}
```

**3. 重启 Claude Code 并验证**

```
/mcp
```

### 方式二：使用 pip 安装

```bash
pip install unifuncs-mcp-server
```

然后配置 `.mcp.json`：

```json
{
  "mcpServers": {
    "unifuncs": {
      "type": "stdio",
      "command": "unifuncs-mcp-server",
      "env": {
        "UNIFUNCS_API_KEY": "sk-你的API Key"
      }
    }
  }
}
```

### 方式三：从源码运行

```bash
# 克隆仓库
git clone https://github.com/UniFuncs/ufn-mcp-server.git
cd ufn-mcp-server

# 安装依赖
pip install -e .

# 或者直接运行
pip install mcp httpx
python src/unifuncs_mcp/server.py
```

配置 `.mcp.json`：

```json
{
  "mcpServers": {
    "unifuncs": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/ufn-mcp-server/src/unifuncs_mcp/server.py"],
      "env": {
        "UNIFUNCS_API_KEY": "sk-你的API Key"
      }
    }
  }
}
```

## 工具说明

### 1. deep_search - 深度搜索

使用 S2/S1 模型进行网络搜索和信息整合。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| query | string | 必填 | 搜索查询内容 |
| model | string | "s2" | "s2"(更强) 或 "s1"(更快) |
| max_depth | int | 25 | 搜索深度 1-25，建议 25 |
| reference_style | string | "link" | link / character / hidden |
| introduction | string | - | 设定回答角色和风格 |
| domain_scope | string | - | 限定搜索网站，逗号分隔 |
| domain_blacklist | string | - | 排除网站，逗号分隔 |

**示例：**
```
帮我深度搜索一下 "MCP 协议是什么"

用 deep_search 搜索 Python 异步编程，限定在 docs.python.org
```

### 2. deep_research - 深度研究

使用 U2/U1/U1-Pro 模型进行深度分析，产出万字报告。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| topic | string | 必填 | 研究主题 |
| model | string | "u2" | "u2"(通用) / "u1"(信息收集) / "u1-pro"(专业分析) |
| max_depth | int | 25 | 研究深度 1-25 |
| output_type | string | "report" | 输出类型（见下表） |
| output_length | int | 10000 | 预期输出长度（字符） |
| reference_style | string | "link" | link / character / hidden |
| plan_approval | bool | false | 是否生成研究计划并等待用户批准 |

**output_type 可选值：**
| 值 | 说明 |
|----|------|
| report | 万字报告 |
| summary | 精炼摘要 |
| wechat-article | 微信公众号文章 |
| xiaohongshu-article | 小红书文章 |
| toutiao-article | 头条文章 |
| zhihu-article | 知乎文章 |
| zhihu-answer | 知乎回答 |
| weibo-article | 微博博文 |

**示例：**
```
帮我深度研究一下 "大语言模型的幻觉问题"

用 deep_research 研究 "Rust vs Go 性能对比"，输出为知乎文章格式
```

### 3. web_search - 网页搜索

执行实时网络搜索，获取搜索结果列表。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| query | string | 必填 | 搜索关键词 |
| count | int | 10 | 每页结果数量，1-50 |
| page | int | 1 | 页码 |
| format | string | "markdown" | 输出格式：json / markdown / md / text / txt |
| freshness | string | - | 时效性：Day / Week / Month / Year |
| area | string | - | 搜索区域：global / cn（cn 地区结果经过审查过滤） |
| includeImages | bool | false | 是否包含图片结果 |

**示例：**
```
用 web_search 搜索 "Claude MCP 教程"

网页搜索 "Python 3.12 新特性"，只要最近一周的结果
```

### 4. web_reader - 网页阅读

读取并解析网页内容，提取结构化正文。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| url | string | 必填 | 目标网页 URL |
| format | string | "markdown" | 输出格式：markdown / md / text / txt |
| liteMode | bool | false | 启用可读性过滤，只保留正文 |
| includeImages | bool | true | 是否包含图片 |
| maxWords | int | 0 | 最大字符数，0 表示无限制 (max: 5000000) |
| readTimeout | int | 120000 | 读取超时毫秒数 |
| topic | string | - | 提取与特定主题相关的内容 |
| linkSummary | bool | false | 附加页面所有链接 |

**示例：**
```
用 web_reader 读取 https://docs.anthropic.com/claude/docs

读取网页 https://example.com，只提取与 "API" 相关的内容
```

## 模型说明

### 深度搜索模型 (S 系列)
- **S2**: 第二代深度搜索，更强更准确（推荐）
- **S1**: 第一代深度搜索，更快

### 深度研究模型 (U 系列)
- **U2**: 第二代通用研究，擅长信息挖掘（推荐）
- **U1**: 第一代研究，擅长信息收集
- **U1-Pro**: 专业研究，擅长深度分析

### Web API
- **Web Search**: 实时网页搜索，返回搜索结果列表
- **Web Reader**: 网页内容提取，返回结构化正文

## 相关链接

- [UniFuncs 官网](https://unifuncs.com)
- [深度搜索 API 文档](https://unifuncs.com/api/deepsearch)
- [深度研究 API 文档](https://unifuncs.com/api/deepresearch)
- [网页搜索 API 文档](https://unifuncs.com/api/web-search)
- [网页阅读 API 文档](https://unifuncs.com/api/web-reader)
- [获取 API Key](https://unifuncs.com/account)
- [U深搜体验](https://s.unifuncs.com)
- [U深研体验](https://dr.unifuncs.com)

## License

MIT License
