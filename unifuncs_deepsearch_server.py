#!/usr/bin/env python3
"""
UniFuncs MCP Server
===================
将 UniFuncs API 封装为 MCP 工具，供 Claude Code 使用。

API 文档:
- 深度搜索: https://unifuncs.com/api/deepsearch
- 深度研究: https://unifuncs.com/api/deepresearch
- 网页搜索: https://unifuncs.com/api/web-search
- 网页阅读: https://unifuncs.com/api/web-reader
"""

import os
import json
import logging
import sys
from typing import Optional, Literal

import httpx
from mcp.server.fastmcp import FastMCP

# 配置日志（输出到 stderr，避免干扰 stdio JSON-RPC）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("unifuncs-mcp")

# 初始化 MCP 服务器
mcp = FastMCP(
    name="unifuncs",
    instructions="UniFuncs API MCP 服务器 - 提供深度搜索(S2/S1)、深度研究(U2/U1/U1-Pro)、网页搜索和网页阅读能力"
)

# API 端点配置
API_ENDPOINTS = {
    "deepsearch": "https://api.unifuncs.com/deepsearch/v1/chat/completions",
    "deepresearch": "https://api.unifuncs.com/deepresearch/v1/chat/completions",
    "web_search": "https://api.unifuncs.com/api/web-search/search",
    "web_reader": "https://api.unifuncs.com/api/web-reader/read"
}

# 模型配置
DEEPSEARCH_MODELS = ["s2", "s1"]
DEEPRESEARCH_MODELS = ["u2", "u1", "u1-pro"]

# 引用格式
REFERENCE_STYLES = ["link", "character", "hidden"]

# Web API 格式
WEB_SEARCH_FORMATS = ["json", "markdown", "md", "text", "txt"]
WEB_READER_FORMATS = ["markdown", "md", "text", "txt"]

# 时效性选项
FRESHNESS_OPTIONS = ["Day", "Week", "Month", "Year"]

# 搜索区域选项
AREA_OPTIONS = ["global", "cn"]

# 输出类型（深度研究专用）
OUTPUT_TYPES = [
    "report",           # 万字报告
    "summary",          # 精炼摘要
    "wechat-article",   # 微信公众号文章
    "xiaohongshu-article",  # 小红书文章
    "toutiao-article",  # 头条文章
    "zhihu-article",    # 知乎文章
    "zhihu-answer",     # 知乎回答
    "weibo-article"     # 微博博文
]


def get_api_key():
    """获取 API Key"""
    return os.getenv("UNIFUNCS_API_KEY", "")


def create_http_client():
    """创建配置好的 HTTP 客户端"""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=10.0,
            read=1800.0,  # 30 分钟读取超时
            write=10.0,
            pool=5.0
        ),
        limits=httpx.Limits(
            max_keepalive_connections=5,
            max_connections=10
        )
    )


async def make_request(
    endpoint: str,
    request_body: dict,
    max_retries: int = 2
) -> str:
    """执行 API 请求的核心函数"""
    api_key = get_api_key()
    if not api_key:
        return "错误: 未配置 UNIFUNCS_API_KEY 环境变量。请在 MCP 配置中设置您的 API Key。"

    query_preview = request_body.get("messages", [{}])[0].get("content", "")[:50]
    model = request_body.get("model", "unknown")
    logger.info(f"请求 API: {endpoint} (model={model}, query={query_preview}...)")

    last_error = None
    # 在重试循环外创建客户端，复用连接
    async with create_http_client() as client:
        for attempt in range(max_retries + 1):
            try:
                response = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=request_body
                )
                response.raise_for_status()
                result = response.json()

                # 解析 OpenAI 兼容格式的响应
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0].get("message", {}).get("content", "")
                    if content:
                        logger.info(f"请求完成，返回 {len(content)} 字符")
                        return content

                logger.warning("响应格式不符合预期，返回原始 JSON")
                return json.dumps(result, ensure_ascii=False, indent=2)

            except httpx.HTTPStatusError as e:
                error_msg = f"API 请求失败 (HTTP {e.response.status_code})"
                try:
                    error_detail = e.response.json()
                    error_msg += f": {json.dumps(error_detail, ensure_ascii=False)}"
                except Exception:
                    error_msg += f": {e.response.text}"

                # 4xx 错误不重试，直接返回
                if 400 <= e.response.status_code < 500:
                    logger.error(error_msg)
                    return error_msg

                last_error = error_msg
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries + 1}): {error_msg}")

            except httpx.TimeoutException as e:
                last_error = f"请求超时: {str(e)}"
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{max_retries + 1})")

            except httpx.ConnectError as e:
                last_error = f"连接失败: {str(e)}"
                logger.warning(f"连接失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")

            except Exception as e:
                last_error = f"请求失败: {str(e)}"
                logger.error(last_error, exc_info=True)
                return last_error

    return f"{last_error}\n\n提示: 请稍后重试。"


