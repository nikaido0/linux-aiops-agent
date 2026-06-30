"""规则引擎 - 过滤日志中的噪声，只关注真正的异常

维护一个规则列表，日志条目命中规则才触发分析。
避免大量 INFO/WARN 日志浪费 LLM 调用和用户注意力。
"""

import re
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class Rule:
    name: str                     # 规则名，如 "OOM"
    patterns: List[str]           # 关键词列表，如 ["oom", "out of memory"]
    severity: str = "warning"     # critical / warning / info
    category: str = "system"      # system / application / network / disk


# 默认规则集 - 只有这些类别的错误才触发分析
DEFAULT_RULES = [
    # 系统级
    Rule("OOM", ["oom", "out of memory", "killed process"], "critical", "system"),
    Rule("KernelPanic", ["kernel panic", "kernel oops"], "critical", "system"),
    Rule("Segfault", ["segfault", "segmentation fault", "signal 11"], "critical", "system"),
    Rule("SoftLockup", ["soft lockup", "hung_task", "blocked for"], "warning", "system"),
    Rule("EXT4Error", ["ext4-fs error", "journal has aborted", "remounting.*read.only"], "critical", "disk"),

    # 磁盘
    Rule("DiskFull", ["no space left on device", "disk usage.*\d+%"], "critical", "disk"),
    Rule("DiskIO", ["i/o error", "buffer i/o error", "failed to write"], "critical", "disk"),
    Rule("InodeFull", ["inode usage.*\d+%", "inode exhausted"], "warning", "disk"),

    # 网络
    Rule("ConntrackFull", ["nf_conntrack.*table full", "conntrack.*dropping"], "warning", "network"),
    Rule("NetworkDown", ["link down", "carrier lost", "network is unreachable"], "critical", "network"),
    Rule("ConnectionRefused", ["connection refused", "connection timed out"], "warning", "network"),
    Rule("DNSFailure", ["name or service not known", "temporary failure in name resolution"], "warning", "network"),

    # 进程
    Rule("ProcessDied", ["main process exited", "failed with result", "unit entered failed"], "warning", "system"),
    Rule("ServiceCrash", ["core dumped", "aborted", "signal 6", "sigabrt"], "critical", "application"),

    # 应用
    Rule("OOMApp", ["outofmemoryerror", "java heap space", "gc overhead limit exceeded"], "critical", "application"),
    Rule("NullPointer", ["nullpointerexception", "null pointer exception"], "warning", "application"),
    Rule("TooManyConnections", ["too many connections", "connection pool exhausted"], "warning", "application"),
    Rule("MySQLDeadlock", ["deadlock found", "lock wait timeout"], "warning", "application"),
]


class RuleEngine:
    """规则引擎 - 判断日志是否需要触发告警"""

    def __init__(self, rules: Optional[List[Rule]] = None):
        self.rules = rules or DEFAULT_RULES
        # 预编译正则
        self._compiled = [(r, re.compile('|'.join(r.patterns), re.IGNORECASE)) for r in self.rules]
        logger.info(f"规则引擎初始化, {len(self.rules)} 条规则")

    def match(self, log_entry: str) -> Optional[Rule]:
        """判断日志是否匹配规则，返回第一个匹配的规则"""
        for rule, pattern in self._compiled:
            if pattern.search(log_entry):
                return rule
        return None

    def get_keyword(self, log_entry: str) -> Optional[str]:
        """返回日志中命中的关键词（用于 RAG 检索）"""
        rule = self.match(log_entry)
        if not rule:
            return None
        for p in rule.patterns:
            if re.search(p, log_entry, re.IGNORECASE):
                return p
        return rule.patterns[0]


rule_engine = RuleEngine()
