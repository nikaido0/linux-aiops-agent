# Linux 日志管理与 Logrotate

## 日志文件位置
```bash
/var/log/syslog          # 系统日志 (Ubuntu/Debian)
/var/log/messages        # 系统日志 (CentOS/RHEL)
/var/log/kern.log        # 内核日志（OOM、硬件错误）
/var/log/auth.log        # 认证日志（SSH、sudo）
/var/log/nginx/          # Nginx 访问和错误日志
/var/log/mysql/          # MySQL 日志
/var/log/dpkg.log        # 包管理器日志
```

## journalctl (systemd 日志)
```bash
journalctl -p err -n 20           # 最近 20 条错误
journalctl -u nginx --since "1h"  # 最近 1 小时 nginx 日志
journalctl -f                     # 实时跟踪
journalctl --disk-usage           # 查看日志占用磁盘
journalctl --vacuum-size=500M     # 限制日志占用 500MB
journalctl --vacuum-time=7d       # 只保留 7 天
```

## Logrotate 配置

```bash
# /etc/logrotate.d/nginx
/var/log/nginx/*.log {
    daily                   # 按天轮转
    rotate 7               # 保留 7 份
    compress               # 压缩旧日志
    delaycompress          # 延迟一天压缩
    missingok              # 文件不存在不报错
    notifempty             # 空文件不轮转
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```

## 常见问题

### 日志占满磁盘
- `du -sh /var/log/* | sort -rh | head -10` 找出大日志
- `find /var/log -name "*.gz" -delete` 清理压缩包
- 配置 logrotate 限制日志大小

### 日志不轮转
- 检查 logrotate 配置语法: `logrotate -d /etc/logrotate.d/app`
- 手动执行: `logrotate -f /etc/logrotate.d/app`
- 检查 cron: `ls -la /etc/cron.daily/logrotate`
