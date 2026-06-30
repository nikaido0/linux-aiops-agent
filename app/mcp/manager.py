"""MCP 管理器 - 全局单例，自动管理子进程生命周期"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, List, Union, Any
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from loguru import logger
from app.config import config
from .client import load_mcp_tools_safe, retry_interceptor

# MCP 服务脚本路径
MCP_SERVERS_DIR = Path(__file__).resolve().parent.parent.parent / "mcp_servers"

MCP_SERVER_SCRIPTS = {
    "log": MCP_SERVERS_DIR / "log_server.py",
    "linux": MCP_SERVERS_DIR / "linux_server.py",
    "search": MCP_SERVERS_DIR / "search_server.py",
}


class MCPManager:
    """MCP 管理器 - 自动管理子进程生命周期

    启动时自动拉起 MCP Server 子进程，关闭时自动清理。
    用户只需 python cli.py，不需要手动管理多个终端。
    """

    _client: Optional[MultiServerMCPClient] = None
    _processes: List[subprocess.Popen] = []

    @classmethod
    def _start_server_processes(cls):
        """启动所有 MCP Server 子进程"""
        if cls._processes:
            return

        python = sys.executable
        for name, script_path in MCP_SERVER_SCRIPTS.items():
            if not script_path.exists():
                logger.warning(f"MCP 脚本不存在: {script_path}")
                continue
            try:
                proc = subprocess.Popen(
                    [python, str(script_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                cls._processes.append(proc)
                logger.info(f"MCP [{name}] 已启动 (PID {proc.pid})")
            except Exception as e:
                logger.warning(f"MCP [{name}] 启动失败: {e}")

    @classmethod
    def _stop_server_processes(cls):
        """关闭所有 MCP Server 子进程"""
        for proc in cls._processes:
            try:
                proc.terminate()
                proc.wait(timeout=3)
                logger.info(f"MCP 进程 (PID {proc.pid}) 已停止")
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        cls._processes.clear()

    @classmethod
    async def get_client(cls) -> MultiServerMCPClient:
        if cls._client is None:
            cls._start_server_processes()
            logger.info("初始化 MCP 客户端...")
            cls._client = MultiServerMCPClient(
                config.mcp_servers,
                tool_interceptors=[retry_interceptor],
            )
            logger.info(f"MCP 客户端初始化完成, 服务器: {list(config.mcp_servers.keys())}")
        return cls._client

    @classmethod
    async def get_tools(cls) -> List[Union[BaseTool, Any]]:
        client = await cls.get_client()
        # 连接 MCP 服务（重试 2 次）
        for attempt in range(2):
            tools, err = await load_mcp_tools_safe(client)
            if not err:
                logger.info(f"成功加载 {len(tools)} 个 MCP 工具")
                return tools
            if attempt < 1:
                await asyncio.sleep(3)
        logger.info(f"MCP 工具不可用（{err}），仅使用本地工具")
        return []

    @classmethod
    async def close(cls):
        """清理 MCP 客户端连接并停止子进程"""
        cls._client = None
        cls._stop_server_processes()
        logger.info("MCP 已关闭")

    @classmethod
    def close_sync(cls):
        """同步关闭（用于信号处理器）"""
        cls._stop_server_processes()
