# MQTT 协议规范

> 本文档定义平台与设备间的 MQTT 通信协议，所有边缘端、设备模拟器、后端订阅器必须严格遵守。
> Broker：EMQX 5.x（启用 MQTT 5.0），认证：用户名/密码 + ACL，传输层：TLS（推荐）。

## 1. 连接认证

| 字段        | 取值                                              |
| ----------- | ------------------------------------------------- |
| `username`  | `device_key`（设备唯一标识）                      |
| `password`  | `HMAC-SHA256(device_secret, client_id+timestamp)` |
| `client_id` | `iot-{tenant_id}-{device_key}-{nonce}`            |
| `keepalive` | 60 秒                                             |
| `clean_session` | `false`（QoS1 离线消息）                      |

EMQX 通过 webhook 调用 `POST /internal/auth/mqtt` 进行二次校验，返回 `{allow, tenant_id, device_id}`。

## 2. Topic 设计原则

```
iot/{tenant_id}/{device_key}/{direction}/{action}[/...]
```

- `direction`：`up`（设备 → 平台）/ `down`（平台 → 设备）
- 所有 Topic 必须以 `iot/{tenant_id}/` 开头，EMQX ACL 强制隔离租户
- 通配符订阅仅平台后端可用：`iot/+/+/up/#`

## 3. Topic 列表

### 3.1 设备 → 平台（up）

| Topic                                              | QoS | 描述           | 频率   |
| -------------------------------------------------- | --- | -------------- | ------ |
| `iot/{tenant_id}/{device_key}/up/property`         | 1   | 属性上报       | 按需   |
| `iot/{tenant_id}/{device_key}/up/event`            | 1   | 事件上报       | 按需   |
| `iot/{tenant_id}/{device_key}/up/heartbeat`        | 0   | 心跳           | 30s    |
| `iot/{tenant_id}/{device_key}/up/shadow/reported`  | 1   | 影子上报       | 按需   |
| `iot/{tenant_id}/{device_key}/up/cmd/reply`        | 1   | 指令回执       | 按需   |
| `iot/{tenant_id}/{device_key}/up/ota/progress`     | 1   | OTA 进度       | 按需   |
| `iot/{tenant_id}/{device_key}/up/log`              | 0   | 设备日志       | 按需   |

### 3.2 平台 → 设备（down）

| Topic                                              | QoS | 描述           |
| -------------------------------------------------- | --- | -------------- |
| `iot/{tenant_id}/{device_key}/down/cmd`            | 1   | 指令下发       |
| `iot/{tenant_id}/{device_key}/down/shadow/desired` | 1   | 期望态推送     |
| `iot/{tenant_id}/{device_key}/down/ota/notify`     | 1   | OTA 通知       |
| `iot/{tenant_id}/{device_key}/down/config`         | 1   | 配置下发       |

### 3.3 系统事件（仅平台内部订阅）

| Topic                                | 来源        |
| ------------------------------------ | ----------- |
| `$SYS/brokers/+/clients/+/connected` | EMQX        |
| `$SYS/brokers/+/clients/+/disconnected` | EMQX     |

## 4. 消息格式

所有 JSON 消息统一信封：

```json
{
  "msg_id": "uuid-v4",
  "timestamp": 1733836800000,
  "version": "1.0",
  "data": { ... }
}
```

### 4.1 属性上报 `up/property`

```json
{
  "msg_id": "1f3c...",
  "timestamp": 1733836800000,
  "version": "1.0",
  "data": {
    "temperature": 25.6,
    "humidity": 60,
    "battery": 87
  }
}
```

### 4.2 事件上报 `up/event`

```json
{
  "msg_id": "...",
  "timestamp": 1733836800000,
  "version": "1.0",
  "data": {
    "event": "alarm",
    "level": "warning",
    "code": "TEMP_HIGH",
    "message": "温度超过阈值",
    "extra": { "value": 85.2, "threshold": 80 }
  }
}
```

