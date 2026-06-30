"""扩充测试数据集到 100 条"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

path = Path("scripts/evaluation/test_dataset.json")
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Current: {len(data)}")

more = [
    {"id": "MEM-008", "category": "memory", "question": "如何查看进程内存占用排行", "expected_doc": "process-management", "expected_keywords": ["ps", "%mem", "排序"]},
    {"id": "MEM-009", "category": "memory", "question": "Linux swap 使用过高怎么办", "expected_doc": "memory-usage", "expected_keywords": ["swap", "swappiness", "内存"]},
    {"id": "MEM-010", "category": "memory", "question": "JVM 堆内存怎么设置", "expected_doc": "memory-usage", "expected_keywords": ["Xmx", "Xms", "JVM"]},
    {"id": "CPU-007", "category": "cpu", "question": "如何用 perf 分析 CPU 性能", "expected_doc": "cpu-usage", "expected_keywords": ["perf", "采样", "热点"]},
    {"id": "CPU-008", "category": "cpu", "question": "load average 多少算高", "expected_doc": "cpu-usage", "expected_keywords": ["负载", "平均负载", "CPU"]},
    {"id": "DSK-008", "category": "disk", "question": "/tmp 目录写满了怎么办", "expected_doc": "disk-usage", "expected_keywords": ["/tmp", "临时文件", "清理"]},
    {"id": "DSK-009", "category": "disk", "question": "如何配置 logrotate 清理日志", "expected_doc": "log-management", "expected_keywords": ["logrotate", "轮转"]},
    {"id": "NET-008", "category": "network", "question": "如何抓包分析网络问题", "expected_doc": "network-troubleshooting", "expected_keywords": ["tcpdump", "抓包"]},
    {"id": "NET-009", "category": "network", "question": "curl 请求超时怎么排查", "expected_doc": "network-troubleshooting", "expected_keywords": ["curl", "超时"]},
    {"id": "SVC-007", "category": "service", "question": "Nginx 504 Gateway Timeout", "expected_doc": "nginx-troubleshooting", "expected_keywords": ["504", "proxy_read_timeout"]},
    {"id": "SVC-008", "category": "service", "question": "Nginx 413 Request Entity Too Large", "expected_doc": "nginx-troubleshooting", "expected_keywords": ["413", "client_max_body_size"]},
    {"id": "SVC-009", "category": "service", "question": "如何查看 nginx 访问日志", "expected_doc": "nginx-troubleshooting", "expected_keywords": ["access.log", "nginx"]},
    {"id": "DKR-004", "category": "docker", "question": "docker logs 看不到日志", "expected_doc": "docker-troubleshooting", "expected_keywords": ["docker", "logs"]},
    {"id": "DKR-005", "category": "docker", "question": "Docker 容器网络不通", "expected_doc": "docker-troubleshooting", "expected_keywords": ["docker", "网络"]},
    {"id": "DKR-006", "category": "docker", "question": "docker exec 进入容器", "expected_doc": "docker-troubleshooting", "expected_keywords": ["docker", "exec"]},
    {"id": "MYS-004", "category": "mysql", "question": "MySQL 主从延迟怎么办", "expected_doc": "mysql-troubleshooting", "expected_keywords": ["主从", "延迟"]},
    {"id": "MYS-005", "category": "mysql", "question": "如何查看 MySQL 当前连接数", "expected_doc": "mysql-troubleshooting", "expected_keywords": ["Threads_connected", "max_connections"]},
    {"id": "MYS-006", "category": "mysql", "question": "mysqladmin flush-hosts 作用", "expected_doc": "mysql-troubleshooting", "expected_keywords": ["flush-hosts", "blocked"]},
    {"id": "LOG-005", "category": "log", "question": "dmesg 命令怎么用", "expected_doc": "log-management", "expected_keywords": ["dmesg", "内核"]},
    {"id": "LOG-006", "category": "log", "question": "如何实时查看系统日志", "expected_doc": "log-management", "expected_keywords": ["tail", "journalctl"]},
    {"id": "PRC-004", "category": "process", "question": "pstree 查看进程树", "expected_doc": "process-management", "expected_keywords": ["pstree"]},
    {"id": "KRN-005", "category": "kernel", "question": "sysctl 永久生效怎么配置", "expected_doc": "kernel-tuning", "expected_keywords": ["sysctl.conf", "持久化"]},
    {"id": "KRN-006", "category": "kernel", "question": "怎么修改打开文件数限制", "expected_doc": "kernel-tuning", "expected_keywords": ["ulimit", "nofile"]},
    {"id": "SEC-006", "category": "security", "question": "如何查看登录失败记录", "expected_doc": "ssh-troubleshooting", "expected_keywords": ["auth.log", "登录"]},
    {"id": "SEC-007", "category": "security", "question": "find 命令查找大文件", "expected_doc": "file-permissions", "expected_keywords": ["find", "size"]},
    {"id": "SEC-008", "category": "security", "question": "chmod 755 是什么意思", "expected_doc": "file-permissions", "expected_keywords": ["chmod", "755", "权限"]},
    {"id": "PERF-005", "category": "performance", "question": "strace 怎么跟踪进程", "expected_doc": "slow-response", "expected_keywords": ["strace", "系统调用"]},
    {"id": "PERF-006", "category": "performance", "question": "ab 压力测试工具怎么用", "expected_doc": "slow-response", "expected_keywords": ["ab", "压测"]},
    {"id": "PERF-007", "category": "performance", "question": "怎么分析应用程序性能瓶颈", "expected_doc": "slow-response", "expected_keywords": ["perf", "火焰图", "热点"]},
    {"id": "CRS-004", "category": "cross", "question": "服务器重启后服务没自启", "expected_doc": "service-unavailable", "expected_keywords": ["systemctl", "enable"]},
    {"id": "CRS-005", "category": "cross", "question": "crontab 定时任务不执行", "expected_doc": "process-management", "expected_keywords": ["cron", "crontab"]},
    {"id": "CRS-006", "category": "cross", "question": "系统时间不对怎么同步", "expected_doc": "service-unavailable", "expected_keywords": ["ntp", "时间同步"]},
    {"id": "CRS-007", "category": "cross", "question": "yum install 安装失败", "expected_doc": "service-unavailable", "expected_keywords": ["yum", "安装"]},
    {"id": "CRS-009", "category": "cross", "question": "SELinux 导致权限问题", "expected_doc": "file-permissions", "expected_keywords": ["SELinux", "权限"]},
    {"id": "CRS-010", "category": "cross", "question": "如何查看系统运行时间", "expected_doc": "process-management", "expected_keywords": ["uptime", "运行时间"]},
    {"id": "CRS-011", "category": "cross", "question": "如何查看当前登录用户", "expected_doc": "process-management", "expected_keywords": ["who", "w", "登录用户"]},
    {"id": "CRS-012", "category": "cross", "question": "如何查看系统发行版信息", "expected_doc": "service-unavailable", "expected_keywords": ["cat /etc/os-release", "uname"]},
]

data.extend(more)
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Total: {len(data)}")
