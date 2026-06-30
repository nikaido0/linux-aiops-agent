# Linux 防火墙与 iptables 管理

## 常用命令
```bash
# 查看规则
iptables -L -n -v                # 详细规则列表
iptables -S                      # 规则脚本格式

# 开放端口
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 封禁 IP
iptables -A INPUT -s 10.0.0.100 -j DROP

# 保存规则
iptables-save > /etc/iptables/rules.v4
iptables-restore < /etc/iptables/rules.v4
```

## firewalld (CentOS/RHEL)
```bash
firewall-cmd --list-all
firewall-cmd --add-port=8080/tcp --permanent
firewall-cmd --reload
firewall-cmd --zone=public --add-service=http --permanent
```

## 常见问题

### 端口开了但连不上
- 检查 `iptables -L -n` 确认规则顺序（第一条匹配生效）
- 检查 SELinux: `getenforce`, `setenforce 0` 临时关闭测试
- 检查服务监听: `ss -tlnp | grep <port>`

### Docker 导致 iptables 混乱
- Docker 会自动插入 iptables 规则
- `DOCKER-USER` 链用于自定义规则，不会被 Docker 覆盖
- 重启 Docker 会重置 iptables

### conntrack 表满
- 症状: `nf_conntrack: table full, dropping packet`
- 查看: `sysctl net.netfilter.nf_conntrack_max`
- 临时: `sysctl -w net.netfilter.nf_conntrack_max=1048576`
- 持久化: 写入 `/etc/sysctl.conf`
