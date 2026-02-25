# UniFuncs MCP Server

MCP Server for the UniFuncs API - Enhanced with Deep Search and Deep Research capabilities

## Features

This MCP server provides access to the following UniFuncs APIs:

### 1. Web Search (`web-search`)
Real-time web search with comprehensive results
- Search across the internet with keywords
- Filter by freshness (Day/Week/Month/Year)
- Pagination support (1-50 results per page)
- Multiple output formats (JSON/Markdown/Text)

### 2. Web Reader (`web-reader`)
Extract detailed content from web pages
- Clean content extraction
- Optional image inclusion
- Link summary support
- Markdown output

### 3. Deep Search - Sync (`deep-search-sync`)
Real-time deep search with immediate results
- Model: S3
- Streaming support
- Instant response

### 4. Deep Search - Async (`deep-search-create-task` + `deep-search-query-task`)
Asynchronous deep search for complex queries
- Create task and get task_id immediately
- Poll for task status and results
- Background processing for large queries

### 5. Deep Research (`deep-research-create-task` + `deep-research-query-task`)
Comprehensive deep research capabilities
- Models: U1, U1-Pro
- Customizable research parameters:
  - Introduction: Set researcher persona
  - Reference style: link/number/footnote
  - Max depth: Up to 50 iterations (25 recommended)
  - Domain scope: Limit search to specific domains
  - Domain blacklist: Exclude specific domains
  - Custom output prompts
  - Important URLs, keywords, and prompts
- Async task management

## Setup

### API Key

Get a UniFuncs API Key:
https://unifuncs.com/account

### NPX (STDIO)

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

### SSE Server

For SSE transport, set the environment variable:

```bash
export UNIFUNCS_SSE_SERVER=true
export UNIFUNCS_SSE_SERVER_PORT=5656  # Optional, default is 5656
```

Or use the `--sse` flag:

```bash
npx @unifuncs/ufn-mcp-server --sse
```

## Tool Reference

### web-search
```
Query: Search keywords
Freshness: Day | Week | Month | Year (optional)
Page: Page number, default 1 (optional)
Count: Results per page, 1-50, default 10 (optional)
Format: json | markdown | text, default json (optional)
```

### web-reader
```
URL: Page URL to read
Format: markdown (optional)
IncludeImages: boolean (optional)
LinkSummary: boolean (optional)
```

### deep-search-sync
```
Model: s3 (default: s3)
Messages: Array of {role: "user"|"assistant"|"system", content: string}
Stream: boolean (default: false)
```

### deep-search-create-task
```
Model: s3 (default: s3)
Messages: Array of {role: "user"|"assistant"|"system", content: string}
Returns: task_id for querying status
```

### deep-search-query-task
```
Task_ID: Task ID from create_task
Returns: Task status, progress, and results when completed
```

### deep-research-create-task
```
Model: u1 | u1-pro (default: u1)
Content: Research question/topic
Introduction: Researcher persona (optional)
Reference_Style: link | number | footnote (default: link)
Generate_Summary: boolean (default: false)
Max_Depth: 1-50 (default: 25, recommended)
Domain_Scope: Comma-separated domains (optional)
Domain_Blacklist: Comma-separated domains to exclude (optional)
Output_Prompt: Custom output template (optional)
Important_URLs: Comma-separated URLs (optional)
Important_Keywords: Comma-separated keywords (optional)
Important_Prompt: Important prompt content (optional)
Push_To_Share: boolean (default: false)
Set_Public: boolean (default: false)
Returns: task_id for querying status
```

### deep-research-query-task
```
Task_ID: Task ID from create_task
Returns: Task status, progress, and results when completed
```

## Examples

### Web Search
```javascript
{
  "query": "OpenClaw AI",
  "count": 5,
  "format": "json"
}
```

### Deep Search Async
```javascript
// Create task
{
  "model": "s3",
  "messages": [
    { "role": "user", "content": "What are the latest developments in AI?" }
  ]
}

// Query task (use returned task_id)
{
  "task_id": "3aff2a91-7795-4b73-8dab-0593551a27a1"
}
```

### Deep Research
```javascript
// Create research task
{
  "model": "u1",
  "content": "Analyze the impact of AI on healthcare",
  "max_depth": 25,
  "domain_scope": "arxiv.org, nature.com",
  "generate_summary": true
}

// Query research task
{
  "task_id": "research-task-id-here"
}
```

## Pricing

- Web Search: Pay per request
- Web Reader: Pay per request
- Deep Search: Pay per token usage
- Deep Research: 
  - U1: 0.6 PTC/M Tokens
  - U1-Pro: 1.2 PTC/M Tokens

For detailed pricing, visit: https://unifuncs.com/pricing

## Support

- Documentation: https://unifuncs.com/api
- GitHub: https://github.com/UniFuncs/ufn-mcp-server
- Email: service@unifuncs.com
- WeChat: unifuncs

## License

MIT

## Changelog

### v0.1.0 (2026-02-25)
- Added Deep Search sync API support
- Added Deep Search async API (create_task + query_task)
- Added Deep Research async API (create_task + query_task)
- Enhanced documentation with all tool references
- Improved error handling

### v0.0.6
- Initial release with web-search and web-reader
