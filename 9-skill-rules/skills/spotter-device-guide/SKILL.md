---
name: spotter-device-guide
description: Spotter/SSF 设备体系速查与设备类型命名变更清单，用于电子围栏(SSF100/SSF200/SSF210)开发与重命名时统一修改
---

# Spotter 设备开发通用指南

## 一、设备体系速查

### 1. 主设备分类

| 类别 | 版本接口 | 设备 |
|------|----------|------|
| Sentry 察打一体 | `get_sentry_version()` | SFL200, SFL210 |
| 泛雷视（非 Sentry） | `get_radar_v_version()` | SRP100/200/210, SSF100/200/210, BPH110 |

### 2. Spotter / 电子围栏

| 产品 | HostDevType | ALINK_DEV_ID | 组成 |
|------|-------------|--------------|------|
| Spotter SSF100 | HOST_DEV_TYPE_SSF100 = 0x1b | ALINK_DEV_ID_SSF100 = 0x1b | 近程雷达+近程PTZ+TracerP(STP130) |
| Spotter Pro SSF200 | HOST_DEV_TYPE_SSF200 = 0x23 | ALINK_DEV_ID_SSF200 = 0x23 | 中程四面阵雷达+中程PTZ+STF200 |
| Spotter Pro SSF210 | HOST_DEV_TYPE_SSF210 = 0x34 | ALINK_DEV_ID_SSF210 = 0x34 | 中程机扫雷达+中程PTZ+STF200 |

### 2.1 SFL300 硬件与产品映射（待补充/已对齐）

> 来源：电源板现状与架构分析（2026-07）；与罗工/产品对齐结论。

**SFL300 在 AGX / 仓库里就是 SSF100**（`HOST_DEV_TYPE_SSF100` / `ALINK_DEV_ID_SSF100 = 0x1b`）。SFL300 只是对外产品名，**不是**独立的 `HostDevType` / `ALINK_DEV_ID`。

| 产品对外名称 | 仓库内 / AGX 主设备类型 | 系统组成 | 电源板硬件 |
|--------------|-------------------------|----------|------------|
| Spotter Pro | SSF200 (0x23) / SSF210 (0x34) | 中程雷达 + 中程 PTZ + STF200 等 | **同一块电源板** |
| **SFL300** | **SSF100 (0x1b)**（AGX 主控即此类型） | 见下表 | **同一块电源板** |

**SFL300 产品包组成（AGX 侧主设备固定为 SSF100）：**

| 组成部分 | 说明 |
|----------|------|
| SSF100 | **AGX 主控**（`HOST_DEV_TYPE_SSF100`）；SFL300 在 AGX 中即此类型 |
| 和普 PTZ Z201 | PTZ **子设备**（`DEV_TYPE_PTZ_HEPU_Z201 = 37`） |
| 1~4 个小雷达 | 近程雷达子设备 |
| 电侦 | Tracer / 电侦子设备 |
| Hunter V | **车载无人机反制器**（非打击炮） |

**开发约定：**

- 开发一律按 **SSF100**（即 SFL300 的 AGX 主控）+ 各子设备，**不新增**设备类型枚举。
- PTZ 相关开发走「和普 PTZ 子设备」通路（见「二·补」），不新增 HostDevType/ALINK_DEV_ID。
- SFL300 与 Spotter Pro **电源板硬件一致**；差异在组网上下文（SFL300：无 C2 时 AGX/SSF100 顶替 C2 对端接电源板 ALINK）。

### 3. 关键协议与代码位置

| 消息/概念 | 用途 | 关键文件 |
|------------|------|----------|
| 0x77 | 电子围栏心跳/父子设备 | alink_efence.cpp |
| 0x8D | 雷视设备信息 | 复用雷视协议 |
| 0xBA/0xBB | 设备搜索与应答 | eth_link.c, eth_link_server.c |
| 0xFD | 子设备透传 | alink_system.cpp, c2_network.cpp |
| 0x0020 | STF200 侦测 | alink_tracerMatrix.cpp |
| 版本/SN | get_radar_v_version, get_sentry_version | netcon_protocol.cpp, eth_link.c |
| 设备类型配置 | setDeviceType.sh → sqlite → hostDeviceCfg.yaml | hostDeviceCfg.cpp, configCommDef.h |

---

## 二、设备类型 / 命名变更清单

新增或重命名 Spotter 相关设备类型时，按下列清单逐项检查，避免漏改。

### 1. 枚举与配置（必改）

| 文件 | 修改内容 |
|------|----------|
| `public/config/configUtils/configCommDef.h` | `HostDevType`：新增或重命名枚举项，数值与协议一致 |
| `src/srv/alink/alink.h` | `alink_dev_id_t`：新增或重命名 `ALINK_DEV_ID_xxx` |
| `src/srv/eth_link/eth_protocol/netcon_protocol.cpp` | `get_radar_v_version()`：增加对应 `HostDevType` 分支，设置版本前缀字符串（如 `SSF100_`） |
| `public/config/yamlConfig/hostDeviceCfg.cpp` | `addDevSnPrefix()`：增加对应 case，设置 SN 前缀（如 `SSF100-`）和 `find("SSF100")` |

