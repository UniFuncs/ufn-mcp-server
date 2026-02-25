#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import express, { Request, Response } from "express";
import { z } from "zod";
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

async function request(
  method: string,
  url: string,
  data?: Record<string, any>
): Promise<string | Record<string, any>> {
  const options: any = {
    method: method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${UNIFUNCS_API_KEY}`,
    },
  };
  
  if (data) {
    options.body = JSON.stringify(data);
  }
  
  const response = await fetch(
    `${UNIFUNCS_API_BASE}/${url.replace(/^\//, "")}`,
    options
  );
  
  if (response.headers.get("Content-Type")?.includes("application/json")) {
    const result = (await response.json()) as {
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

// Web Search Tool
async function handleWebSearch(params: any) {
  const data = await request("POST", "/api/web-search/search", params);
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(data),
      },
    ]
  } as any;
}

// Web Reader Tool
async function handleWebReader(params: any) {
  const content = await request("POST", "/api/web-reader/read", params);
  return {
    content: [
      {
        type: "text",
        text: typeof content === "string" ? content : JSON.stringify(content),
      },
    ],
  } as any;
}

// Deep Search - Sync Tool
async function handleDeepSearchSync(params: any) {
  const { model = "s3", messages, stream = false } = params;
  const data = await request("POST", "/deepsearch/v1/chat/completions", {
    model,
    messages,
    stream
  });
  return {
    content: [
      {
        type: "text",
        text: typeof data === "string" ? data : JSON.stringify(data),
      },
    ],
  } as any;
}

// Deep Search - Create Task Tool
async function handleDeepSearchCreateTask(params: any) {
  const { model = "s3", messages } = params;
  const data = await request("POST", "/deepsearch/v1/create_task", {
    model,
    messages
  });
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(data),
      },
    ],
  } as any;
}

// Deep Search - Query Task Tool
async function handleDeepSearchQueryTask(params: any) {
  const { task_id } = params;
  const data = await request("GET", `/deepsearch/v1/query_task?task_id=${task_id}`);
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(data),
      },
    ],
  } as any;
}

// Deep Research - Create Task Tool
async function handleDeepResearchCreateTask(params: any) {
  const {
    model = "u1",
    content,
    introduction,
    reference_style = "link",
    generate_summary = false,
    max_depth = 25,
    domain_scope,
    domain_blacklist,
    output_prompt,
    important_urls,
    important_keywords,
    important_prompt,
    push_to_share = false,
    set_public = false
  } = params;
  
  const requestData: any = {
    model,
    messages: [{ role: "user", content }]
  };
  
  // Add optional parameters
  if (introduction) requestData.introduction = introduction;
  if (reference_style) requestData.reference_style = reference_style;
  if (generate_summary) requestData.generate_summary = generate_summary;
  if (max_depth) requestData.max_depth = max_depth;
  if (domain_scope) requestData.domain_scope = domain_scope;
  if (domain_blacklist) requestData.domain_blacklist = domain_blacklist;
  if (output_prompt) requestData.output_prompt = output_prompt;
  if (important_urls) requestData.important_urls = important_urls;
  if (important_keywords) requestData.important_keywords = important_keywords;
  if (important_prompt) requestData.important_prompt = important_prompt;
  if (push_to_share) requestData.push_to_share = push_to_share;
  if (set_public) requestData.set_public = set_public;
  
  const data = await request("POST", "/deepresearch/v1/create_task", requestData);
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(data),
      },
    ],
  } as any;
}

// Deep Research - Query Task Tool
async function handleDeepResearchQueryTask(params: any) {
  const { task_id } = params;
  const data = await request("GET", `/deepresearch/v1/query_task?task_id=${task_id}`);
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(data),
      },
    ],
  } as any;
}

// Server setup
const server = new McpServer({
  name: "mcp-server/unifuncs",
  version: "0.1.0",
});

