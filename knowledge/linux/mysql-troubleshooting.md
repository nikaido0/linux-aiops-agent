# MySQL 数据库运维

## 常用命令
```bash
# 状态检查
systemctl status mysql
mysqladmin ping
mysqladmin status

# 连接数
mysql -e "SHOW STATUS LIKE 'Threads_connected'"
mysql -e "SHOW STATUS LIKE 'Max_used_connections'"
mysql -e "SHOW VARIABLES LIKE 'max_connections'"

# 当前查询
mysql -e "SHOW FULL PROCESSLIST"

# 慢查询分析
mysql -e "SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10"
```

## 常见问题

### Too Many Connections
- 连接池耗尽，应用无法建立新连接
- **临时**: `mysqladmin -u root -p flush-hosts` 解封被锁主机
- **短期**: 调大 `max_connections = 500`
- **长期**: 检查应用连接池配置，用完及时释放

### 慢查询
- `long_query_time = 2` 记录超过 2 秒的查询
- `EXPLAIN SELECT ...` 查看执行计划，检查是否全表扫描
- 常见原因: 缺少索引、多表 JOIN 没索引、查询数据量太大

### 主从延迟
```bash
mysql -e "SHOW SLAVE STATUS\G" | grep -E "Seconds_Behind_Master|Slave_IO_Running|Slave_SQL_Running"
```
- `Seconds_Behind_Master` > 0 表示延迟
- 原因: 从库性能不足、大事务、网络延迟

### 死锁
```sql
SHOW ENGINE INNODB STATUS\G;
```
- 查看 LATEST DETECTED DEADLOCK 部分
- 原因: 两个事务互相等待对方释放锁
- 解决: 统一 SQL 中表的访问顺序，缩短事务时间
