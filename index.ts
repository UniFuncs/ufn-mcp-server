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
  data: Record<string, any>
): Promise<string | Record<string, any>> {
  const response = await fetch(
    `${UNIFUNCS_API_BASE}/${url.replace(/^\//, "")}`,
    {
      method: method,
      body: JSON.stringify(data),
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${UNIFUNCS_API_KEY}`,
      },
    }
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

// Server setup
const server = new McpServer({
  name: "mcp-server/unifuncs",
  version: "0.0.6",
});

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

}
else {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.log("UniFuncs MCP Server running on stdio");
}
