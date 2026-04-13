-- ============================================================
-- System 模块数据库表 DDL
-- 包含: tenants, users, roles, menus, depts, user_roles,
--       role_menus, api_keys, audit_logs, oauth2_clients,
--       oauth2_access_tokens, oauth2_refresh_tokens
-- ============================================================

-- ============ 租户 ============
CREATE TABLE tenants (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(50) NOT NULL,                  -- 租户唯一标识
    domain          VARCHAR(200),                          -- 绑定域名
    contact_name    VARCHAR(50),
    contact_phone   VARCHAR(20),
    contact_email   VARCHAR(100),
    package_id      BIGINT,
    status          SMALLINT NOT NULL DEFAULT 0,           -- 0正常 1禁用
    expire_at       TIMESTAMPTZ,
    device_quota    INTEGER NOT NULL DEFAULT 100,
    user_quota      INTEGER NOT NULL DEFAULT 50,
    storage_quota   BIGINT NOT NULL DEFAULT 10737418240,   -- 默认 10GB
    storage_used    BIGINT NOT NULL DEFAULT 0,
    remark          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator_id      BIGINT,
    updater_id      BIGINT,
    deleted         BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_tenants_code UNIQUE (code)
);
CREATE INDEX idx_tenants_status ON tenants (status, deleted);
COMMENT ON TABLE tenants IS '租户表';

-- ============ 部门 ============
CREATE TABLE depts (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL,
    parent_id   BIGINT NOT NULL DEFAULT 0,
    name        VARCHAR(50) NOT NULL,
    sort        INTEGER NOT NULL DEFAULT 0,
    leader_id   BIGINT,
    phone       VARCHAR(20),
    email       VARCHAR(100),
    status      SMALLINT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator_id  BIGINT,
    updater_id  BIGINT,
    deleted     BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_depts_tenant_parent ON depts (tenant_id, parent_id);
COMMENT ON TABLE depts IS '部门表';

-- ============ 用户 ============
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    username        VARCHAR(50) NOT NULL,
    password_hash   VARCHAR(200) NOT NULL,
    nickname        VARCHAR(50),
    email           VARCHAR(100),
    phone           VARCHAR(20),
    avatar          VARCHAR(500),
    dept_id         BIGINT,
    sex             SMALLINT,                              -- 0未知 1男 2女
    status          SMALLINT NOT NULL DEFAULT 0,           -- 0正常 1禁用
    is_super        BOOLEAN NOT NULL DEFAULT FALSE,        -- 是否超级管理员
    last_login_at   TIMESTAMPTZ,
    last_login_ip   VARCHAR(50),
    login_failed    INTEGER NOT NULL DEFAULT 0,            -- 连续登录失败次数
    locked_until    TIMESTAMPTZ,                           -- 锁定到何时
    remark          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator_id      BIGINT,
    updater_id      BIGINT,
    deleted         BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_users_tenant_username UNIQUE (tenant_id, username)
);
CREATE INDEX idx_users_tenant_status ON users (tenant_id, status, deleted);
CREATE INDEX idx_users_dept ON users (tenant_id, dept_id);
COMMENT ON TABLE users IS '用户表';

-- ============ 角色 ============
CREATE TABLE roles (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    name            VARCHAR(50) NOT NULL,
    code            VARCHAR(50) NOT NULL,
    sort            INTEGER NOT NULL DEFAULT 0,
    data_scope      SMALLINT NOT NULL DEFAULT 1,           -- 1全部 2自定义部门 3本部门 4本部门及下级 5仅本人
    data_scope_dept_ids JSONB DEFAULT '[]'::jsonb,          -- data_scope=2 时使用
    status          SMALLINT NOT NULL DEFAULT 0,
    type            SMALLINT NOT NULL DEFAULT 2,           -- 1内置 2自定义
    remark          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator_id      BIGINT,
    updater_id      BIGINT,
    deleted         BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_roles_tenant_code UNIQUE (tenant_id, code)
);
CREATE INDEX idx_roles_tenant_status ON roles (tenant_id, status, deleted);
COMMENT ON TABLE roles IS '角色表';

