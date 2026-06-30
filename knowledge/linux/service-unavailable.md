# 服务不可用处理方案

## 问题描述
服务不可用是最严重的故障，会导致用户无法访问、业务完全中断。

## 排查步骤

### 1. 检查服务状态
```bash
# Systemd 服务状态
systemctl status <service-name>
systemctl list-units --failed

# 监听端口
ss -tlnp
netstat -tlnp

# 进程检查
ps aux | grep <service-name>
pgrep -a <service-name>
```

### 2. 查看服务日志
```bash
# Journalctl 日志
journalctl -u <service-name> --since "15 min ago" -n 100
journalctl -u <service-name> -p err --since "15 min ago"

# 应用日志
tail -200 /var/log/<service>/error.log
less /var/log/<service>/app.log
```

### 3. 检查系统资源
```bash
# 磁盘和 inode
df -h
df -i

# 内存
free -h

# 文件描述符
cat /proc/sys/fs/file-nr
ulimit -n
```

### 4. 检查依赖服务
```bash
# 数据库连接测试
mysqladmin -h <host> -u <user> ping
redis-cli ping

# 网络连通性
ping -c 3 <dependency-host>
curl -I http://<dependency>:<port>/health
```

## 常见原因

### 应用崩溃
- 进程不存在，systemctl status 显示 failed
- **处理**: `systemctl restart <service>` → 查看启动日志 → 回滚到稳定版本

### 端口被占用
- `ss -tlnp` 显示端口被其他进程占用
- **处理**: 杀死占用进程 → 修改端口配置

### 资源耗尽
- 磁盘满 / OOM / 文件描述符耗尽
- **处理**: 清理资源 → 重启服务 → 调整系统限制

### 配置错误
- 最近有配置变更，服务启动失败
- **处理**: 检查配置文件语法 → `systemctl daemon-reload` → 回滚配置

### 依赖服务故障
- 数据库、Redis、MQ 等不可用
- **处理**: 恢复依赖服务 → 切换备用实例 → 启用降级

## 命令速查
```bash
systemctl status <name>     # 服务状态
systemctl restart <name>    # 重启服务
journalctl -u <name> -f     # 跟踪服务日志
journalctl -u <name> -p err # 错误级别日志
ss -tlnp                    # 监听端口
lsof -i :<port>             # 端口占用进程
systemctl daemon-reload     # 重载配置
```
