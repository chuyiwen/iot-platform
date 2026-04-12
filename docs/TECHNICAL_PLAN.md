# IoT SaaS 平台技术方案（FastAPI 全栈）

> 参考芋道源码（yudao）架构设计理念，采用 Python FastAPI 全栈实现。
> 核心原则：**模块化解耦** · **全链路多租户** · **框架组件化** · **渐进式复杂度**

---

## 一、技术栈总览

| 层 | 技术选型 | 说明 |
|----|---------|------|
| Web 框架 | FastAPI 0.115+ | 异步高性能，自动 OpenAPI 文档 |
| ORM | SQLAlchemy 2.x + asyncpg | 异步 ORM，声明式模型 |
| 数据库迁移 | Alembic | 版本化迁移，支持多租户 |
| 认证授权 | 自研 OAuth2 + JWT | 参考 yudao，Access+Refresh Token，Redis 存储 |
| 权限框架 | 自研 RBAC+数据权限 | 参考 yudao 数据权限插件思路，SQLAlchemy 事件拦截 |
| 任务队列 | Celery 5.x + Redis Broker | 异步任务、定时任务、租户级任务 |
| 缓存 | Redis 7 + redis-py async | 缓存/分布式锁/限流/会话 |
| 对象存储 | MinIO (S3 兼容) + boto3 | 图像/文件/固件包存储 |
| 时序数据库 | TimescaleDB (PG 扩展) | 设备遥测数据，hypertable+压缩 |
| MQTT Broker | EMQX 5.x | 设备接入，内置 ACL/认证 |
| MQTT Client | aiomqtt (asyncio) | 后端订阅设备消息 |
| 前端 | React 18 + TypeScript + Ant Design Pro | 管理后台 |
| 前端 (H5) | React + Ant Design Mobile | 扫码预约/司机端 |
| API 文档 | Swagger UI + ReDoc (FastAPI 内置) | 自动生成 |
| 测试 | pytest + pytest-asyncio + httpx | 单测/集成测试 |
| 代码质量 | ruff + mypy + pre-commit | lint/类型检查/提交钩子 |
| CI/CD | GitHub Actions | lint → test → build → deploy |
| 容器化 | Docker + Docker Compose | 开发环境一键起 |
| 生产部署 | K8s + Helm (后期) | 生产级编排 |
| 监控 | Prometheus + Grafana + Loki | 指标/日志/告警 |
| 追踪 | OpenTelemetry + Jaeger | 分布式链路追踪 |
| 错误追踪 | Sentry | 异常捕获与告警 |

---

## 二、项目结构（参考 yudao 模块化设计）

### 2.1 Monorepo 总体布局

