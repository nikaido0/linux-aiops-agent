# CPU 使用率过高处理方案

## 问题描述
CPU 使用率持续超过 80% 会导致系统响应变慢、请求超时，严重时可能触发雪崩效应。

## 排查步骤

### 1. 查看系统负载
```bash
# 查看整体 CPU 负载
top
htop

# 查看 CPU 核心使用情况
mpstat -P ALL 1 5

# 查看进程 CPU 占用
ps aux --sort=-%cpu | head -10
pidstat -u 1 5
```

### 2. 定位高消耗进程
top 输出说明：
- `%CPU` — 进程 CPU 使用率
- `TIME+` — 进程累计 CPU 时间
- `COMMAND` — 进程名

重点关注：
- 单个进程 CPU 占用接近 100% → 可能是死循环
- 多个进程 CPU 均匀升高 → 可能是流量突增

### 3. 查看详细线程信息
```bash
# 查看进程内各线程 CPU 占用
top -H -p <PID>
ps -T -p <PID>
```

### 4. 分析系统日志
```bash
# 查看系统日志
dmesg | tail -50
journalctl -k --since "5 min ago"
```

## 常见原因

### 死循环或无限递归
- 单个进程 CPU 占用接近 100%
- 应用日志有大量重复错误堆栈
- **处理**: 重启服务 → 定位代码问题 → 修复部署

### 流量突增
- 多个进程 CPU 均匀升高
- 请求量明显增加
- **处理**: 扩容实例 → 检查流量来源 → 启用限流

### 定时任务重叠
- CPU 使用率周期性升高
- crontab 任务执行时间重叠
- **处理**: 调整任务时间 → 加互斥锁

### 数据库慢查询
- 应用 CPU 高但业务逻辑简单
- MySQL 慢查询日志增长
- **处理**: 分析慢 SQL → 加索引 → 优化查询

## 命令速查
```bash
# 实时监控
top                    # 进程视图（按 P 按 CPU 排序）
htop                   # 增强版 top
mpstat 1              # 每核 CPU 使用率
sar -u 1 5            # 历史 CPU 数据

# 进程分析
ps -eo pid,ppid,cmd,%cpu,%mem --sort=-%cpu | head
pidstat -p <PID> 1    # 单进程监控
strace -p <PID>       # 跟踪系统调用

# 性能分析
perf top              # 实时性能分析
perf record -g -p <PID>  # 采样热点
```
