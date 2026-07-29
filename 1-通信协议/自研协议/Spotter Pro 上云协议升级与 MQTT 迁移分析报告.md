# Spotter Pro 上云协议升级与 MQTT 迁移分析报告

> 修订说明（2026-07-29）：按仓库定稿协议与 `nexus_gateway` 实装核对，纠正原稿中 Base64/`version` 字符串等偏差；并补充 **Topic SN（主 SN vs PTZ SN）** 讨论结论。

## 1. 项目背景与目标

Spotter / Spotter Pro 直连天盾上云，设备侧由 `nexus_gateway`（现网）对接 MQTT。新协议（`Spotter_Spotter Pro上云协议.md`）在保持 MQTT + JSON 传输的前提下，统一外层 `CloudMessage` 信封与业务 payload 契约，并引入 `version` 做新老兼容。

嵌入式落地策略：

| 节点 | 协议 | 用途 |
|------|------|------|
| `ros_ws/src/nexus_gateway` | 旧协议（对内指导文档） | Spotter Pro **现网保留** |
| `ros_ws/src/nexus_gateway_sfl300` | 新协议（从 gateway 拷贝后改造） | SFL300 / 新协议对接 |

核心目标：

- **协议标准化**：统一 CloudMessage 信封 + method / Topic / payload 映射。
- **平滑迁移**：`version` 区分新旧；旧节点不改，新节点独立演进。
- **契约清晰**：业务字段以 `.proto` 定义；MQTT **线上仍为 JSON**。

## 2. MQTT 上云架构（与现网一致的部分）

- 设备经 TLS MQTT 连天盾 Broker；Topic 形如 `thing/product/{SN}/osd|services|requests|...`。
- 路由依赖信封字段：`tid` / `bid` / `method` / `gateway` / `timestamp`（新协议另加 `version`）。
- 设备鉴权 SN 与 `nexus_gateway.json` / broker 注册一致；子设备另有独立产品 SN（如 PTZ）。

## 3. 新老协议对照

### 3.1 老协议（对内指导文档 + `nexus_gateway`）

- MQTT payload：**纯 JSON**（cJSON 组包），无统一 `@type`。
- 无信封级 `version` 字段（或等价物）。
- method / Topic 按章节约定（如 `device_heart`、`ptz_turn`、`device_stream_url`）。

> 原稿写「老协议调试困难因二进制」**不成立**：现网老协议就是 JSON，可读。

### 3.2 新协议（Spotter_Spotter Pro上云协议.md）

- 外层统一 `CloudMessage`（proto 定义字段）。
- 增加 **`version`**：`0`（或缺省）= 老协议语义；**`1` = v1 新协议**（整型，不是 `"2.0"` 字符串）。
- `data`：`google.protobuf.Any` 的 **JSON 映射**：带 `@type`，业务字段平铺（见协议上报示例）。
- method / Topic 有调整（如视觉锁定改 `/uav`、控制多为 `spotter_*` 等）。

## 4. 协议设计核心：JSON 信封 + Protobuf 契约（纠正）

**定稿（以 Spotter 协议正文示例为准，忽略原稿 Base64 方案）：**

- **传输层**：整包仍是 MQTT **JSON 文本**。
- **信封**：`CloudMessage` 字段（`tid/bid/timestamp/gateway/method/version/data`）。
- **载荷**：`data` 为 JSON **对象**，含 `@type`（如 `type.googleapis.com/cloud.SpotterVisionLockData`）及平铺业务字段。

示例（0xE3 视觉锁定，节选）：

```json
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "device_uav_video",
  "version": 1,
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterVisionLockData",
    "timestamp": 1667220873800,
    "sn": "PTZ_SN_001",
    "working_state": 3,
    "fusion_target_id": 42,
    "vision_target_u": 960,
    "vision_target_v": 540,
    "video_source": 0
  }
}
```

**已废弃的错误描述（原稿）：**

- ~~`data` 为 Base64(Protobuf 二进制)~~
- ~~`version: "2.0"` 字符串~~
- ~~客户端先 SerializeToString 再 Base64 填 data~~

Protobuf 的作用是：**字段契约 / 可选 codegen / 与云端类型对齐**；不是要求 MQTT 发 binary 整包。

设计优势（修正后）：

- 网关/联调仍可读 JSON；`method` + Topic 即可路由。
- `@type` 标明 payload 类型，避免同 method 多语义歧义（如多个 `device_heart` 靠类型区分）。
- `version=1` 让天盾区分新老客户端。

## 5. Topic 中的 SN：主 SN vs PTZ SN（补充讨论）

天盾物模型是 **网关（Spotter Pro）+ 子设备（PTZ type=1017 等）**。Topic 路径上的 `{SN}` 与报文 `gateway` 字段含义不同，不能混为一谈。

### 5.1 通用规则

| 字段 / 路径 | 含义 |
|-------------|------|
| Topic 中的 `{SN}` | **该条 MQTT 通道所属产品身份**（主机或某一子设备） |
| 报文 `gateway` | **归属哪台 Spotter Pro 整机**（直连场景多为整机主 SN） |
| 控制类 `data.sn` | **命令目标子设备**（当 Topic 已是主 SN 时用来区分控谁） |

### 5.2 `nexus_gateway` 实装结论（已核对代码）

