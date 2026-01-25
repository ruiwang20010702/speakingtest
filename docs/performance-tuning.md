# 性能调优指南

本文档提供 AI 口语测评系统的性能分析和调优建议。

## 系统瓶颈分析

### 核心瓶颈：AI 评测吞吐量

**问题描述**：
- Qwen API 限制：omni 模型 60 RPM（每分钟请求数）
- 单消费者吞吐：约 1 QPS（每秒 1 条评测）
- 500 并发学生提交 → 需要约 8 分钟才能全部完成评测

**数学计算**：
```
单消费者吞吐 = 60 RPM ÷ 60 秒 = 1 QPS
500 条任务 ÷ 1 QPS = 500 秒 ≈ 8.3 分钟
```

### 容量规划参考

| 目标 QPS | 需要消费者数 | Qwen 账号要求 | 预计延迟 |
|---------|-------------|--------------|----------|
| 5 QPS   | 5 个        | 300 RPM      | 100 秒/500任务 |
| 10 QPS  | 10 个       | 600 RPM      | 50 秒/500任务 |
| 20 QPS  | 20 个       | 1200 RPM     | 25 秒/500任务 |

---

## 配置调优

### 1. Qwen API 并发配置

根据账号配额调整以下环境变量：

```bash
# qwen3-omni-flash（音频评测）
QWEN_OMNI_CONCURRENCY=5      # 最大并发数
QWEN_OMNI_RPM=60             # 每分钟请求数

# qwen-plus（文本分析）
QWEN_PLUS_CONCURRENCY=10     # 最大并发数
QWEN_PLUS_RPM=600            # 每分钟请求数
```

**调整建议**：
- 联系阿里云提升账号配额
- 配合提升 `QWEN_OMNI_RPM` 和 `QWEN_OMNI_CONCURRENCY`
- 注意：并发数 ≤ RPM / 60

### 2. 消息队列配置

```bash
# 消费者预取倍数
QUEUE_PREFETCH_MULTIPLIER=1  # prefetch = concurrency * multiplier

# 压测模式（⚠️ 仅限测试环境）
QUEUE_DISABLE_SLEEP=false    # true 时禁用限速 sleep
```

### 3. 数据库连接池

```bash
DB_POOL_SIZE=30       # 基础连接池大小
DB_MAX_OVERFLOW=70    # 最大溢出连接数（总计 100）
```

**500 并发建议**：
```bash
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
```

### 4. 上传并发限制

```bash
UPLOAD_MAX_CONCURRENT=20   # 最大并发上传数
UPLOAD_MAX_SIZE_MB=20      # 单文件最大大小
```

**高并发场景建议**：
- 增加 `UPLOAD_MAX_CONCURRENT` 到 50
- 确保服务器内存充足（每个上传最多占用 20MB）

---

## 数据库优化

### 索引策略

系统已添加以下组合索引以优化常见查询：

| 表 | 索引 | 用途 |
|----|------|------|
| `users` | `(role, status)` | 后台教师/学生列表 |
| `tests` | `(student_id, status)` | 学生测评列表 |
| `tests` | `(student_id, status, created_at)` | 带时间排序的列表 |
| `test_items` | `(test_id, question_no)` | 题目详情查询 |
| `verification_codes` | `(email, code, is_used, expires_at)` | 登录验证 |
| `student_entry_tokens` | `(student_id, is_used, expires_at)` | 入口验证 |
| `report_share_tokens` | `(token, is_revoked, expires_at)` | 家长查看 |
| `audit_logs` | `(target_type, target_id, created_at)` | 安全审计 |

**应用索引**：

```bash
# 执行迁移脚本
psql -U postgres -d speakingtest -f database/migrations/003_add_performance_indexes.sql
```

### 数据清理

定期清理过期数据，避免表膨胀：

```bash
# 预览模式
python scripts/cleanup_expired_data.py --dry-run

# 实际执行
python scripts/cleanup_expired_data.py

# 只清理指定表
python scripts/cleanup_expired_data.py --tables verification_codes,student_entry_tokens
```

**清理策略**：

| 表 | 保留策略 | 默认天数 |
|----|----------|---------|
| `verification_codes` | 过期/已用 | 7 天 |
| `student_entry_tokens` | 过期/已用 | 30 天 |
| `report_share_tokens` | 过期+已撤销 | 90 天 |
| `audit_logs` | 时间 | 365 天（需显式启用） |

**Cron 定时任务**：

```bash
# 每天凌晨 3 点执行清理
0 3 * * * cd /path/to/backend && python scripts/cleanup_expired_data.py >> /var/log/cleanup.log 2>&1
```

