"""Linux 系统状态 MCP 服务

在 Linux 上通过 subprocess 执行系统命令获取实时状态。
在 Windows 上返回模拟数据用于开发调试。

启动: python mcp_servers/linux_server.py
端口: 8004
"""

import json
import os
import platform
import shlex
import subprocess
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("linux-server", port=8004)
IS_LINUX = platform.system() == "Linux"


def _run(cmd: str, timeout: int = 10) -> Optional[str]:
    try:
        r = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


@mcp.tool()
def system_info() -> str:
    """查看系统基本信息: 主机名、OS 版本、内核、运行时间"""
    if IS_LINUX:
        info = {}
        if o := _run("uname -a"):
            info["kernel"] = o.strip()
        if o := _run("cat /etc/os-release 2>/dev/null | head -4"):
            for line in o.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    info[k.lower()] = v.strip('"')
        if o := _run("uptime -p"):
            info["uptime"] = o.strip()
        if o := _run("hostname"):
            info["hostname"] = o.strip()
        return json.dumps(info if info else _mock_sysinfo(), ensure_ascii=False, indent=2)

    return json.dumps({"source": "mock", **_mock_sysinfo()}, ensure_ascii=False, indent=2)


@mcp.tool()
def cpu_info() -> str:
    """查看 CPU 使用率、负载、占用最高的进程"""
    if IS_LINUX:
        data = {}
        if o := _run("top -bn1 | head -5"):
            data["summary"] = o.strip()
        if o := _run("ps aux --sort=-%cpu | head -11"):
            data["top_processes"] = [l for l in o.strip().split("\n") if l]
        if o := _run("cat /proc/loadavg"):
            data["load_avg"] = o.strip()
        if o := _run("mpstat -P ALL 1 1 2>/dev/null | tail +4"):
            data["per_core"] = [l for l in o.strip().split("\n") if l]
        return json.dumps(data if data else _mock_cpu(), ensure_ascii=False, indent=2)

    return json.dumps({"source": "mock", **_mock_cpu()}, ensure_ascii=False, indent=2)


@mcp.tool()
def memory_info() -> str:
    """查看内存使用率、Swap、占用最高的进程"""
    if IS_LINUX:
        data = {}
        if o := _run("free -h"):
            data["free"] = o.strip()
        if o := _run("cat /proc/meminfo | head -20"):
            data["meminfo"] = [l for l in o.strip().split("\n") if l]
        if o := _run("ps aux --sort=-%mem | head -11"):
            data["top_processes"] = [l for l in o.strip().split("\n") if l]
        if o := _run("swapon --show 2>/dev/null"):
            data["swap"] = [l for l in o.strip().split("\n") if l]
        return json.dumps(data if data else _mock_memory(), ensure_ascii=False, indent=2)

    return json.dumps({"source": "mock", **_mock_memory()}, ensure_ascii=False, indent=2)


@mcp.tool()
def disk_info() -> str:
    """查看磁盘使用率、inode、挂载点、大目录"""
    if IS_LINUX:
        data = {}
        if o := _run("df -h | grep '^/'"):
            data["disk_usage"] = [l for l in o.strip().split("\n") if l]
        if o := _run("df -i | grep '^/' 2>/dev/null"):
            data["inode_usage"] = [l for l in o.strip().split("\n") if l]
        if o := _run("du -sh /* 2>/dev/null | sort -rh | head -10"):
            data["large_dirs"] = [l for l in o.strip().split("\n") if l]
        return json.dumps(data if data else _mock_disk(), ensure_ascii=False, indent=2)

    return json.dumps({"source": "mock", **_mock_disk()}, ensure_ascii=False, indent=2)


@mcp.tool()
def process_list(sort_by: str = "cpu", limit: int = 10) -> str:
    """查看当前运行的进程

    Args:
        sort_by: 排序字段 (cpu / memory / pid / name)
        limit: 返回条数
    """
    sort_map = {"cpu": "%cpu", "memory": "%mem", "pid": "pid", "name": "comm"}
    sort_key = sort_map.get(sort_by, "%cpu")
    if IS_LINUX:
        o = _run(f"ps aux --sort=-{sort_key} | head -{limit + 1}")
        if o:
            return json.dumps({"processes": [l for l in o.strip().split("\n") if l], "sort_by": sort_by}, ensure_ascii=False, indent=2)

    return json.dumps({"source": "mock", "sort_by": sort_by, "processes": _mock_processes()[:limit]}, ensure_ascii=False, indent=2)