### 4.3 心跳 `up/heartbeat`

```json
{
  "msg_id": "...",
  "timestamp": 1733836800000,
  "version": "1.0",
  "data": {
    "ip": "192.168.1.10",
    "rssi": -67,
    "uptime": 3600,
    "free_mem": 1048576
  }
}
```

### 4.4 指令下发 `down/cmd`

```json
{
  "msg_id": "...",
  "timestamp": 1733836800000,
  "version": "1.0",
  "data": {
    "command_id": "cmd-uuid",
    "command": "reboot",
    "params": { "delay": 5 },
    "timeout": 30
  }
}
```

### 4.5 指令回执 `up/cmd/reply`

```json
{
  "msg_id": "...",
  "timestamp": 1733836800000,
  "version": "1.0",
  "data": {
    "command_id": "cmd-uuid",
    "code": 0,
    "message": "ok",
    "result": { ... }
  }
}
```

### 4.6 影子期望态 `down/shadow/desired`

```json
{
  "msg_id": "...",
  "timestamp": 1733836800000,
  "version": "1.0",
  "data": {
    "version": 12,
    "desired": {
      "led": "on",
      "interval": 10
    }
  }
}
```

### 4.7 影子上报态 `up/shadow/reported`

```json
{
  "msg_id": "...",
  "timestamp": 1733836800000,
  "version": "1.0",
  "data": {
    "reported": {
      "led": "on",
      "interval": 10
    }
  }
}
```

### 4.8 OTA 通知 `down/ota/notify`

```json
{
  "msg_id": "...",
  "timestamp": 1733836800000,
  "version": "1.0",
  "data": {
    "job_id": 1234,
    "firmware_id": 56,
    "version": "1.2.3",
    "url": "https://minio.example.com/firmware/...sig",
    "size": 2097152,
    "hash": "sha256:...",
    "sign_method": "RSA2048",
    "signature": "..."
  }
}
```

### 4.9 OTA 进度 `up/ota/progress`

```json
{
  "msg_id": "...",
  "timestamp": 1733836800000,
  "version": "1.0",
  "data": {
    "job_id": 1234,
    "status": 3,
    "progress": 60,
    "message": "downloading"
  }
}
```

## 5. ACL 规则

EMQX ACL 通过 HTTP 后端从平台拉取，规则：

```
allow  publish    iot/${tenant_id}/${username}/up/#
allow  subscribe  iot/${tenant_id}/${username}/down/#
deny   publish    iot/+/+/down/#
deny   subscribe  iot/+/+/up/#       # 设备不能订阅其他设备上行
```

平台后端使用 super-user 账号订阅 `iot/+/+/up/#`。

## 6. 离线/重连策略

- 设备使用 LWT（Last Will & Testament）：
  - Topic：`iot/{tenant_id}/{device_key}/up/event`
  - Payload：`{"event":"offline","reason":"unexpected"}`
  - QoS：1，retain：false
- EMQX disconnected webhook 触发平台 `device.offline` 事件
- 30 秒内未收到心跳判定为离线

## 7. 二进制协议（可选）

`product.data_format = "binary"` 时使用 TLV 编码：

```
+--------+--------+--------+----------+--------+
| Magic  | Ver    | Type   | Length   | Value  |
| 2 byte | 1 byte | 1 byte | 4 byte   | N byte |
+--------+--------+--------+----------+--------+
```

- Magic：`0xAA55`
- 网络字节序（大端）
- CRC32 附加在末尾

## 8. 安全要求

- 必须使用 TLS 1.2+（生产环境）
- `device_secret` 至少 32 字节随机串
- 一机一密产品：`device_secret` 仅在创建时返回一次
- 一型一密产品：首次连接时通过 `dynamic_register` Topic 动态获取设备密钥

## 9. 版本兼容

- `version` 字段标识协议版本，平台保留对 `1.x` 的向后兼容
- 不识别的 Topic：丢弃并打 warning 日志
- 不识别的字段：忽略，按现有字段处理
