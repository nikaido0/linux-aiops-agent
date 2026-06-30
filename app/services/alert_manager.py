"""告警管理器 - 去重 + 事件队列

避免同一个错误反复推送，维护已处理告警的指纹。
"""

import time
import hashlib
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class Alert:
    id: str                              # 指纹 hash
    rule_name: str                       # 规则名，如 "OOM"
    severity: str                        # critical / warning
    category: str                        # system / disk / network / application
    raw_log: str                         # 原始日志行
    source: str                          # /var/log/syslog / journalctl
    timestamp: str                       # 日志时间
    discovered_at: float = 0.0           # 发现时间戳
    diagnosis: str = ""                  # LLM 分析结果
    read: bool = False                   # 用户是否已读


class AlertManager:
    """告警管理器

    职责:
    - 根据内容指纹去重（同一条日志只告警一次）
    - 维护待处理队列
    - 记录历史告警
    """

    def __init__(self, dedup_seconds: int = 300):
        self.dedup_seconds = dedup_seconds  # 同一指纹多少秒内不重复
        self._history: Dict[str, Alert] = {}  # 指纹 → Alert
        self._pending: List[Alert] = []        # 未读告警
        logger.info(f"告警管理器初始化, 去重窗口: {dedup_seconds}s")

    @staticmethod
    def _fingerprint(log_entry: str) -> str:
        """日志指纹: 取内容前 100 字符的 MD5"""
        return hashlib.md5(log_entry[:100].encode()).hexdigest()[:16]

    def push(self, log_entry: str, rule_name: str, severity: str, category: str, source: str, timestamp: str) -> Optional[Alert]:
        """推送新告警，已在去重窗口中则忽略"""
        fp = self._fingerprint(log_entry)
        now = time.time()

        # 去重检查
        existing = self._history.get(fp)
        if existing and (now - existing.discovered_at) < self.dedup_seconds:
            return None

        alert = Alert(
            id=fp,
            rule_name=rule_name,
            severity=severity,
            category=category,
            raw_log=log_entry,
            source=source,
            timestamp=timestamp,
            discovered_at=now,
        )
        self._history[fp] = alert
        self._pending.append(alert)
        logger.info(f"告警: [{severity}] {rule_name} - {log_entry[:80]}")
        return alert

    def get_pending(self) -> List[Alert]:
        """获取所有未读告警"""
        pending = self._pending.copy()
        self._pending.clear()
        for alert in pending:
            alert.read = True
        return pending

    def has_pending(self) -> bool:
        return len(self._pending) > 0

    def count_history(self) -> int:
        return len(self._history)


alert_manager = AlertManager()
