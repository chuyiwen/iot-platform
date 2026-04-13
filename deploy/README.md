# 开发环境启动指南

## 前提条件

- Docker
- Docker Compose v2

## 快速启动

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，修改默认密码（建议用于开发环境）：

```
POSTGRES_USER=iot
POSTGRES_PASSWORD=iot_dev_pass
POSTGRES_DB=iot_platform
REDIS_PASSWORD=redis_dev_pass
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
```

### 2. 启动基础设施服务

```bash
docker compose up -d postgres redis minio
```

等待 healthcheck 通过（约 30-60 秒）。

### 3. 验证服务状态

```bash
docker compose ps
```

确保 postgres、redis、minio、createbuckets 均为 healthy 或 exited 状态。

### 4. 服务访问地址

| 服务 | 访问地址 | 备注 |
|------|---------|------|
| PostgreSQL | localhost:5432 | 用户名：iot |
| Redis | localhost:6379 | 需密码认证 |
| MinIO Console | http://localhost:9001 | 用户名：minioadmin |
| EMQX Dashboard | http://localhost:18083 | 默认用户名：admin |

### 5. 启动完整服务（含后端）

```bash
docker compose up -d
```

或指定 profile 方式：

```bash
docker compose --profile app up -d
```

## 停止服务

```bash
docker compose down
```

清除数据卷：

```bash
docker compose down -v
```

## 常见问题

- **postgres 无法启动**：检查 `.env` 中的密码是否为空或包含特殊字符，建议使用 alphanumeric 组合。
- **minio 创建 bucket 失败**：确保 minio 已完全启动，查看 createbuckets 日志：`docker compose logs createbuckets`
- **emqx 连接不到 backend**：确保 backend 服务已启动，检查网络配置。