async def make_web_api_request(
    endpoint: str,
    request_body: dict,
    operation_name: str,
    return_json: bool = False
) -> str:
    """执行 Web API 请求的通用函数（用于 web_search 和 web_reader）

    Args:
        endpoint: API 端点 URL
        request_body: 请求体（已包含 apiKey）
        operation_name: 操作名称，用于日志和错误消息
        return_json: 是否以 JSON 格式返回结果

    Returns:
        API 响应内容
    """
    try:
        async with create_http_client() as client:
            response = await client.post(
                endpoint,
                headers={"Content-Type": "application/json"},
                json=request_body
            )
            response.raise_for_status()

            if return_json:
                result = response.json()
                return json.dumps(result, ensure_ascii=False, indent=2)
            else:
                return response.text

    except httpx.HTTPStatusError as e:
        error_msg = f"{operation_name}失败 (HTTP {e.response.status_code})"
        try:
            error_detail = e.response.json()
            error_msg += f": {json.dumps(error_detail, ensure_ascii=False)}"
        except Exception:
            error_msg += f": {e.response.text}"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        error_msg = f"{operation_name}失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


# ============================================================
# 深度搜索 API (Deep Search) - 使用 S2/S1 模型
# ============================================================

@mcp.tool()
async def deep_search(
    query: str,
    model: str = "s2",
    max_depth: int = 25,
    reference_style: str = "link",
    introduction: Optional[str] = None,
    domain_scope: Optional[str] = None,
    domain_blacklist: Optional[str] = None,
    output_prompt: Optional[str] = None
) -> str:
    """执行深度搜索，高速、准确、全面地搜索任何信息。

    使用 UniFuncs 深度搜索引擎 (S2/S1 模型) 进行网络搜索和信息整合。
    会自动搜索多个网页、提取关键信息、整合成结构化的回答。

    适用场景：
    - 快速获取问题答案（如"Python GIL 是什么"）
    - 查找特定信息（如"Claude API 的价格"）
    - 了解某个话题的概况（如"2024年AI发展趋势"）
    - 技术问题排查（如"React useEffect 无限循环"）

    与 web_search 的区别：
    - deep_search：智能搜索 + AI 整合，返回结构化答案
    - web_search：原始搜索结果列表，需要自己阅读和整理

    Args:
        query: 搜索查询内容（必填）。可以是问题、关键词或完整句子。
        model: 模型版本，可选值：
            - "s2"：第二代深度搜索，更强更准确（推荐，默认）
            - "s1"：第一代深度搜索，速度更快
        max_depth: 搜索深度，范围 1-25（默认 25）。
            - 数值越大搜索越深入全面，但耗时更长
            - 简单问题可用 10-15，复杂问题建议 25
        reference_style: 引用格式，可选值：
            - "link"：Markdown 链接格式（默认，推荐）
            - "character"：纯文本引用
            - "hidden"：隐藏引用来源
        introduction: 设定回答的角色和风格（可选）。
            例如："你是一位资深的Python开发者，请用专业但易懂的方式回答"
        domain_scope: 限定搜索网站（可选）。多个网站用逗号分隔。
            例如："github.com,stackoverflow.com" 只搜索这两个网站
        domain_blacklist: 排除网站（可选）。多个网站用逗号分隔。
            例如："csdn.net,zhihu.com" 排除这些网站的结果
        output_prompt: 自定义输出提示词（可选）。
            例如："请用中文回答，并给出代码示例"

    Returns:
        搜索结果，包含：
        - 结构化的答案内容
        - 引用来源（根据 reference_style 格式化）
        - 相关信息和补充说明
    """
    if not query or not query.strip():
        return "错误: 搜索查询不能为空"
    if model not in DEEPSEARCH_MODELS:
        return f"错误: model 必须是 {DEEPSEARCH_MODELS} 之一"
    if max_depth < 1 or max_depth > 25:
        return "错误: max_depth 必须在 1-25 之间"
    if reference_style not in REFERENCE_STYLES:
        return f"错误: reference_style 必须是 {REFERENCE_STYLES} 之一"

    request_body = {
        "model": model,
        "messages": [{"role": "user", "content": query.strip()}],
        "stream": False,
        "max_depth": max_depth,
        "reference_style": reference_style
    }

    if introduction:
        request_body["introduction"] = introduction
    if domain_scope:
        request_body["domain_scope"] = domain_scope
    if domain_blacklist:
        request_body["domain_blacklist"] = domain_blacklist
    if output_prompt:
        request_body["output_prompt"] = output_prompt

    return await make_request(API_ENDPOINTS["deepsearch"], request_body)


