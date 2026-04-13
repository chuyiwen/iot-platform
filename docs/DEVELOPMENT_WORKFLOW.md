# 开发工作流 — 契约驱动 + 原子任务 + 模型分级

> 目标：**用最少的 token 开发大型项目**。通过契约先行、任务原子化、上下文最小化，让每个开发任务只消耗 5k-15k tokens，而不是动辄 100k+。

---

## 一、核心原则

### 1.1 契约先行（Contract-First）

所有接口在编码前**一次性定义、全局只读**：

```
docs/contracts/
├── schemas/          # Pydantic VO/DTO (请求/响应模型)
│   ├── common.py     # 通用分页/响应/错误
│   ├── system.py     # 用户/角色/菜单/租户
│   ├── device.py     # 设备/分组/指令/OTA
│   ├── telemetry.py  # 遥测/告警规则/告警
│   ├── image.py      # 图像/CVAT/标注
│   ├── weighbridge.py
│   ├── appointment.py
│   └── dispatch.py
├── models/           # SQL 表结构 (DDL)
│   ├── 01_system.sql
│   ├── 02_device.sql
│   ├── 03_telemetry.sql
│   ├── 04_image.sql
│   ├── 05_weighbridge.sql
│   ├── 06_appointment.sql
│   └── 07_dispatch.sql
├── protocols/        # 跨模块 Protocol 接口 (依赖倒置)
│   ├── system_api.py   # UserInfoProvider, TenantProvider
│   ├── device_api.py   # DeviceQueryProvider
│   └── ...
├── api-spec.yaml     # OpenAPI 路径规范（路径+方法+请求/响应 schema ref）
├── mqtt-spec.md      # MQTT 主题与消息格式
├── errors.yaml       # 统一错误码
├── events.yaml       # 内部事件总线定义
└── permissions.yaml  # 权限标识清单
```

**规则**：
- ✅ 任务**只读**契约文件，**不可修改**
- ❌ 如需修改契约，必须先开 "契约变更任务"，所有依赖任务重审
- ✅ 契约变更独立 commit，commit message 前缀 `contract:`

### 1.2 任务原子化

**一个任务 = 一个 YAML 文件**，位于 `docs/tasks/` 下。每个任务必须满足：
- 单文件或少量文件产出（通常 <500 行代码）
- 明确声明依赖的契约文件
- 明确声明依赖的前置任务
- 有可执行的验收标准（pytest 或命令）
- 预估 token 预算（超过拆分）

### 1.3 上下文最小化

启动一个任务时，只加载：
1. 任务 YAML 本身（~1k tokens）
2. 任务声明的 `context_files`（通常 2-5 个文件，~3-8k tokens）
3. 任务声明的 `depends_on` 的产物（1-2 个文件，~2-4k tokens）

**禁止**：读整个项目、grep 全仓库、探索目录。

### 1.4 模型分级

| 模型 | 适用 | 占比目标 |
|------|------|---------|
| Haiku 4.5 | Pydantic schema、SQL DDL、CRUD 模板、单测样板、fixture、固定配置 | 80% |
| Sonnet 4.6 | Service 业务逻辑、Controller、集成测试、边缘采集器、前端页面 | 15% |
| Opus 4.6 | 多租户过滤器、数据权限、OAuth2、告警引擎、架构决策、疑难 bug | 5% |

---

## 二、任务 YAML 规范

### 2.1 Schema

```yaml
# docs/tasks/<task_id>.yaml
id: P1-05-03                        # 唯一编号，Phase-Module-Seq
title: 实现用户 Service 层
phase: 1                            # MS1 地基
module: system
model: sonnet                       # haiku | sonnet | opus
status: pending                     # pending | in_progress | completed | blocked

# 依赖声明
depends_on:
  - P1-02-01                        # 必须先完成的任务
  - P1-04-02

# 契约文件（只读）
contracts:
  - docs/contracts/schemas/system.py
  - docs/contracts/models/01_system.sql
  - docs/contracts/protocols/system_api.py
  - docs/contracts/errors.yaml
  - docs/contracts/permissions.yaml

# 依赖的产物文件（已由前置任务生成）
context_files:
  - backend/app/core/db/crud_base.py
  - backend/app/core/db/tenant_model.py
  - backend/app/core/security/auth.py

# 产出文件
produces:
  - backend/app/modules/system/service/user_service.py
  - backend/app/modules/system/dal/user_crud.py

# 实现目标（具体可验证）
requirements:
  - 实现 UserServiceProtocol 中声明的所有方法
  - 密码必须用 bcrypt 加密（使用 passlib）
  - 创建/更新用户时自动触发 AuditLog
  - 用户名在租户内唯一（数据库已有约束，此处做友好报错）
  - 违反业务规则时抛出 docs/contracts/errors.yaml 中定义的错误码

# 验收标准
acceptance:
  tests:
    - tests/unit/system/test_user_service.py
  commands:
    - pytest tests/unit/system/test_user_service.py -v
    - ruff check backend/app/modules/system/service/user_service.py
    - mypy backend/app/modules/system/service/user_service.py
  coverage: 85

# Token 预算（超了必须拆分）
token_budget:
  input: 10000                      # 上下文 + 提示词
  output: 4000                      # 生成代码
  total: 14000

# 备注
notes: |
  - 不需要读其他 service 文件
  - crud_base.py 已提供分页/软删/租户注入，直接使用
  - 参考 AuthService 中的密码处理方式（context_files 已包含）
```