```
iot-platform/
├── backend/                          # 后端（FastAPI）
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI 入口，注册所有路由
│   │   ├── core/                     # 框架核心层（对应 yudao-framework）
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # Pydantic Settings 配置管理
│   │   │   ├── security/             # 认证授权框架
│   │   │   │   ├── auth.py           # JWT Token 生成/校验
│   │   │   │   ├── oauth2.py         # OAuth2 授权模式
│   │   │   │   ├── permissions.py    # RBAC 权限校验依赖
│   │   │   │   └── api_key.py        # API Key 认证
│   │   │   ├── tenant/               # 多租户框架
│   │   │   │   ├── context.py        # TenantContext (ContextVar)
│   │   │   │   ├── middleware.py     # 租户识别中间件
│   │   │   │   ├── deps.py           # 租户注入依赖
│   │   │   │   └── filters.py        # SQLAlchemy 自动过滤
│   │   │   ├── data_permission/      # 数据权限框架
│   │   │   │   ├── rules.py          # 数据权限规则定义
│   │   │   │   └── filters.py        # SQL 自动注入 WHERE
│   │   │   ├── db/                   # 数据库框架
│   │   │   │   ├── session.py        # AsyncSession 工厂
│   │   │   │   ├── base_model.py     # 基础模型（含审计字段）
│   │   │   │   ├── tenant_model.py   # 租户模型基类
│   │   │   │   └── crud_base.py      # 通用 CRUD 基类
│   │   │   ├── cache/                # 缓存框架
│   │   │   │   ├── redis_client.py   # Redis 异步客户端
│   │   │   │   ├── decorators.py     # @cached 装饰器
│   │   │   │   └── tenant_cache.py   # 租户隔离缓存
│   │   │   ├── mq/                   # 消息队列框架
│   │   │   │   ├── mqtt_client.py    # MQTT 异步客户端
│   │   │   │   ├── event_bus.py      # 内部事件总线(Redis Stream)
│   │   │   │   └── celery_app.py     # Celery 实例
│   │   │   ├── storage/              # 对象存储框架
│   │   │   │   ├── s3_client.py      # MinIO/S3 客户端
│   │   │   │   └── presigned.py      # 预签名 URL 生成
│   │   │   ├── logging.py            # 结构化日志(JSON)
│   │   │   ├── errors.py             # 统一错误码 + 异常类
│   │   │   ├── exceptions.py         # 全局异常处理器
│   │   │   ├── pagination.py         # 统一分页
│   │   │   ├── rate_limit.py         # 限流器
│   │   │   └── tracing.py            # OpenTelemetry 集成
│   │   │
│   │   ├── modules/                  # 业务模块层（对应 yudao-module-*）
│   │   │   ├── system/               # 系统管理（必选）
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api/              # API 定义（VO/DTO）
│   │   │   │   │   ├── schemas.py    # Pydantic 请求/响应模型
│   │   │   │   │   └── deps.py       # 跨模块依赖接口
│   │   │   │   ├── controller/       # 路由层
│   │   │   │   │   ├── admin/        # 管理后台 API
│   │   │   │   │   └── app/          # 用户端 API
│   │   │   │   ├── service/          # 业务逻辑层
│   │   │   │   ├── dal/              # 数据访问层
│   │   │   │   │   ├── models.py     # SQLAlchemy 模型
│   │   │   │   │   └── crud.py       # 数据库操作
│   │   │   │   └── router.py         # 模块路由汇总
│   │   │   │
│   │   │   ├── infra/                # 基础设施（必选）
│   │   │   ├── device/               # 设备管理
│   │   │   ├── telemetry/            # 时序数据
│   │   │   ├── alarm/                # 告警引擎
│   │   │   ├── image/                # 图像管理 + CVAT
│   │   │   ├── weighbridge/          # 地磅系统
│   │   │   ├── appointment/          # 扫码预约
│   │   │   └── dispatch/             # 车辆调度
│   │   │
│   │   └── worker/                   # Celery Worker 入口
│   │       ├── tasks/                # 异步任务定义
│   │       └── schedules.py          # 定时任务配置
│   │
│   ├── alembic/                      # 数据库迁移
│   │   ├── versions/
│   │   └── env.py
│   ├── tests/                        # 测试
│   │   ├── conftest.py               # fixtures
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── scripts/                      # 脚本
│   │   ├── seed.py                   # 种子数据
│   │   └── codegen.py                # 代码生成器
│   ├── pyproject.toml                # 依赖管理 (uv/poetry)
│   ├── Dockerfile
│   └── alembic.ini
│
├── frontend/                         # 前端（React + AntD Pro）
│   ├── src/
│   │   ├── api/                      # 后端 API 调用封装
│   │   ├── components/               # 公共组件
│   │   ├── layouts/                  # 布局
│   │   ├── pages/                    # 页面
│   │   ├── stores/                   # 状态管理 (Zustand)
│   │   ├── hooks/                    # 自定义 hooks
│   │   ├── utils/                    # 工具函数
│   │   ├── locales/                  # 国际化
│   │   └── App.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── edge/                             # 边缘 Agent（Python）
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── main.py                   # 入口
│   │   ├── mqtt_handler.py           # MQTT 通信
│   │   ├── collectors/               # 数据采集器（插件式）
│   │   │   ├── image_collector.py
│   │   │   ├── sensor_collector.py
│   │   │   └── weighbridge_reader.py
│   │   ├── uploader.py               # 上传管理（断点续传）
│   │   ├── cache.py                  # 本地 SQLite 缓存
│   │   ├── ota.py                    # OTA 升级
│   │   └── monitor.py                # 资源自监控
│   ├── install.sh                    # 安装脚本
│   ├── iot-edge.service              # systemd 服务
│   └── pyproject.toml
│
├── deploy/                           # 部署配置
│   ├── docker-compose.yml            # 开发环境
│   ├── docker-compose.prod.yml       # 生产环境
│   ├── nginx/
│   ├── emqx/
│   ├── prometheus/
│   ├── grafana/
│   └── k8s/                          # Helm charts（后期）
│
├── docs/                             # 文档
│   ├── ROADMAP.md
│   ├── TECHNICAL_PLAN.md             # 本文件
│   ├── API.md
│   └── DEPLOYMENT.md
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
├── Makefile
├── .env.example
├── .pre-commit-config.yaml
└── .gitignore
```

### 2.2 业务模块内部分层（参考 yudao api+biz 模式）

每个模块统一采用 **api / controller / service / dal** 四层：

```
modules/device/
├── __init__.py
├── api/
│   ├── schemas.py          # Pydantic VO/DTO（入参/出参）
│   └── deps.py             # 供其他模块调用的接口（依赖倒置）
├── controller/
│   ├── admin/
│   │   ├── device_controller.py      # 管理端: /admin-api/device/*
│   │   ├── device_group_controller.py
│   │   └── device_ota_controller.py
│   └── app/
│       └── device_app_controller.py  # 设备端: /app-api/device/*
├── service/
│   ├── device_service.py             # 业务逻辑
│   ├── heartbeat_service.py
│   ├── shadow_service.py
│   └── ota_service.py
├── dal/
│   ├── models.py            # SQLAlchemy ORM 模型
│   └── crud.py              # 数据访问操作
├── mq/
│   ├── consumers.py         # MQTT/Event 消费者
│   └── producers.py         # 事件发布者
├── tasks.py                 # Celery 异步任务
└── router.py                # 本模块路由汇总 → main.py 注册
```

### 2.3 模块间调用规则（依赖倒置）

