# Linux 文件权限与管理

## 权限基础
```bash
# 查看
ls -l                    # -rwxr-xr-x 1 root root 1234 Jun 30 10:00 file
#         ↑ ↑↑ ↑↑↑
#       类型 用户 组 其他人
#         d=目录 l=链接

# 修改
chmod 755 file           # rwxr-xr-x
chmod u+x file           # 给用户加执行权
chown user:group file    # 修改所有者
```

## 常见问题

### Permission Denied
- 执行文件没加 x 权限: `chmod +x script.sh`
- 目录没有 r 权限: `chmod +r /path`（不能 ls）
- 目录没有 x 权限: `chmod +x /path`（不能 cd）

### 权限数字速查
```
r=4, w=2, x=1
rwx=7, rw-=6, r-x=5, r--=4
755 = rwxr-xr-x   (常见可执行文件)
644 = rw-r--r--   (常见普通文件)
600 = rw-------   (密钥文件)
700 = rwx------   (脚本)
```

### SSH 密钥权限
```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
chmod 600 ~/.ssh/id_rsa        # 私钥
chmod 644 ~/.ssh/id_rsa.pub    # 公钥
```
权限不对 SSH 会直接拒绝连接。

### 查找特殊权限文件
```bash
find / -perm -4000 -type f     # SUID（以所有者身份执行）
find / -perm -2000 -type f     # SGID
find / -nouser -o -nogroup     # 孤立的文件（所有者已被删除）
```

### ACL（扩展权限）
```bash
setfacl -m u:user:rwx /path    # 给特定用户权限
getfacl /path                   # 查看 ACL
setfacl -b /path                # 清除 ACL
```
