# SSH 远程访问故障排查

## 常用命令
```bash
# 服务端
systemctl status sshd
ss -tlnp | grep :22
journalctl -u sshd -n 50 --no-pager

# 客户端调试
ssh -vvv user@host            # 详细调试输出
ssh-keygen -R hostname        # 清除已知主机密钥
```

## 常见问题

### Connection Refused
- SSH 服务没启动: `systemctl start sshd`
- 端口不对: 检查 `/etc/ssh/sshd_config` 中的 `Port`
- 防火墙拦截: `iptables -L -n | grep :22`

### Permission Denied (publickey)
- 密钥不匹配: 检查 `~/.ssh/authorized_keys`
- 权限错误: `~/.ssh` 应为 700，`authorized_keys` 应为 600
- SELinux 拦截: `restorecon -Rv ~/.ssh`

### Too many authentication failures
- 错误尝试过多，IP 被临时封禁
- **处理**: 等几分钟或 `systemctl restart sshd`
- `/etc/ssh/sshd_config` 中 `MaxAuthTries` 控制重试次数

### 连接慢（卡住几秒）
- DNS 反向查询: `UseDNS no` 加到 sshd_config
- GSSAPI 认证: `GSSAPIAuthentication no`

### 安全加固
```bash
# /etc/ssh/sshd_config 推荐配置
Port 2222                          # 改默认端口
PasswordAuthentication no          # 禁止密码登录
PermitRootLogin prohibit-password  # 禁止 root 密码登录
MaxAuthTries 3                     # 最多 3 次尝试
ClientAliveInterval 300            # 5 分钟心跳
```
