# 服务响应时间过长处理方案

## 问题描述
P99 响应时间持续超过 3 秒会导致用户体验下降、请求堆积、超时错误扩散。

## 排查步骤

### 1. 查看系统资源使用
```bash
# CPU 和内存
top -bn1 | head -20
sar -u 1 5              # CPU 历史趋势
sar -r 1 5              # 内存历史趋势

# 磁盘 IO
iostat -x 1 5
iotop                   # 进程 IO 排行

# 网络
sar -n DEV 1 5          # 网络流量
```

### 2. 分析应用性能
```bash
# 进程级耗时分析
time curl http://localhost:<port>/api/health
ab -n 100 -c 10 http://localhost:<port>/  # 压力测试

# 系统调用跟踪
strace -f -T -p <PID> 2>&1 | head -50
perf top -p <PID>
```

### 3. 数据库慢查询分析
```bash
# MySQL 慢查询
mysql -e "SHOW VARIABLES LIKE 'slow_query%';"
mysql -e "SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10;"

# 当前运行中的查询
mysql -e "SHOW FULL PROCESSLIST;"

# 连接池状态
mysql -e "SHOW STATUS LIKE 'Threads_connected';"
mysql -e "SHOW STATUS LIKE 'Max_used_connections';"
```

## 常见原因

### 数据库慢查询
- 慢查询日志有大量记录
- 数据库 CPU 使用率高
- **处理**: `EXPLAIN ANALYZE <sql>` → 加索引 → 优化 JOIN → 读写分离

### 外部 API 调用超时
- 特定接口响应时间长
- 下游服务响应慢
- **处理**: 设置合理超时 → 熔断降级 → 异步化

### 代码性能问题
- CPU 使用率高但有明显热点
- **处理**: `perf top` 定位 → 优化算法 → 减少对象创建

### 缓存失效/穿透
- 缓存命中率突降
- 数据库查询激增
- **处理**: 缓存预热 → 布隆过滤器 → 空值缓存

### 资源不足
- CPU/内存/IO 任意一项达到瓶颈
- **处理**: 扩容实例 → 升级配置 → 限流保护

## 命令速查
```bash
# 性能排查
time <command>            # 命令耗时
top/htop                  # 进程 CPU 排行
iotop                     # 进程 IO 排行
strace -T -p <PID>        # 系统调用耗时
perf top                  # 性能热点
perf record -g -p <PID>    # 采样热点

# 压测工具
ab -n 1000 -c 50 <url>    # ApacheBench
wrk -t4 -c50 <url>        # 现代压测
http_load                 # 文件 URL 压测

# 数据库
mysql -e "SHOW PROCESSLIST"  # 当前查询
pt-query-digest /var/lib/mysql/slow.log  # 慢查询分析
```