| 能力 | Topic 用的 SN | `gateway` 字段 | 代码位置（要点） |
|------|---------------|----------------|------------------|
| PTZ 心跳 `device_heart` | **PTZ SN** | Spotter Pro 主 SN | `SubDevicePublisher` → `TopicOsdFor(ptz.sn)`；SN 来自 `ptzDevicesCfg` 第 1 路 |
| 推流 `device_stream_url` | **PTZ SN**（`/requests` 与 `/requests_reply`） | Spotter Pro 主 SN | `ServiceRequestor::RequestStreamUrlOnce` → `TopicRequestsFor(ptzSn)` |
| PTZ 转台/变焦 `ptz_turn` / `ptz_zoom` | **Spotter Pro 主 SN** `/services` | 主 SN / 校验 | 文档 §4.8.4.2；目标 PTZ 在 **`data.sn`** |
| 视觉锁定 `device_uav_video` | **主 SN** `/osd` | （按组包规则） | `VisionTargetPublisher` → `m_topics->TopicOsd()` |
| 主机心跳 / 融合目标等 | **主 SN** | 主 SN | 主机物模型 |

PTZ SN 取值：`RosDataBridge::GetPtzSubStatus()` → `g_ptzDevCfgApi.getFirstDevSn()`。

### 5.3 为什么「只有」心跳和推流 Topic 用 PTZ SN？（有意设计）

1. **子设备状态通道**：天盾把 PTZ 注册为子产品；子设备姿态/心跳走 `thing/product/{子设备SN}/osd`（通用规则，不限 PTZ）。
2. **推流身份绑在摄像头/PTZ 产品上**：云端媒体按子产品发 RTMP，故 `device_stream_url` 的 request/reply 落在 `{PTZ_SN}/requests*`。
3. **下行控制走整机网关**：`/services` 用主 SN，`data.sn` 指明控哪台 PTZ——一台主机多子设备时只订一条 services，且避免多机误订同一子设备 Topic。

文档两处写 `{PTZ_设备 SN}`（心跳 osd、推流 requests）与代码一致；**不是**整条 PTZ 链路都用 PTZ SN。

### 5.4 若把下行控制也改成 PTZ SN Topic，会有什么问题？（咨询结论）

**不推荐**，现网曾订 `{PTZ_SN}/services`，后因问题收回。主要风险：

1. **多网关抢同一 Topic**：两台 Spotter Pro 若配置了相同 PTZ SN，都会订阅同一 `{PTZ_SN}/services` → 双执行、双 `services_reply` → 云端 correlator 异常（如 inconsistent / errorCode=10001）。见 `NexusGateway.cpp` 订阅注释。
2. **运行期 SN 变更**：启动时按旧 PTZ SN 订阅，配置变更后收不到命令；主 SN 更稳，目标靠每次 `data.sn`。
3. **与现网文档不一致**：§4.8.4.2 明确 Topic 为 Spotter Pro SN；改 Topic 需云端同步。
4. **应答 Topic 必须成对**：下行若改 PTZ SN，reply 也要走 `{PTZ_SN}/services_reply`，否则云端等不到应答。

仅当云端明确改为「按子设备下发控制」且全局保证 PTZ SN 唯一、单机独占订阅时，才适合改回 PTZ SN Topic。

## 6. 关键问答（纠正）

### Q1：线上是不是发 Protobuf 二进制？

**A**：否。MQTT 发 **JSON**。Protobuf 定义字段；`data` 用 Any 的 JSON（`@type` + 平铺字段）。

### Q2：还要不要 Base64？

**A**：**不要。** 以 Spotter 协议上报示例为准；原稿 Base64 方案作废。

### Q3：`version` 怎么填？

**A**：整型。新协议客户端发 **`version: 1`**。不要用 `"2.0"` 字符串。

### Q4：新老如何共存？

**A**：设备侧双节点：`nexus_gateway` 继续旧 JSON；`nexus_gateway_sfl300` 发 `version=1` 新信封。天盾按 `version` / 能力分流。勿在同一进程混发两套信封。

### Q5：PTZ 相关到底用哪个 SN？

**A**：见 §5。心跳与推流 Topic = **PTZ SN**；控制与整机感知 = **主 SN**（控制再用 `data.sn` 指 PTZ）。`gateway` 字段一般为 **主 SN**。

## 7. 实施建议（嵌入式）

- 新协议开发只改 **`nexus_gateway_sfl300`**，不要动现网 `nexus_gateway`。
- 组包：CloudMessage JSON + `version=1` + `data.@type`；method/Topic 跟新协议一览表。
- PTZ 心跳 / `device_stream_url`：**保持 Topic 用 PTZ SN**（与现网、文档一致），除非天盾书面变更。
- 下行控制：**保持主 SN `/services` + `data.sn`**。
- 联调对照协议 JSON 示例，勿按已废弃的 Base64 流程实现。

## 8. 总结

新协议升级的实质是：**同一套 MQTT JSON 通道上，换成带 `version` 与 `@type` 的 CloudMessage 契约**，而不是改成 binary Protobuf 传输。SN 使用上继续遵循「子设备状态/推流用子 SN，整机命令/整机感知用主 SN」——与天盾网关物模型一致，且已被 `nexus_gateway` 实装与踩坑经验验证。
