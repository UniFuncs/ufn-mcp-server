#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema, } from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";

function getApiKey() {
    const apiKey = process.env.UNIFUNCS_API_KEY;
    if (!apiKey) {
        console.error("UNIFUNCS_API_KEY environment variable is not set");
        process.exit(1);
    }
    return apiKey;
}

const UNIFUNCS_API_KEY = getApiKey();
const UNIFUNCS_API_BASE = "https://api.unifuncs.com";

const WEB_SEARCH_TOOL = {
    name: "web-search",
    description: "通过关键词检索互联网上的信息列表",
    inputSchema: {
        type: "object",
        properties: {
            query: {
                type: "string",
                description: "搜索关键词"
            },
            freshness: {
                type: "string",
                description: "时效性，通常使用Day",
                enum: ["Day", "Week", "Month", "Year"],
            },
            page: {
                type: "number",
                description: "页码，从1开始，默认为1",
                default: 1
            },
            count: {
                type: "number",
                description: "每页数量，默认为10",
                default: 10,
                minimum: 1,
                maximum: 50
            }
        },
        required: ["query"],
    }
}

const WEB_READER_TOOL = {
    name: "web-reader",
    description: "阅读指定页面的详细内容",
    inputSchema: {
        type: "object",
        properties: {
            url: {
                type: "string",
                description: "待阅读的页面URL"
            },
            format: {
                type: "string",
                description: "输出格式，通常使用markdown",
                enum: ["markdown"],
                default: "markdown"
            },
            includeImages: {
                type: "boolean",
                description: "是否包含图片，默认为true",
                default: true
            },
            linkSummary: {
                type: "boolean",
                description: "是否包含链接摘要，默认为true",
                default: true
            }
        },
        required: ["url"]
    }
}

const ALL_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_READER_TOOL,
];

async function request(method: string, url: string, data: Record<string, any>): Promise<string | Record<string, any>> {
    const response = await fetch(`${UNIFUNCS_API_BASE}/${url.replace(/^\//, "")}`, {
        method: method,
        body: JSON.stringify(data),
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${UNIFUNCS_API_KEY}`,
        },
    });
    if (response.headers.get("Content-Type")?.includes("application/json")) {
        const result = await response.json() as {
            code: number;
            message: string;
            data: any;
        };
        if (result.code !== 0) {
            throw new Error(result.message);
        }
        return result.data;
    }
    return response.text();
}

async function handleWebSearch(query: string, freshness: string, page: number, count: number) {
    const data = await request("POST", "/api/web-search/search", {
        query,
        freshness,
        page,
        count,
    });
    return {
        content: [{
            type: "text",
            text: JSON.stringify(data)
        }]
    };
}

async function handleWebReader(url: string, format: string, includeImages: boolean, linkSummary: boolean) {
    const content = await request("POST", "/api/web-reader/read", {
        url,
        format,
        includeImages,
        linkSummary,
    });
    return {
        content: [{
            type: "text",
            text: typeof content === 'string' ? content : JSON.stringify(content)
        }]
    };
}

// Server setup
const server = new Server({
    name: "mcp-server/unifuncs",
    version: "0.0.1",
}, {
    capabilities: {
        tools: {},
    },
});

// Set up request handlers
server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: ALL_TOOLS,
}));
server.setRequestHandler(CallToolRequestSchema, async (request: any) => {
    try {
        switch (request.params.name) {
            case "web-search": {
                const { query, freshness, page, count } = request.params.arguments;
                return await handleWebSearch(query, freshness, page, count);
            }
            case "web-reader": {
                const { url, format, includeImages, linkSummary } = request.params.arguments;
                return await handleWebReader(url, format, includeImages, linkSummary);
            }
            default:
                return {
                    content: [{
                        type: "text",
                        text: `Unknown tool: ${request.params.name}`
                    }],
                    isError: true
                };
        }
    } catch (error) {
        return {
            content: [{
                type: "text",
                text: `Error: ${error instanceof Error ? error.message : String(error)}`
            }],
            isError: true
        };
    }
});

async function runServer() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("UniFuncs MCP Server running on stdio");
}

runServer().catch((error) => {
    console.error("Fatal error running server:", error);
    process.exit(1);
});