// Register Web Search Tool
server.tool(
  "web-search",
  "通过关键词检索互联网上的信息列表",
  {
    query: z.string(),
    freshness: z.enum(["Day", "Week", "Month", "Year"]).optional(),
    page: z.number().min(1).optional(),
    count: z.number().min(1).max(50).optional(),
    format: z.enum(["markdown", "text", "json"]).optional(),
  },
  handleWebSearch
);

// Register Web Reader Tool
server.tool(
  "web-reader",
  "抓取指定页面URL的详细内容",
  {
    url: z.string(),
    format: z.enum(["markdown"]).optional(),
    includeImages: z.boolean().optional(),
    linkSummary: z.boolean().optional(),
  },
  handleWebReader
);

// Register Deep Search - Sync Tool
server.tool(
  "deep-search-sync",
  "深度搜索同步接口，实时返回搜索结果",
  {
    model: z.enum(["s3"]).optional().default("s3"),
    messages: z.array(z.object({
      role: z.enum(["user", "assistant", "system"]),
      content: z.string()
    })),
    stream: z.boolean().optional().default(false),
  },
  handleDeepSearchSync
);

// Register Deep Search - Create Task Tool
server.tool(
  "deep-search-create-task",
  "创建深度搜索异步任务，立即返回task_id",
  {
    model: z.enum(["s3"]).optional().default("s3"),
    messages: z.array(z.object({
      role: z.enum(["user", "assistant", "system"]),
      content: z.string()
    })),
  },
  handleDeepSearchCreateTask
);

// Register Deep Search - Query Task Tool
server.tool(
  "deep-search-query-task",
  "查询深度搜索异步任务状态和结果",
  {
    task_id: z.string(),
  },
  handleDeepSearchQueryTask
);

// Register Deep Research - Create Task Tool
server.tool(
  "deep-research-create-task",
  "创建深度研究任务，进行深度的网络信息研究和分析",
  {
    model: z.enum(["u1", "u1-pro"]).optional().default("u1"),
    content: z.string(),
    introduction: z.string().optional(),
    reference_style: z.enum(["link", "number", "footnote"]).optional().default("link"),
    generate_summary: z.boolean().optional().default(false),
    max_depth: z.number().min(1).max(50).optional().default(25),
    domain_scope: z.string().optional(),
    domain_blacklist: z.string().optional(),
    output_prompt: z.string().optional(),
    important_urls: z.string().optional(),
    important_keywords: z.string().optional(),
    important_prompt: z.string().optional(),
    push_to_share: z.boolean().optional().default(false),
    set_public: z.boolean().optional().default(false),
  },
  handleDeepResearchCreateTask
);

// Register Deep Research - Query Task Tool
server.tool(
  "deep-research-query-task",
  "查询深度研究任务状态和结果",
  {
    task_id: z.string(),
  },
  handleDeepResearchQueryTask
);

// Start server
if (process.env.UNIFUNCS_SSE_SERVER || process.argv.includes("--sse")) {
  const app = express();
  const transports: { [sessionId: string]: SSEServerTransport } = {};

  app.get("/sse", async (_: Request, res: Response) => {
    const transport = new SSEServerTransport("/messages", res);
    transports[transport.sessionId] = transport;
    res.on("close", () => {
      delete transports[transport.sessionId];
    });
    await server.connect(transport);
  });

  app.post("/messages", async (req: Request, res: Response) => {
    const sessionId = req.query.sessionId as string;
    const transport = transports[sessionId];
    if (transport) {
      await transport.handlePostMessage(req, res);
    } else {
      res.status(400).send("No transport found for sessionId");
    }
  });

  const port = Number(process.env.UNIFUNCS_SSE_SERVER_PORT || 5656);
  app.listen(port, () => {
    console.log(`UniFuncs MCP Server running on http://localhost:${port}`);
  });
} else {
  const transport = new StdioServerTransport();
  server.connect(transport);
  console.log("UniFuncs MCP Server running on stdio");
}
