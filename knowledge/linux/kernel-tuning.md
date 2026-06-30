# Linux 内核参数调优

## 查看当前参数
```bash
sysctl -a                     # 所有参数
cat /proc/sys/vm/swappiness   # 单个参数
```

## 内存相关

### swappiness（内存换出倾向）
```bash
# 默认 60，越小越少用 swap
sysctl -w vm.swappiness=10
# 持久化: /etc/sysctl.conf
```

### OOM 行为
```bash
# 0=默认, 1=总是触发, 2=根据内存比例触发
sysctl -w vm.overcommit_memory=1
sysctl -w vm.overcommit_ratio=80

# 每个进程的 OOM 权重
echo -1000 > /proc/<PID>/oom_score_adj  # 禁止 OOM 杀死
echo 1000 > /proc/<PID>/oom_score_adj   # 优先 OOM 杀死
```

## 网络相关

### conntrack 连接跟踪
```bash
# 查看当前状态
sysctl net.netfilter.nf_conntrack_count
sysctl net.netfilter.nf_conntrack_max

# 调大连接跟踪表（默认 65536，服务器建议 1048576）
sysctl -w net.netfilter.nf_conntrack_max=1048576

# 缩短超时时间
sysctl -w net.netfilter.nf_conntrack_tcp_timeout_established=600
```

### TIME_WAIT 优化
```bash
# 缩短 TIME_WAIT（默认 60 秒）
sysctl -w net.ipv4.tcp_fin_timeout=15

# 开启 TIME_WAIT 复用
sysctl -w net.ipv4.tcp_tw_reuse=1

# 调整端口范围
sysctl -w net.ipv4.ip_local_port_range="1024 65535"
```

### 文件描述符
```bash
# 查看当前限制
ulimit -n
cat /proc/sys/fs/file-max

# 调大
ulimit -n 65535
# 持久化: /etc/security/limits.conf
# * soft nofile 65535
# * hard nofile 65535
```
