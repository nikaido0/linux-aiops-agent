# 网络故障排查方案

## 问题描述
网络故障会导致服务不可访问、连接超时、丢包、DNS 解析失败等。

## 排查步骤

### 1. 检查网络连通性
```bash
# 基础连通性测试
ping -c 5 <target>
ping -c 5 -s 1472 <target>  # 测试 MTU

# 路由追踪
traceroute <target>
mtr <target>            # 增强版路由追踪

# 端口连通性
nc -zv <host> <port>
telnet <host> <port>
timeout 3 bash -c "echo >/dev/tcp/<host>/<port>" && echo "open" || echo "closed"
```

### 2. 查看网络接口和连接
```bash
# 网络接口状态
ip addr show
ip link show
ethtool <interface>

# 查看网络连接
ss -tlnp               # 监听端口
ss -tan | grep ESTAB   # 已建立连接
ss -tan | awk '{print $1}' | sort | uniq -c  # 连接状态统计

# 连接数统计
netstat -ant | wc -l
ss -s                  # 连接统计摘要
```

### 3. DNS 排查
```bash
# DNS 解析测试
nslookup <domain>
dig <domain> +short
host <domain>

# DNS 缓存
systemd-resolve --statistics  # systemd-resolved
```

### 4. 防火墙和 iptables
```bash
# 防火墙规则
iptables -L -n -v
iptables -S
nft list ruleset

# Firewalld
firewall-cmd --list-all
firewall-cmd --list-ports
```

## 常见原因

### DNS 解析失败
- 域名无法解析为 IP
- **处理**: 检查 DNS 配置 → 切换 DNS 服务器 → 检查 /etc/resolv.conf

### 防火墙拦截
- 特定端口无法访问
- **处理**: 检查 iptables 规则 → `iptables -I INPUT -p tcp --dport <port> -j ACCEPT`

### 路由错误
- traceroute 显示路由中断
- **处理**: 检查路由表 `ip route show` → 修正默认网关

### MTU 问题
- 大包不通，小包正常
- **处理**: `ip link set mtu 1400 <interface>` → 调整 MTU

### 带宽饱和
- 网络延迟高，丢包率上升
- **处理**: `nload` 查看流量 → `tc` 限流 → 扩容带宽

## 命令速查
```bash
ping <host>             # ICMP 连通性
traceroute <host>       # 路由路径
mtr <host>              # 实时路由+丢包
ss -tlnp               # 监听端口
ss -tan                # TCP 连接
ip addr show           # IP 地址
ip route show          # 路由表
nslookup <domain>      # DNS 查询
dig <domain>           # 详细 DNS 查询
curl -v http://<host>  # HTTP 测试
nc -zv <host> <port>   # 端口扫描
tcpdump -i eth0        # 抓包分析
nload                  # 实时带宽
iftop                  # 连接带宽排行
```