```
device 模块需要调用 system 模块获取用户信息：

  device/service/ → 依赖 system/api/deps.py 中定义的 Protocol
  system/service/ 实现此 Protocol
  main.py 启动时注册到 FastAPI 依赖注入容器

  不允许直接 import 其他模块的 service 层
```

---

## 三、核心框架设计

### 3.1 多租户框架（全链路隔离，参考 yudao TenantDatabaseInterceptor）

从 HTTP 请求 → 数据库 → 缓存 → 异步任务 → MQTT，全链路自动注入 tenant_id。

**租户上下文** — 基于 Python contextvars：

```python
# core/tenant/context.py
from contextvars import ContextVar

_tenant_id: ContextVar[int | None] = ContextVar("tenant_id", default=None)

class TenantContext:
    @staticmethod
    def get() -> int | None:
        return _tenant_id.get()

    @staticmethod
    def set(tenant_id: int) -> None:
        _tenant_id.set(tenant_id)

    @staticmethod
    def require() -> int:
        tid = _tenant_id.get()
        if tid is None:
            raise TenantRequiredError()
        return tid
```

**数据库自动过滤**（核心，对应 yudao MyBatis Plus 多租户插件）：

```python
# core/tenant/filters.py — SQLAlchemy event 拦截
@event.listens_for(Session, "do_orm_execute")
def _inject_tenant_filter(execute_state):
    """拦截所有 ORM 查询，自动追加 WHERE tenant_id = :tid"""
    tenant_id = TenantContext.get()
    if tenant_id and _is_tenant_entity(execute_state):
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(TenantModel,
                lambda cls: cls.tenant_id == tenant_id)
        )
```

**缓存隔离** — Key 自动追加 `:t{tenant_id}` 后缀
**Celery 租户透传** — before_task_publish 注入 header，task_prerun 恢复
**@tenant_ignore** — 装饰器跳过过滤（对应 yudao @TenantIgnore）

---

### 3.2 认证授权框架（参考 yudao 自研 OAuth2）

**Token 体系**：

```
AccessToken (JWT, 30min)
  ├── sub: user_id, tenant_id, jti(uuid)
  └── Redis: token:{jti} → LoginUser 信息

RefreshToken (Opaque UUID, 30天)
  └── Redis: refresh:{uuid} → user_id, tenant_id, scopes

登出/踢出 → blacklist:{jti} 加入黑名单
```

**授权模式**：

| 模式 | 场景 | 端点 |
|------|------|------|
| Password | 后台/APP 登录 | POST /admin-api/auth/login |
| Authorization Code | 第三方 SSO | /admin-api/oauth2/authorize |
| Client Credentials | 设备/服务间 | POST /admin-api/oauth2/token |
| API Key | 第三方对接 | Header: X-API-Key |

**权限校验**（FastAPI Depends）：

```python
# 使用方式
@router.get("/devices")
async def list_devices(
    user: LoginUser = require_permissions("device:list"),
):
    ...
```

---

### 3.3 数据权限框架（参考 yudao DataPermission）

五种数据范围：全部 / 指定部门 / 本部门 / 本部门及下级 / 仅本人

```python
# 自动注入 WHERE 条件，业务代码无感
def apply_data_permission(query, user: LoginUser, model_class):
    scope = user.data_scope
    if scope == DataScope.ALL:
        return query
    elif scope == DataScope.SELF_ONLY:
        return query.where(model_class.creator_id == user.id)
    elif scope == DataScope.DEPT_ONLY:
        return query.where(model_class.dept_id == user.dept_id)
    ...
```

---

### 3.4 统一响应与错误码

```python
# 统一响应格式
class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "成功"
    data: T | None = None

# 错误码分段
# 通用 0xxxx | 租户 1xxxx | 设备 2xxxx | 地磅 3xxxx | 预约 4xxxx
```

---

### 3.5 数据库模型基类（参考 yudao BaseDO / TenantBaseDO）

```python
class BaseModel(DeclarativeBase):
    """所有模型基类，含审计字段 + 软删除"""
    __abstract__ = True
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at, updated_at, creator_id, updater_id, deleted

class TenantModel(BaseModel):
    """需要租户隔离的模型基类"""
    __abstract__ = True
    tenant_id: Mapped[int] = mapped_column(BigInteger, index=True)

class CRUDBase(Generic[ModelType, CreateSchema, UpdateSchema]):
    """通用 CRUD，自动注入 tenant_id + 软删除 + 分页"""
    async def get / get_multi / create / update / soft_delete
```

---

## 四、核心数据模型

### 4.1 系统管理（system 模块）

