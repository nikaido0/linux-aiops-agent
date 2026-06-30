# Linux 进程管理

## 常用命令
```bash
# 查看进程
ps aux                           # 所有进程
ps aux --sort=-%cpu | head 10    # CPU 排行
ps aux --sort=-%mem | head 10    # 内存排行
ps -eo pid,ppid,cmd,%cpu,%mem --sort=-%cpu | head

# 进程树
pstree -p
ps auxf

# 实时监控
top -o %CPU                      # 按 CPU 排序
htop                             # 交互式
```

## 信号管理
```bash
kill -15 <PID>    # SIGTERM，优雅终止
kill -9 <PID>     # SIGKILL，强制杀死
kill -1 <PID>     # SIGHUP，重载配置
kill -3 <PID>     # SIGQUIT，生成线程堆栈

# 按名称杀
pkill -f "python script.py"
killall nginx
```

## 进程状态
```
R (running)      正在运行或可运行
S (sleeping)     等待事件完成
D (uninterrupt)  不可中断睡眠（通常是 IO）
Z (zombie)       僵死进程（父进程没回收）
T (stopped)      被暂停（Ctrl+Z）
```

## 僵尸进程处理
```bash
# 查看僵尸进程
ps aux | grep Z
ps -eo pid,stat,comm | grep Z

# 僵尸进程已经不能 kill，只能处理父进程
kill -15 <parent_pid>    # 先正常终止父进程
kill -9 <parent_pid>     # 不行就强制杀
# 父进程死了之后僵尸进程由 init 接管并回收
```

## 进程资源限制
```bash
# 查看进程限制
cat /proc/<PID>/limits
# 修改系统限制（/etc/security/limits.conf）
# * soft nofile 65535
# * hard nofile 65535
```
