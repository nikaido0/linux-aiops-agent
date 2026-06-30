# 内存使用率过高处理方案

## 问题描述
内存使用率持续超过 85% 会导致频繁 GC、OOM（Out Of Memory）、系统使用 Swap 性能急剧下降。

## 排查步骤

### 1. 查看内存使用
```bash
# 总体内存使用
free -h
cat /proc/meminfo

# 进程内存排行
ps aux --sort=-%mem | head -10
top -o %MEM

# 查看 Swap 使用
swapon --show
vmstat 1 5
```

### 2. 检查 OOM 日志
```bash
# 查看 OOM Killer 记录
dmesg | grep -i oom
journalctl -k | grep -i oom

# 系统日志
grep -i "out of memory" /var/log/syslog
```

### 3. 分析进程内存详情
```bash
# 进程内存映射
pmap -x <PID>
cat /proc/<PID>/status | grep -E "VmRSS|VmSize|VmSwap"

# 查看内存页
smem -t -p -k
```

## 常见原因

### 内存泄漏
- 内存使用率持续缓慢上升
- Full GC 后内存无法释放
- **处理**: 重启释放 → dump 堆转储 → 用 MAT 分析

### 流量突增
- 内存突然升高，与流量同步
- GC 能回收大部分内存
- **处理**: 扩容实例 → 优化缓存 → 增加内存配置

### 缓存配置不当
- 缓存占用内存过大
- 缓存命中率低
- **处理**: 调整缓存上限 → 设置合理 TTL → LRU 淘汰

### JVM 参数不合理
- 堆内存配置过小
- GC 频率过高
- **处理**: 调整 -Xmx/-Xms → 优化 GC 算法

## 命令速查
```bash
# 内存监控
free -h               # 内存总量/已用/可用
vmstat 1 5            # 内存换页统计
smem -t -k            # 更准确的内存统计

# 进程分析
pmap -x <PID>         # 进程内存映射
cat /proc/<PID>/smaps # 进程内存详情
lsof -p <PID>         # 进程打开的文件

# 系统限制
ulimit -a             # 查看系统资源限制
sysctl vm.overcommit_memory  # 内存过载策略
```