### 只读连接优化

系统提供两种数据库连接方式：

```python
from src.infrastructure.database import get_db, get_db_readonly

# 写操作（自动 commit）
@router.post("/users")
async def create_user(db: AsyncSession = Depends(get_db)):
    ...

# 读操作（不 commit，性能更好）
@router.get("/users")
async def get_users(db: AsyncSession = Depends(get_db_readonly)):
    ...
```

### 缓存策略

统计接口使用 Redis 缓存（5 分钟 TTL）：

```python
from src.infrastructure.cache import cache_get, cache_set

# 检查缓存
cached = await cache_get("stats:overview")
if cached:
    return cached

# 计算并缓存
result = await compute_stats()
await cache_set("stats:overview", result, ttl=300)
```

---

## 水平扩容指南

### 方式一：增加消费者实例

1. **修改消费者启动脚本**：

```bash
# 启动多个 Part1 消费者
python scripts/part1_worker.py &
python scripts/part1_worker.py &
python scripts/part1_worker.py &

# 启动多个 Part2 消费者
python scripts/part2_worker.py &
python scripts/part2_worker.py &
python scripts/part2_worker.py &
```

2. **使用 Supervisor 管理**：

```ini
[program:part2_worker]
command=python scripts/part2_worker.py
numprocs=5
process_name=%(program_name)s_%(process_num)02d

[program:dlq_worker]
command=python scripts/dlq_worker.py
numprocs=1
process_name=%(program_name)s
```

### 方式二：增加 API 实例

1. **使用 Gunicorn 多 worker**：

```bash
gunicorn src.infrastructure.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
```

2. **使用 Nginx 负载均衡**：

```nginx
upstream backend {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
    server 127.0.0.1:8004;
}
```

---

## 性能监控

### 关键指标

| 指标 | 健康阈值 | 告警阈值 |
|------|---------|---------|
| 队列积压 | < 100 | > 500 |
| 评测延迟 | < 60s | > 180s |
| API 响应时间 | < 200ms | > 1000ms |
| 数据库连接使用率 | < 80% | > 90% |
| Redis 内存使用 | < 70% | > 85% |

### 监控命令

```bash
# RabbitMQ 队列状态
rabbitmqctl list_queues name messages consumers

# PostgreSQL 连接数
SELECT count(*) FROM pg_stat_activity;

# Redis 内存使用
redis-cli info memory
```

---

## 压测建议

### 测试环境配置

```bash
# 启用压测模式（禁用消费者 sleep）
QUEUE_DISABLE_SLEEP=true

# 提高数据库连接池
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100

# 提高上传并发
UPLOAD_MAX_CONCURRENT=50
```

### Locust 压测示例

```python
from locust import HttpUser, task, between

class StudentUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def submit_test(self):
        # 模拟提交测评
        self.client.post("/api/v1/tests/submit", ...)
```

### 性能基准

| 场景 | 目标 | 实际 | 状态 |
|------|------|------|------|
| API 吞吐（无评测）| 500 QPS | TBD | ⏳ |
| 评测吞吐（单消费者）| 1 QPS | 1 QPS | ✅ |
| 评测吞吐（5 消费者）| 5 QPS | TBD | ⏳ |
| 上传并发 | 50 并发 | TBD | ⏳ |

---

## 常见问题

### Q1: 评测队列持续积压怎么办？

**解决方案**：
1. 增加消费者实例数
2. 联系阿里云提升 Qwen 账号配额
3. 考虑批量处理优化

### Q2: 数据库连接耗尽怎么办？

**解决方案**：
1. 增加 `DB_POOL_SIZE` 和 `DB_MAX_OVERFLOW`
2. 检查是否有慢查询（开启 SQL echo）
3. 考虑读写分离

### Q3: 内存使用过高怎么办？

**解决方案**：
1. 减少 `UPLOAD_MAX_CONCURRENT`
2. 检查是否有内存泄漏
3. 增加服务器内存

---

## 总结

### 核心结论

1. **AI 评测是系统瓶颈**：受 Qwen API RPM 限制，单消费者约 1 QPS
2. **500 QPS 目标**：需要提升 Qwen 账号配额 + 多消费者实例
3. **API 层可水平扩容**：通过增加 API 实例和负载均衡实现
4. **数据库和 Redis 是支撑**：需要合理配置连接池和缓存

### 优化优先级

1. 🔴 **高优先级**：提升 Qwen 账号配额
2. 🟡 **中优先级**：增加消费者实例
3. 🟢 **低优先级**：数据库优化、缓存优化