-- ============ 菜单/权限 ============
CREATE TABLE menus (
    id              BIGSERIAL PRIMARY KEY,
    parent_id       BIGINT NOT NULL DEFAULT 0,
    name            VARCHAR(50) NOT NULL,
    permission      VARCHAR(100),                          -- 权限标识: device:list
    type            SMALLINT NOT NULL,                     -- 1目录 2菜单 3按钮
    sort            INTEGER NOT NULL DEFAULT 0,
    path            VARCHAR(200),                          -- 前端路由
    icon            VARCHAR(100),
    component       VARCHAR(200),
    component_name  VARCHAR(100),
    visible         BOOLEAN NOT NULL DEFAULT TRUE,
    keep_alive      BOOLEAN NOT NULL DEFAULT TRUE,
    always_show     BOOLEAN NOT NULL DEFAULT FALSE,
    status          SMALLINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator_id      BIGINT,
    updater_id      BIGINT,
    deleted         BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_menus_parent ON menus (parent_id, deleted);
CREATE INDEX idx_menus_permission ON menus (permission);
COMMENT ON TABLE menus IS '菜单/权限表（全局共享，不分租户）';

-- ============ 用户-角色关联 ============
CREATE TABLE user_roles (
    user_id     BIGINT NOT NULL,
    role_id     BIGINT NOT NULL,
    tenant_id   BIGINT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator_id  BIGINT,
    PRIMARY KEY (user_id, role_id)
);
CREATE INDEX idx_user_roles_role ON user_roles (role_id);
CREATE INDEX idx_user_roles_tenant ON user_roles (tenant_id);
COMMENT ON TABLE user_roles IS '用户-角色关联';

-- ============ 角色-菜单关联 ============
CREATE TABLE role_menus (
    role_id     BIGINT NOT NULL,
    menu_id     BIGINT NOT NULL,
    tenant_id   BIGINT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (role_id, menu_id)
);
CREATE INDEX idx_role_menus_menu ON role_menus (menu_id);
CREATE INDEX idx_role_menus_tenant ON role_menus (tenant_id);
COMMENT ON TABLE role_menus IS '角色-菜单关联';

-- ============ API Key ============
CREATE TABLE api_keys (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    name            VARCHAR(100) NOT NULL,
    key_prefix      VARCHAR(20) NOT NULL,                  -- 显示前缀: iot_xxxxxxxx
    key_hash        VARCHAR(200) NOT NULL,                 -- SHA256(完整key)
    scopes          JSONB NOT NULL DEFAULT '[]'::jsonb,    -- 权限范围
    expire_at       TIMESTAMPTZ,
    last_used_at   TIMESTAMPTZ,
    last_used_ip   VARCHAR(50),
    status          SMALLINT NOT NULL DEFAULT 0,
    remark          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator_id      BIGINT,
    deleted         BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_api_keys_tenant ON api_keys (tenant_id, status, deleted);
CREATE INDEX idx_api_keys_hash ON api_keys (key_hash);
COMMENT ON TABLE api_keys IS 'API Key 表';

-- ============ 审计日志 ============
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT,
    user_id         BIGINT,
    username        VARCHAR(50),
    module          VARCHAR(50) NOT NULL,                  -- system / device / weighbridge ...
    operation       VARCHAR(200) NOT NULL,
    method          VARCHAR(10),                           -- GET / POST / PUT / DELETE
    request_url     VARCHAR(500),
    request_params  JSONB,
    request_body    JSONB,
    response_code   INTEGER,
    response_body   JSONB,
    ip              VARCHAR(50),
    user_agent      VARCHAR(500),
    duration_ms     INTEGER,
    error_message   TEXT,
    trace_id        VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_logs_tenant_time ON audit_logs (tenant_id, created_at DESC);
CREATE INDEX idx_audit_logs_user ON audit_logs (user_id, created_at DESC);
CREATE INDEX idx_audit_logs_module ON audit_logs (module, created_at DESC);
COMMENT ON TABLE audit_logs IS '操作审计日志';

-- ============ OAuth2 客户端 ============
CREATE TABLE oauth2_clients (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    client_id       VARCHAR(100) NOT NULL,
    client_secret   VARCHAR(200) NOT NULL,
    name            VARCHAR(100) NOT NULL,
    logo            VARCHAR(500),
    description     TEXT,
    redirect_uris   JSONB NOT NULL DEFAULT '[]'::jsonb,
    grant_types     JSONB NOT NULL DEFAULT '["password"]'::jsonb,
    scopes          JSONB NOT NULL DEFAULT '[]'::jsonb,
    access_token_validity_seconds  INTEGER NOT NULL DEFAULT 1800,
    refresh_token_validity_seconds INTEGER NOT NULL DEFAULT 2592000,
    status          SMALLINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator_id      BIGINT,
    deleted         BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_oauth2_clients_client_id UNIQUE (client_id)
);
CREATE INDEX idx_oauth2_clients_tenant ON oauth2_clients (tenant_id);
COMMENT ON TABLE oauth2_clients IS 'OAuth2 客户端表';

-- ============ OAuth2 Access Token (DB 备份, 主存储是 Redis) ============
CREATE TABLE oauth2_access_tokens (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    user_id         BIGINT NOT NULL,
    user_type       SMALLINT NOT NULL DEFAULT 1,           -- 1 admin / 2 app
    client_id       VARCHAR(100) NOT NULL,
    access_token    VARCHAR(64) NOT NULL,                  -- jti uuid
    refresh_token   VARCHAR(64),
    scopes          JSONB DEFAULT '[]'::jsonb,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_oauth2_at_token UNIQUE (access_token)
);
CREATE INDEX idx_oauth2_at_user ON oauth2_access_tokens (tenant_id, user_id);
COMMENT ON TABLE oauth2_access_tokens IS 'OAuth2 AccessToken 持久化';

CREATE TABLE oauth2_refresh_tokens (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    user_id         BIGINT NOT NULL,
    user_type       SMALLINT NOT NULL DEFAULT 1,
    client_id       VARCHAR(100) NOT NULL,
    refresh_token   VARCHAR(64) NOT NULL,
    scopes          JSONB DEFAULT '[]'::jsonb,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_oauth2_rt_token UNIQUE (refresh_token)
);
CREATE INDEX idx_oauth2_rt_user ON oauth2_refresh_tokens (tenant_id, user_id);
COMMENT ON TABLE oauth2_refresh_tokens IS 'OAuth2 RefreshToken 持久化';