### 2.2 任务拆分原则

如果一个任务的 `total` 预算超过 20k tokens，**必须拆分**：

- **按文件拆**：一个文件一个任务
- **按层拆**：schema/DAL/service/controller/test 各一个任务
- **按功能拆**：user 管理、role 管理、menu 管理各一个任务

---

## 三、模型分级规则

### 3.1 Haiku 4.5（80% 任务）

**判断标准**：任务 = 模板化填充，判断分支少，有明确样例可参考。

**典型任务**：
- 写 Pydantic schemas（字段定义）
- 写 SQL DDL
- 写 SQLAlchemy 模型（字段到 Python 类）
- 写 CRUDBase 子类（基本 CRUD 继承）
- 写基础 API controller（调用 service）
- 写单元测试样板（given/when/then）
- 写 Alembic 迁移脚本
- 写 fixtures
- 写 OpenAPI 响应示例
- 写国际化 JSON 文件
- 写 Docker Compose 条目
- 写 systemd 单元文件
- 写 Makefile targets

### 3.2 Sonnet 4.6（15% 任务）

**判断标准**：涉及业务规则、多分支、跨组件调用，但有明确契约约束。

**典型任务**：
- 实现业务 service 层（校验、规则、事务）
- 实现复杂 controller（组合多个 service）
- 写集成测试（testcontainers + 真实依赖）
- 实现 MQTT 消费者逻辑
- 实现 Celery 任务（含异常与重试）
- 实现边缘采集器（硬件交互 + 业务逻辑）
- 实现前端页面组件（状态管理 + 交互）
- 实现告警规则评估
- 实现 EMQX 认证回调
- 调试失败的集成测试

### 3.3 Opus 4.6（5% 任务）

**判断标准**：没有明确样例，涉及架构决策、全局一致性、复杂算法。

**典型任务**：
- 设计多租户过滤器（SQLAlchemy event）
- 设计数据权限引擎
- 设计自研 OAuth2（多授权模式）
- 设计告警规则引擎（条件组合 + 时间窗口）
- 设计 OTA 灰度发布算法
- 设计地磅稳重判定算法
- 排查跨多模块的性能问题
- 架构重构、契约重新设计
- 疑难 bug 定位（没有明显线索）

### 3.4 判断流程

```
1. 这个任务有没有相似样例？
   有 → 继续
   没有 → Opus

2. 会不会涉及 3+ 个文件的跨层逻辑？
   不会 → Haiku
   会 → 继续

3. 有没有复杂业务规则或算法？
   没有 → Sonnet
   有（难度中）→ Sonnet
   有（难度高）→ Opus
```

---

## 四、工作流

### 4.1 开发循环

```
┌─────────────────────────────────────────────────────────┐
│  1. 契约阶段（一次性，Opus）                             │
│     写完所有 docs/contracts/*，锁定接口                  │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  2. 任务生成阶段（Opus/Sonnet）                          │
│     将 ROADMAP 拆为 docs/tasks/*.yaml                   │
│     每个任务标注模型/依赖/上下文                          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  3. 任务执行阶段（按模型分发）                            │
│     for task in tasks:                                  │
│       spawn(model=task.model,                           │
│             context=task.contracts + task.context_files,│
│             prompt=task.requirements)                   │
│       run(task.acceptance.commands)                     │
│       if pass: mark_completed                          │
│       else: escalate_model_or_split                    │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  4. 集成验证阶段                                         │
│     跑 integration/e2e 测试                              │
│     发现契约问题 → 回到步骤 1                            │
└─────────────────────────────────────────────────────────┘
```

### 4.2 单个任务的 prompt 模板