# ============================================================
# 深度研究 API (Deep Research) - 使用 U2/U1/U1-Pro 模型
# ============================================================

@mcp.tool()
async def deep_research(
    topic: str,
    model: str = "u2",
    max_depth: int = 25,
    output_type: str = "report",
    output_length: int = 10000,
    reference_style: str = "link",
    plan_approval: bool = False,
    introduction: Optional[str] = None,
    domain_scope: Optional[str] = None,
    domain_blacklist: Optional[str] = None,
    output_prompt: Optional[str] = None
) -> str:
    """执行深度研究，进行深度分析并产出专业报告。

    使用 UniFuncs 深度研究引擎 (U2/U1/U1-Pro 模型) 进行多轮迭代研究。
    会自动制定研究计划、多轮搜索、深度分析、整合成专业报告。
    耗时较长（通常 2-10 分钟），适合需要深度分析的场景。

    适用场景：
    - 学术研究（如"大语言模型的幻觉问题研究"）
    - 技术调研（如"Rust vs Go 性能对比分析"）
    - 市场分析（如"2024年中国新能源汽车市场分析"）
    - 撰写万字报告、行业白皮书
    - 自媒体文章创作（知乎、公众号、小红书等）

    与 deep_search 的区别：
    - deep_search (S系列)：快速搜索（秒级），返回信息整合，适合简单问题
    - deep_research (U系列)：深度研究（分钟级），返回结构化分析报告，适合复杂主题

    注意事项：
    - 研究耗时较长，请耐心等待
    - 复杂主题建议使用 max_depth=25
    - 可通过 output_type 直接生成适合各平台的文章格式

    Args:
        topic: 研究主题（必填）。描述越详细，研究结果越精准。
            例如："分析 2024 年大语言模型在代码生成领域的最新进展和局限性"
        model: 模型版本，可选值：
            - "u2"：第二代通用研究，擅长信息挖掘（推荐，默认）
            - "u1"：第一代研究，擅长信息收集，速度较快
            - "u1-pro"：专业研究，擅长深度分析，质量最高但最慢
        max_depth: 研究深度，范围 1-25（默认 25）。
            - 数值越大研究越深入，但耗时越长
            - 简单主题可用 15-20，复杂主题建议 25
        output_type: 输出类型，可选值：
            - "report"：万字深度报告（默认）
            - "summary"：精炼摘要（约 1000-2000 字）
            - "wechat-article"：微信公众号文章风格
            - "xiaohongshu-article"：小红书文章风格
            - "toutiao-article"：头条文章风格
            - "zhihu-article"：知乎专栏文章风格
            - "zhihu-answer"：知乎回答风格
            - "weibo-article"：微博长文风格
        output_length: 预期输出长度，单位：字符数（默认 10000）。
            - 实际长度可能有所浮动
            - summary 类型建议 2000，report 类型建议 10000+
        reference_style: 引用格式，可选值：
            - "link"：Markdown 链接格式（默认）
            - "character"：纯文本引用
            - "hidden"：隐藏引用来源
        plan_approval: 是否先生成研究计划等待确认（默认 False）。
            - True：先返回研究计划，确认后再执行
            - False：直接执行研究，返回最终报告
        introduction: 设定研究员的角色和口吻（可选）。
            例如："你是一位资深的行业分析师，请用专业严谨的语言撰写报告"
        domain_scope: 限定搜索网站（可选）。多个网站用逗号分隔。
        domain_blacklist: 排除网站（可选）。多个网站用逗号分隔。
        output_prompt: 自定义输出提示词（可选）。
            例如："请在报告开头添加摘要，结尾添加参考文献列表"

    Returns:
        深度研究报告，包含：
        - 结构化的研究内容（根据 output_type 格式化）
        - 数据分析和洞察
        - 引用来源（根据 reference_style 格式化）
    """
    if not topic or not topic.strip():
        return "错误: 研究主题不能为空"
    if model not in DEEPRESEARCH_MODELS:
        return f"错误: model 必须是 {DEEPRESEARCH_MODELS} 之一"
    if max_depth < 1 or max_depth > 25:
        return "错误: max_depth 必须在 1-25 之间"
    if output_type not in OUTPUT_TYPES:
        return f"错误: output_type 必须是 {OUTPUT_TYPES} 之一"
    if reference_style not in REFERENCE_STYLES:
        return f"错误: reference_style 必须是 {REFERENCE_STYLES} 之一"

    request_body = {
        "model": model,
        "messages": [{"role": "user", "content": topic.strip()}],
        "stream": False,
        "max_depth": max_depth,
        "output_type": output_type,
        "output_length": output_length,
        "reference_style": reference_style,
        "plan_approval": plan_approval
    }

    if introduction:
        request_body["introduction"] = introduction
    if domain_scope:
        request_body["domain_scope"] = domain_scope
    if domain_blacklist:
        request_body["domain_blacklist"] = domain_blacklist
    if output_prompt:
        request_body["output_prompt"] = output_prompt

    return await make_request(API_ENDPOINTS["deepresearch"], request_body)