@mcp.tool()
def service_status(name: str = "") -> str:
    """查看 systemd 服务状态

    Args:
        name: 服务名，为空则列出所有 failed 服务
    """
    if IS_LINUX:
        cmd = f"systemctl status {name} --no-pager -l" if name else "systemctl list-units --failed --no-pager"
        o = _run(cmd)
        if o:
            return json.dumps({"service": name or "all failed", "status": o.strip()}, ensure_ascii=False, indent=2)

    return json.dumps({"source": "mock", "service": name or "all", "status": _mock_services(name)}, ensure_ascii=False, indent=2)


@mcp.tool()
def network_info() -> str:
    """查看网络状态: 监听端口、连接数、接口流量"""
    if IS_LINUX:
        data = {}
        if o := _run("ss -tlnp"):
            data["listening"] = [l for l in o.strip().split("\n") if l]
        if o := _run("ss -tan | awk '{print $1}' | sort | uniq -c"):
            data["conn_state"] = [l for l in o.strip().split("\n") if l]
        if o := _run("ip addr show | grep inet"):
            data["interfaces"] = [l.strip() for l in o.strip().split("\n") if l]
        return json.dumps(data if data else _mock_network(), ensure_ascii=False, indent=2)

    return json.dumps({"source": "mock", **_mock_network()}, ensure_ascii=False, indent=2)


# ── Mock 数据 ──────────────────────────────────────────


def _mock_sysinfo():
    return {"hostname": "node-1", "os": "Ubuntu 22.04.3 LTS", "kernel": "Linux 5.15.0-91-generic", "uptime": "up 14 days, 6 hours", "cpu": "Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz"}


def _mock_cpu():
    return {"load_avg": "4.52 3.78 2.95 1/1024 12345", "usage": "user: 35%, system: 12%, idle: 50%, iowait: 3%", "top_processes": [{"pid": 1234, "name": "java", "cpu%": 85.3}, {"pid": 5678, "name": "mysqld", "cpu%": 12.5}, {"pid": 9012, "name": "python3", "cpu%": 8.1}]}


def _mock_memory():
    return {"total": "31.2G", "used": "25.6G", "free": "5.6G", "usage%": 82, "swap_total": "4.0G", "swap_used": "1.2G", "top_processes": [{"pid": 1234, "name": "java", "mem%": 45.3}, {"pid": 5678, "name": "mysqld", "mem%": 12.8}]}


def _mock_disk():
    return [{"mount": "/", "total": "400G", "used": "320G", "avail": "80G", "use%": "80%"}, {"mount": "/var/log", "total": "50G", "used": "42G", "avail": "8G", "use%": "84%"}, {"mount": "/data", "total": "1T", "used": "800G", "avail": "200G", "use%": "80%"}]


def _mock_processes():
    return [{"pid": 1234, "name": "java", "cpu": 85.3, "mem": 45.2, "status": "running"}, {"pid": 5678, "name": "mysqld", "cpu": 12.5, "mem": 12.8, "status": "running"}, {"pid": 9012, "name": "nginx", "cpu": 0.5, "mem": 0.3, "status": "running"}]


def _mock_services(name=""):
    return {"sshd": "active (running)", "nginx": "active (running)", "mysql": "active (running)", "java-service": "failed (exit code 1)"}.get(name, {"failed": ["java-service"], "running": ["sshd", "nginx", "mysql"]})


def _mock_network():
    return {"listening_ports": [{"port": 22, "process": "sshd"}, {"port": 80, "process": "nginx"}, {"port": 3306, "process": "mysqld"}, {"port": 8080, "process": "java"}], "connections": {"ESTAB": 245, "TIME_WAIT": 89, "LISTEN": 12}}


if __name__ == "__main__":
    print(f"Linux MCP server starting on port 8004 (platform: {platform.system()})...")
    mcp.run(transport="sse")
