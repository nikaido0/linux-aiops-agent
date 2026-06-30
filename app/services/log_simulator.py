"""日志模拟器 - Windows 开发环境下写入模拟日志文件

在 logs/simulated/syslog.log 中写入真实格式的日志，
LogWatcher 像读 Linux /var/log/syslog 一样读这个文件。
"""

import asyncio
import random
from datetime import datetime, timedelta
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent.parent / "logs" / "simulated" / "syslog.log"

HOSTS = ["node-01", "node-02", "node-03", "node-04", "node-05"]

# 每组是一个前置上下文 + 一条匹配规则的日志
SCENARIOS = [
    # ── OOM ──
    (["node-01", "kernel"], "oom-killer: gfp_mask=0x100cca(GFP_HIGHUSER(MOVABLE)), order=0, oom_score_adj=0"),
    (["node-01", "kernel"], "java invoked oom-killer: order=0, oom_score_adj=0, gfp_mask=0x100cca"),
    (["node-02", "kernel"], "Out of memory: Killed process 1234 (java) total-vm:8456789kB, anon-rss:6234567kB, file-rss:234kB"),
    (["node-02", "kernel"], "Killed process 5678 (mysqld) by signal 9 (SIGKILL)"),
    (["node-02", "systemd"], "mysqld.service: Main process exited, code=killed, status=9/SIGKILL"),

    # ── 磁盘 ──
    (["node-03", "kernel"], "EXT4-fs error (device sda1): ext4_mb_generate_buddy:756: group 42, 32254 clusters in bitmap, 32255 in gd"),
    (["node-03", "kernel"], "Aborting journal on device sda1."),
    (["node-03", "kernel"], "EXT4-fs (sda1): Remounting filesystem read-only"),
    (["node-04", "app-server"], "java.io.IOException: No space left on device"),
    (["node-04", "kernel"], "Buffer I/O error on device dm-0, logical block 123456789"),

    # ── 网络 ──
    (["node-05", "kernel"], "nf_conntrack: table full, dropping packet"),
    (["node-05", "kernel"], "nf_conntrack: table full, dropping packet. net_ratelimit: 100 callbacks suppressed"),

    # ── 应用 OOM ──
    (["node-06", "app-server"], "java.lang.OutOfMemoryError: Java heap space"),
    (["node-06", "app-server"], "java.lang.OutOfMemoryError: GC overhead limit exceeded"),
    (["node-06", "app-server"], "Exception in thread 'http-nio-8080-exec-12' java.lang.OutOfMemoryError: unable to create new native thread"),

    # ── 段错误 ──
    (["node-07", "kernel"], "segfault at 7f8c4a0b3000 ip 00007f8c4a0b3e50 sp 00007ffd8f3a4b80 error 6 in libjvm.so+0x3e50"),
    (["node-07", "systemd"], "nginx.service: Main process exited, code=dumped, status=11/SEGV"),

    # ── MySQL ──
    (["node-08", "mysqld"], "[ERROR] Too many connections - max_connections=200"),
    (["node-08", "app-server"], "com.zaxxer.hikari.HikariPool-1 - Connection is not available, request timed out after 30000ms"),
    (["node-08", "mysqld"], "[ERROR] Host 'app-01' is blocked because of many connection errors; unblock with 'mysqladmin flush-hosts'"),

    # ── 连接超时 ──
    (["node-09", "app-server"], "java.net.ConnectException: Connection refused: /10.0.0.50:6379 (Redis)"),
    (["node-09", "app-server"], "java.net.SocketTimeoutException: Connect timed out: /10.0.0.51:3306"),

    # ── CPU ──
    (["node-10", "kernel"], "watchdog: BUG: soft lockup - CPU#0 stuck for 22s! [java:5678]"),
    (["node-10", "kernel"], "watchdog: BUG: soft lockup - CPU#1 stuck for 23s! [mysqld:5679]"),

    # ── 进程崩溃 ──
    (["node-01", "systemd"], "java.service: Main process exited, code=killed, status=9/SIGKILL"),
    (["node-03", "systemd"], "sshd.service: Main process exited, code=exited, status=255"),
]


class LogSimulator:
    """日志模拟器 - 持续向日志文件写入真实格式的日志"""

    def __init__(self, interval: int = 20):
        self.interval = interval
        self._running = False
        self._task: asyncio.Task = None
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    async def start(self):
        self._running = True
        # 初始化日志文件（模拟轮转）
        LOG_FILE.write_text("# Linux AIOps Agent - Simulated System Log\n")
        self._task = asyncio.create_task(self._run())
        print(f"  [日志模拟器] 写入: {LOG_FILE}")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _run(self):
        while self._running:
            await self._write_batch()
            await asyncio.sleep(self.interval)

    async def _write_batch(self):
        count = random.randint(1, 3)
        selected = random.sample(SCENARIOS, min(count, len(SCENARIOS)))
        now = datetime.now()
        lines = []
        for (host, facility), message in selected:
            ts = (now - timedelta(seconds=random.randint(0, 60))).strftime("%b %d %H:%M:%S")
            lines.append(f"{ts} {host} {facility}: {message}")
        lines.append("")
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        async with asyncio.Lock():
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.writelines(f"{l}\n" for l in lines)


log_simulator = LogSimulator(interval=20)