```sql
-- 租户
CREATE TABLE tenants (
    id            BIGSERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,          -- 租户名称
    domain        VARCHAR(200),                   -- 绑定域名
    contact_name  VARCHAR(50),                    -- 联系人
    contact_phone VARCHAR(20),                    -- 联系电话
    package_id    BIGINT,                         -- 套餐 ID
    status        SMALLINT DEFAULT 0,             -- 0正常 1禁用
    expire_at     TIMESTAMPTZ,                    -- 过期时间
    device_quota  INT DEFAULT 100,                -- 设备配额
    storage_quota BIGINT DEFAULT 10737418240,     -- 存储配额(bytes, 默认10GB)
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    deleted       BOOLEAN DEFAULT FALSE
);

-- 用户
CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    tenant_id     BIGINT NOT NULL REFERENCES tenants(id),
    username      VARCHAR(50) NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    nickname      VARCHAR(50),
    email         VARCHAR(100),
    phone         VARCHAR(20),
    avatar        VARCHAR(500),
    dept_id       BIGINT,
    status        SMALLINT DEFAULT 0,
    last_login_at TIMESTAMPTZ,
    last_login_ip VARCHAR(50),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    creator_id    BIGINT,
    deleted       BOOLEAN DEFAULT FALSE,
    UNIQUE(tenant_id, username)
);

-- 角色
CREATE TABLE roles (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    name        VARCHAR(50) NOT NULL,
    code        VARCHAR(50) NOT NULL,             -- 角色标识: admin, operator
    data_scope  SMALLINT DEFAULT 1,               -- 数据范围(1-5)
    sort        INT DEFAULT 0,
    status      SMALLINT DEFAULT 0,
    remark      TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    deleted     BOOLEAN DEFAULT FALSE,
    UNIQUE(tenant_id, code)
);

-- 角色-菜单关联
CREATE TABLE role_menus (
    role_id BIGINT NOT NULL,
    menu_id BIGINT NOT NULL,
    PRIMARY KEY (role_id, menu_id)
);

-- 用户-角色关联
CREATE TABLE user_roles (
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY (user_id, role_id)
);

-- 菜单/权限
CREATE TABLE menus (
    id            BIGSERIAL PRIMARY KEY,
    parent_id     BIGINT DEFAULT 0,
    name          VARCHAR(50) NOT NULL,
    permission    VARCHAR(100),                   -- 权限标识: device:list
    type          SMALLINT NOT NULL,              -- 1目录 2菜单 3按钮
    path          VARCHAR(200),
    component     VARCHAR(200),
    icon          VARCHAR(100),
    sort          INT DEFAULT 0,
    status        SMALLINT DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 部门
CREATE TABLE depts (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    parent_id   BIGINT DEFAULT 0,
    name        VARCHAR(50) NOT NULL,
    sort        INT DEFAULT 0,
    leader_id   BIGINT,
    status      SMALLINT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- API Key
CREATE TABLE api_keys (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    name        VARCHAR(100) NOT NULL,
    key_hash    VARCHAR(200) NOT NULL,            -- SHA256(key)
    prefix      VARCHAR(10) NOT NULL,             -- 前缀用于识别: iot_xxxx
    scopes      JSONB DEFAULT '[]',               -- 权限范围
    expire_at   TIMESTAMPTZ,
    last_used   TIMESTAMPTZ,
    status      SMALLINT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 操作审计日志
CREATE TABLE audit_logs (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT,
    user_id     BIGINT,
    username    VARCHAR(50),
    module      VARCHAR(50),                      -- system, device, weighbridge
    operation   VARCHAR(200),                     -- 操作描述
    method      VARCHAR(10),                      -- HTTP Method
    request_url VARCHAR(500),
    request_body JSONB,
    response_code INT,
    ip          VARCHAR(50),
    user_agent  VARCHAR(500),
    duration_ms INT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_logs_tenant_time ON audit_logs(tenant_id, created_at DESC);

-- OAuth2 客户端
CREATE TABLE oauth2_clients (
    id            BIGSERIAL PRIMARY KEY,
    tenant_id     BIGINT NOT NULL,
    client_id     VARCHAR(100) NOT NULL UNIQUE,
    client_secret VARCHAR(200) NOT NULL,
    name          VARCHAR(100),
    redirect_uris JSONB DEFAULT '[]',
    grant_types   JSONB DEFAULT '["password"]',
    scopes        JSONB DEFAULT '[]',
    status        SMALLINT DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.2 设备管理（device 模块）

```sql
-- 设备
CREATE TABLE devices (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    device_key      VARCHAR(100) NOT NULL,        -- 设备唯一标识
    device_secret   VARCHAR(200),                 -- 设备密钥
    name            VARCHAR(100),
    product_id      BIGINT,                       -- 产品型号 ID
    group_id        BIGINT,                       -- 设备分组
    sn              VARCHAR(100),                 -- 序列号
    firmware_ver    VARCHAR(50),                  -- 当前固件版本
    status          SMALLINT DEFAULT 0,           -- 0未激活 1在线 2离线 3异常 4禁用
    last_online_at  TIMESTAMPTZ,
    last_offline_at TIMESTAMPTZ,
    last_ip         VARCHAR(50),                  -- 最后上报 IP
    local_ip        VARCHAR(50),                  -- 内网 IP
    longitude       DECIMAL(10, 7),
    latitude        DECIMAL(10, 7),
    address         VARCHAR(200),
    tags            JSONB DEFAULT '{}',
    ext_config      JSONB DEFAULT '{}',           -- 设备扩展配置
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    creator_id      BIGINT,
    deleted         BOOLEAN DEFAULT FALSE,
    UNIQUE(tenant_id, device_key)
);
CREATE INDEX idx_devices_status ON devices(tenant_id, status);