# ============================================================
# 网页搜索 API (Web Search)
# ============================================================

@mcp.tool()
async def web_search(
    query: str,
    count: int = 10,
    page: int = 1,
    format: str = "markdown",
    freshness: Optional[str] = None,
    area: Optional[str] = None,
    includeImages: bool = False
) -> str:
    """执行网页搜索，获取实时搜索结果列表。

    使用 UniFuncs Web Search API 进行实时网络搜索。
    返回原始搜索结果列表（标题、URL、摘要），不做 AI 整合。
    速度快，适合需要自己筛选和处理搜索结果的场景。

    适用场景：
    - 获取搜索结果列表，自行筛选有用的网页
    - 查找特定网页的 URL
    - 了解某个关键词有哪些相关网页
    - 配合 web_reader 使用：先搜索找到 URL，再读取具体内容

    与 deep_search 的区别：
    - web_search：返回原始搜索结果列表，需要自己阅读和整理
    - deep_search：AI 智能整合，直接返回结构化答案

    分页说明：
    - 每页最多返回 50 条结果（count 参数控制）
    - 通过 page 参数翻页获取更多结果
    - 例如：count=50, page=1 获取第 1-50 条
    - 例如：count=50, page=2 获取第 51-100 条

    Args:
        query: 搜索关键词（必填）。支持搜索引擎语法。
            例如："Python 教程"、"site:github.com FastAPI"
        count: 每页结果数量，范围 1-50（默认 10）。
            - 需要更多结果时可设为 50
            - 配合 page 参数可获取大量结果
        page: 页码，从 1 开始（默认 1）。
            - page=1 返回第 1 到第 count 条结果
            - page=2 返回第 count+1 到第 2*count 条结果
            - 以此类推，可翻页获取更多结果
        format: 输出格式，可选值：
            - "markdown"：Markdown 格式（默认，推荐）
            - "md"：同 markdown
            - "json"：JSON 格式，便于程序处理
            - "text"：纯文本格式
            - "txt"：同 text
        freshness: 结果时效性过滤（可选），可选值：
            - "Day"：最近一天
            - "Week"：最近一周
            - "Month"：最近一个月
            - "Year"：最近一年
            - 不设置则返回所有时间的结果
        area: 搜索区域（可选），可选值：
            - "global"：全球搜索
            - "cn"：中国区搜索（注意：结果可能经过过滤）
        includeImages: 是否包含图片搜索结果（默认 False）。
            - True：返回结果中包含相关图片
            - False：只返回网页结果

    Returns:
        搜索结果列表，每条结果包含：
        - 网页标题
        - 网页 URL
        - 内容摘要
        - （如 includeImages=True）相关图片
    """
    # 参数验证
    if not query or not query.strip():
        return "错误: 搜索关键词不能为空"
    if count < 1 or count > 50:
        return "错误: count 必须在 1-50 之间"
    if format not in WEB_SEARCH_FORMATS:
        return f"错误: format 必须是 {WEB_SEARCH_FORMATS} 之一"
    if freshness and freshness not in FRESHNESS_OPTIONS:
        return f"错误: freshness 必须是 {FRESHNESS_OPTIONS} 之一"
    if area and area not in AREA_OPTIONS:
        return f"错误: area 必须是 {AREA_OPTIONS} 之一"

    # API Key 检查
    api_key = get_api_key()
    if not api_key:
        return "错误: 未配置 UNIFUNCS_API_KEY 环境变量。请在 MCP 配置中设置您的 API Key。"

    logger.info(f"网页搜索: {query[:50]}...")

    # 构建请求体
    request_body = {
        "query": query.strip(),
        "apiKey": api_key,
        "count": count,
        "page": page,
        "format": format,
        "includeImages": includeImages
    }

    if freshness:
        request_body["freshness"] = freshness
    if area:
        request_body["area"] = area

    # 使用通用 Web API 请求函数
    return await make_web_api_request(
        API_ENDPOINTS["web_search"],
        request_body,
        "网页搜索",
        return_json=(format == "json")
    )


