-- ============================================================
-- Device 模块数据库表 DDL
-- 包含: products, devices, device_groups, device_group_relations,
--       device_shadows, device_commands, firmware_packages, ota_jobs,
--       ota_job_devices, device_online_log
-- ============================================================

-- ============ 产品（设备型号） ============
CREATE TABLE products (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(50) NOT NULL,                  -- 产品标识
    category        VARCHAR(50),                           -- 类别: camera/sensor/weighbridge
    manufacturer    VARCHAR(100),
    model           VARCHAR(100),
    description     TEXT,
    auth_type       SMALLINT NOT NULL DEFAULT 1,           -- 1一型一密 2一机一密
    auth_secret     VARCHAR(200),                          -- 一型一密用
    data_format     VARCHAR(20) DEFAULT 'json',            -- json / binary
    metric_schema   JSONB,                                 -- 遥测指标 schema 定义
    status          SMALLINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator_id      BIGINT,
    updater_id      BIGINT,
    deleted         BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_products_tenant_code UNIQUE (tenant_id, code)
);
CREATE INDEX idx_products_tenant ON products (tenant_id, status, deleted);
COMMENT ON TABLE products IS '产品/设备型号';

-- ============ 设备 ============
CREATE TABLE devices (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    product_id      BIGINT,
    device_key      VARCHAR(100) NOT NULL,                 -- 设备唯一标识(MQTT username)
    device_secret   VARCHAR(200) NOT NULL,                 -- 设备密钥(MQTT password 哈希)
    name            VARCHAR(100),
    sn              VARCHAR(100),                          -- 设备序列号
    firmware_version VARCHAR(50),
    hardware_version VARCHAR(50),
    status          SMALLINT NOT NULL DEFAULT 0,           -- 0未激活 1在线 2离线 3异常 4禁用
    activated_at    TIMESTAMPTZ,
    last_online_at  TIMESTAMPTZ,
    last_offline_at TIMESTAMPTZ,
    last_ip         VARCHAR(50),
    local_ip        VARCHAR(50),
    longitude       DECIMAL(10, 7),
    latitude        DECIMAL(10, 7),
    address         VARCHAR(200),
    tags            JSONB DEFAULT '{}'::jsonb,
    ext_config      JSONB DEFAULT '{}'::jsonb,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator_id      BIGINT,
    updater_id      BIGINT,
    deleted         BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_devices_tenant_key UNIQUE (tenant_id, device_key)
);
CREATE INDEX idx_devices_tenant_status ON devices (tenant_id, status, deleted);
CREATE INDEX idx_devices_product ON devices (tenant_id, product_id);
CREATE INDEX idx_devices_last_online ON devices (tenant_id, last_online_at DESC);
COMMENT ON TABLE devices IS '设备表';