### 2. 组网与 C2（必改）

| 文件 | 修改内容 |
|------|----------|
| `src/srv/eth_link/eth_link_server.c` | 设备发现时 `device_type` 与子设备类型赋值（与 C2/协议约定一致） |
| `src/srv/eth_link/eth_link.c` | 若有按设备类型分支的逻辑（如 SN 前缀），增加新类型 |
| `src/srv/eth_link/eth_protocol/netcon_protocol.cpp` | 若有按 `ALINK_DEV_ID_xxx` 分支（如 SN 前缀），增加新 ID |
| `src/app/c2_network/c2_network.cpp` | 电子围栏/C2 相关判断中增加新 `ALINK_DEV_ID_xxx` |
| `src/app/electronic_fence_app/electronic_fence_app.cpp` | 电子围栏使能判断中增加新设备类型 |
| `src/srv/alink/command/efence/alink_efence.cpp` | 电子围栏协议分支中增加新设备类型 |
| `src/srv/alink/command/target/alink_target.c` | 若按设备类型控制上报等，增加新类型 |

### 3. 脚本与冗余定义（按需）

| 文件 | 说明 |
|------|------|
| `config/sqlite/setDeviceType.sh` | 新增设备时增加参数与 `device_type_code`（与 HostDevType 数值一致） |
| `ros_ws/src/sysmanager/src/protocol/sysprotocol.h` | 若保留本地枚举副本，需与 alink.h 同步 |
| `public/config/oldConfig/cfg.h` | 旧配置枚举副本，按需同步 |
| `ros_ws/src/electronic_fence/include/alink_devices.h` | 电子围栏侧枚举副本，需与 alink.h 同步 |

### 4. 融合 / AI 节点（交对应团队）

| 文件 | 说明 |
|------|------|
| `ros_ws/.../fusion_config_manager.cpp` | `getRadarVType()` 的 switch 中增加或改名 case，映射到 `eProductType_t` |
| `ros_ws/.../camera.h` 等 | 若有设备类型注释或分支，同步枚举名 |

### 5. 兼容旧名（可选）

若其他模块暂未同步改名，可在 `configCommDef.h` 中为枚举增加别名，避免编译失败：

```c
HOST_DEV_TYPE_SSF100       = 0x1b,
HOST_DEV_TYPE_SPOTTER      = HOST_DEV_TYPE_SSF100,  // 旧名兼容，待 xxx 迁移后移除
```

`alink.h` 同理，可保留 `ALINK_DEV_ID_SPOTTER = ALINK_DEV_ID_SSF100`，待引用方全部迁移后再删。

---

## 二·补、和普 PTZ 子设备接入（Z201 / SFL300）

> 场景：SSF100 接入新款和普 PTZ **Z201（框型）**。这属于「新增 PTZ **子设备**类型」，与第二节的「新增主设备类型」不同——**不改 HostDevType / ALINK_DEV_ID**，只扩 PTZ 子设备枚举与和普通路分支。

### 1. 枚举与配置（Z201 已在 `feature/main_sfl300` 提交 `84d7d0c6` 接入）

| 文件 | 修改内容 | Z201 取值 |
|------|----------|-----------|
| `public/config/configUtils/configCommDef.h` | `SubDevType` 新增 | `DEV_TYPE_PTZ_HEPU_Z201 = 37` |
| `public/config/yamlConfig/ptzDevicesCfg.h` | `PtzType` 新增 | `PTZ_HEPU_Z201 = 9` |
| `ros_ws/.../srp100_message/.../CmdEnum.msg` | ROS 侧枚举副本 | `DEV_TYPE_PTZ_HEPU_Z201 = 37` |
| `ros_ws/src/ptz_service/src/ptzDevice/ptzDevice.h` | 工厂 `DeviceType` + `createDevice` case | `HEPU_PTZ_Z201` → `PtzDeviceHepu` |
| `ros_ws/src/ptz_service/src/rosService/rosService.cpp` | yaml type→DeviceType 映射、AI 订阅判断 | `PTZ_HEPU_Z201` |
| `ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp` | `loadPtzConfigBySn` 里 PtzType→`deviceDevType_` | → 37 |
| `iotDevices/ptzHepuSDK/include/ptz_hepu_capality.h` | 能力矩阵 `kHepuZ201Caps`、`hepuPtzIsHepuType`、`hepuPtzTypeName` | `{wiper=false, window_heat=false, defog=true, day_night=true}` |
| `public/config/yamlConfig/subDevicesCfg.cpp` | `getDevListSentry` 和普 PTZ 判断 | +37 |
| `src/app/ros_app/ros_app.cpp` | `isPtzSubDev`、和普在线 device_type 判断 | +37 |
| `src/app/ptz/ptz_app.cpp` | `check_hepu_ptz_device` | +37 |
| `src/srv/alink/command/system/alink_system.cpp` | `isPtzSubDev` | +37 |
| `src/srv/alink/command/sentry/alink_sentry.cpp` | 0x10 子设备类型判断 | +37 |
| `src/srv/eth_link/eth_link_server.c` | `getSentryOnlineSubDevicesInfo` 非 sentry 子设备过滤 | +37 |
| `ros_ws/src/sysmonit/src/http_api.cpp` + `web/index.html` | 展示名/映射表 | code 9 / 37 = `PTZ_HEPU_Z201` |