# ============================================================
# 网页阅读 API (Web Reader)
# ============================================================

@mcp.tool()
async def web_reader(
    url: str,
    format: str = "markdown",
    liteMode: bool = False,
    includeImages: bool = True,
    maxWords: int = 0,
    readTimeout: int = 120000,
    topic: Optional[str] = None,
    linkSummary: bool = False
) -> str:
    """读取并解析网页内容，提取结构化正文。

    使用 UniFuncs Web Reader API 获取网页的结构化内容。
    自动去除广告、导航栏等干扰元素，提取干净的正文内容。
    支持大多数网页，包括新闻、博客、文档等。

    适用场景：
    - 阅读网页文章的完整内容
    - 提取网页正文用于分析或总结
    - 配合 web_search 使用：先搜索找到 URL，再读取具体内容
    - 获取文档页面的详细信息
    - 批量采集网页内容

    与浏览器直接访问的区别：
    - web_reader：提取干净的正文，去除广告和干扰元素
    - 浏览器：显示完整页面，包含所有元素

    使用建议：
    - 普通文章：使用默认参数即可
    - 长文章：设置 liteMode=True 只保留正文
    - 需要链接：设置 linkSummary=True 获取页面所有链接
    - 特定内容：使用 topic 参数只提取相关内容

    Args:
        url: 目标网页 URL（必填）。必须是完整的 URL，包含 http:// 或 https://。
            例如："https://docs.python.org/3/tutorial/index.html"
        format: 输出格式，可选值：
            - "markdown"：Markdown 格式（默认，推荐）
            - "md"：同 markdown
            - "text"：纯文本格式，去除所有格式
            - "txt"：同 text
        liteMode: 可读性过滤模式（默认 False）。
            - True：只保留正文内容，去除侧边栏、页脚等
            - False：保留更多页面元素
            - 建议长文章或内容复杂的页面开启
        includeImages: 是否包含图片（默认 True）。
            - True：在 Markdown 中包含图片链接
            - False：只返回文本内容
        maxWords: 最大字符数限制，范围 0-5000000（默认 0）。
            - 0：不限制，返回完整内容
            - 设置具体数值：内容超过时会被截断
            - 例如：maxWords=10000 限制返回 10000 字符
        readTimeout: 读取超时时间，单位：毫秒（默认 120000，即 2 分钟）。
            - 某些大页面或慢速网站可能需要更长时间
            - 可设置更大值如 300000（5 分钟）
        topic: 提取特定主题相关内容（可选）。
            - 设置后只返回与该主题相关的段落
            - 例如：topic="API 使用方法" 只提取 API 相关内容
            - 适合从长文档中提取特定信息
        linkSummary: 是否附加页面链接列表（默认 False）。
            - True：在内容末尾附加页面中所有链接的列表
            - False：只返回正文内容
            - 适合需要了解页面链接结构的场景

    Returns:
        网页内容，格式取决于 format 参数：
        - Markdown 格式：保留标题、列表、链接等结构
        - 纯文本格式：去除所有格式标记
        - （如 linkSummary=True）末尾附加链接列表
    """
    # 参数验证
    if not url or not url.strip():
        return "错误: 网页 URL 不能为空"
    if format not in WEB_READER_FORMATS:
        return f"错误: format 必须是 {WEB_READER_FORMATS} 之一"
    if maxWords < 0 or maxWords > 5000000:
        return "错误: maxWords 必须在 0-5000000 之间"

    # API Key 检查
    api_key = get_api_key()
    if not api_key:
        return "错误: 未配置 UNIFUNCS_API_KEY 环境变量。请在 MCP 配置中设置您的 API Key。"

    logger.info(f"网页阅读: {url[:80]}...")

    # 构建请求体
    request_body = {
        "url": url.strip(),
        "apiKey": api_key,
        "format": format,
        "liteMode": liteMode,
        "includeImages": includeImages,
        "readTimeout": readTimeout,
        "linkSummary": linkSummary
    }

    if maxWords > 0:
        request_body["maxWords"] = maxWords
    if topic:
        request_body["topic"] = topic

    # 使用通用 Web API 请求函数
    return await make_web_api_request(
        API_ENDPOINTS["web_reader"],
        request_body,
        "网页阅读",
        return_json=False
    )


