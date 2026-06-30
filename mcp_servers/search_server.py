"""联网搜索 MCP 服务

提供网络搜索能力，让 Agent 能获取运维相关的在线资料。
当前为模拟实现，配置 SEARCH_API_KEY 后可对接真实搜索 API。

启动: python mcp_servers/search_server.py
端口: 8005
"""

import json
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("search-server", port=8005)


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """联网搜索运维相关信息

    Args:
        query: 搜索关键词
        max_results: 最大返回结果数
    """
    import re
    results = _mock_search(query, max_results)
    return json.dumps({"query": query, "total": len(results), "results": results}, ensure_ascii=False, indent=2)


def _mock_search(query: str, limit: int):
    db = {
        "oom": [
            {"title": "Linux OOM Killer 机制详解", "snippet": "当系统内存不足时，Linux OOM Killer 会选择并杀死进程来释放内存..."},
            {"title": "Java OutOfMemoryError 排查指南", "snippet": "常见的 OOM 类型: Java heap space, GC overhead limit exceeded..."},
        ],
        "nullpointer": [
            {"title": "Java NullPointerException 排查技巧", "snippet": "NPE 是最常见的 Java 异常，排查方法包括查看栈顶异常信息..."},
        ],
        "connection refused": [
            {"title": "Connection Refused 原因分析", "snippet": "端口未监听、防火墙拦截、服务未启动是常见原因..."},
        ],
        "too many connections": [
            {"title": "MySQL Too Many Connections 解决", "snippet": "修改 max_connections, 优化连接池, 排查僵死连接..."},
        ],
        "disk full": [
            {"title": "Linux 磁盘空间不足处理", "snippet": "清理日志、临时文件、Docker 镜像，配置 logrotate..."},
        ],
        "cpu load": [
            {"title": "Linux CPU 负载过高排查", "snippet": "使用 top/htop 定位高 CPU 进程，检查死循环、流量突增..."},
        ],
        "memory leak": [
            {"title": "Linux 内存泄漏排查", "snippet": "使用 valgrind, memleak 定位泄漏点，JVM 使用 jmap dump..."},
        ],
    }

    q = query.lower()
    for key, results in db.items():
        if key in q:
            return results[:limit]

    return [{"title": f"关于 {query} 的搜索结果", "snippet": f"这是关于 {query} 的模拟搜索结果。配置搜索 API 后可获取真实结果。"}]


if __name__ == "__main__":
    print("Search MCP server starting on port 8005...")
    mcp.run(transport="sse")
