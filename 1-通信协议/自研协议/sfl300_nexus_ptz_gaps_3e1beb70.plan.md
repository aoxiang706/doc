---
name: SFL300 nexus PTZ gaps
overview: 在 feature/sfl300 上仅增量补齐 nexus_gateway 的 PTZ 天盾缺口（不迁 CloudMessage、不启 nexus_gateway_sfl300）。协议依据为「云平台设备上云指导文档(对内).md」，method 仍用现有 ptz_* JSON 信封。
todos:
  - id: ec-four-fields
    content: 0xEC device_heart：补 detect_camera_*/defog/win_heat + 真实 ptz_ctl_mode（PtzOsdInfo→ros_app→BuildPtzSubStatus）
    status: pending
  - id: ptz-ctl-mode-mqtt
    content: 新增 MQTT ptz_ctl_mode(0x8c)，复用 alink 手动/自动逻辑
    status: pending
  - id: ptz-set-pixel-mqtt
    content: 新增 MQTT ptz_set_pixel(0x95) → /ptz_track_pixel_cmd_from_user
    status: pending
  - id: zoom-audit-z201
    content: 对照 alink 扫 ptz_zoom 缺口；Z201 拒窗加热 cmd12/13
    status: pending
  - id: turn-cmd6-verify
    content: 验收 ptz_turn cmd=6 角速度（代码已有）
    status: pending
isProject: false
---

# SFL300：nexus_gateway PTZ 缺口补齐（精简方案）

> **与旧计划关系**：[`sfl300_tiandun_ptz_gaps_4337ce36.plan.md`](/home/skyfend/.cursor/plans/sfl300_tiandun_ptz_gaps_4337ce36.plan.md) **原样保留**（含 CloudMessage / `nexus_gateway_sfl300` 方案）。本文件为**新开发方案**，勿混用。

---

## 1. 方案变更（相对旧计划）

| 项 | 旧方案（保留文档） | **本方案** |
|----|-------------------|------------|
| 分支 | — | [`feature/sfl300`](ros_ws/src/nexus_gateway) |
| 节点 | 新建/改造 `nexus_gateway_sfl300` | **继续只用** [`nexus_gateway`](ros_ws/src/nexus_gateway) |
| 协议形态 | CloudMessage + `@type` + method 改名 | **现网 JSON 信封不变**（`tid/bid/method/gateway/data`） |
| 工作量 | 大重构 | **只补缺失功能** |
| 协议文档 | Spotter_Spotter Pro上云协议.md | [`云平台设备上云指导文档(对内).md`](/home/skyfend/workspace/云平台设备上云指导文档(对内).md) |

**明确不做**：Protobuf/`version` 信封、method 批量改名（`spotter_ptz_*`）、Topic 大迁、启用 `nexus_gateway_sfl300`。

---

## 2. 缺口清单与现状

依据需求表 + 袁伟健对齐 C2 的缺口说明，对照 `feature/sfl300` 代码：

| 项 | C2 / 需求 | 天盾 MQTT（现状） | 动作 |
|----|-----------|-------------------|------|
| 0xEC 心跳 | 全字段 | `{PTZ_SN}/osd` · `device_heart`；缺 **4 字段**；`ptz_ctl_mode` 写死 0 | **补上报** |
| 0x8a 转台 | 含 cmd=6 角速度 | [`ExecutePtzTurn`](ros_ws/src/nexus_gateway/src/ros/RosDataBridge.cpp) **已有 cmd=6** | **联调验收**（非从零开发） |
| 0x8b 相机 | zoom/focus/ICR/透雾/窗加热等 | `ptz_zoom` 已注册；需对照 alink **扫漏**；Z201 **无窗加热** | **扫漏 + Z201 拦截 12/13** |
| 0x8c 模式 | 手动/自动 | **无 MQTT**；alink 已有 [`alink_set_ptz_ctl_mode`](src/srv/alink/command/system/alink_system.cpp) | **新增下行** |
| 0x95 点选 | 像素框锁定 | **无 MQTT**；C2 链已通 → `/ptz_track_pixel_cmd_from_user` | **新增下行** |

Topic / SN 规则保持现网（有意设计，不改）：

