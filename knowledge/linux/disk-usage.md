# 磁盘使用率过高处理方案

## 问题描述
磁盘使用率过高会导致无法写入数据、日志丢失、应用崩溃、数据库损坏。

## 排查步骤

### 1. 查看磁盘使用情况
```bash
# 磁盘分区使用率
df -h
df -i                    # inode 使用情况

# 目录空间排行
du -sh /* 2>/dev/null | sort -rh | head -10
du -sh /var/log/* | sort -rh | head -10

# 查找大文件
find / -type f -size +1G -exec ls -lh {} \; 2>/dev/null
find / -type f -size +100M 2>/dev/null | xargs ls -lh | sort -k5 -rh | head -20
```

### 2. 检查日志文件
```bash
# 日志目录大小
du -sh /var/log/
ls -lhS /var/log/*.log | head -10

# 检查日志轮转
cat /etc/logrotate.conf
ls -la /etc/logrotate.d/
```

### 3. 检查进程打开的文件
```bash
# 查找已删除但未释放的文件（占用空间但 df 看不到）
lsof | grep '(deleted)'
lsof -nP +L1             # 查看链接数 0 的文件
```

## 常见原因

### 日志文件过大
- /var/log 占用大量空间
- 应用日志持续增长，没有轮转
- **处理**: `> /var/log/large.log` 清空 → 配置 logrotate → 调整日志级别

### 临时文件堆积
- /tmp 目录占用大
- 大量未清理的临时文件
- **处理**: `find /tmp -type f -mtime +7 -delete` → 定时清理

### Docker 镜像占用
```bash
docker system df            # 查看 Docker 磁盘使用
docker system prune -a      # 清理未使用资源
docker image prune -a       # 清理未使用镜像
```

### 数据文件增长过快
- 数据库文件持续增长
- 无数据归档策略
- **处理**: 归档历史数据 → 清理过期数据 → 扩容磁盘

## 命令速查
```bash
df -h                 # 磁盘分区使用
df -i                 # inode 使用
du -sh /path          # 目录总大小
du -sh * | sort -rh   # 目录下各项目大小
ncdu /path            # 交互式磁盘分析（需安装）
lsof | grep deleted   # 未释放的文件
find / -size +1G      # 查找大文件
fstrim -av            # SSD 回收未使用块
```
