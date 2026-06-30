# Nginx 故障排查

## 常用命令
```bash
# 状态检查
nginx -t                       # 测试配置语法
systemctl status nginx
ss -tlnp | grep 80             # 检查端口监听

# 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## 常见问题

### 502 Bad Gateway
- 上游服务挂了: 检查后端进程 `systemctl status <backend>`
- Unix socket 权限: `ls -la /var/run/php-fpm.sock`
- 超时配置: `proxy_read_timeout` 太短

### 504 Gateway Timeout
- 后端响应太慢 → 优化后端性能
- `proxy_read_timeout` 设置过短 → nginx.conf 中增大

### 413 Request Entity Too Large
- `client_max_body_size` 默认 1M，上传大文件需要增大

### 端口被占
```bash
ss -tlnp | grep :80
lsof -i :80
```
可能是另一个 nginx 进程或 Apache 占用。

### 配置示例
```nginx
server {
    listen 80;
    server_name example.com;
    client_max_body_size 100M;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_read_timeout 60s;
    }
}
```