# ============================================================
# 便捷工具
# ============================================================

@mcp.tool()
async def check_config() -> str:
    """检查当前 MCP 服务器的配置状态。

    使用此工具可以快速诊断 UniFuncs MCP 服务器的运行状态，包括：
    - API Key 配置情况
    - 各 API 端点地址
    - 可用工具列表及其功能说明
    - 各模型的特点介绍

    适用场景：
    - 首次使用时检查配置是否正确
    - API 调用失败时排查配置问题
    - 了解服务器支持的工具和功能
    - 验证 API Key 是否已正确设置

    此工具不需要任何参数，直接调用即可。

    Returns:
        配置状态报告，包含：
        - API Key 状态（已配置/未配置）及脱敏预览
        - 所有 API 端点的完整 URL
        - 可用工具对照表（工具名、模型、用途）
        - 各模型的功能说明
        - 整体服务状态（正常/需要配置）
    """
    api_key = get_api_key()
    api_key_status = "已配置" if api_key else "未配置"
    if api_key and len(api_key) > 12:
        api_key_preview = f"{api_key[:8]}...{api_key[-4:]}"
    else:
        api_key_preview = "N/A"

    config_info = f"""
UniFuncs MCP 配置状态
=====================

API Key: {api_key_status} ({api_key_preview})

API 端点:
- 深度搜索: {API_ENDPOINTS["deepsearch"]}
- 深度研究: {API_ENDPOINTS["deepresearch"]}
- 网页搜索: {API_ENDPOINTS["web_search"]}
- 网页阅读: {API_ENDPOINTS["web_reader"]}

可用工具:
┌─────────────────┬──────────────┬─────────────────────────────────┐
│ 工具            │ 模型/类型    │ 用途                            │
├─────────────────┼──────────────┼─────────────────────────────────┤
│ deep_search     │ s2 / s1      │ 深度搜索，快速获取信息          │
│ deep_research   │ u2/u1/u1-pro │ 深度研究，专业分析万字报告      │
│ web_search      │ Web API      │ 网页搜索，获取搜索结果列表      │
│ web_reader      │ Web API      │ 网页阅读，提取网页正文内容      │
│ check_config    │ -            │ 配置检查                        │
└─────────────────┴──────────────┴─────────────────────────────────┘

模型说明:
- S2: 第二代深度搜索，更强更准确
- S1: 第一代深度搜索，更快
- U2: 第二代通用研究，擅长信息挖掘
- U1: 第一代研究，擅长信息收集
- U1-Pro: 专业研究，擅长深度分析
- Web API: 通用网页搜索和阅读接口

状态: {'✅ 正常' if api_key else '❌ 请配置 UNIFUNCS_API_KEY 环境变量'}
"""
    return config_info.strip()


def main():
    """启动 MCP 服务器"""
    logger.info("启动 UniFuncs MCP Server...")

    api_key = get_api_key()
    if not api_key:
        logger.warning("警告: UNIFUNCS_API_KEY 未配置")
    else:
        logger.info("API Key 已配置，服务器就绪")

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
