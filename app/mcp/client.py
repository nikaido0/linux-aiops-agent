"""MCP 客户端工具函数 - 重试拦截器、异常处理、安全加载"""

import asyncio
from typing import List, Optional, Union, Any
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from mcp.types import CallToolResult, TextContent
from loguru import logger


def format_exception_chain(exc: BaseException) -> str:
    """展开 ExceptionGroup，便于定位真实异常"""
    sub = getattr(exc, "exceptions", None)
    if sub is not None:
        lines = [str(exc)]
        for i, s in enumerate(sub):
            lines.append(f"  [{i}] {format_exception_chain(s)}")
        return "\n".join(lines)
    msg = f"{type(exc).__name__}: {exc}"
    cause = exc.__cause__ or exc.__context__
    if cause and cause is not exc:
        return f"{msg}\n  caused by: {format_exception_chain(cause)}"
    return msg


async def load_mcp_tools_safe(
    client: MultiServerMCPClient,
) -> tuple[List[Union[BaseTool, Any]], Optional[str]]:
    """安全加载 MCP 工具，失败时返回错误信息而非抛出异常"""
    try:
        tools = await client.get_tools()
        return tools, None
    except BaseException as e:
        return [], format_exception_chain(e)


async def retry_interceptor(
    request: MCPToolCallRequest,
    handler,
    max_retries: int = 3,
    delay: float = 1.0,
):
    """MCP 工具调用重试拦截器（指数退避）

    当工具调用失败时，使用指数退避自动重试。
    所有重试都失败时返回错误信息，不向上抛异常——避免一个工具失败拖垮整个 Agent 流程。
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            logger.info(f"MCP 调用 {request.name} (第 {attempt+1}/{max_retries} 次)")
            return await handler(request)
        except Exception as e:
            last_error = e
            logger.warning(f"MCP {request.name} 失败 (第 {attempt+1} 次): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay * (2**attempt))

    error_msg = f"工具 {request.name} 重试 {max_retries} 次后失败: {last_error}"
    logger.error(error_msg)
    return CallToolResult(content=[TextContent(type="text", text=error_msg)], isError=True)