-- 设备分组
CREATE TABLE device_groups (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    parent_id   BIGINT DEFAULT 0,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    sort        INT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 设备影子（期望态 vs 上报态）
CREATE TABLE device_shadows (
    device_id       BIGINT PRIMARY KEY REFERENCES devices(id),
    reported_state  JSONB DEFAULT '{}',           -- 设备上报的状态
    desired_state   JSONB DEFAULT '{}',           -- 平台期望的状态
    reported_at     TIMESTAMPTZ,
    desired_at      TIMESTAMPTZ,
    version         INT DEFAULT 0
);

-- 设备指令
CREATE TABLE device_commands (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    device_id   BIGINT NOT NULL,
    command     VARCHAR(100) NOT NULL,
    params      JSONB DEFAULT '{}',
    status      SMALLINT DEFAULT 0,               -- 0已发送 1已送达 2已执行 3超时 4失败
    response    JSONB,
    sent_at     TIMESTAMPTZ DEFAULT NOW(),
    acked_at    TIMESTAMPTZ,
    timeout_sec INT DEFAULT 30,
    creator_id  BIGINT
);

-- OTA 固件包
CREATE TABLE firmware_packages (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    product_id  BIGINT,
    version     VARCHAR(50) NOT NULL,
    file_url    VARCHAR(500) NOT NULL,
    file_size   BIGINT,
    file_hash   VARCHAR(100),                     -- SHA256
    changelog   TEXT,
    status      SMALLINT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- OTA 升级任务
CREATE TABLE ota_jobs (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    firmware_id     BIGINT NOT NULL,
    name            VARCHAR(100),
    strategy        SMALLINT DEFAULT 0,           -- 0全量 1灰度(百分比) 2指定设备
    target_devices  JSONB,                        -- 目标设备列表/条件
    total_count     INT DEFAULT 0,
    success_count   INT DEFAULT 0,
    failure_count   INT DEFAULT 0,
    status          SMALLINT DEFAULT 0,           -- 0待执行 1进行中 2已完成 3已取消
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.3 时序数据（telemetry 模块）

```sql
-- 遥测数据（TimescaleDB hypertable）
CREATE TABLE telemetry (
    time        TIMESTAMPTZ NOT NULL,
    device_id   BIGINT NOT NULL,
    tenant_id   BIGINT NOT NULL,
    metric      VARCHAR(100) NOT NULL,            -- 指标名: temperature, humidity
    value_num   DOUBLE PRECISION,                 -- 数值型
    value_str   VARCHAR(500),                     -- 字符串型
    tags        JSONB DEFAULT '{}'
);
SELECT create_hypertable('telemetry', 'time');
CREATE INDEX idx_telemetry_device ON telemetry(tenant_id, device_id, metric, time DESC);

-- 压缩策略：7天后压缩，365天后删除
SELECT add_compression_policy('telemetry', INTERVAL '7 days');
SELECT add_retention_policy('telemetry', INTERVAL '365 days');

-- 连续聚合（5分钟/1小时/1天）
CREATE MATERIALIZED VIEW telemetry_5m WITH (timescaledb.continuous) AS
SELECT time_bucket('5 minutes', time) AS bucket,
       device_id, tenant_id, metric,
       avg(value_num) AS avg_val,
       min(value_num) AS min_val,
       max(value_num) AS max_val,
       count(*) AS cnt
FROM telemetry
GROUP BY bucket, device_id, tenant_id, metric;

-- 告警规则
CREATE TABLE alarm_rules (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    name        VARCHAR(100) NOT NULL,
    device_ids  JSONB,                            -- 适用设备（空=全部）
    metric      VARCHAR(100) NOT NULL,
    condition   VARCHAR(20) NOT NULL,             -- gt, lt, eq, between
    threshold   JSONB NOT NULL,                   -- {"value": 80} 或 {"min": 10, "max": 90}
    duration    INT DEFAULT 0,                    -- 持续秒数
    severity    SMALLINT DEFAULT 1,               -- 1info 2warning 3critical
    channels    JSONB DEFAULT '[]',               -- 通知渠道
    cooldown    INT DEFAULT 300,                  -- 冷却时间(秒)
    enabled     BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 告警记录
CREATE TABLE alarms (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    rule_id     BIGINT,
    device_id   BIGINT NOT NULL,
    severity    SMALLINT NOT NULL,
    title       VARCHAR(200) NOT NULL,
    content     TEXT,
    status      SMALLINT DEFAULT 0,               -- 0未处理 1已确认 2已处理 3已忽略
    acked_by    BIGINT,
    acked_at    TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_alarms_tenant_status ON alarms(tenant_id, status, created_at DESC);
```

### 4.4 图像与 CVAT（image 模块）

```sql
-- 图像
CREATE TABLE images (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    device_id   BIGINT NOT NULL,
    batch_id    BIGINT,
    file_key    VARCHAR(500) NOT NULL,            -- MinIO 对象 key
    file_size   BIGINT,
    file_hash   VARCHAR(64),                      -- SHA256 去重
    width       INT,
    height      INT,
    mime_type   VARCHAR(50) DEFAULT 'image/jpeg',
    captured_at TIMESTAMPTZ NOT NULL,             -- 采集时间
    longitude   DECIMAL(10, 7),
    latitude    DECIMAL(10, 7),
    tags        JSONB DEFAULT '{}',
    status      SMALLINT DEFAULT 0,               -- 0已上传 1已推送CVAT 2已标注 3已审核
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_images_device_time ON images(tenant_id, device_id, captured_at DESC);
CREATE UNIQUE INDEX idx_images_hash ON images(tenant_id, file_hash);

-- CVAT 任务
CREATE TABLE cvat_tasks (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    cvat_project_id INT,                          -- CVAT 项目 ID
    cvat_task_id    INT,                          -- CVAT 任务 ID
    name            VARCHAR(200),
    image_count     INT DEFAULT 0,
    annotation_format VARCHAR(20) DEFAULT 'COCO', -- COCO/YOLO/PascalVOC
    status          SMALLINT DEFAULT 0,           -- 0创建 1标注中 2已完成 3已审核
    result_url      VARCHAR(500),                 -- 标注结果下载 URL
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 标注结果
CREATE TABLE annotations (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    image_id    BIGINT NOT NULL,
    task_id     BIGINT,
    format      VARCHAR(20) NOT NULL,
    data        JSONB NOT NULL,                   -- 标注 JSON
    version     SMALLINT DEFAULT 1,               -- raw=1, reviewed=2, approved=3
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.5 地磅系统（weighbridge 模块）

```sql
-- 地磅设备
CREATE TABLE weighbridge_devices (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    device_id   BIGINT REFERENCES devices(id),    -- 关联 IoT 设备
    name        VARCHAR(100) NOT NULL,
    protocol    VARCHAR(50) NOT NULL,             -- METTLER_TOLEDO, AND, CUSTOM
    connection  JSONB NOT NULL,                   -- {"type":"serial","port":"/dev/ttyS0","baud":9600}
    location    VARCHAR(200),
    max_weight  DECIMAL(10, 2),                   -- 最大量程(kg)
    min_weight  DECIMAL(10, 2),                   -- 最小量程
    precision   DECIMAL(10, 4),                   -- 精度
    status      SMALLINT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 称重单
CREATE TABLE weighbridge_tickets (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    ticket_no       VARCHAR(50) NOT NULL,         -- 磅单号
    weighbridge_id  BIGINT NOT NULL,
    vehicle_plate   VARCHAR(20) NOT NULL,         -- 车牌号
    vehicle_id      BIGINT,
    driver_name     VARCHAR(50),
    driver_phone    VARCHAR(20),
    material        VARCHAR(100),                 -- 货物名称
    supplier        VARCHAR(100),                 -- 供应商/客户
    direction       SMALLINT NOT NULL,            -- 1进 2出
    mode            SMALLINT DEFAULT 1,           -- 1两次过磅 2一次过磅
    gross_weight    DECIMAL(10, 2),               -- 毛重(kg)
    tare_weight     DECIMAL(10, 2),               -- 皮重(kg)
    net_weight      DECIMAL(10, 2),               -- 净重(kg)
    gross_time      TIMESTAMPTZ,
    tare_time       TIMESTAMPTZ,
    gross_image_ids JSONB DEFAULT '[]',           -- 毛重抓拍
    tare_image_ids  JSONB DEFAULT '[]',           -- 皮重抓拍
    appointment_id  BIGINT,                       -- 关联预约单
    status          SMALLINT DEFAULT 0,           -- 0进行中 1已完成 2异常 3已作废
    remark          TEXT,
    synced          BOOLEAN DEFAULT FALSE,        -- 是否已同步到云端（离线模式）
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    creator_id      BIGINT,
    UNIQUE(tenant_id, ticket_no)
);
CREATE INDEX idx_tickets_plate ON weighbridge_tickets(tenant_id, vehicle_plate, created_at DESC);

-- 车辆档案
CREATE TABLE vehicles (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    plate       VARCHAR(20) NOT NULL,
    rfid        VARCHAR(100),
    vehicle_type VARCHAR(50),                     -- 大货/小货/罐车
    max_load    DECIMAL(10, 2),                   -- 额定载重
    carrier_id  BIGINT,                           -- 承运商
    blacklisted BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, plate)
);

-- 司机档案
CREATE TABLE drivers (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    name        VARCHAR(50) NOT NULL,
    phone       VARCHAR(20) NOT NULL,
    id_card     VARCHAR(50),                      -- 加密存储
    license_no  VARCHAR(50),
    vehicle_ids JSONB DEFAULT '[]',
    blacklisted BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.6 预约与调度（appointment + dispatch 模块）

```sql
-- 预约单
CREATE TABLE appointments (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    appt_no     VARCHAR(50) NOT NULL,             -- 预约号
    vehicle_plate VARCHAR(20) NOT NULL,
    driver_name VARCHAR(50),
    driver_phone VARCHAR(20),
    material    VARCHAR(100),
    direction   SMALLINT NOT NULL,                -- 1进 2出
    dock_id     BIGINT,                           -- 装卸口
    time_slot   TSTZRANGE NOT NULL,               -- 预约时段
    qr_code     VARCHAR(200),                     -- 二维码核销码
    status      SMALLINT DEFAULT 0,               -- 0待到场 1已到场 2已叫号 3过磅中 4已完成 5已取消 6爽约
    arrived_at  TIMESTAMPTZ,
    called_at   TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, appt_no)
);
CREATE INDEX idx_appt_slot ON appointments USING GIST(time_slot);

-- 装卸口/时段容量
CREATE TABLE dock_slots (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    name        VARCHAR(100) NOT NULL,            -- 装卸口名称
    dock_type   VARCHAR(50),                      -- 装货/卸货/通用
    capacity    INT DEFAULT 5,                    -- 每时段容量
    status      SMALLINT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 排队队列
CREATE TABLE queue_tickets (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    appointment_id  BIGINT,
    vehicle_plate   VARCHAR(20) NOT NULL,
    queue_no        INT NOT NULL,                 -- 排队号
    dock_id         BIGINT,
    priority        SMALLINT DEFAULT 0,           -- 优先级
    status          SMALLINT DEFAULT 0,           -- 0等待 1叫号 2服务中 3完成 4过号
    called_at       TIMESTAMPTZ,
    served_at       TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 调度任务
CREATE TABLE dispatch_tasks (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    task_no         VARCHAR(50) NOT NULL,
    vehicle_id      BIGINT,
    driver_id       BIGINT,
    carrier_id      BIGINT,
    material        VARCHAR(100),
    origin          VARCHAR(200),
    destination     VARCHAR(200),
    planned_at      TIMESTAMPTZ,
    status          SMALLINT DEFAULT 0,           -- 0待派 1已派 2运输中 3已到达 4已完成 5已取消
    appointment_id  BIGINT,
    ticket_id       BIGINT,                       -- 关联磅单
    remark          TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 承运商
CREATE TABLE carriers (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    name        VARCHAR(100) NOT NULL,
    contact     VARCHAR(50),
    phone       VARCHAR(20),
    status      SMALLINT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Webhook 订阅
CREATE TABLE webhooks (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    url         VARCHAR(500) NOT NULL,
    secret      VARCHAR(200),                     -- HMAC 签名密钥
    events      JSONB NOT NULL,                   -- ["device.online", "alarm.triggered"]
    status      SMALLINT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 五、MQTT 主题与协议设计

### 5.1 主题规范

```
前缀: iot/{tenant_id}/{device_key}/

上行（设备→平台）:
  iot/{tid}/{dk}/telemetry          # 遥测数据上报
  iot/{tid}/{dk}/status             # 状态/心跳上报
  iot/{tid}/{dk}/ip                 # IP 地址上报
  iot/{tid}/{dk}/event              # 事件上报（告警/异常）
  iot/{tid}/{dk}/image/meta         # 图像元数据上报（文件走 S3）
  iot/{tid}/{dk}/command/reply/{id} # 指令回执
  iot/{tid}/{dk}/ota/progress       # OTA 升级进度
  iot/{tid}/{dk}/shadow/reported    # 影子上报态

下行（平台→设备）:
  iot/{tid}/{dk}/command/{id}       # 指令下发
  iot/{tid}/{dk}/config             # 配置下发
  iot/{tid}/{dk}/shadow/desired     # 影子期望态
  iot/{tid}/{dk}/ota/push           # OTA 升级推送
```

### 5.2 消息格式（JSON）

```json
// 遥测上报
{
  "ts": 1712900000000,
  "metrics": {"temperature": 26.5, "humidity": 65.2, "weight": 15320.5}
}

// 心跳/状态上报
{
  "ts": 1712900000000,
  "uptime": 86400, "ip": "192.168.1.100", "public_ip": "114.80.x.x",
  "cpu": 45.2, "memory": 62.1, "disk": 38.5, "firmware": "1.2.3"
}

// 指令下发
{
  "id": "cmd_abc123",
  "command": "capture_image",
  "params": {"resolution": "1920x1080", "count": 1},
  "timeout": 30
}
```

### 5.3 EMQX 认证与 ACL

- **设备认证**：EMQX HTTP Auth 插件回调 → `POST /internal/mqtt/auth`
- **ACL 隔离**：每设备只可 pub/sub 自己 `iot/{tid}/{dk}/#` 下的主题
- **上下线通知**：EMQX WebHook → `POST /internal/mqtt/webhook`

---

## 六、部署架构

### 6.1 开发环境（Docker Compose 一键起）

```yaml
services:
  postgres:       # PG 16 + TimescaleDB
  redis:          # Redis 7
  minio:          # MinIO (S3 兼容)
  emqx:           # EMQX 5.x
  backend:        # FastAPI (uvicorn --reload)
  celery-worker:  # Celery Worker
  celery-beat:    # Celery Beat
  frontend:       # Vite dev server
```

### 6.2 生产环境

```
CloudFlare/SLB → Nginx Ingress
  ├── FastAPI ×N pods (Gunicorn + Uvicorn workers)
  ├── Celery Worker ×N pods
  ├── Celery Beat ×1
  ├── Frontend CDN (Vite build → S3/CDN)
  └── EMQX Cluster (3 节点)
后端存储:
  ├── PG Primary + Replica + TimescaleDB
  ├── Redis Cluster (6 节点)
  └── MinIO Cluster (or 云 S3)
```

---

## 七、开发任务清单（按执行顺序）

### Phase 1: 地基

| 编号 | 任务 | 产出文件/目录 | 测试 |
|------|------|-------------|------|
| P1-01 | 项目初始化 + 工程脚手架 | pyproject.toml, Dockerfile, docker-compose.yml, Makefile, .pre-commit, CI | 构建通过 |
| P1-02 | 核心框架层 | core/db/, core/errors.py, core/exceptions.py, core/pagination.py, core/logging.py | test_errors.py |
| P1-03 | 多租户框架 | core/tenant/ (context, middleware, filters, decorators) | test_tenant_isolation.py |
| P1-04 | 认证授权框架 | core/security/, core/cache/ | test_jwt.py, test_auth_flow.py |
| P1-05 | 系统管理模块 | modules/system/ 全部 + alembic 初始迁移 + seed.py | test_rbac.py, test_user_service.py |
| P1-06 | 设备管理模块(基础) | modules/device/ + core/mq/mqtt_client.py | test_device_lifecycle.py |
| P1-07 | EMQX 集成 | deploy/emqx/, 内部 auth/acl 端点 | test_mqtt_acl.py |

### Phase 2: 数据打通

| 编号 | 任务 | 产出 | 测试 |
|------|------|------|------|
| P2-01 | 时序数据模块 | modules/telemetry/ + TimescaleDB 迁移 | test_telemetry_ingest.py |
| P2-02 | 告警引擎 | modules/alarm/ + core/mq/event_bus.py | test_rule_engine.py, test_alarm_flow.py |
| P2-03 | 图像采集核心链路 | modules/image/ + core/storage/ | test_image_upload.py |
| P2-04 | 边缘 Agent 基础版 | edge/ 全部 | test_edge_cache.py |

### Phase 3: CVAT 闭环

| 编号 | 任务 | 产出 | 测试 |
|------|------|------|------|
| P3-01 | CVAT 对接 | modules/image/service/cvat_*.py + tasks.py | test_cvat_integration.py |

### Phase 4: 业务落地

| 编号 | 任务 | 产出 | 测试 |
|------|------|------|------|
| P4-01 | 地磅系统 | modules/weighbridge/ + edge/weighbridge_reader.py | test_weighing_flow.py |
| P4-02 | 扫码预约 | modules/appointment/ | test_appointment_flow.py |
| P4-03 | 车辆调度 | modules/dispatch/ | test_dispatch_flow.py |
| P4-04 | 业务闭环联调 | 全链路: 预约→到场→叫号→过磅→出场 | test_full_business_flow.py |

### Phase 5: 平台化

| 编号 | 任务 | 产出 | 测试 |
|------|------|------|------|
| P5-01 | 前端控制台 | frontend/ 全部页面 | Playwright E2E |
| P5-02 | 开放平台 | Webhook + 限流 + 文档站 | test_webhook.py |
| P5-03 | 安全加固 | 加密/HTTPS/风控/扫描 | ZAP + trivy |
| P5-04 | 可观测性 | Prometheus/Grafana/Sentry/OTel | 健康检查 |

---

## 八、测试策略

| 层次 | 工具 | 覆盖要求 | 运行时机 |
|------|------|---------|---------|
| 单元测试 | pytest + pytest-asyncio | ≥80% | 每次 push |
| 集成测试 | pytest + testcontainers | 核心链路 | 每次 PR |
| 契约测试 | schemathesis | OpenAPI 100% | 每次 PR |
| E2E 测试 | Playwright | 关键路径 | nightly |
| 性能测试 | locust | 基线回归 | 周期性 |
| 安全扫描 | trivy + pip-audit + ZAP | 0 高危 | 每次 PR |

---

## 九、关键依赖版本

```toml
[project]
requires-python = ">=3.11"

[project.dependencies]
fastapi = ">=0.115"
uvicorn = {extras = ["standard"], version = ">=0.30"}
sqlalchemy = {extras = ["asyncio"], version = ">=2.0"}
asyncpg = ">=0.29"
alembic = ">=1.13"
pydantic = ">=2.7"
pydantic-settings = ">=2.2"
redis = {extras = ["hiredis"], version = ">=5.0"}
celery = {extras = ["redis"], version = ">=5.4"}
aiomqtt = ">=2.1"
boto3 = ">=1.34"
python-jose = {extras = ["cryptography"], version = ">=3.3"}
passlib = {extras = ["bcrypt"], version = ">=1.7"}
structlog = ">=24.1"
httpx = ">=0.27"
opentelemetry-api = ">=1.24"
opentelemetry-sdk = ">=1.24"
sentry-sdk = {extras = ["fastapi"], version = ">=2.0"}

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "pytest-cov", "httpx", "ruff", "mypy", "pre-commit"]
edge = ["paho-mqtt", "opencv-python-headless", "pyserial", "pillow"]
```

---

_技术方案随开发推进持续更新。_
