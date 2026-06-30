# Docker 容器问题排查

## 常用命令
```bash
# 查看容器状态
docker ps -a                    # 所有容器
docker stats                    # 实时资源占用
docker logs <container> --tail 100

# 查看镜像磁盘占用
docker system df
docker system prune -a -f       # 清理所有未使用资源

# 进入容器调试
docker exec -it <container> /bin/bash
docker inspect <container>      # 查看容器详情
```

## 常见问题

### 容器频繁重启
- **排查**: `docker ps --filter "status=exited"` 查看退出码
- **日志**: `docker logs <container> --tail 50`
- **处理**: 退出码 137 = SIGKILL(OOM), 139 = SIGSEGV(段错误), 143 = SIGTERM(正常停止)

### 磁盘空间暴涨
- Docker 默认日志驱动不限制大小，长期运行会占满磁盘
- **处理**: 配置 `/etc/docker/daemon.json`:
  ```json
  {"log-opts": {"max-size": "10m", "max-file": "3"}}
  ```

### 容器无法连网
- 检查网络模式: `docker network ls`
- 检查 DNS 配置: `/etc/docker/daemon.json` 的 dns 字段
- 检查 iptables: Docker 依赖 iptables 做网络转发
