"""Log Watcher - 主动日志监控

后台线程周期检查 systemd 日志 (journalctl)，
命中规则引擎的异常条目自动触发 RAG + LLM 分析，
通过 AlertManager 推送告警给前端/CLI。

设计原则:
- 不直接扫全量日志，维护 last_check 偏移量增量检查
- 不把原始日志直接喂 LLM，通过规则引擎过滤后 + RAG 知识分析
- 不重复报警，通过 AlertManager 去重
"""

import asyncio
import platform
import shlex
import time
from pathlib import Path
import subprocess
import time
from datetime import datetime
from typing import Optional, List
from loguru import logger
from app.services.rule_engine import rule_engine
from app.services.alert_manager import alert_manager
from app.services.knowledge_service import knowledge_service
from app.providers.registry import ProviderRegistry
from langchain_core.messages import HumanMessage, SystemMessage

IS_LINUX = platform.system() == "Linux"


def _run_cmd(cmd: str, timeout: int = 10) -> Optional[str]:
    try:
        r = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


class LogWatcher:
    """日志监控器 - 后台线程增量扫描日志"""

    def __init__(self, interval: int = 15):
        self.interval = interval
        self._last_check = ""
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._file_pos = 0  # Windows 文件读取偏移量
        self._log_file = Path(__file__).resolve().parent.parent.parent / "logs" / "simulated" / "syslog.log"

    async def start(self):
        """启动后台监控"""
        self._running = True
        self._last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"LogWatcher 已启动, 间隔 {self.interval}s")

    async def stop(self):
        """停止监控"""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("LogWatcher 已停止")

    async def _run_loop(self):
        """主循环"""
        while self._running:
            try:
                await self._check()
            except Exception as e:
                logger.debug(f"LogWatcher 检查异常: {e}")
            await asyncio.sleep(self.interval)

    async def _check(self):
        """检查新日志"""
        entries = self._fetch_new_entries()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._last_check = now

        matched = []
        for entry in entries:
            rule = rule_engine.match(entry)
            if rule:
                matched.append((entry, rule))

        if not matched:
            return

        # 先分析，完成后再推送到 pending 列表
        from app.services.alert_manager import Alert

        async def analyze_and_push(entry, rule):
            fp = alert_manager._fingerprint(entry)
            if fp in alert_manager._history:
                return
            alert = Alert(
                id=fp, rule_name=rule.name, severity=rule.severity,
                category=rule.category, raw_log=entry, timestamp=now,
                source="/var/log/syslog" if IS_LINUX else "(mock)",
                discovered_at=time.time(),
            )
            await self._analyze_alert(alert)
            # 分析完成后再推入 pending
            alert_manager._history[fp] = alert
            alert_manager._pending.append(alert)
            logger.info(f"告警: [{rule.severity}] {rule.name} - {entry[:80]}")

        await asyncio.gather(*[analyze_and_push(e, r) for e, r in matched])

    def _fetch_new_entries(self) -> List[str]:
        """增量获取新日志条目

        在 Linux 上用 journalctl --since 查询。
        在 Windows 上读取 simulated/syslog.log 文件。
        """
        if IS_LINUX:
            cmd = f"journalctl --since '{self._last_check}' -p err --no-pager -n 50 2>/dev/null"
            output = _run_cmd(cmd)
            if output:
                return [l for l in output.strip().split("\n") if l.strip() and not l.startswith("--")]
            return []

        # Windows: 读取模拟日志文件
        return self._read_log_file()

    def _read_log_file(self) -> List[str]:
        """增量读取模拟日志文件"""
        if not self._log_file.exists():
            return []

        with open(self._log_file, "r", encoding="utf-8") as f:
            f.seek(self._file_pos)
            new_lines = f.readlines()
            self._file_pos = f.tell()

        entries = []
        for line in new_lines:
            line = line.strip()
            if line and not line.startswith("#"):
                entries.append(line)
        return entries

    async def _analyze_alert(self, alert):
        """对告警进行 RAG + LLM 分析"""
        try:
            # 提取关键词用于检索
            keyword = rule_engine.get_keyword(alert.raw_log) or alert.rule_name
            context = knowledge_service.search(keyword)

            llm = ProviderRegistry.get_llm(temperature=0.3, streaming=False)
            result = await llm.ainvoke([
                SystemMessage(content=f"你是一个 Linux 运维专家。分析以下日志，基于知识库给出诊断和建议。\n\n## 知识库参考\n{context}"),
                HumanMessage(content=f"## 日志\n{alert.raw_log}\n\n请分析原因并给出排查步骤和风险等级（低/中/高）。"),
            ])

            alert.diagnosis = result.content if hasattr(result, "content") else str(result)
            logger.info(f"告警分析完成 [{alert.rule_name}]: {len(alert.diagnosis)} 字符")

        except Exception as e:
            alert.diagnosis = f"分析失败: {e}"
            logger.warning(f"告警分析失败 [{alert.rule_name}]: {e}")


log_watcher = LogWatcher(interval=15)
