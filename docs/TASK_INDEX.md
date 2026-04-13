# 任务索引与状态看板

> 此文件是任务执行的总索引，每次完成任务后更新状态。
> 详细的任务定义见 `docs/tasks/<task_id>.yaml`。

## 统计

| 状态 | Haiku | Sonnet | Opus | 合计 |
|------|:-----:|:------:|:----:|:----:|
| pending | 1 | 1 | 1 | 3 |
| in_progress | 0 | 0 | 0 | 0 |
| completed | 1 | 0 | 0 | 1 |
| blocked | 0 | 0 | 0 | 0 |

**Token 预算累计**：~51k tokens（预估） / ~23.5k tokens（实际，已完成 1/4）

---

## Phase 1 — 地基

### 基础设施 (infra)

| ID | 标题 | 模型 | 依赖 | 预算 | 状态 |
|----|------|:----:|------|:----:|:----:|
| [P1-01-01](tasks/P1-01-01.yaml) | 初始化后端项目脚手架 | haiku | - | 11k | ✅ completed |
| [P1-01-02](tasks/P1-01-02.yaml) | 初始化 docker-compose 开发环境 | haiku | P1-01-01 | 9k | pending |
| [P1-02-01](tasks/P1-02-01.yaml) | 实现数据库会话与基础模型 | sonnet | P1-01-01 | 14k | pending |
| [P1-03-01](tasks/P1-03-01.yaml) | 实现多租户上下文与 ORM 自动过滤 | opus | P1-02-01 | 17k | pending |
| P1-03-02 | 租户中间件与 FastAPI 依赖集成 | sonnet | P1-03-01 | — | TBD |
| P1-04-01 | JWT 认证核心 | sonnet | P1-02-01 | — | TBD |
| P1-04-02 | Redis 缓存客户端 + 租户隔离 | haiku | P1-03-01 | — | TBD |
| P1-04-03 | 自研 OAuth2 授权端点 | opus | P1-04-01 | — | TBD |
| P1-04-04 | RBAC 权限依赖注入 | sonnet | P1-04-01 | — | TBD |
| P1-04-05 | API Key 认证 | haiku | P1-04-01 | — | TBD |

### 系统管理 (system) — 契约优先

| ID | 标题 | 模型 | 依赖 | 预算 | 状态 |
|----|------|:----:|------|:----:|:----:|
| P1-00-01 | 生成 system 模块契约 (schemas + sql + protocols) | opus | - | — | TBD |
| P1-05-01 | system 模块 SQLAlchemy 模型 | haiku | P1-00-01, P1-02-01 | — | TBD |
| P1-05-02 | system 模块 Pydantic schemas | haiku | P1-00-01 | — | TBD |
| P1-05-03 | user_service 实现 | sonnet | P1-05-01, P1-04-01 | — | TBD |
| P1-05-04 | role_service 实现 | sonnet | P1-05-01 | — | TBD |
| P1-05-05 | menu_service 实现 | haiku | P1-05-01 | — | TBD |
| P1-05-06 | dept_service 实现 | haiku | P1-05-01 | — | TBD |
| P1-05-07 | tenant_service 实现 | sonnet | P1-05-01 | — | TBD |
| P1-05-08 | auth_service 实现（登录/登出/刷新） | sonnet | P1-04-03 | — | TBD |
| P1-05-09 | audit_service 实现（审计日志） | haiku | P1-05-01 | — | TBD |
| P1-05-10 | system controllers (admin) × 7 | haiku | P1-05-03..09 | — | TBD |
| P1-05-11 | system 模块集成测试 | sonnet | P1-05-10 | — | TBD |
| P1-05-12 | 种子数据脚本（初始租户+超管） | haiku | P1-05-10 | — | TBD |

### 设备管理 (device) — 最小可用

| ID | 标题 | 模型 | 依赖 | 预算 | 状态 |
|----|------|:----:|------|:----:|:----:|
| P1-06-00 | 生成 device 模块契约 | sonnet | - | — | TBD |
| P1-06-01 | device 模块 SQLAlchemy 模型 | haiku | P1-06-00 | — | TBD |
| P1-06-02 | device 模块 Pydantic schemas | haiku | P1-06-00 | — | TBD |
| P1-06-03 | device_service 实现 | sonnet | P1-06-01 | — | TBD |
| P1-06-04 | heartbeat_service 实现 | sonnet | P1-06-01, P1-04-02 | — | TBD |
| P1-06-05 | device admin controller | haiku | P1-06-03 | — | TBD |
| P1-06-06 | MQTT 客户端核心封装 | sonnet | P1-01-02 | — | TBD |
| P1-06-07 | device MQTT 消费者（心跳/状态/IP） | sonnet | P1-06-04, P1-06-06 | — | TBD |
| P1-06-08 | EMQX 内部 HTTP Auth/ACL 端点 | sonnet | P1-06-03 | — | TBD |
| P1-06-09 | device 生命周期集成测试 | sonnet | P1-06-07, P1-06-08 | — | TBD |

---

## Phase 2 — 数据打通（待拆分）

- telemetry 模块（约 10 个任务）
- alarm 模块（约 8 个任务）
- image 上传核心（约 6 个任务）
- edge agent 基础版（约 8 个任务）

## Phase 3 — CVAT 闭环（待拆分）

- CVAT 对接服务（约 5 个任务）

## Phase 4 — 业务落地（待拆分）

- weighbridge（约 12 个任务）
- appointment（约 8 个任务）
- dispatch（约 8 个任务）
- 业务闭环 E2E（约 3 个任务）

## Phase 5 — 平台化（待拆分）

- frontend（约 25 个任务）
- 开放平台 + Webhook（约 5 个任务）
- 安全加固（约 6 个任务）
- 可观测性（约 6 个任务）

---

## 使用方式

### 启动一个任务

复制以下 prompt，把 `<TASK_ID>` 换成任务编号：

```
执行任务 <TASK_ID>。

严格遵守：
1. 只读取 docs/tasks/<TASK_ID>.yaml 中 contracts 和 context_files 列出的文件
2. 禁止 grep 全仓库、禁止读其他模块代码
3. 严格按 contracts 定义实现，不偏离
4. 生成 produces 中的所有文件
5. 生成 acceptance.tests 中的测试
6. 运行 acceptance.commands，全部通过才算完成
7. 完成后更新 docs/tasks/<TASK_ID>.yaml 的 status=completed 并回填 actual_tokens
8. 更新 docs/TASK_INDEX.md 的状态

不做 requirements 之外的任何事。
```

### 模型选择

- `haiku` 任务 → 启动时显式指定 `/model haiku` 或在 prompt 中声明
- `sonnet` 任务 → 默认（4.6 Sonnet）
- `opus` 任务 → 启动时 `/model opus`

### 任务失败处理

1. 失败 1 次 → 检查 requirements 是否清晰、契约是否完整
2. 失败 2 次 → 升级模型（haiku→sonnet→opus）
3. 仍失败 → 拆分任务或补充契约

---

_此文件每次任务完成后更新。_