启动任意任务时使用此模板（可复制到 Claude Code 中）：

```
执行任务 <TASK_ID>。

严格遵守以下规则：
1. 只读取 docs/tasks/<TASK_ID>.yaml 中 contracts 和 context_files 列出的文件
2. 禁止 grep 全仓库、禁止读取其他模块代码
3. 严格按 contracts 定义的 schema/protocol 实现
4. 生成 produces 列表中的文件
5. 生成 acceptance.tests 中的测试文件
6. 运行 acceptance.commands，全部通过后才算完成
7. 完成后更新 docs/tasks/<TASK_ID>.yaml 的 status 为 completed

不要做任何 requirements 之外的事情。
```

### 4.3 升级规则

- **任务失败 2 次** → 升级一档模型（Haiku → Sonnet → Opus）
- **升级后仍失败** → 拆分任务或回到契约阶段
- **上下文不够** → 检查契约是否有遗漏，补齐契约而非加大上下文

### 4.4 并行策略

任务之间无依赖时可并行：
- 同一 Phase 内同级别任务（比如 system 模块的 user/role/menu 的 schema 生成）并行给 3 个 Haiku
- 不同 Phase 的独立模块（比如 weighbridge 和 appointment）并行

---

## 五、Token 预算估算

### 5.1 单任务预算

| 任务类型 | 模型 | 输入 | 输出 | 单任务总计 |
|---------|------|------|------|-----------|
| Pydantic schema 生成 | Haiku | 3k | 2k | 5k |
| SQL DDL 生成 | Haiku | 2k | 3k | 5k |
| SQLAlchemy 模型 | Haiku | 4k | 3k | 7k |
| CRUD 类 | Haiku | 5k | 3k | 8k |
| 基础 Controller | Haiku | 6k | 3k | 9k |
| 单元测试 | Haiku | 6k | 4k | 10k |
| Service 业务层 | Sonnet | 10k | 5k | 15k |
| 集成测试 | Sonnet | 12k | 6k | 18k |
| 多租户过滤器 | Opus | 15k | 6k | 21k |
| 架构决策 | Opus | 20k | 8k | 28k |

### 5.2 全项目预估（粗略）

假设整个 IoT 平台拆为 **300 个原子任务**：
- Haiku × 240 任务 × 平均 7k = **1,680k tokens**
- Sonnet × 45 任务 × 平均 15k = **675k tokens**
- Opus × 15 任务 × 平均 25k = **375k tokens**

**总计 ~2.7M tokens**

**对比**：不做契约、不拆任务、单 Sonnet 线性开发，同规模项目 token 消耗约 **15M-25M**。

**节省比例：~85%**

### 5.3 预算监控

- 每完成一个任务，记录实际消耗到 `docs/tasks/<id>.yaml` 的 `actual_tokens` 字段
- 每周汇总对比 budget vs actual，调整估算模型
- 发现某类任务常超预算 → 拆分模式，或换下一档模型

---

## 六、目录约定

```
docs/
├── contracts/              # 契约层（只读）
│   ├── schemas/
│   ├── models/
│   ├── protocols/
│   ├── api-spec.yaml
│   ├── mqtt-spec.md
│   ├── errors.yaml
│   ├── events.yaml
│   └── permissions.yaml
├── tasks/                  # 任务清单
│   ├── _template.yaml      # 任务模板
│   ├── P1-01-xx.yaml       # Phase 1 地基
│   ├── P2-01-xx.yaml       # Phase 2 数据打通
│   └── ...
├── ROADMAP.md              # 总索引（高层模块）
├── TECHNICAL_PLAN.md       # 技术方案（架构与模型）
├── DEVELOPMENT_WORKFLOW.md # 本文件（方法论）
└── TASK_INDEX.md           # 任务索引 + 状态看板（自动生成）
```

---

## 七、关键约定

1. **契约是真理**：契约与代码冲突时，改代码不改契约（除非走契约变更任务）
2. **任务即合约**：任务 YAML 定义的 produces/acceptance 即验收标准，不多做不少做
3. **不跨任务读代码**：需要某个产物时，加到 context_files；读不到就说明依赖未声明清楚
4. **失败即拆分**：任务失败 2 次优先拆分而非加大上下文
5. **契约演进有成本**：改契约意味着所有下游任务重审，所以契约阶段投入 Opus 值得
6. **产物即契约的一部分**：某个任务产出的类/函数签名必须与契约一致，下游任务依赖的是签名

---

_本文档是项目的开发方法论基石，所有开发必须遵循此工作流。_
