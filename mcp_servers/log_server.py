"""日志查询 MCP 服务

在 Linux 服务器上运行时，通过 subprocess 执行 journalctl、dmesg 等真实命令。
在 Windows/无权限环境下降级为模拟数据，方便开发调试。

启动: python mcp_servers/log_server.py
端口: 8003
"""

import json
import platform
import subprocess
import shlex
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("log-server", port=8003)
IS_LINUX = platform.system() == "Linux"


def _run_cmd(cmd: str, timeout: int = 10) -> Optional[str]:
    """执行 shell 命令，失败返回 None"""
    try:
        result = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout if result.returncode == 0 else None
    except Exception:
        return None


@mcp.tool()
def query_journalctl(
    priority: str = "err",
    since: str = "1 hour ago",
    unit: str = "",
    lines: int = 50,
) -> str:
    """查询 systemd 日志 (journalctl)

    在 Linux 上执行 journalctl 命令，在 Windows 上返回模拟数据。

    Args:
        priority: 日志级别 (emerg/alert/crit/err/warning/info/debug)
        since: 时间范围，如 "1 hour ago" "yesterday" "2026-06-29 00:00:00"
        unit: 按 systemd 单元过滤，如 "sshd" "nginx" "docker"
        lines: 返回行数
    """
    if IS_LINUX:
        cmd = f"journalctl --no-pager -p {priority} --since '{since}' -n {lines}"
        if unit:
            cmd += f" -u {unit}"
        output = _run_cmd(cmd)
        if output:
            lines_list = output.strip().split("\n")
            return json.dumps({"source": "journalctl", "total": len(lines_list), "logs": lines_list}, ensure_ascii=False, indent=2)

    # 模拟数据（开发环境或命令不可用时）
    samples = _mock_journalctl(priority, unit)
    return json.dumps({"source": "journalctl (mock)", "total": len(samples), "logs": samples[:lines]}, ensure_ascii=False, indent=2)


@mcp.tool()
def query_log_files(
    path: str = "/var/log/syslog",
    keyword: str = "",
    lines: int = 50,
) -> str:
    """查询日志文件内容（tail/grep）

    在 Linux 上执行 tail -n 或 grep 命令查看系统日志文件。

    Args:
        path: 日志文件路径, 如 /var/log/syslog /var/log/nginx/error.log
        keyword: 关键词过滤（可选）
        lines: 返回行数
    """
    if IS_LINUX:
        if keyword:
            cmd = f"grep -i '{keyword}' {path} 2>/dev/null | tail -{lines}"
        else:
            cmd = f"tail -{lines} {path} 2>/dev/null"
        output = _run_cmd(cmd)
        if output:
            lines_list = output.strip().split("\n")
            return json.dumps({"source": path, "total": len(lines_list), "logs": lines_list}, ensure_ascii=False, indent=2)

    # 模拟
    sample = _mock_log_file(path, keyword)
    return json.dumps({"source": f"{path} (mock)", "total": len(sample), "logs": sample[:lines]}, ensure_ascii=False, indent=2)


@mcp.tool()
def query_dmesg(
    keyword: str = "",
    lines: int = 30,
) -> str:
    """查询内核日志 (dmesg)

    查看系统内核消息，包括 OOM、磁盘错误、硬件故障等。

    Args:
        keyword: 关键词过滤（可选）
        lines: 返回行数
    """
    if IS_LINUX:
        cmd = "dmesg --human --time-format iso" + (f" | grep -i '{keyword}'" if keyword else "") + f" | tail -{lines}"
        output = _run_cmd(cmd, timeout=5)
        if output:
            lines_list = output.strip().split("\n")
            return json.dumps({"source": "dmesg", "total": len(lines_list), "logs": lines_list}, ensure_ascii=False, indent=2)

    samples = _mock_dmesg()
    return json.dumps({"source": "dmesg (mock)", "total": len(samples), "logs": samples[:lines]}, ensure_ascii=False, indent=2)


def _mock_journalctl(priority: str, unit: str = ""):
    now = "Jun 29 10:00:00"
    entries = {
        "err": [
            f"{now} node-1 kernel: [12345] OOM Killer invoked for process java (PID 1234)",
            f"{now} node-1 kernel: [12346] Out of memory: Killed process 1234 (java)",
            f"{now} node-1 sshd[2345]: fatal: timeout before authentication for 192.168.1.100",
            f"{now} node-1 kernel: [12347] EXT4-fs error (device sda1): journal has aborted",
            f"{now} node-1 app-server: java.io.IOException: No space left on device",
        ],
        "warning": [
            f"{now} node-1 kernel: [12348] CPU usage: 85%, threshold: 80%",
            f"{now} node-1 kernel: [12349] nf_conntrack: table full, dropping packet",
            f"{now} node-1 systemd: Disk usage /var/log: 82%",
            f"{now} node-1 systemd: Time has been changed",
            f"{now} node-1 app-server: Slow query detected: 3.5s",
        ],
    }
    default = entries.get(priority, entries["err"])
    if unit:
        return [e for e in default if unit in e]
    return default


def _mock_log_file(path: str, keyword: str = ""):
    samples = {
        "syslog": [
            "Jun 29 10:00:00 node-1 kernel: [12345] CPU usage: 85% on node-1",
            "Jun 29 10:01:00 node-1 kernel: [12346] Killed process 1234 (java) by signal 9 (SIGKILL)",
            "Jun 29 10:02:00 node-1 kernel: [12347] nf_conntrack: table full, dropping packet",
        ],
        "nginx": [
            "192.168.1.100 - - [29/Jun/2026:10:00:00 +0800] \"GET /api/orders HTTP/1.1\" 502 0 \"-\" \"curl/7.68\"",
            "192.168.1.101 - - [29/Jun/2026:10:01:00 +0800] \"POST /api/payment HTTP/1.1\" 504 0 \"-\" \"python-requests\"",
        ],
        "default": [
            f"Jun 29 10:00:00 node-1 {path}: [ERROR] simulated log entry 1",
            f"Jun 29 10:01:00 node-1 {path}: [WARN] simulated log entry 2",
        ],
    }
    for key, logs in samples.items():
        if key in path:
            result = logs
            break
    else:
        result = samples["default"]

    if keyword:
        result = [e for e in result if keyword.lower() in e.lower()]
    return result


def _mock_dmesg():
    return [
        "[2026-06-29T10:00:00+0800] OOM Killer: Killed process 1234 (java) total-vm:8456789kB",
        "[2026-06-29T10:01:00+0800] EXT4-fs (sda1): Remounting filesystem read-only",
        "[2026-06-29T10:02:00+0800] watchdog: BUG: soft lockup - CPU#0 stuck for 22s!",
        "[2026-06-29T10:03:00+0800] nf_conntrack: table full, dropping packet",
        "[2026-06-29T10:04:00+0800] Buffer I/O error on device sda1, logical block 123456",
    ]


if __name__ == "__main__":
    print(f"Log MCP server starting on port 8003 (platform: {platform.system()})...")
    mcp.run(transport="sse")
