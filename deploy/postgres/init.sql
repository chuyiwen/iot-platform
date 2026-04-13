-- 创建 TimescaleDB 扩展
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 创建应用专用角色（可选，主数据库已由 POSTGRES_DB 创建）
COMMENT ON DATABASE iot_platform IS 'IoT SaaS Platform 主数据库';