- 心跳 / 推流 Topic → **PTZ SN**；`gateway` → 主 SN  
- 控制 `ptz_*` Topic → **主 SN** `/services`，目标在 `data.sn`

---

## 3. 实现设计

### 3.1 0xEC：补 4 字段 + 真实 `ptz_ctl_mode`

需上云字段（相对 C2 / 缺口说明）：

- `detect_camera_mode` / `detect_camera`
- `defog_enable` / `win_heat_enable`

另：[`BuildPtzSubStatus`](ros_ws/src/nexus_gateway/src/protocol/ThingModelBuilder.cpp) 已发 `ptz_ctl_mode`，但 [`OnPtzOsdInfo`](ros_ws/src/nexus_gateway/src/ros/RosDataBridge.cpp) 注释写明**占位 0** → 改为镜像真实值。

改动链：

1. 扩展 [`PtzOsdInfo.msg`](ros_ws/src/srp100_message/skyfend_interfaces/msg/ptz_msg/PtzOsdInfo.msg)（已有 detect_*；补 `ptz_ctl_mode`、`defog_enable`、`win_heat_enable`）
2. [`ros_app_publish_ptz_osd_info`](src/app/ros_app/ros_app.cpp) 从 `alink_ptz_info_t` / 和普状态填全
3. `NexusPtzSubStatus` + `OnPtzOsdInfo` + `BuildPtzSubStatus` 写出上述 JSON 字段

> 说明：当前对内文档 §4.8.2.4 **尚未写出**上述 4 字段；实现按缺口清单先做 AGX 上报，并与天盾同步改文档。

### 3.2 0x8a：cmd=6 验收

代码已走 `/cmd_set` cmd_id=58（角速度）。本任务：**实机/联调确认**与 C2 0x8a 行为一致即可，无大改。

### 3.3 0x8b：扫漏 + Z201 窗加热

- 对照 [`alink_ctrl_ptz_zoom`](src/srv/alink/command/system/alink_system.cpp) 与 [`ExecutePtzZoom`](ros_ws/src/nexus_gateway/src/ros/RosDataBridge.cpp)：列出未实现/语义偏差（尤其 cmd 8/9 `state_code`）
- Z201：[`ptz_hepu_capality.h`](iotDevices/ptzHepuSDK/include/ptz_hepu_capality.h) `window_heat=false` → cmd **12/13 直接失败**；请天盾按钮置灰（前端，非本仓）

### 3.4 0x8c：新增 `ptz_ctl_mode`

- Topic：`thing/product/{SpotterProSN}/services`（与 `ptz_turn` 同）
- method 默认：**`ptz_ctl_mode`**（与现网 `ptz_turn`/`ptz_zoom` 命名一致；对内文档暂无此节，需补协议）
- data：`{ sn, cmd:1, ptz_ctl_mode:0|1 }`
- 实现：`CloudCommandHandler` 注册 → 复用 / 抽取与 `alink_set_ptz_ctl_mode` 相同逻辑（设 `g_ptz_ctl_mode` 或等价 ROS），应答 `services_reply`

### 3.5 0x95：新增画面点选

- Topic：同上主 SN `/services`
- method 默认：**`ptz_set_pixel`**
- data：对齐 C2 0x95（`sn, video_source_enum, pixel_max/min_u/v, pixel_aim_x/y`）
- 实现：发 [`/ptz_track_pixel_cmd_from_user`](ros_ws/src/ptz100_guide_ai/ptz_guider_ctl/include/ptz_guider_ros_adapter.h)（激光则 laser topic）；设备侧耐杰/和普链路已通

---

## 4. 开发顺序

1. 0xEC 字段镜像（上报可见，联调最快）
2. 0x8c 下行
3. 0x95 下行
4. 0x8b 扫漏 + Z201 窗加热拦截
5. 0x8a cmd=6 验收

---

## 5. 默认命名（若与天盾不一致再改）

| 能力 | MQTT method |
|------|-------------|
| 0x8c | `ptz_ctl_mode` |
| 0x95 | `ptz_set_pixel` |

请确认天盾是否已定其它 method 名；未定前按上表实现。

---

## 6. 非本任务

- CloudMessage / `@type` / `nexus_gateway_sfl300`
- 融合/雷达/标定/mask 等非 PTZ 缺口
- 改心跳/推流 Topic 的 SN 规则