-- ============ 设备分组 ============
CREATE TABLE device_groups (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    parent_id       BIGINT NOT NULL DEFAULT 0,
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(50),
    description     TEXT,
    sort            INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator_id      BIGINT,
    updater_id      BIGINT,
    deleted         BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_device_groups_tenant_parent ON device_groups (tenant_id, parent_id);
COMMENT ON TABLE device_groups IS '设备分组';

-- ============ 设备-分组关联 ============
CREATE TABLE device_group_relations (
    device_id   BIGINT NOT NULL,
    group_id    BIGINT NOT NULL,
    tenant_id   BIGINT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (device_id, group_id)
);
CREATE INDEX idx_device_group_rel_group ON device_group_relations (group_id);
CREATE INDEX idx_device_group_rel_tenant ON device_group_relations (tenant_id);

-- ============ 设备影子（期望态 vs 上报态） ============
CREATE TABLE device_shadows (
    device_id       BIGINT PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    reported_state  JSONB NOT NULL DEFAULT '{}'::jsonb,
    desired_state   JSONB NOT NULL DEFAULT '{}'::jsonb,
    reported_at     TIMESTAMPTZ,
    desired_at      TIMESTAMPTZ,
    version         INTEGER NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_device_shadows_tenant ON device_shadows (tenant_id);
COMMENT ON TABLE device_shadows IS '设备影子';

-- ============ 设备指令 ============
CREATE TABLE device_commands (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    device_id       BIGINT NOT NULL,
    command_id      VARCHAR(64) NOT NULL,                  -- 客户端指令唯一 ID (用于回执匹配)
    command         VARCHAR(100) NOT NULL,
    params          JSONB DEFAULT '{}'::jsonb,
    status          SMALLINT NOT NULL DEFAULT 0,           -- 0已发送 1已送达 2已执行 3超时 4失败
    response        JSONB,
    error_message   TEXT,
    timeout_seconds INTEGER NOT NULL DEFAULT 30,
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at    TIMESTAMPTZ,
    acked_at        TIMESTAMPTZ,
    creator_id      BIGINT,
    CONSTRAINT uq_device_commands_cmd_id UNIQUE (command_id)
);
CREATE INDEX idx_device_commands_device ON device_commands (tenant_id, device_id, sent_at DESC);
CREATE INDEX idx_device_commands_status ON device_commands (tenant_id, status, sent_at DESC);
COMMENT ON TABLE device_commands IS '设备指令记录';

-- ============ 设备上下线日志 ============
CREATE TABLE device_online_logs (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    device_id       BIGINT NOT NULL,
    event_type      SMALLINT NOT NULL,                     -- 1上线 2离线
    ip              VARCHAR(50),
    reason          VARCHAR(200),
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_device_online_logs_device ON device_online_logs (tenant_id, device_id, occurred_at DESC);
COMMENT ON TABLE device_online_logs IS '设备上下线日志';

-- ============ 固件包 ============
CREATE TABLE firmware_packages (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    product_id      BIGINT,
    version         VARCHAR(50) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    file_url        VARCHAR(500) NOT NULL,
    file_key        VARCHAR(500) NOT NULL,                 -- MinIO key
    file_size       BIGINT NOT NULL,
    file_hash       VARCHAR(128) NOT NULL,                 -- SHA256
    sign_method     VARCHAR(20),                           -- 签名算法
    signature       VARCHAR(500),                          -- 签名
    changelog       TEXT,
    status          SMALLINT NOT NULL DEFAULT 0,           -- 0草稿 1已发布 2已下架
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator_id      BIGINT,
    deleted         BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_firmware_product_version UNIQUE (tenant_id, product_id, version)
);
CREATE INDEX idx_firmware_tenant ON firmware_packages (tenant_id, status, deleted);
COMMENT ON TABLE firmware_packages IS '固件包';

-- ============ OTA 升级任务 ============
CREATE TABLE ota_jobs (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    name            VARCHAR(200) NOT NULL,
    firmware_id     BIGINT NOT NULL,
    strategy        SMALLINT NOT NULL DEFAULT 0,           -- 0全量 1按比例灰度 2指定设备
    strategy_config JSONB DEFAULT '{}'::jsonb,             -- {"percentage": 10, "device_ids": [...]}
    target_count    INTEGER NOT NULL DEFAULT 0,
    pending_count   INTEGER NOT NULL DEFAULT 0,
    success_count   INTEGER NOT NULL DEFAULT 0,
    failure_count   INTEGER NOT NULL DEFAULT 0,
    status          SMALLINT NOT NULL DEFAULT 0,           -- 0待执行 1进行中 2已暂停 3已完成 4已取消
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator_id      BIGINT,
    deleted         BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_ota_jobs_tenant ON ota_jobs (tenant_id, status, deleted);
COMMENT ON TABLE ota_jobs IS 'OTA 升级任务';

-- ============ OTA 任务-设备关联 ============
CREATE TABLE ota_job_devices (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    job_id          BIGINT NOT NULL,
    device_id       BIGINT NOT NULL,
    status          SMALLINT NOT NULL DEFAULT 0,           -- 0待推送 1已推送 2下载中 3升级中 4成功 5失败
    progress        SMALLINT NOT NULL DEFAULT 0,           -- 0-100
    error_message   TEXT,
    pushed_at       TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    CONSTRAINT uq_ota_job_devices UNIQUE (job_id, device_id)
);
CREATE INDEX idx_ota_job_devices_status ON ota_job_devices (tenant_id, job_id, status);
COMMENT ON TABLE ota_job_devices IS 'OTA 任务下设备升级进度';