### 2. 心跳 / 相机 / 转台（复用和普通路，Z201 无独立驱动）

- **心跳**：0xE5（`get_hepu_ptz_dev_info` 上报 `g_hepu_ptz_info.device_type`）+ 0x77（`subDevicesCfg`）。Z201 已加入 PTZ 子设备判断，实机上报 `device_type=37`。
- **相机控制**：`C2 0x8b` → `alink_ctrl_ptz_zoom` → 引导 → `PtzDeviceHepu`（变焦/聚焦/`setIcr`）。与 Z50/DMA35 同路。
- **转台**：速度等级（0x8a `cmd=2`）+ **角速度（0x8a `cmd=6`，提交 `49492858` 已接 `controlPtzWithRealSpeed`→`HVS_ControlMoveWithRealSpeed`）**。任务单「未实现角速度」为过时描述，代码已实现，差 Z201 实机验收。

### 3. 已知缺口 / 待办（Z201 特有）

- **能力表门控（窗加热）已实现**：`loadPtzConfigBySn` 缓存 `caps_`。透雾与窗加热分线程：`defogPollThread_`（visibleCfg）/ `windowHeatPollThread_`（AUX_DEFROST），各按 `caps_.defog` / `caps_.window_heat` 独立启停。Z201 无窗加热时不启窗加热线程、忽略 `CTRL_CMD_WINDOW_HEAT_ON/OFF`、0xEC `win_heat_enable` 固定上报关；透雾线程仍可单独启动。雨刷对所有型号本就"0x8b not wired yet"未接，`caps_.wiper` 暂无下发路径可门控。
- **FOV 事实与引导策略（已拍板）**：
  - 事实：Z201 视场范围比 Z50 **小很多**，**与 DMS15 一致**（非 Z50 表）。
  - **引导不按 PTZ 型号分支算 FOV**；只需区分「大飞机 / 小飞机」模式（陈科威确认）。
  - 引导侧相关入参只有三项：**分辨率、所需像素数、大小飞机模式对应的飞机尺寸**；这三项不变则引导**不用改**（袁伟健确认）。
  - 引导按既有逻辑照常算、照常下发；若目标 FOV **超出设备物理范围，由设备按物理极限执行**（袁伟健确认），不在引导侧按型号裁剪。
  - 设备侧若需正确 clamp/映射，`ptzHepuViewCfg` 仍建议补 Z201（或复用 DMS15）标定表；与「引导不按型号分支」不矛盾。
- **融合侧未跟 Z201**：`rvfusion_service` 的 `eDeviceType_t` 仅有 `HOP100/HOP101`（Z50/Z50C），`ros_pub/sub_msg_adapter.h`、`sensor_pack.h` 未映射 Z201，影响融合标注/上报类型（不影响基础控台/心跳）。交融合团队补。
- **运行配置**：现场 `ptzDevicesCfg.yaml` 需把 PTZ 配成 `type: 9`（代码不会自动改型号）。

---

## 三、使用方式

- **查设备 ID / 类型**：直接问「SSF200 的 ALINK_DEV_ID 是多少」「get_radar_v_version 里有哪些类型」等，按第一节表格回答。
- **查 SFL300**：按「2.1 SFL300 硬件与产品映射」回答——对外名 SFL300 = 仓库/AGX 主控 SSF100；组成含 Z201/小雷达/电侦/Hunter V；不新增主设备枚举。
- **做命名/新增主设备类型**：按第二节清单逐文件修改，避免漏改；涉及融合/AI 时注明交对应团队并可选加兼容别名。
- **接入和普 PTZ 子设备（如 Z201/SFL300）**：按「二·补」章节改 PTZ 子设备枚举与和普通路分支，**不动 HostDevType/ALINK_DEV_ID**；注意能力表门控、设备侧 FOV 标定（引导不按型号分支）、融合枚举三处缺口。
- **协议与代码路径**：按第一节「关键协议与代码位置」定位到具体文件再改。
