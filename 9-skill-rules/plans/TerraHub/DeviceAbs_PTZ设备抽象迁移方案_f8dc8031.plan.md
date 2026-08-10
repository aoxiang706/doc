---
name: ""
overview: ""
todos: []
isProject: false
---

# DeviceAbs PTZ 设备抽象迁移方案

> **文档版本**：v2.0
> **更新日期**：2026-04-10
> **状态**：迁移方案设计（v2.0 修订：视频流链路剥离到 LiveStream，PtzModule 仅保留控制+状态）
> **关联文档**：[PTZ设备处理模块设计文档.md](../../PTZ设备处理模块设计文档.md)（现状描述）、[Infra三方库_自研库_日志接口包装_方案.md](Infra三方库_自研库_日志接口包装_方案.md)、[视频直播服务设计文档_f939159b.plan.md](视频直播服务设计文档_f939159b.plan.md)（视频流链路）

---

## 一、概述

### 1.1 迁移目标

将 `ptz100_agx` 中分散在 2 个 ROS2 节点（`ptz100_ros`、`ptz_service`）的 PTZ 设备处理逻辑，重构为 AimRT Module 架构下的 `**PtzModule`**，统一管理和普、耐杰两类 PTZ 设备的**控制、状态上报**两条链路，并向 DeviceManager 和 LiveStream 发布设备上下线及能力信息(包括PTZ支持云台转动控制、变焦Zoom、聚焦focus等)。

> **视频流链路**（拉流解码、SHM 帧管理、编码推流）**不在 PtzModule 范围内**，归 LiveStream 负责，详见 [视频直播服务设计文档](视频直播服务设计文档_f939159b.plan.md)。

### 1.2 范围

> **本次重构侧重点**：云边端重构项目基于 **SSF200（Spotter Pro 四面阵中程电子围栏）** 进行系统改造。SSF200 使用和普 PTZ，因此和普优先。


| 设备                    | 本次迁移        | 说明                                          |
| --------------------- | ----------- | ------------------------------------------- |
| **和普 PTZ**（三型/四型 Z50） | 优先实现（控制+状态） | SSF200 标配 PTZ，现有 `ptz_service` 的工厂模式可直接复用   |
| **耐杰 PTZ**（近程/中程）     | 其次实现（控制+状态） | SSF210 等产品使用，新建 `PtzDeviceNaijie` 子类，纳入统一工厂 |


> **关于激光设备**：激光 PTZ（霍克眼 HEF/HEP）虽带有 PTZ 云台功能，但其主要用途是**激光打击**，属于**打击类设备**（对应 SAPIENT 体系中的 Effector Node），将作为独立模块单独设计，不纳入本 PtzModule 方案。

### 1.3 现状要点（详见 PTZ设备处理模块设计文档）


| 维度      | 和普 PTZ                                          | 耐杰 PTZ                                                 |
| ------- | ----------------------------------------------- | ------------------------------------------------------ |
| ROS2 节点 | `ptz_service`（`ros_ws/`）                        | `ptz100_ros`（`src/app/`）                               |
| 工厂模式    | `PtzDevice::createDevice()` → `PtzDeviceHepu`   | 无工厂，硬编码在 `ptz_app.cpp`                                 |
| 视频接入    | RTSP 拉流                                         | RTSP 拉流                                                |
| 解码      | `GstSourceDecode`（NVDEC 硬解）                     | `GstSourceDecode`（NVDEC 硬解）                            |
| 推流      | `GstRtspClient` → UDP RTP → MediaMTX            | `GstRtspClient` → UDP RTP → MediaMTX                   |
| 控制协议    | 和普 HTTP/SDK（TCP 39020）                          | UDP 私有协议（`eth_link_ptz` + `ptz_protocol/`）             |
| SDK 位置  | `iotDevices/ptzHepuSDK/` + `thirdpart/hepuSdk/` | `thirdpart/naijie/` + `src/srv/eth_link/ptz_protocol/` |


**关键差异**：和普已有完整的 `PtzDeviceBase` → `PtzDeviceHepu` 工厂模式；耐杰没有 `PtzDeviceNaijie` 类，逻辑散落在 `ptz_app.cpp`（拉流）+ `alg_app.cpp`（推流）+ `eth_link_ptz`（控制）中。

> **视频相关代码迁移归属**：上表中的视频接入、解码、推流相关代码（GstSourceDecode、GstRtspClient、ShmTransferFrame）均迁移至 **LiveStream**，不归 PtzModule。PtzModule 仅迁移控制协议和状态上报部分。耐杰的拉流解码代码（`ptz_app.cpp`）和编码推流代码（`alg_app.cpp` 中 `image_get_thread`）均为嵌入式模块代码，需要迁移到 LiveStream。

---

## 二、目标架构

### 2.1 AimRT Module 设计

`PtzModule` 作为 AimRT Module，遵循 `Initialize` → `Start` → `Shutdown` 生命周期，统一管理所有 PTZ 设备的**控制和状态**。视频流链路由 LiveStream 负责。

```mermaid
flowchart TD
    FW[AimRT 框架] --> PTZ["PtzModule<br/>Initialize / Start / Shutdown"]

    PTZ --> FACTORY["PtzDevice 统一工厂<br/>createDevice(type)"]
    FACTORY --> HEPU["PtzDeviceHepu<br/>和普设备实现"]
    FACTORY --> NAIJIE["PtzDeviceNaijie<br/>耐杰设备实现"]

    PTZ --> CFG["Configurator<br/>ptz_config.yaml"]
    PTZ --> CH_CTRL["AimRT Channel<br/>订阅控制指令"]
    PTZ --> CH_STATUS["AimRT Channel<br/>发布状态上报"]
    PTZ --> CH_DEVICE["AimRT Channel<br/>发布设备上下线+能力"]

    HEPU --> HEPU_SDK["HepuPtz SDK<br/>控制+状态"]
    NAIJIE --> NJ_SDK["耐杰协议<br/>eth_link_ptz"]

    CH_DEVICE --> LIVE["LiveStream<br/>（视频流链路）"]
    CH_DEVICE --> DM["DeviceManager<br/>（设备管理）"]
    CH_STATUS --> DM
```



### 2.2 Module 生命周期

```mermaid
flowchart TD
    A[AimRT 框架加载 PtzModule] --> B["Initialize()"]
    B --> C["Start()"]
    C --> D["运行中"]
    D --> E["Shutdown()"]

    B --> B1[读取 ptz_config.yaml]
    B1 --> B2[注册 AimRT Channel 订阅/发布]
    B2 --> B3[初始化设备工厂]

    C --> C1[枚举在线设备]
    C1 --> C2[创建设备实例]
    C2 --> C3["发布设备上线通知<br/>（→ LiveStream + DeviceManager）"]
    C3 --> C4["发布设备能力<br/>（→ DeviceManager）"]
    C4 --> C5[启动状态上报定时器]

    E --> E1[停止所有设备 SDK 连接]
    E1 --> E2[发布设备离线通知]
    E2 --> E3[释放设备资源]
```



### 2.3 统一设备工厂

在现有 `PtzDevice` 工厂基础上扩展，增加耐杰设备类型注册：

```mermaid
classDiagram
    class PtzDeviceBase {
        <<abstract>>
        +Initialize(config) bool
        +Shutdown()
        +ctrlPtzGuidance(cmd) int32
        +ctrlPtzTrack(cmd) int32
        +ctrlPtzMotion(cmd) int32
        +ctrlPtzLens(cmd) int32
        +ctrlPtzManualLockTarget(cmd) int32
        +ctrlPtzSwitchTrack(cmd) int32
        +onAiDetectionResults(results)
        +GetStatus() PtzStatus
        +GetLensInfo() PtzLensInfo
        +GetAzimuthPitch() AzimuthPitchInfo
        +GetDeviceInfo() PtzDeviceInfo
        +GetCapability() PtzDeviceCapability
    }

    class PtzDeviceHepu {
        -deviceApi_ : HepuPtz
        -hepuSmart_ : PtzHepuSmart
        -ctrlHepuGuidance()
        -ctrlHepuTrack()
    }

    class PtzDeviceNaijie {
        -ethLinkPtz_ : EthLinkPtz
        -ctrlNaijieGuidance()
        -ctrlNaijieTrack()
        -sendPtzPackage(cmd)
    }

    class PtzDevice {
        <<factory>>
        +createDevice(type, config) unique_ptr~PtzDeviceBase~
    }

    PtzDeviceBase <|-- PtzDeviceHepu
    PtzDeviceBase <|-- PtzDeviceNaijie
    PtzDevice ..> PtzDeviceBase : creates
```



**工厂类型扩展**：


| 枚举值                   | 设备类型          | 实现类               | 状态     |
| --------------------- | ------------- | ----------------- | ------ |
| `PTZ_HEPU` (4)        | 和普三型 Z50（非制冷） | `PtzDeviceHepu`   | 迁移     |
| `PTZ_HEPU_COOLED` (6) | 和普四型 Z50（制冷）  | `PtzDeviceHepu`   | 迁移     |
| `PTZ_NAIJIE` (0)      | 耐杰近程 PTZ      | `PtzDeviceNaijie` | **新建** |
| `PTZ_NAIJIE_MID` (5)  | 耐杰中程 PTZ      | `PtzDeviceNaijie` | **新建** |


> 激光设备（HEF100/HEP10/HEP21）不再作为 PTZ 枚举预留，将归属独立的打击设备模块。

---

## 三、两条链路 + 设备管理接口

### 3.1 控制链路

> **控制架构核心原则**：PTZ 云台的转台运动（motion）、变焦（zoom）、聚焦（focus）等控制需要**统一的控制源**——即**引导节点**（旧架构中 `ptz100_guide_ai/ptz_guider_ctl`）。用户操作（来自 PC/天盾）也需先经引导节点处理后再统一下发到 PTZ 设备，而非直接控制。原因是引导节点需要协调多个控制源（用户手动、融合引导、AI 跟踪），避免冲突。
>
> 旧架构中，C2 的 0x8a（转台控制）和 0x8b（变焦/聚焦控制）指令通过 `alink_ctrl_ptz` / `alink_ctrl_ptz_zoom` → `ros_app_cmd_set()` → ROS2 `/cmd_set` → 引导节点 `cmdset_callback` → 引导节点统一输出 `/ptz_motion_cmd`、`/ptz_lens_cmd` 等 → PTZ 设备。
>
> 少数设备特有辅助功能（透雾、窗口加热、ICR 等）不影响云台指向，引导节点不关心，旧代码中由 `ros_app` 直接发布到 `/ptz_lens_cmd`（绕过引导节点），新架构中改为 Gateway 直接 RPC 调用 PtzModule。

**控制流分为三条路径**：

1. **路径 ①：用户操作 → 引导节点 → PtzModule**：用户通过 PC/天盾下发的转台/镜头控制指令，Gateway 发布 AimRT Channel `user/ptz_control_cmd` → 算法ROS2适配层订阅并转为 ROS2 `/cmd_set` → 引导节点处理后统一发布 `/ptz_motion_cmd`、`/ptz_lens_cmd` 等 → 算法ROS2适配层 → AimRT Channel → PtzModule
2. **路径 ②：AI视觉算法/融合算法 → 引导节点 → PtzModule**：融合节点将多源目标融合后提供给引导节点做指向决策，AI 视觉节点输出跟踪结果供引导节点做跟踪闭环。引导节点综合各来源的态势数据后，输出统一的控制 Topic
3. **路径 ③：设备直控（绕过引导节点）**：透雾、窗口加热、ICR 等设备特有辅助功能不影响云台指向，Gateway 直接 RPC 下发到 PtzModule

> **路径 ① 架构决策：为什么用户操作由 Gateway → 算法ROS2适配层，而不是 Gateway → PtzModule → 适配层？**
>
> ### **方案对比**
>
> **方案 A**：Gateway → AlgoROS2Adapter → 引导节点 → AlgoROS2Adapter → PtzModule
>
> **方案 B**：Gateway → PtzModule → AlgoROS2Adapter → 引导节点 → AlgoROS2Adapter → PtzModule
>
>
> | **维度**       | **方案 A（Gateway→适配层）**         | **方案 B（Gateway→PtzModule→适配层）**                      |
> | ------------ | ----------------------------- | ---------------------------------------------------- |
> | PtzModule 职责 | 纯设备驱动，只管"收指令→下发硬件"            | 既是设备驱动，又是命令路由器                                       |
> | 数据流          | 单向清晰                          | **环路**：PtzModule 先收命令转发，再收引导节点处理后的命令                 |
> | Gateway 配合   | 需发布一个 Channel（`user/ptz_cmd`） | 需调用 PtzModule 的 RPC/Channel                          |
> | Gateway 工作量  | 发布一个 Channel                  | 调用一个 RPC/Channel，**工作量一样**                           |
> | 耦合度          | Gateway 不感知内部路由               | PtzModule 必须感知 AlgoROS2Adapter 的存在                   |
> | 环路问题         | 无                             | **有**：PtzModule 收到用户指令 → 转发 → 引导节点处理 → 又回到 PtzModule |
>
>
> **关键问题是方案 B 的环路**：
>
> Gateway → PtzModule（第1次收到命令，但不能执行，要转发）

```
>      → AlgoROS2Adapter → 引导节点
>
>      → AlgoROS2Adapter → PtzModule（第2次收到命令，这次才执行）
> 
```

> PtzModule 需要区分"这是用户原始命令（要转发）"还是"这是引导节点处理后的命令（要执行）"——这会引入额外的状态判断逻辑，增加复杂度且容易出 bug。
>
> ### **其实 Gateway 的配合成本很低**
>
> 在 AimRT 的 pub/sub 模型中，Gateway 开发者的工作量其实**两种方案一样**：
>
> - 方案 A：Gateway 发布 Channel `user/ptz_cmd`，AlgoROS2Adapter 订阅
> - 方案 B：Gateway 发布 Channel 或调用 RPC 到 PtzModule
>
> 都是 Gateway 发一条消息出去，区别只是目标 Topic 名不同。AimRT Channel 是解耦的，**发布方不需要知道谁订阅**，Gateway 开发者只需要按约定的 Proto 格式发布即可，不需要关心后面是谁处理。

---

> 【注】曾考虑过"Gateway → PtzModule → 算法ROS2适配层 → 引导节点 → 算法ROS2适配层 → PtzModule"方案，这样 PtzModule 开发者可独立控制全流程，无需 Gateway 开发者额外配合。但分析后**否决**，原因如下：
>
> 1. **环路问题**：PtzModule 会两次收到同一条指令——第一次从 Gateway 收到（需转发不执行），第二次从引导节点收到（需执行不转发），必须引入额外的状态判断逻辑区分"转发"和"执行"，增加复杂度且容易出 bug
> 2. **职责污染**：PtzModule 的定位是**纯设备驱动层**（收指令 → 翻译为设备私有协议 → 下发硬件），不应承担命令路由职责
> 3. **Gateway 配合成本其实一样**：在 AimRT 的 pub/sub 模型中，Gateway 无论发到哪个 Channel（发给适配层的 `user/ptz_control_cmd` 还是发给 PtzModule 的某个 Topic），工作量都是"按约定 Proto 格式发布一条消息"，没有额外成本
> 4. **AimRT Channel 天然解耦**：Gateway 发布者不需要知道谁订阅，只需发布到约定的 Channel Topic，算法ROS2适配层自行订阅并转为 ROS2 `/cmd_set`
>
> 因此采用方案 A：**Gateway 发布用户操作 Channel → 算法ROS2适配层订阅并转为 ROS2 `/cmd_set` → 引导节点处理 → 输出控制 Topic → 算法ROS2适配层转为 AimRT Channel → PtzModule 执行**。PtzModule 保持纯设备驱动，职责单一，无环路。

```mermaid
flowchart LR
    subgraph 外部用户
        PC["PC 浏览器"]
        TD["天盾"]
    end

    subgraph TerraHub["TerraHub（AimRT 进程）"]
        WGW["WebGateway"]
        NGW["NexusGateway"]
        BRIDGE["AlgoROS2Adapter<br/>算法ROS2适配层<br/>AimRT ↔ ROS2 转换"]
        PTZ["PtzModule<br/>指令分发 → 设备"]
    end

    subgraph ROS2["ROS2 世界（保留）"]
        GUID["引导节点<br/>ptz_guider_ctl<br/>（统一控制源）"]
        AI["AI 视觉节点"]
    end

    PC -->|"HTTP/WS"| WGW
    TD -->|"MQTT"| NGW

    WGW -->|"①Channel: user/ptz_control_cmd"| BRIDGE
    NGW -->|"①Channel: user/ptz_control_cmd"| BRIDGE

    BRIDGE -->|"/cmd_set<br/>（用户操作转为ROS2）"| GUID
    GUID -->|"②引导统一输出<br/>/ptz_motion_cmd<br/>/ptz_lens_cmd<br/>/ptz_guidance_cmd 等"| BRIDGE

    AI -->|"/visiblelight_track_objs<br/>/infrared_track_objs"| BRIDGE

    BRIDGE -->|"AimRT Channel<br/>（6个控制+AI结果）<br/>全部 Channel"| PTZ

    WGW -->|"路径③: 设备直控 RPC<br/>透雾/加热/ICR"| PTZ
    NGW -->|"路径③: 设备直控 RPC<br/>透雾/加热/ICR"| PTZ
```



**PtzModule 订阅的控制接口（全部来自引导节点，经算法ROS2适配层转发，均为 AimRT Channel）**：


| 现有 ROS2 Topic（ptz100_agx）         | 发布方  | 迁移后 AimRT Channel                | 消息类型 (pb)                | 通信方式        | 说明                        |
| --------------------------------- | ---- | -------------------------------- | ------------------------ | ----------- | ------------------------- |
| `/ptz_guidance_cmd`               | 引导节点 | `ptz/guidance_cmd`               | `PtzGuidanceCmd`         | **Channel** | 引导控制（方位角/俯仰角指向），~3-5Hz    |
| `/ptz_track_cmd`                  | 引导节点 | `ptz/track_cmd`                  | `PtzTrackCmd`            | **Channel** | 跟踪控制（启停/搜索），事件触发          |
| `/ptz_motion_cmd`                 | 引导节点 | `ptz/motion_cmd`                 | `PtzMotionCmd`           | **Channel** | 转台运动（方向/速度），用户操作经引导节点统一输出 |
| `/ptz_lens_cmd`                   | 引导节点 | `ptz/lens_cmd`                   | `PtzLensCmd`             | **Channel** | 镜头控制（变焦/聚焦），用户操作经引导节点统一输出 |
| `/ptz_manual_lock_target_cmd`     | 引导节点 | `ptz/manual_lock_target_cmd`     | `PtzManualLockTargetCmd` | **Channel** | 手动锁定目标，用户操作经引导节点输出        |
| `/ptz_switch_tracking_source_cmd` | 引导节点 | `ptz/switch_tracking_source_cmd` | `PtzSwitchTrackCmd`      | **Channel** | 切换跟踪视频源（可见光/红外）           |


**PtzModule 订阅的 AI 检测结果（来自 AI 模块，经算法ROS2适配层转发）**：


| 现有 ROS2 Topic                                     | 发布方     | 迁移后 AimRT Channel     | 消息类型 (pb)       | 通信方式        | 说明                                          |
| ------------------------------------------------- | ------- | --------------------- | --------------- | ----------- | ------------------------------------------- |
| `/visiblelight_track_objs`、`/infrared_track_objs` | AI 视觉节点 | `ptz/ai_track_result` | `AiTrackResult` | **Channel** | AI 检测/跟踪结果回传设备（和普用于替代智能分析盒子），帧率驱动 ~15-25fps |


**PtzModule 提供的设备直控 RPC（绕过引导节点，Gateway 直接调用）**：

> 旧架构中 `alink_ctrl_ptz` 0x8a 指令中，透雾/加热等功能直接调用 `ros_app_pub_hepu_ptz_defog()`、`ros_app_pub_hepu_ptz_window_heat()` 发布到 `/ptz_lens_cmd`，绕过引导节点的 `/cmd_set` 路径。新架构中改为 Gateway 直接 RPC 调用 PtzModule。


| RPC 方法                 | 请求/响应                               | 调用方                                | 说明                |
| ---------------------- | ----------------------------------- | ---------------------------------- | ----------------- |
| `PtzDefogControl`      | `PtzDefogCmd` → `PtzCmdResult`      | WebGateway（←PC）/ NexusGateway（←天盾） | 和普透雾开关（引导节点不关心）   |
| `PtzWindowHeatControl` | `PtzWindowHeatCmd` → `PtzCmdResult` | 同上                                 | 和普窗口加热开关（引导节点不关心） |
| `PtzIcrControl`        | `PtzIcrCmd` → `PtzCmdResult`        | 同上                                 | ICR 日夜切换（引导节点不关心） |


**协议转换不变**：

- **和普**：回调内部调用 `HepuPtzCtrl` SDK（TCP 39020），逻辑从 `ptz_service/rosService` 搬到 `PtzModule` 回调
- **耐杰**：回调内部组装 `ptz_protocol_msg_t`（`ptz_protocol/` 中定义的私有协议结构），通过 `sendPtzPackage()` → UDP 下发到耐杰 PTZ，逻辑从 `ros_app` + `eth_link_ptz` 搬到 `PtzDeviceNaijie`

### 3.2 状态上报链路

> **现状说明**：下表左列为 `**ptz100_agx` 现有代码**中的 ROS2 Topic，右列为迁移后的 AimRT Channel。状态上报全部使用 **Channel**（一对多广播），供 DeviceManager、WebGateway（→PC 浏览器）、NexusGateway（→天盾）、算法ROS2适配层（→融合/引导算法）订阅。

**现有 ROS2 Topic → AimRT Channel 迁移映射**：


| 现有 ROS2 Topic（ptz100_agx 现状） | 迁移后 AimRT Channel        | 消息类型 (pb)          | 频率    | 订阅方                                                          |
| ---------------------------- | ------------------------ | ------------------ | ----- | ------------------------------------------------------------ |
| `/ptz_status`                | `ptz/status`             | `PtzStatus`        | 10 Hz | DeviceManager, WebGateway（→PC）, NexusGateway（→天盾）, 算法ROS2适配层 |
| `/ptz_lens_info`             | `ptz/lens_info`          | `PtzLensInfo`      | 10 Hz | WebGateway（→PC）, NexusGateway（→天盾）, 算法ROS2适配层（→融合/AI）        |
| `/ptz_azimuth_pitch_info`    | `ptz/azimuth_pitch_info` | `AzimuthPitchInfo` | 10 Hz | 算法ROS2适配层（→融合/引导）, NexusGateway（→天盾）                         |
| `/ptz_device_info`           | `ptz/device_info`        | `PtzDeviceInfo`    | 10 Hz | DeviceManager, WebGateway（→PC）, NexusGateway（→天盾）            |


### 3.3 设备管理与上层 Module 接口

PtzModule 与 DeviceManager、LiveStream、WebGateway 等模块之间的交互：


| AimRT Channel                    | 方向                                                            | 消息类型                          | 说明                                  |
| -------------------------------- | ------------------------------------------------------------- | ----------------------------- | ----------------------------------- |
| `device/ptz_online`              | PtzModule → LiveStream, DeviceManager                         | `PtzOnlineNotify` (pb)        | 设备上线通知（SN、type、IP、相机列表、RTSP URL）    |
| `device/ptz_offline`             | PtzModule → LiveStream, DeviceManager                         | `PtzOfflineNotify` (pb)       | 设备离线通知                              |
| `device/ptz_capability`          | PtzModule → DeviceManager                                     | `PtzDeviceCapability` (pb)    | 设备能力上报（相机列表、支持跟踪/引导/镜头控制等）          |
| `ptz/status`                     | PtzModule → DeviceManager, WebGateway（→PC）, NexusGateway（→天盾） | `PtzStatus` (pb)              | 设备状态                                |
| `ptz/guidance_cmd`               | 引导节点（经算法ROS2适配层）→ PtzModule                                   | `PtzGuidanceCmd` (pb)         | 引导控制指令（proto 在 `protocols/fusion/`） |
| `ptz/track_cmd`                  | 引导节点（经算法ROS2适配层）→ PtzModule                                   | `PtzTrackCmd` (pb)            | 跟踪控制指令（proto 在 `protocols/fusion/`） |
| `ptz/motion_cmd`                 | 引导节点（经算法ROS2适配层）→ PtzModule                                   | `PtzMotionCmd` (pb)           | 转台运动（用户操作经引导节点统一输出）                 |
| `ptz/lens_cmd`                   | 引导节点（经算法ROS2适配层）→ PtzModule                                   | `PtzLensCmd` (pb)             | 镜头控制（用户操作经引导节点统一输出）                 |
| `ptz/manual_lock_target_cmd`     | 引导节点（经算法ROS2适配层）→ PtzModule                                   | `PtzManualLockTargetCmd` (pb) | 手动锁定目标                              |
| `ptz/switch_tracking_source_cmd` | 引导节点（经算法ROS2适配层）→ PtzModule                                   | `PtzSwitchTrackCmd` (pb)      | 切换跟踪视频源                             |
| `ptz/ai_track_result`            | AI Module（经算法ROS2适配层）→ PtzModule                              | `AiTrackResult` (pb)          | AI 检测结果（回传设备做跟踪闭环）                  |


```mermaid
flowchart LR
    subgraph ROS2["ROS2 算法节点（不参与重构）"]
        GUID["引导节点\nptz_guider_ctl"]
        AI["AI 视觉节点"]
    end

    subgraph AimRT["TerraHub AimRT 进程"]
        ADAPTER["AlgoROS2Adapter\n算法ROS2适配层"]
        PTZ["PtzModule"]
        LIVE["LiveStream"]
        WGW["WebGateway"]
        NGW["NexusGateway"]
        DM["DeviceManager"]
    end

    GUID -->|"guidance_cmd\nmotion_cmd\nlens_cmd"| ADAPTER
    GUID -->|"track_cmd\nmanual_lock_target_cmd\nswitch_tracking_source_cmd"| ADAPTER
    AI -->|"visiblelight_track_objs\ninfrared_track_objs"| ADAPTER

    ADAPTER -->|"Channel:\nptz/guidance_cmd\nptz/motion_cmd\nptz/lens_cmd"| PTZ
    ADAPTER -->|"Channel:\nptz/track_cmd\nptz/ai_track_result\n等"| PTZ

    PTZ -->|"Channel:\nptz/status\nptz/azimuth_pitch_info"| ADAPTER
    ADAPTER -->|"ROS2 Topic"| GUID

    PTZ -->|"device/ptz_online\ndevice/ptz_offline"| LIVE
    PTZ -->|"device/ptz_online\nptz_capability\nptz/status"| DM
    PTZ -->|"ptz/status\nptz/lens_info"| WGW
    PTZ -->|"ptz/status\nazimuth_pitch_info"| NGW
```



---

## 四、目录结构

`Ptz/` 根目录放 **PTZ 公共文件**（Module 入口、抽象基类、工厂、配置），各设备型号的独有实现按 `{厂家}Ptz/` 子目录组织（与 skill 目录规范一致：`Ptz/HepuPtz/`、`Ptz/NaijiePtz/`）。Protobuf 定义放在仓库级 `protocols/device/ptz/` 目录。

```
TerraHub/src/02_DevAbsLayer/01_Detector/Ptz/
│
│   ── 公共文件（Module 入口 + 设备抽象 + 工厂）──
├── CMakeLists.txt
├── ptz_module.h                    # PtzModule 类定义（AimRT Module）
├── ptz_module.cpp                  # PtzModule 实现（Initialize/Start/Shutdown）
├── ptz_config.yaml                 # 设备配置（设备列表、IP、端口等）
├── ptz_device_base.h               # PtzDeviceBase 抽象基类（控制+状态接口）
├── ptz_device_factory.h            # PtzDevice 工厂（按 type 创建设备）
├── ptz_device_factory.cpp
│
│   ── 和普 PTZ ──
├── HepuPtz/
│   ├── hepu_ptz_device.h           # 和普设备实现
│   ├── hepu_ptz_device.cpp
│   ├── hepu_ptz_ctrl.h             # 和普控制协议封装（从 iotDevices/ptzHepuSDK/ 迁入）
│   ├── hepu_ptz_ctrl.cpp
│   ├── hepu_ptz_smart.h            # AI 结果回传和普（UDP 39080）
│   └── sdk/
│       └── hepuSdk/                # 和普厂家 SDK（头文件 + 预编译库，从 thirdpart/hepuSdk/ 迁入）
│
│   ── 耐杰 PTZ（无 SDK，通过 UDP 私有协议直接通信）──
├── NaijiePtz/
│   ├── naijie_ptz_device.h         # 耐杰设备实现（新建）
│   ├── naijie_ptz_device.cpp
│   ├── naijie_eth_link.h           # 耐杰以太网 UDP 协议封装（从 src/srv/eth_link/ 迁入，重命名）
│   ├── naijie_eth_link.cpp
│   └── naijie_protocol/            # 耐杰 UDP 协议定义（从 src/srv/eth_link/ptz_protocol/ 迁入）
│       ├── naijie_ptz_control.h
│       └── naijie_ptz_protocol.h

TerraHub/protocols/device/ptz/       # Protobuf 消息定义（仓库级）
├── hepu.proto                       # 和普设备消息（状态+控制+设备信息+能力）
└── naijie.proto                     # 耐杰设备消息（同上）

TerraHub/protocols/fusion/           # 引导类指令（融合算法模块定义）
└── ptz_guidance.proto               # PtzGuidanceCmd、PtzTrackCmd 等
```

---

## 五、SDK 迁移策略

### 5.1 和普 SDK

和普 PTZ 通过厂家提供的 SDK（预编译库 + 头文件）进行控制和状态查询。


| 来源                       | 目标                            | 说明                                |
| ------------------------ | ----------------------------- | --------------------------------- |
| `iotDevices/ptzHepuSDK/` | `Ptz/HepuPtz/hepu_ptz_ctrl.*` | 和普控制协议封装（`HepuPtz`、`HepuPtzCtrl`） |
| `thirdpart/hepuSdk/`     | `Ptz/HepuPtz/sdk/hepuSdk/`    | 和普厂家 SDK（头文件 + 预编译库）              |


### 5.2 耐杰协议

> **耐杰 PTZ 不使用 SDK**，而是通过 **UDP 私有协议**直接与 PTZ 设备通信。协议的组包/解包逻辑在 `ptz_protocol/` 中定义，通过 `eth_link_ptz` 封装 UDP 收发。


| 来源                                  | 目标                                | 说明                  |
| ----------------------------------- | --------------------------------- | ------------------- |
| `src/srv/eth_link/eth_link_ptz.cpp` | `Ptz/NaijiePtz/naijie_eth_link.*` | 耐杰以太网 UDP 协议封装（重命名） |
| `src/srv/eth_link/ptz_protocol/`    | `Ptz/NaijiePtz/naijie_protocol/`  | 耐杰 UDP 协议定义（组包/解包）  |


### 5.3 路径变更说明

和普 SDK 从 Infra 层 `thirdpartylibs/` 移入 `Ptz/HepuPtz/sdk/` 目录，保持设备代码与 SDK 的内聚性。耐杰无厂家 SDK，协议代码从 `src/srv/eth_link/` 迁入 `Ptz/NaijiePtz/` 并统一重命名。CMake 中只需调整 `target_link_directories` 和 `target_include_directories`。

---

## 六、迁移步骤

### 阶段一：和普 PTZ（优先，P0）


| 步骤  | 工作内容                          | 来源 → 目标                                                                   |
| --- | ----------------------------- | ------------------------------------------------------------------------- |
| 1   | 创建 PtzModule 骨架               | 新建 `ptz_module.h/cpp`，实现 AimRT Module 生命周期                                |
| 2   | 迁移 PtzDeviceBase 基类（仅控制+状态）   | `ptz_service/src/ptzDevice/ptzDeviceBase.h` → `ptz_device_base.h`（移除视频成员） |
| 3   | 迁移 PtzDeviceHepu 实现（仅控制+状态）   | `ptz_service/src/ptzDevice/ptzDeviceHepu.h/cpp` → `hepu/`（移除推流线程）         |
| 4   | 迁移和普控制封装                      | `iotDevices/ptzHepuSDK/` → `hepu/hepu_ptz_ctrl.h/cpp`                     |
| 5   | 迁移和普 SDK                      | `thirdpart/hepuSdk/` → `sdk/hepuSdk/`                                     |
| 6   | 迁移工厂类                         | `ptz_service/src/ptzDevice/ptzDevice.h` → `ptz_device_factory.h`          |
| 7   | 替换 ROS2 Topic 为 AimRT Channel | `rosService.cpp` 中的订阅/发布逻辑改为 AimRT Channel                                |
| 8   | 定义 Protobuf 消息                | 填充 `protocols/device/ptz/hepu.proto`                                      |
| 9   | 实现 DeviceManager 上报接口         | 发布 `device/ptz_online`、`device/ptz_capability`、`ptz/status` 等 Channel     |
| 10  | 编写 CMakeLists.txt             | 链接 skyfendlibs、hepuSdk 等依赖                                                |
| 11  | 集成测试                          | 验证控制、状态上报两条链路 + DeviceManager 通知                                          |


### 阶段二：耐杰 PTZ


| 步骤  | 工作内容                  | 来源 → 目标                                                            |
| --- | --------------------- | ------------------------------------------------------------------ |
| 1   | 新建 PtzDeviceNaijie 子类 | 参考 `PtzDeviceHepu` 实现 `PtzDeviceNaijie`（仅控制+状态）                    |
| 2   | 迁移耐杰控制协议封装            | `src/srv/eth_link/eth_link_ptz.cpp` → `naijie/eth_link_ptz.cpp`    |
| 3   | 迁移耐杰协议定义              | `src/srv/eth_link/ptz_protocol/` → `naijie/ptz_protocol/`          |
| 4   | 迁移耐杰 SDK              | `thirdpart/naijie/` → `sdk/naijie/`                                |
| 5   | 扩展工厂注册                | 在 `PtzDevice::createDevice()` 中增加 `PTZ_NAIJIE`、`PTZ_NAIJIE_MID` 分支 |
| 6   | 定义 Protobuf 消息        | 填充 `protocols/device/ptz/naijie.proto`                             |
| 7   | 集成测试                  | 验证耐杰控制、状态上报两条链路                                                    |


> **注**：耐杰的视频代码（`ptz_app.cpp` 拉流解码 + `alg_app.cpp` 编码推流）迁移到 **LiveStream**，不在本阶段范围。

---

## 七、耐杰 PtzDeviceNaijie 设计要点

耐杰设备**没有工厂模式**，逻辑严重散落在 6+ 个源文件中，耦合度远高于和普。解耦工作量不小，需逐层梳理。

### 7.1 代码散落全景（按职责分类）

#### A. 协议栈层（UDP 私有协议 —— 迁移到 PtzDeviceNaijie）


| 功能              | 现有文件                                                   | 函数/代码段                                                                                                          | 迁移目标                               |
| --------------- | ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| UDP 收发 + 回调分发   | `src/srv/eth_link/eth_link_ptz.cpp`                    | `eth_protocol_handler`、`send_ptz_package`、`eth_ptz_command_register`、`eth_link_ptz_init/uninit`                 | `naijie/eth_link_ptz.h/cpp`        |
| 打包/拆包/CRC       | `src/srv/eth_link/ptz_protocol/ptz_control_protocol.c` | `ptz_protocol_package`、`ptz_protocol_network_data_analysis`、`ptz_protocol_crc_cal`                              | `naijie/ptz_protocol/`             |
| 各控制命令字段填充       | `src/srv/eth_link/ptz_protocol/ptz_control.c`          | `send_ptz_control_addr`、`send_ptz_control_track`、`send_ptz_peripheral_ctrl`、`send_ptz_ai_ctrl` 等全部 `send_ptz_*` | `naijie/ptz_protocol/`             |
| TMCC/设备搜索（并行封装） | `src/srv/eth_link/ptz_protocol/ptz_tmcc.cpp`           | `tmcc_search_device_init`、`tmcc_control_init`、`tmcc_control_set`                                                | `naijie/ptz_protocol/`             |
| 设备信息查询          | `eth_link_ptz.cpp`                                     | `get_ptz_dev_info`、`get_ptz_dev_ip`、`ptz_connect_status`                                                        | `PtzDeviceNaijie::GetDeviceInfo()` |


#### B. 状态解析层（协议上行回调 —— 迁移到 PtzDeviceNaijie）

> **关键发现**：大量耐杰状态解析代码在 `ai_main.cpp` 中，而非 `ptz_app.cpp`。


| 功能            | 现有文件                              | 函数/代码段                                           | 行号(约)    | 迁移目标                                    |
| ------------- | --------------------------------- | ------------------------------------------------ | -------- | --------------------------------------- |
| 俯仰/方位角解析      | `src/srv/algs/ai_alg/ai_main.cpp` | `ptz_pitch_azimuth`                              | 118-164  | `PtzDeviceNaijie::onAzimuthPitchData()` |
| 设备基础状态        | `ai_main.cpp`                     | `ptz_dev_status`                                 | 181-204  | `PtzDeviceNaijie::onDeviceStatus()`     |
| 扩展工作状态（搜索/跟踪） | `ai_main.cpp`                     | `ptz_dev_ext_info_0x08`                          | 211-285  | `PtzDeviceNaijie::onExtWorkStatus()`    |
| 镜头 FOV/焦距/变焦  | `ai_main.cpp`                     | `ptz_lense_ext_info_0x0c`                        | 325-351  | `PtzDeviceNaijie::onLensInfo()`         |
| AI 目标列表→融合    | `ai_main.cpp`                     | `ptz_target_info`、`nature_result2ai_target_info` | 287-323  | **→ AI/融合模块**（不归 PtzModule）             |
| 目标丢失 QS 包     | `ai_main.cpp`                     | `ptz_target_missing_qs_msg`                      | 166-178  | `PtzDeviceNaijie::onTargetMissing()`    |
| 系统扩展信息        | `ptz_app.cpp`                     | `ptz_sys_ext_info_0x15`                          | 428-437  | `PtzDeviceNaijie` 内部处理                  |
| 状态→ROS 发布     | `ros_app.cpp`                     | `convert_ptzinfo2Rosmsg`                         | 881-1099 | `PtzModule` AimRT Channel 发布            |


#### C. 控制指令层（上层→耐杰 —— 迁移到 PtzDeviceNaijie）


| 功能         | 现有文件          | 函数/代码段                                                     | 行号(约)     | 迁移目标                                                  |
| ---------- | ------------- | ---------------------------------------------------------- | --------- | ----------------------------------------------------- |
| ROS 引导→指向  | `ros_app.cpp` | `ptzGuidanceCmd_callback`                                  | 1181-1202 | `PtzDeviceNaijie::ctrlPtzGuidance()`                  |
| ROS 跟踪命令   | `ros_app.cpp` | `ptzTrackCmd_callback`                                     | 1204-1224 | `PtzDeviceNaijie::ctrlPtzTrack()`                     |
| ROS 方向/速度  | `ros_app.cpp` | `ptzMotion_callback`                                       | 1226-1245 | `PtzDeviceNaijie::ctrlPtzMotion()`                    |
| ROS 镜头控制   | `ros_app.cpp` | `ptzLenCmd_callback`                                       | 1271-1341 | `PtzDeviceNaijie::ctrlPtzLens()`                      |
| ROS 手动锁定   | `ros_app.cpp` | `ptzManualLockTargetCmd_callback`                          | 1343-1376 | `PtzDeviceNaijie::ctrlPtzManualLockTarget()`          |
| ROS 切换跟踪源  | `ros_app.cpp` | `ptzSwitchTrackingSourceCmd_callback`                      | 1247-1262 | `PtzDeviceNaijie::ctrlPtzSwitchTrack()`               |
| ROS→协议转发   | `ptz_app.cpp` | `ptz_packet_ckb_handle`、`ptz_data_2_ros_data`              | 439-508   | PtzModule 回调 → `PtzDeviceNaijie`                      |
| AI 直接指向/变焦 | `ai_main.cpp` | `setPTZ*`、`SetCameraZoom`、`PTZTracking`、`StoppingTracking` | 364-530   | **→ 融合/AI 模块通过 AimRT Channel 下发**，PtzDeviceNaijie 只接收 |
| 雷达引导 PTZ   | `ai_main.cpp` | `radarGuide*`、`radar_2ptz`、Tracer 引导分支                     | 617-1112  | **→ 融合模块**（PtzGuidanceCmd Channel），不归 PtzModule       |
| 搜索跟踪       | `ai_main.cpp` | `SearchAndTracking`                                        | 1106-1112 | **→ 融合模块**（PtzTrackCmd Channel）                       |


#### D. 视频链路（迁移到 LiveStream，不归 PtzModule）


| 功能             | 现有文件          | 函数/代码段                                           | 迁移目标                                        |
| -------------- | ------------- | ------------------------------------------------ | ------------------------------------------- |
| RTSP 拉流解码      | `ptz_app.cpp` | `load_ptz()` 中 GstSourceDecode 初始化               | **→ LiveStream**                            |
| SHM 原始帧写入      | `ptz_app.cpp` | `shmTransferFrame` 调用                            | **→ LiveStream**                            |
| AI 结果读取 + 编码推流 | `alg_app.cpp` | `image_get_thread` / `image_get_thread_infrared` | **→ LiveStream**                            |
| 推流 RTSP URL 获取 | `ptz_app.cpp` | `push_frame_to_c2*` 内 `get_ptz_dev_info`         | **→ LiveStream**（通过 PtzOnlineNotify 携带 URL） |


#### E. Alink/C2 侧（新架构废弃，不迁移）


| 功能                 | 现有文件                                         | 说明             |
| ------------------ | -------------------------------------------- | -------------- |
| C2 查 PTZ 设备信息      | `alink_system.cpp` → `alink_get_ptzdev_info` | 新架构无 C2 app，废弃 |
| 俯仰方位→Alink 0xEC 上报 | `ai_main.cpp` → `alink_upload_ptz_info`      | 新架构废弃 Alink 上报 |
| 跟踪状态→Alink 上报      | `ros_app.cpp` → `alink_upload_track_status`  | 新架构废弃          |
| Alink 控制 PTZ       | `alink_system.cpp` → `alink_ctrl_ptz*`       | 新架构废弃          |


#### F. 全局状态/枚举（需解耦）


| 类型                                | 现有位置               | 说明                         |
| --------------------------------- | ------------------ | -------------------------- |
| `realtime_pa_t` 实时角度缓存            | `ai_main.cpp` 全局变量 | 迁移到 `PtzDeviceNaijie` 成员变量 |
| `lens_information` 镜头缓存           | `ai_main.cpp` 全局变量 | 迁移到 `PtzDeviceNaijie` 成员变量 |
| `PTZ_TRACKING_STATUS_RESPONSE` 枚举 | `embed_api.h`      | 在 `naijie.proto` 中重新定义     |
| `ALINK_DEV_TYPE_*PTZ` 枚举          | `embed_api.h`      | PtzType 枚举中对应              |
| `g_detect_camera_mode` 等全局        | `ros_app.cpp`      | 解耦到 PtzModule 配置           |


### 7.2 解耦难点分析


| 难点                       | 影响范围                                                             | 解耦策略                                                                                                           |
| ------------------------ | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `**ai_main.cpp` 耦合最重**   | 方位角解析、镜头信息、设备状态、AI引导控制全在此文件，约 1000 行耐杰相关代码                       | 状态解析回调迁移到 `PtzDeviceNaijie`；引导控制（`setPTZ*`、`radarGuide*`）属于融合算法逻辑，迁移到融合模块，通过 AimRT Channel（`PtzGuidanceCmd`）下发 |
| **回调注册链**                | `ptz_app.cpp` → `eth_ptz_command_register` → 回调函数在 `ai_main.cpp` | 新架构中 `PtzDeviceNaijie` 自己注册回调，回调内部更新设备状态并通过 Channel 发布                                                         |
| **Alink 上报与状态混合**        | `ptz_pitch_azimuth` 在解析方位角的同时调用 `alink_upload_ptz_info`          | 拆分：状态解析归 `PtzDeviceNaijie`，上报归上层模块订阅 Channel                                                                   |
| `**embed_api` 全局状态**     | `realtime_pa_t`、`lens_information` 等全局变量被多个模块读写                  | 将 PTZ 相关状态收敛到 `PtzDeviceNaijie` 成员变量，通过 AimRT Channel 发布供外部订阅                                                  |
| **AI 直接调用 `send_ptz_*`** | `ai_main.cpp` 中 AI 算法直接调用协议发送函数控制耐杰                              | 新架构中 AI/融合模块通过 AimRT Channel 发送 `PtzGuidanceCmd`/`PtzTrackCmd`，PtzModule 订阅后转发到设备                              |


### 7.3 关键注意事项

1. **不迁移 FFmpeg 旧代码**：`src/app/ptz/ffmpeg/` 已弃用，不迁移
2. **不迁移 Alink 相关逻辑**：新架构已无 C2 app 和 Alink 协议，原 `alink_upload_ptz_info`、`alink_upload_track_status`、`alink_ctrl_ptz` 等整体废弃
3. `**ai_main.cpp` 需分拆**：其中约 200 行状态解析回调归 `PtzDeviceNaijie`，约 800 行引导/跟踪控制归融合模块，AI 目标列表处理归 AI 模块。这三块在新架构中通过 AimRT Channel 解耦
4. **视频代码归 LiveStream**：耐杰拉流（`ptz_app.cpp` 中 GstSourceDecode）和推流（`alg_app.cpp` 中 GstRtspClient + `image_get_thread`）均为嵌入式代码，迁移到 LiveStream，不归 PtzModule
5. `**ros_app.cpp` ROS 回调→AimRT Channel**：7 个 ROS 订阅回调的逻辑不变，仅替换为 AimRT Channel 订阅回调，内部仍调用 `PtzDeviceNaijie` 的控制方法

---

## 八、配置文件设计

`ptz_config.yaml`（AimRT Module 配置，由 Configurator 加载）。PtzModule 仅需设备基础信息（SN、type、IP、控制端口、RTSP URL），视频编码参数和 SHM 命名由 LiveStream 的 `livestream_config.yaml` 管理。

```yaml
ptz:
  devices:
    - sn: "PTZ-HEPU-001"
      type: 4                          # PTZ_HEPU
      ip: "192.168.1.100"
      control_port: 39020              # 和普 TCP 控制端口
      visible_url: "rtsp://admin:Abc.12345@192.168.1.100:554/ch0/stream1"
      thermal_url: "rtsp://admin:Abc.12345@192.168.1.100:554/ch1/stream1"
      visible_resolution: [1920, 1080]
      thermal_resolution: [640, 512]

    - sn: "PTZ-NAIJIE-001"
      type: 0                          # PTZ_NAIJIE
      ip: "192.168.1.101"
      visible_url: "rtsp://192.168.1.101/channel=0,stream=0"
      thermal_url: "rtsp://192.168.1.101/channel=1,stream=1"
      visible_resolution: [1920, 1080]
      thermal_resolution: [640, 512]
```

> **RTSP URL 在配置中保留**：虽然 PtzModule 不做视频处理，但设备上线通知（`PtzOnlineNotify`）需携带 RTSP URL 和分辨率信息，供 LiveStream 创建视频 Pipeline。

**与现有配置的关系**：


| 现有配置                        | TerraHub 对应          | 说明                        |
| --------------------------- | -------------------- | ------------------------- |
| `config/ptzDevicesCfg.yaml` | `ptz_config.yaml`    | 合并到 AimRT Module 配置中      |
| `PtzDevicesCfg` 单例          | AimRT `Configurator` | 通过 `GetConfigurator()` 读取 |


---

## 九、Protobuf 消息定义

Proto 文件按**设备类别**组织（而非具体设备型号），一个 proto 文件定义该类别所有设备共用的模块间通信消息。设备型号差异在 PtzModule 内部通过 C++ 工厂模式（`PtzDeviceHepu` / `PtzDeviceNaijie`）处理，不暴露到 Proto 层。引导类指令（来自融合算法）放在 `protocols/fusion/` 目录。

基于现有 ROS2 `.msg` 字段（`skyfend_interfaces/msg/ptz_msg/`）1:1 映射为 proto3。

### 9.1 `protocols/device/ptz/ptz.proto`

> **为什么合并为一个 `ptz.proto`，而非 `hepu.proto` + `naijie.proto`**：
>
> - Proto 文件用于**模块间通信**（PtzModule ↔ Gateway / DeviceManager / AlgoROS2适配层 / LiveStream），消费方不感知底层是和普还是耐杰，只关心统一的 `PtzStatus`、`PtzMotionCmd` 等消息类型
> - PtzModule 内部与具体设备的通信是 C++ 原生调用（SDK/UDP 私有协议），不经过 Protobuf 序列化
> - 设备型号通过 `device_sn` 和 `device_type` 字段区分，无需拆分 Proto 文件
> - 原有的 `hepu.proto` 和 `naijie.proto` 空文件合并为单一 `ptz.proto`（`package terrahub.device.ptz`）
>
> 以下 message 定义基于原 `ptz100_agx` 中 `skyfend_interfaces/msg/ptz_msg/` 的 ROS2 消息转换而来。最终字段需与 SAPIENT 协议对齐后确定。
>
> **说明**：PtzModule 不直接与天盾或 PC 浏览器通信，只需定义好自身的 SAPIENT Protobuf 消息，供 NexusGateway / WebGateway / DeviceManager 等对接模块订阅使用。Gateway 与外部系统（天盾 MQTT、PC HTTP/WS）的协议由 Gateway 负责人定义，不阻塞 PtzModule 的 Proto 开发。

**状态数据**（PtzModule 发布，10 Hz）：

```protobuf
syntax = "proto3";
package terrahub.device.ptz;

message PtzStatus {
  string device_sn = 1;
  uint64 timestamp_ms = 2;
  uint32 work_status = 3;           // 0=离线 1=在线 2=故障
  uint32 work_mode = 4;             // 0=待机 1=搜索 2=跟踪 3=引导
  uint32 tracking_video_source = 5; // 0=可见光 1=红外
  uint32 tracking_status = 6;       // 0=未跟踪 1=跟踪中 2=目标丢失
  float ir_power = 7;               // 红外功率
  bool defog_on = 8;                // 透雾状态
  bool window_heat_on = 9;          // 窗口加热状态
  uint32 icr_mode = 10;             // ICR 日夜模式
  string firmware_version = 11;
}

message PtzLensInfo {
  string device_sn = 1;
  uint64 timestamp_ms = 2;
  // 可见光镜头
  float visible_fov_h = 3;          // 水平视场角
  float visible_fov_v = 4;          // 垂直视场角
  float visible_zoom = 5;           // 变焦倍率
  float visible_focal = 6;          // 焦距 mm
  float visible_focus = 7;          // 聚焦位置
  uint32 visible_resolution_w = 8;
  uint32 visible_resolution_h = 9;
  // 红外镜头
  float infrared_fov_h = 10;
  float infrared_fov_v = 11;
  float infrared_zoom = 12;
  float infrared_focal = 13;
  float infrared_focus = 14;
  uint32 infrared_resolution_w = 15;
  uint32 infrared_resolution_h = 16;
  // 当前活跃镜头
  uint32 active_camera = 17;        // 0=可见光 1=红外
  uint32 detect_camera_status = 18; // 探测相机状态
}

message AzimuthPitchInfo {
  string device_sn = 1;
  uint64 timestamp_ms = 2;
  float horizontal_angle = 3;       // 方位角 deg
  float pitching_angle = 4;         // 俯仰角 deg
  float horizontal_speed = 5;       // 方位角速度 deg/s
  float pitching_speed = 6;         // 俯仰角速度 deg/s
  float north_angle = 7;            // 北向角
  float horizontal_angle_raw = 8;   // 原始方位角（未修正）
  float pitching_angle_raw = 9;     // 原始俯仰角
  float roll_angle = 10;            // 横滚角
  uint32 angle_source = 11;         // 角度来源（设备/IMU）
}
```

**设备信息**：

```protobuf
message CameraInfo {
  string camera_index = 1;          // "visible-0"、"infrared-0" 等
  uint32 resolution_w = 2;
  uint32 resolution_h = 3;
  string rtsp_url = 4;              // 设备 RTSP 拉流地址
  string description = 5;
}

message PtzDeviceInfo {
  string device_sn = 1;
  uint32 device_type = 2;           // PtzType 枚举
  string ip = 3;
  uint32 control_port = 4;
  bool connected = 5;
  float horizontal_angle = 6;
  float pitching_angle = 7;
  float visible_zoom = 8;
  float infrared_zoom = 9;
  string firmware_version = 10;
  string model = 11;
  uint32 work_status = 12;
  uint32 work_mode = 13;
  repeated CameraInfo cameras = 14;
  uint64 timestamp_ms = 15;
  uint64 uptime_s = 16;
}

message PtzOnlineNotify {
  string device_sn = 1;
  uint32 device_type = 2;
  string ip = 3;
  repeated CameraInfo cameras = 4;
}

message PtzOfflineNotify {
  string device_sn = 1;
  uint32 device_type = 2;
}

message PtzDeviceCapability {
  string device_sn = 1;
  uint32 device_type = 2;
  repeated CameraInfo cameras = 3;
  bool support_tracking = 4;
  bool support_guidance = 5;
  bool support_lens_control = 6;
  bool support_defog = 7;
  bool support_window_heat = 8;
  bool support_icr = 9;
  bool support_ir_power = 10;
}
```

**设备控制指令**（全部来自引导节点统一输出，经算法ROS2适配层转为 AimRT Channel）：

```protobuf
message PtzMotionCmd {
  string device_sn = 1;
  uint64 timestamp_ms = 2;
  uint32 motion_dir_cmd = 3;       // 0=停 1=上 2=下 3=左 4=右 5=左上 6=右上 7=左下 8=右下
  float horizontal_speed = 4;      // 方位角速度 deg/s
  float pitching_speed = 5;        // 俯仰角速度 deg/s
  float target_horizontal = 6;     // 目标方位角（位置环模式）
  float target_pitching = 7;       // 目标俯仰角
  uint32 motion_mode = 8;          // 0=速度环 1=位置环
}

message PtzLensCmd {
  string device_sn = 1;
  uint64 timestamp_ms = 2;
  uint32 ctrl_cmd = 3;             // 0=zoom_in 1=zoom_out 2=zoom_stop 3=focus_near
                                   // 4=focus_far 5=focus_stop 6=focus_auto ...
                                   // 20=defog_on 21=defog_off 22=window_heat_on 等
  float focal = 4;
  float zoom = 5;
  float focus = 6;
  uint32 camera_index = 7;         // 0=可见光 1=红外
  float speed = 8;                 // 变焦/聚焦速度
  int32 preset_id = 9;             // 预置位 ID
  uint32 ir_power = 10;            // 红外功率
  uint32 icr_mode = 11;            // ICR 日夜模式
}

message PtzManualLockTargetCmd {
  string device_sn = 1;
  uint64 timestamp_ms = 2;
  float target_x = 3;             // 归一化 x [0,1]
  float target_y = 4;             // 归一化 y [0,1]
  float target_w = 5;             // 框宽
  float target_h = 6;             // 框高
  uint32 track_video_source = 7;  // 0=可见光 1=红外
  uint32 lock_mode = 8;           // 0=点击锁定 1=框选锁定
  uint32 target_id = 9;
}

message PtzSwitchTrackCmd {
  string device_sn = 1;
  uint64 timestamp_ms = 2;
  uint32 ctrl_cmd = 3;            // 操作类型：0=切换跟踪相机(PTZ_CTRL_DETECT_CAMERA) 1=切换跟踪相机模式(PTZ_CTRL_DETECT_CAMERA_MODE)
  uint32 tracking_source = 4;    // ctrl_cmd=0 时：目标相机 0=可见光 1=红外 2=可见光细节 3=可见光主画面
  uint32 detect_camera_mode = 5; // ctrl_cmd=1 时：跟踪相机模式值
}

// 设备直控 RPC 响应
message PtzCmdResult {
  int32 code = 1;                 // 0=成功, 非0=错误码
  string message = 2;
  string device_sn = 3;
}

// 设备直控 RPC 请求（透雾/加热/ICR，绕过引导节点）
message PtzDefogCmd {
  string device_sn = 1;
  bool enable = 2;
}

message PtzWindowHeatCmd {
  string device_sn = 1;
  bool enable = 2;
}

message PtzIcrCmd {
  string device_sn = 1;
  uint32 icr_mode = 2;           // 0=白天 1=夜间 2=自动
}
```

### 9.2 `protocols/fusion/ptz_guidance.proto`（引导类指令）

引导指令由融合算法模块发出，不属于 PTZ 设备自身数据，放在 `device/` 外部：

- `PtzGuidanceCmd` — 引导控制（guiding_azimuth、guiding_elevation、guidance_mode 等 12 个字段）
- `PtzTrackCmd` — 跟踪控制（ctrl_cmd 1-7 枚举、搜索范围、track_video_source 等 12 个字段）

### 9.3 AI 跟踪结果（归属 AI 模块 proto）

- `AiTargetItem` — 检测目标（target_id、class_id、score、bbox 等 7 个字段）
- `AiTrackResult` — 跟踪结果（device_sn、ptz_source、frame_id、target_points 列表等 12 个字段）

---

## 十、不迁移的部分


| 内容                                                                                      | 原因                                                                                                          | 归属                   |
| --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------- |
| FFmpeg 旧代码（`src/app/ptz/ffmpeg/`）                                                       | 已弃用，GStreamer 已完全替代                                                                                         | 不迁移                  |
| Alink 命令处理（0x86/0x8a/0x8b）                                                              | 新架构已无 C2 app 和 Alink 协议，整体废弃                                                                                | 废弃不迁移                |
| C2 心跳/设备列表上报（0xE5/0xEB）                                                                 | 新架构已无 C2 app，原上报通路整体废弃                                                                                      | 废弃不迁移                |
| `ai_main.cpp` 中 Alink 上报（`alink_upload`_*）                                              | Alink 上报在新架构中废弃，状态通过 Channel 发布                                                                             | 废弃不迁移                |
| `ai_main.cpp` 中耐杰状态解析（`ptz_pitch_azimuth`、`ptz_dev_status`、`ptz_lense_ext_info_0x0c` 等） | `ai_main.cpp` 以前属于 AI 模块，现由嵌入式接管。其中与嵌入式相关的主要是**耐杰的视频流处理**和**耐杰的状态上报**代码，迁移到 `NaijiePtz/naijie_ptz_device.`* | → PtzModule（嵌入式接管）   |
| `ai_main.cpp` 中引导控制（`setPTZ`*、`radarGuide`*、`SearchAndTracking`）                        | 引导/融合算法逻辑，归引导节点（`ptz_guider_ctl`），通过 AimRT Channel 下发                                                       | → 引导节点（不归 PtzModule） |
| `ai_main.cpp` 中 AI 目标处理（`ptz_target_info`、`nature_result2ai_target_info`）               | AI 算法逻辑，归 AI 模块                                                                                             | → AI 模块              |
| `ai_main.cpp` 中其他代码                                                                     | 目前不清楚具体归属，后续梳理时再确定                                                                                          | **待定**               |
| `ros_app.cpp` 中的 Topic 桥接                                                               | AimRT Channel 直连，无需桥接                                                                                       | 不迁移                  |
| `libmain()` / `embed_api` 全局状态                                                          | 旧架构遗留，按 Module 拆分解耦                                                                                         | 不迁移                  |
| 激光设备实现代码（`laser_service`）                                                               | 激光属于打击类设备，归独立的打击设备模块                                                                                        | 不迁移（归打击模块）           |
| `alink_system.cpp` 中 PTZ 查询/控制                                                          | C2 侧查设备信息、控制 PTZ，新架构废弃                                                                                      | 废弃不迁移                |


---

## 十一、风险与依赖


| 风险/依赖                   | 影响                                                | 缓解措施                                     |
| ----------------------- | ------------------------------------------------- | ---------------------------------------- |
| **耐杰代码散落 6+ 文件，解耦工作量大** | `ai_main.cpp` 约 1000 行耐杰相关代码需分拆到 3 个模块            | 先迁协议栈+状态解析（PtzModule），引导控制随融合模块迁移        |
| 耐杰 `embed_api` 全局状态解耦   | `realtime_pa_t`、`lens_information` 等全局变量被多模块读写    | 收敛到 `PtzDeviceNaijie` 成员变量，通过 Channel 发布 |
| `ai_main.cpp` 回调注册链     | 回调在 `ptz_app.cpp` 注册但实现在 `ai_main.cpp`            | 新架构中 `PtzDeviceNaijie` 自行注册和实现回调         |
| 和普 SDK 闭源               | `hepuSdk` 仅有 `.h` + `.so`                         | 保持二进制兼容，不改 SDK 接口                        |
| DeviceManager 接口未最终确定   | PtzModule 上报格式需与 DeviceManager 对齐                 | 先定义 proto，与鲍工（DeviceManager 负责人）确认       |
| 融合模块同步迁移                | `setPTZ`*/`radarGuide`* 迁移到融合模块后才能完全去掉 ai_main 耦合 | PtzModule 先提供 Channel 接口，融合模块后续对接        |
| Infra 层先行完成             | PtzModule 依赖 skyfendlibs 编译通过                     | 按 Infra → PTZ → LiveStream 顺序实施          |
| 引导指令 proto 归属           | `PtzGuidanceCmd` 等由融合模块定义                         | 与周益辉（算法模块负责人）确认 `protocols/fusion/` 路径   |


---

## 十二、对外交互接口与能力清单

> PtzModule、NexusGateway、WebGateway **均为 TerraHub 内部的 AimRT Module**，运行在同一个 AimRT 进程中。PtzModule 不直接与天盾或 PC 浏览器通信，对外交互通过 Gateway 模块中转：
>
> - **天盾（远程）**：PtzModule → AimRT Channel/RPC → **NexusGateway**（内部 Module） → MQTT EdgeBroker → TailscaleClient → 天盾
> - **PC 浏览器（本地/远程）**：PtzModule → AimRT Channel/RPC → **WebGateway**（内部 Module） → Caddy → Web 前端
> - 视频流不经过 PtzModule，由 LiveStream → MediaMTX → RTSP/WebRTC/HLS → 消费者
>
> PtzModule 与 Gateway 之间的 AimRT 通信**统一使用 SAPIENT 协议的 Protobuf 消息定义**（详见 §13）。

### 12.1 Channel vs RPC 选型分析

> **背景**：本次嵌入式重构中，引导、融合、标定、AI 视觉等算法模块**不参与重构**，保留原有 ROS2 节点。系统增加一个 **算法ROS2适配层（AlgoROS2Adapter）**，负责将 AimRT 内部的 Channel/RPC 通信转换为 ROS2 消息通信。PtzModule 等嵌入式模块与算法ROS2适配层通过 AimRT Channel/RPC 通信，算法ROS2适配层与算法节点通过 ROS2 Topic 通信，实现兼容。后续推动算法重构后可逐步去除此适配层。

**AimRT 通信机制选型原则**：


| 维度      | **Channel（发布/订阅）**   | **RPC（请求/响应）**           |
| ------- | -------------------- | ------------------------ |
| 通信模式    | 异步单向，fire-and-forget | 同步双向，请求→等待→响应            |
| 适用频率    | 高频（≥5Hz），不阻塞发布方      | 低频（用户操作级，<1Hz），发布方等待响应   |
| 发布方是否等待 | **不等待**，发完即走         | **等待响应**，期间线程/协程被占用      |
| 一对多     | 天然支持（多个订阅者）          | 点对点（一个客户端→一个服务端）         |
| 典型场景    | 状态上报、高频控制指令、传感器数据    | 查询、配置、用户操作               |
| 阻塞风险    | 无                    | 高频场景下**会阻塞调用方线程**，导致消息堆积 |


**PtzModule 接口选型决策**：

> **关键修正**：PTZ 的转台运动（motion）、镜头控制（lens）、手动锁定（manual_lock）、切换跟踪源（switch_tracking）等控制指令，在旧架构中**全部由引导节点统一输出**（用户操作先经 `/cmd_set` → 引导节点处理 → 再输出控制 Topic）。因此这些接口的来源是引导节点（经算法ROS2适配层），而非 Gateway 直接调用。全部使用 **Channel**。


| 接口                               | 来源                        | 频率                                 | 选型          | 理由                                   |
| -------------------------------- | ------------------------- | ---------------------------------- | ----------- | ------------------------------------ |
| `ptz/guidance_cmd`               | 引导节点（经算法ROS2适配层）          | **~3-5 Hz**（主循环 10Hz，节流 200-300ms） | **Channel** | 引导指令，引导节点连续发布不等待返回                   |
| `ptz/track_cmd`                  | 引导节点（经算法ROS2适配层）          | 事件触发                               | **Channel** | 跟踪启停，引导节点不需要等 PTZ 确认                 |
| `ptz/motion_cmd`                 | 引导节点（经算法ROS2适配层）          | 由引导节点控制频率                          | **Channel** | 用户转台操作先到引导节点，引导节点统一输出，不直接到 PtzModule |
| `ptz/lens_cmd`                   | 引导节点（经算法ROS2适配层）          | 由引导节点控制频率                          | **Channel** | 用户变焦/聚焦操作先到引导节点，引导节点统一输出             |
| `ptz/manual_lock_target_cmd`     | 引导节点（经算法ROS2适配层）          | 事件触发                               | **Channel** | 用户锁定操作先到引导节点，引导节点统一输出                |
| `ptz/switch_tracking_source_cmd` | 引导节点（经算法ROS2适配层）          | 事件触发                               | **Channel** | 切换跟踪源，引导节点统一输出                       |
| `ptz/ai_track_result`            | AI 模块（经算法ROS2适配层）         | **帧率驱动 ~15-25 fps**                | **Channel** | AI 检测结果按帧推送，AI 模块绝不应等待 PTZ 处理完才继续    |
| 设备直控 RPC（透雾/加热/ICR）              | WebGateway / NexusGateway | 用户操作（<1 Hz）                        | **RPC**     | 设备特有辅助功能，引导节点不关心，Gateway 直接调用返回执行结果  |


**结论**：

- **引导节点→PtzModule（所有控制指令）**：全部用 **Channel**。引导节点是统一控制源，它统一协调用户操作、融合引导、AI 跟踪等多个控制来源后输出控制指令。PtzModule 只需订阅引导节点的输出，不需要区分指令来源
- **AI 模块→PtzModule（检测结果）**：用 **Channel**。帧率驱动 ~15-25fps，AI 模块不等待 PTZ 处理
- **Gateway→PtzModule（设备直控）**：仅**透雾、窗口加热、ICR** 等设备特有辅助功能使用 **RPC**。这些操作不影响云台指向，引导节点不关心，前端需要执行结果反馈
- **用户转台/镜头操作的控制路径**：用户操作 → Gateway 发布 AimRT Channel `user/ptz_control_cmd` → 算法ROS2适配层订阅并转为 ROS2 `/cmd_set` → 引导节点 → `/ptz_motion_cmd` 等 → 算法ROS2适配层 → AimRT Channel → PtzModule。Gateway 不直接调用 PtzModule，PtzModule 也不承担命令转发职责（详见 §3.1 路径①架构决策）
- **PtzModule→外部（状态上报）**：使用 **Channel**。状态数据是一对多广播（DeviceManager、WebGateway、NexusGateway、融合模块都要订阅），WebGateway 转发给 PC 浏览器，NexusGateway 经 MQTT 转发给天盾

### 12.2 算法ROS2适配层与通信架构

> **为什么需要算法ROS2适配层**：本次嵌入式重构中，算法模块（引导、融合、标定、AI 视觉）**不参与重构**，保留原有 ROS2 节点不动。嵌入式模块（PtzModule、RadarModule 等）已迁移到 AimRT，无法直接与算法的 ROS2 节点通信。因此系统增加 **AlgoROS2Adapter（算法ROS2适配层）**，负责将 AimRT 内部的 Channel/RPC 通信转换为原有的 ROS2 消息通信，实现嵌入式模块与算法模块的兼容。后续推动算法重构后可逐步去除此适配层。

```mermaid
flowchart LR
    subgraph AimRT_World["AimRT 世界（TerraHub 进程）"]
        PTZ["PtzModule"]
        WGW["WebGateway<br/>（→PC 浏览器）"]
        NGW["NexusGateway<br/>（→天盾 MQTT）"]
        BRIDGE["AlgoROS2Adapter<br/>算法ROS2适配层<br/>AimRT ↔ ROS2 转换"]
    end

    subgraph ROS2_World["ROS2 世界（保留现有节点）"]
        GUID["引导节点<br/>ptz_guider_ctl<br/>（统一控制源）"]
        FUSION["融合节点"]
        AI["AI 视觉节点"]
        CALIB["标定节点"]
    end

    WGW -->|"①Channel: user/ptz_control_cmd"| BRIDGE
    NGW -->|"①Channel: user/ptz_control_cmd"| BRIDGE
    BRIDGE -->|"ROS2 /cmd_set"| GUID

    GUID -->|"ROS2 引导统一输出<br/>/ptz_guidance_cmd ~3-5Hz<br/>/ptz_motion_cmd<br/>/ptz_lens_cmd 等"| BRIDGE
    AI -->|"ROS2<br/>/visiblelight_track_objs<br/>帧率驱动~15-25fps"| BRIDGE

    BRIDGE -->|"AimRT Channel<br/>6个控制 + AI 结果<br/>（全部 Channel）"| PTZ

    PTZ -->|"AimRT Channel<br/>ptz/status 10Hz<br/>ptz/azimuth_pitch_info 10Hz"| BRIDGE
    BRIDGE -->|"ROS2 Topic<br/>/ptz_status<br/>/ptz_azimuth_pitch_info"| GUID
    BRIDGE -->|"ROS2 Topic"| FUSION
    BRIDGE -->|"ROS2 Topic"| AI

    WGW -->|"③直控RPC: 透雾/加热/ICR"| PTZ
    NGW -->|"③直控RPC: 透雾/加热/ICR"| PTZ
```



### 12.3 PtzModule 发布的 AimRT Channel（状态上报，其他模块可订阅）


| Channel Topic            | 消息类型 (protobuf)       | 频率    | 优先级      | 订阅方                                                          | 说明                                   |
| ------------------------ | --------------------- | ----- | -------- | ------------------------------------------------------------ | ------------------------------------ |
| `ptz/status`             | `PtzStatus`           | 10 Hz | P-Normal | DeviceManager, WebGateway（→PC）, NexusGateway（→天盾）, 算法ROS2适配层 | 设备状态（在线、跟踪状态、工作模式等）                  |
| `ptz/lens_info`          | `PtzLensInfo`         | 10 Hz | P-Normal | WebGateway（→PC）, NexusGateway（→天盾）, 算法ROS2适配层（→融合/AI）        | 镜头信息（FOV、变焦倍率、焦距）                    |
| `ptz/azimuth_pitch_info` | `AzimuthPitchInfo`    | 10 Hz | P-High   | 算法ROS2适配层（→融合/引导）, NexusGateway（→天盾）                         | 方位角/俯仰角（引导闭环核心数据）                    |
| `ptz/device_info`        | `PtzDeviceInfo`       | 10 Hz | P-Low    | DeviceManager, WebGateway（→PC）, NexusGateway（→天盾）            | 设备详情（SN、IP、固件版本、相机列表），与 status 同回调发布 |
| `device/ptz_online`      | `PtzOnlineNotify`     | 事件触发  | P-High   | LiveStream, DeviceManager                                    | 设备上线（携带 RTSP URL、分辨率等）               |
| `device/ptz_offline`     | `PtzOfflineNotify`    | 事件触发  | P-High   | LiveStream, DeviceManager                                    | 设备离线                                 |
| `device/ptz_capability`  | `PtzDeviceCapability` | 事件触发  | P-Normal | DeviceManager                                                | 设备能力（支持跟踪/引导/镜头控制/红外功率等）             |


### 12.4 PtzModule 订阅的 AimRT Channel（高频数据，算法ROS2适配层/算法模块发布）


| Channel Topic                    | 消息类型 (protobuf)          | 发布方               | 频率                                 | 说明                      |
| -------------------------------- | ------------------------ | ----------------- | ---------------------------------- | ----------------------- |
| `ptz/guidance_cmd`               | `PtzGuidanceCmd`         | 算法ROS2适配层（←引导节点）  | **~3-5 Hz**（主循环 10Hz，节流 200-300ms） | 引导控制（方位角/俯仰角指向）         |
| `ptz/track_cmd`                  | `PtzTrackCmd`            | 算法ROS2适配层（←引导节点）  | 事件触发                               | 跟踪控制（启停/搜索）             |
| `ptz/motion_cmd`                 | `PtzMotionCmd`           | 算法ROS2适配层（←引导节点）  | 由引导节点控制频率                          | 转台运动（用户操作经引导节点统一输出）     |
| `ptz/lens_cmd`                   | `PtzLensCmd`             | 算法ROS2适配层（←引导节点）  | 由引导节点控制频率                          | 镜头控制（用户操作经引导节点统一输出）     |
| `ptz/manual_lock_target_cmd`     | `PtzManualLockTargetCmd` | 算法ROS2适配层（←引导节点）  | 事件触发                               | 手动锁定目标                  |
| `ptz/switch_tracking_source_cmd` | `PtzSwitchTrackCmd`      | 算法ROS2适配层（←引导节点）  | 事件触发                               | 切换跟踪视频源                 |
| `ptz/ai_track_result`            | `AiTrackResult`          | 算法ROS2适配层（←AI 节点） | **帧率驱动 ~15-25 fps**                | AI 检测结果回传设备（和普替代智能分析盒子） |


### 12.5 PtzModule 提供的 AimRT RPC（设备直控，Gateway 直接调用，绕过引导节点）

> 仅限引导节点不关心的设备特有辅助功能。转台运动、镜头变焦/聚焦、手动锁定、切换跟踪源等控制指令**不通过 RPC**，而是经引导节点统一输出后以 Channel 方式到达 PtzModule（详见 §3.1 和 §12.1）。


| RPC 方法                 | 请求消息 (protobuf)    | 响应消息           | 调用方                                | 说明                |
| ---------------------- | ------------------ | -------------- | ---------------------------------- | ----------------- |
| `PtzDefogControl`      | `PtzDefogCmd`      | `PtzCmdResult` | WebGateway（←PC）/ NexusGateway（←天盾） | 和普透雾开关（引导节点不关心）   |
| `PtzWindowHeatControl` | `PtzWindowHeatCmd` | `PtzCmdResult` | WebGateway（←PC）/ NexusGateway（←天盾） | 和普窗口加热开关（引导节点不关心） |
| `PtzIcrControl`        | `PtzIcrCmd`        | `PtzCmdResult` | WebGateway（←PC）/ NexusGateway（←天盾） | ICR 日夜切换（引导节点不关心） |


```protobuf
// RPC 通用响应
message PtzCmdResult {
  int32 code = 1;      // 0=成功, 非0=错误码
  string message = 2;  // 错误描述（成功时为空）
  string device_sn = 3;
}
```

### 12.6 PtzModule 提供的能力


| 能力           | 说明                                                                           | 通信方式       | 对应接口                                     |
| ------------ | ---------------------------------------------------------------------------- | ---------- | ---------------------------------------- |
| 设备发现与连接管理    | 自动发现/连接和普（TCP 39020）和耐杰（UDP 9966）PTZ 设备，维护连接状态                               | —          | `device/ptz_online`、`device/ptz_offline` |
| 设备能力上报       | 上报设备支持的能力（相机数量/分辨率/跟踪/引导/镜头控制等），供 DeviceManager 维护全局设备表                      | Channel    | `device/ptz_capability`                  |
| 方位角/俯仰角实时上报  | 10 Hz 发布当前 PTZ 指向角度，供融合算法做引导闭环（经算法ROS2适配层转 ROS2 Topic）                       | Channel    | `ptz/azimuth_pitch_info`                 |
| 设备状态/镜头信息上报  | 10 Hz 发布工作状态、跟踪状态、FOV、变焦倍率，供 WebGateway 转发给 PC 浏览器、NexusGateway 经 MQTT 转发给天盾 | Channel    | `ptz/status`、`ptz/lens_info`             |
| 引导指令执行       | 接收引导节点（经算法ROS2适配层）的引导指令（~3-5Hz），转换为设备私有协议下发到 PTZ 硬件                          | Channel 订阅 | `ptz/guidance_cmd`                       |
| 跟踪控制         | 接收引导节点（经算法ROS2适配层）的跟踪启停指令，下发到 PTZ 硬件                                         | Channel 订阅 | `ptz/track_cmd`                          |
| 转台运动控制       | 接收引导节点（经算法ROS2适配层）统一输出的转台控制指令（用户操作经引导节点转发），下发到设备                             | Channel 订阅 | `ptz/motion_cmd`                         |
| 镜头控制         | 接收引导节点（经算法ROS2适配层）统一输出的镜头控制指令（用户操作经引导节点转发），下发到设备                             | Channel 订阅 | `ptz/lens_cmd`                           |
| 手动锁定目标       | 接收引导节点（经算法ROS2适配层）统一输出的手动锁定指令，下发到设备                                          | Channel 订阅 | `ptz/manual_lock_target_cmd`             |
| 切换跟踪源        | 接收引导节点（经算法ROS2适配层）统一输出的跟踪源切换指令，下发到设备                                         | Channel 订阅 | `ptz/switch_tracking_source_cmd`         |
| AI 检测结果回传设备  | 接收 AI 模块（经算法ROS2适配层）的检测结果（帧率驱动 ~15-25fps），回传到 PTZ 硬件做跟踪闭环                    | Channel 订阅 | `ptz/ai_track_result`                    |
| 透雾控制（设备直控）   | 接收 Gateway 直接下发的透雾开关指令（引导节点不关心），返回执行结果                                       | **RPC**    | `PtzDefogControl`                        |
| 窗口加热（设备直控）   | 接收 Gateway 直接下发的窗口加热指令（引导节点不关心），返回执行结果                                       | **RPC**    | `PtzWindowHeatControl`                   |
| ICR 切换（设备直控） | 接收 Gateway 直接下发的 ICR 日夜切换指令（引导节点不关心），返回执行结果                                  | **RPC**    | `PtzIcrControl`                          |


### 12.7 交互路径图

```mermaid
flowchart LR
    subgraph 外部["外部系统"]
        TD["天盾"]
        PC["PC 浏览器"]
    end

    subgraph 进程["系统进程"]
        MQTT_E["MQTT\nEdgeBroker"]
        CADDY["Caddy"]
        MTX["MediaMTX"]
    end

    subgraph ROS2["ROS2 算法节点（不迁移）"]
        GUID["引导节点"]
        FUSION["融合节点"]
        AI["AI 视觉节点"]
    end

    subgraph AimRT["TerraHub（AimRT 单进程）"]
        NGW["NexusGateway"]
        WGW["WebGateway"]
        BRIDGE["AlgoROS2Adapter\n算法ROS2适配层"]
        PTZ["PtzModule"]
        DM["DeviceManager"]
        LIVE["LiveStream"]
    end

    subgraph HW["PTZ 硬件设备"]
        HP["和普 PTZ\nTCP 39020"]
        NJ["耐杰 PTZ\nUDP 9966"]
    end

    TD <-->|MQTT| MQTT_E
    MQTT_E <-->|MQTT| NGW
    PC <-->|HTTP/WS| CADDY
    CADDY <-->|HTTP/WS| WGW
    PC <-->|WebRTC| MTX

    WGW -->|"①Channel\nuser/ptz_control_cmd"| BRIDGE
    NGW -->|"①Channel\nuser/ptz_control_cmd"| BRIDGE

    BRIDGE -->|"ROS2 /cmd_set"| GUID
    GUID -->|"②引导输出\nguidance/motion/\nlens_cmd 等"| BRIDGE
    FUSION -->|"融合数据"| GUID
    AI -->|"AI跟踪结果"| BRIDGE

    BRIDGE -->|"Channel\n6控制+AI结果"| PTZ

    WGW -->|"③直控RPC\n透雾/加热/ICR"| PTZ
    NGW -->|"③直控RPC\n透雾/加热/ICR"| PTZ

    PTZ -->|"Channel\nstatus 10Hz"| WGW
    PTZ -->|"Channel\nstatus 10Hz"| NGW
    PTZ -->|"Channel\nstatus/azimuth"| BRIDGE
    BRIDGE -->|"ROS2 Topic"| GUID
    BRIDGE -->|"ROS2 Topic"| AI

    PTZ -->|"上下线通知"| LIVE
    PTZ -->|"设备注册+状态"| DM

    LIVE -->|"推流"| MTX

    HP -->|"状态上报\nSDK/TCP"| PTZ
    PTZ -->|"控制下发\nSDK/TCP"| HP
    NJ -->|"状态上报\nUDP 私有协议"| PTZ
    PTZ -->|"控制下发\nUDP 私有协议"| NJ
```



---

## 十三、SAPIENT 协议对齐

### 13.1 SAPIENT 协议简介

**SAPIENT**（Sensing for Asset Protection with Integrated Electronic Networked Technology）是由英国国防部（UK MoD / Dstl）主导开发的开放标准接口协议，已由英国标准协会发布为 **BSI Flex 335**（最新版本 v2.0，2024 年发布）。SAPIENT 定义了一套基于 **Protobuf** 的标准化传感器网络通信接口，官方 Proto 定义见 [dstl/SAPIENT-Proto-Files](https://github.com/dstl/SAPIENT-Proto-Files)。

SAPIENT 系统由三类节点组成：


| 节点类型                          | 说明                            | 在我们系统中的对应                                                                            |
| ----------------------------- | ----------------------------- | ------------------------------------------------------------------------------------ |
| **Sensor Edge Node**（传感器边缘节点） | 在本地做 AI 检测/跟踪，上报处理后的信息（非原始数据） | **PtzModule**（NodeType = `POINTABLE_NODE`，可指向节点）、**RadarModule**（NodeType = `RADAR`） |
| **Effector Node**（效应器节点）      | 接收任务并自主执行（如干扰、打击）             | **激光打击设备**（霍克眼 HEF/HEP 等，独立模块，不在本方案范围）                                               |
| **Fusion Node**（融合节点）         | 信息融合 + 态势展示 + 下发任务指令          | **天盾**（远程）、**PC 浏览器 Web 端**（本地）                                                      |


### 13.2 SAPIENT 核心消息类型与 PtzModule 映射

SAPIENT 标准定义以下核心消息类型（BSI Flex 335 v2.0），每条消息包含 `node_id` + `timestamp` 外层封装为统一的 `SapientMessage`：


| SAPIENT 消息类型        | 方向            | 标准含义                       | PtzModule 对应概念   | 当前文档中的接口                                                      |
| ------------------- | ------------- | -------------------------- | ---------------- | ------------------------------------------------------------- |
| **Registration**    | Edge → Fusion | 节点注册（上报能力：传感器类型、支持模式、覆盖范围） | PTZ 设备上线 + 能力上报  | `device/ptz_online` + `device/ptz_capability`                 |
| **RegistrationAck** | Fusion → Edge | 注册确认（分配 node_id）           | 天盾/PC 确认设备注册     | 待定（新增）                                                        |
| **StatusReport**    | Edge → Fusion | 周期状态上报（健康度、工作模式）           | PTZ 状态上报         | `ptz/status`、`ptz/lens_info`、`ptz/device_info`                |
| **DetectionReport** | Edge → Fusion | 目标检测报告（位置、分类、置信度）          | AI 检测结果 / 雷达目标上报 | `ptz/ai_track_result`（需重新定义）                                  |
| **Task**            | Fusion → Edge | 任务下发（转向、跟踪、扫描模式切换等）        | 用户操作指令 / 引导指令    | RPC `PtzMotion`/`PtzLensControl` 等、Channel `ptz/guidance_cmd` |
| **TaskAck**         | Edge → Fusion | 任务确认（接受/拒绝/完成）             | 操作执行结果           | RPC 响应 `PtzCmdResult`                                         |
| **Alert**           | Edge → Fusion | 异常告警                       | 设备告警             | 待定（新增）                                                        |
| **AlertAck**        | Fusion → Edge | 告警确认                       | —                | 待定（新增）                                                        |
| **Error**           | 双向            | 错误消息                       | —                | 待定（新增）                                                        |


### 13.3 SAPIENT 与 PTZ 业务字段的映射分析

> **结论**：SAPIENT 协议没有为 Camera/PTZ 定义专属 message，保持高度通用性。PTZ 特有字段（FOV、变焦倍率、方位角等）无法直接用 SAPIENT 标准类型表达，需通过**自定义扩展**承载。这与方案 B（SAPIENT 封装 + 自定义扩展）的设计思路完全一致，符合 SAPIENT 的设计哲学。

**SAPIENT 中 PTZ 设备的标识**：注册时 `NodeType` 应设为 `NODE_TYPE_POINTABLE_NODE`（可指向节点），表明设备具备转向能力。非 `NODE_TYPE_CAMERA`（SAPIENT 中无此枚举）。

**PTZ 核心业务字段与 SAPIENT 表达方式映射**：


| PTZ 业务字段      | SAPIENT 标准机制                           | 能否直接表达                                  | 方案 B 实现方式                               |
| ------------- | -------------------------------------- | --------------------------------------- | --------------------------------------- |
| 设备类型标识        | `Registration.NodeDefinition.NodeType` | 可用 `POINTABLE_NODE`                     | 注册时设置                                   |
| 当前视场角（FOV）    | `StatusReport.field_of_view`           | **可直接复用**                               | 复用标准字段                                  |
| 当前方位角/俯仰角     | `StatusReport.status[]`                | 通用 string 类型，精度不足                       | 扩展：自定义 `PtzStatus` 或 `AzimuthPitchInfo` |
| 当前变焦倍率        | `StatusReport.status[]`                | 通用 string 类型，无法表达 float                 | 扩展：自定义 `PtzLensInfo`                    |
| 工作模式/跟踪状态     | `StatusReport.mode` / `status[]`       | 仅 string 枚举                             | 扩展：自定义 `PtzStatus` 中的 uint32 枚举         |
| 云台控制（转动方向/速度） | `Task.Command.look_at`                 | 仅支持指向坐标，不支持速度/方向                        | 扩展：自定义 `PtzMotionCmd`                   |
| 镜头控制（变焦/聚焦）   | `Task.Command`                         | 无对应字段                                   | 扩展：自定义 `PtzLensCmd`                     |
| 透雾/加热/ICR     | `Task.Command`                         | 无对应字段                                   | 扩展：自定义 `PtzDefogCmd` 等                  |
| 手动锁定目标（框选坐标）  | `Task.Command`                         | 无对应字段                                   | 扩展：自定义 `PtzManualLockTargetCmd`         |
| AI 检测/跟踪结果    | `DetectionReport`                      | 基本可用（object_id/location/classification） | 可复用标准类型，PTZ 特有字段扩展                      |


**总结**：SAPIENT 的 `StatusReport`、`Task` 等标准类型过于通用，无法直接表达 PTZ 的精细业务字段。方案 B 的做法——在 `TerraHubMessage.oneof content` 中保留 SAPIENT 标准类型的同时扩展 PTZ 自定义消息——既保证了与 SAPIENT 生态的互操作性（Gateway 对外可映射），又满足了 PTZ 内部控制的全部需求。

### 13.4 SAPIENT 协议的分层理解

SAPIENT 标准（BSI Flex 335 v2.0）包含**两个独立层次**：


| 层次                         | 内容                                                                                       | 是否可替换                 |
| -------------------------- | ---------------------------------------------------------------------------------------- | --------------------- |
| **消息层（Message Schema）**    | Protobuf 消息定义（`SapientMessage`、`Registration`、`StatusReport`、`DetectionReport`、`Task` 等） | **不可替换**——SAPIENT 的核心 |
| **传输层（Transport Binding）** | MQTT 是 BSI Flex 335 的参考传输绑定（topic 命名、QoS 设置等）                                            | **可替换**——标准明确将传输与消息分离 |


"统一使用 SAPIENT 协议"的准确含义：**所有模块间的 Protobuf 消息统一采用 SAPIENT 定义的消息结构（Schema），传输层根据场景选择不同机制。**

### 13.5 AGX 内部架构与 SAPIENT 的关系

> **NexusGateway 和 WebGateway 均为 TerraHub 内部的 AimRT Module**，与 PtzModule、RadarModule、LiveStream 运行在同一个 AimRT 进程中。它们之间通过 AimRT Channel/RPC（底层为 SHM/本地 IPC）通信，不经过网络。

```mermaid
flowchart TD
    subgraph TerraHub_Process["TerraHub（AimRT 单进程）—— AGX 内部"]
        PTZ["PtzModule<br/>（Sensor Edge Node）"]
        RADAR["RadarModule<br/>（Sensor Edge Node）"]
        LIVE["LiveStream"]
        DM["DeviceManager"]
        BRIDGE["AlgoROS2Adapter<br/>算法ROS2适配层<br/>AimRT ↔ ROS2 转换"]
        NGW["NexusGateway<br/>（内部 AimRT Module）"]
        WGW["WebGateway<br/>（内部 AimRT Module）"]

        PTZ -->|"AimRT Channel<br/>SAPIENT PB<br/>（SHM/本地IPC）"| NGW
        PTZ -->|"AimRT Channel<br/>SAPIENT PB<br/>（SHM/本地IPC）"| WGW
        NGW -->|"AimRT RPC<br/>SAPIENT PB"| PTZ
        WGW -->|"AimRT RPC<br/>SAPIENT PB"| PTZ
    end

    subgraph 外部系统
        TD["天盾<br/>（Fusion Node）"]
        PC["PC 浏览器<br/>（Fusion Node）"]
    end

    NGW <-->|"MQTT<br/>SAPIENT PB<br/>（Tailscale VPN）"| TD
    WGW <-->|"HTTP/WebSocket<br/>SAPIENT PB"| PC
```



各通信路径的消息层与传输层：


| 通信路径                                     | 传输机制                          | 消息载荷（统一）             |
| ---------------------------------------- | ----------------------------- | -------------------- |
| PtzModule ↔ NexusGateway（**AGX 内部，同进程**） | AimRT Channel/RPC（SHM/本地 IPC） | **SAPIENT Protobuf** |
| PtzModule ↔ WebGateway（**AGX 内部，同进程**）   | AimRT Channel/RPC（SHM/本地 IPC） | **SAPIENT Protobuf** |
| NexusGateway ↔ 天盾（**跨网络**）               | MQTT（经 Tailscale VPN）         | **SAPIENT Protobuf** |
| WebGateway ↔ PC 浏览器（**跨网络**）             | HTTP / WebSocket（经 Caddy）     | **SAPIENT Protobuf** |
| PtzModule ↔ AlgoROS2Adapter（**AGX 内部**）  | AimRT Channel（SHM）            | **SAPIENT Protobuf** |


**统一消息格式的核心好处**：Gateway 模块仅做**传输适配**（AimRT ↔ MQTT / HTTP），不需要做消息格式转换——内外使用同一份 SAPIENT Protobuf 定义，Gateway 收到后直接序列化转发。

### 13.6 SAPIENT 封装方案选型（待确认）

> **说明**：PtzModule 不直接与天盾或 PC 浏览器通信，只需按 SAPIENT 规范定义好自身的 Protobuf 消息（`protocols/device/ptz/`），供 NexusGateway / WebGateway / DeviceManager 等对接模块订阅使用。Gateway 与外部系统（天盾 MQTT、PC HTTP/WS）的协议转换由各 Gateway 负责人定义，不阻塞 PtzModule 的 Proto 开发。
>
> 仓库中已有 SAPIENT 官方 Proto：`protocols/sapient/sapient_msg/bsi_flex_335_v2_0/`（含 `SapientMessage`、`StatusReport`、`DetectionReport`、`Task`、`Registration` 等），§9.1 中定义的 `PtzStatus` 等自定义消息目前**未使用 SAPIENT 类型**，需确认如何与 SAPIENT 对齐。


| **方式**                         | **做法**                                                                       | **优点**                      | **缺点**                                     |
| ------------------------------ | ---------------------------------------------------------------------------- | --------------------------- | ------------------------------------------ |
| **A. 直接用 SAPIENT 类型**          | PtzModule 发布的 Channel 直接使用 `SapientMessage` 封装，状态用 `StatusReport`，控制用 `Task` | 完全符合 SAPIENT 标准，Gateway 零转换 | SAPIENT 类型过于通用，PTZ 特有字段（FOV、变焦倍率、方位角等）无法表达 |
| **B. SAPIENT 封装 + 自定义扩展**      | 外层用 `SapientMessage`（node_id + timestamp），内部 `oneof content` 中扩展自定义 PTZ 消息   | 既有 SAPIENT 标准结构，又有 PTZ 业务字段 | 需要修改或扩展官方 SAPIENT proto                    |
| **C. 自定义 Proto + Gateway 层映射** | PtzModule 用自定义 `PtzStatus` 等，Gateway 负责转为 SAPIENT 格式对外通信                     | PtzModule 开发简单，业务语义清晰       | Gateway 需要做消息转换，内外不统一                      |


**决定采用方案 B（SAPIENT 封装 + 自定义扩展）**：保持官方 SAPIENT Proto 不修改，创建 `TerraHubMessage` 扩展封装，使用相同信封结构（`node_id` + `timestamp` + `oneof content`），在 `oneof` 中同时包含 SAPIENT 标准类型和 PTZ/Radar 自定义类型。`protocols/device/ptz/ptz.proto` 中的自定义 message（`PtzStatus`、`PtzMotionCmd` 等）保持不变，作为 `TerraHubMessage.oneof content` 的载荷。

**TerraHubMessage 信封定义**（`protocols/common/terrahub_message.proto`）：

```protobuf
syntax = "proto3";
package terrahub;

import "google/protobuf/timestamp.proto";
import "sapient_msg/bsi_flex_335_v2_0/registration.proto";
import "sapient_msg/bsi_flex_335_v2_0/registration_ack.proto";
import "sapient_msg/bsi_flex_335_v2_0/status_report.proto";
import "sapient_msg/bsi_flex_335_v2_0/detection_report.proto";
import "sapient_msg/bsi_flex_335_v2_0/task.proto";
import "sapient_msg/bsi_flex_335_v2_0/task_ack.proto";
import "device/ptz/ptz.proto";

message TerraHubMessage {
  google.protobuf.Timestamp timestamp = 1;
  string node_id = 2;              // 对应 device_sn
  string destination_id = 3;

  oneof content {
    // ── SAPIENT 标准类型（field 4-12，与官方 SapientMessage 对齐）──
    sapient_msg.bsi_flex_335_v2_0.Registration registration = 4;
    sapient_msg.bsi_flex_335_v2_0.RegistrationAck registration_ack = 5;
    sapient_msg.bsi_flex_335_v2_0.StatusReport status_report = 6;
    sapient_msg.bsi_flex_335_v2_0.DetectionReport detection_report = 7;
    sapient_msg.bsi_flex_335_v2_0.Task task = 8;
    sapient_msg.bsi_flex_335_v2_0.TaskAck task_ack = 9;

    // ── PTZ 设备扩展（field 100+）──
    terrahub.device.ptz.PtzStatus ptz_status = 100;
    terrahub.device.ptz.PtzLensInfo ptz_lens_info = 101;
    terrahub.device.ptz.AzimuthPitchInfo ptz_azimuth_pitch_info = 102;
    terrahub.device.ptz.PtzDeviceInfo ptz_device_info = 103;
    terrahub.device.ptz.PtzOnlineNotify ptz_online = 104;
    terrahub.device.ptz.PtzOfflineNotify ptz_offline = 105;
    terrahub.device.ptz.PtzDeviceCapability ptz_capability = 106;
    terrahub.device.ptz.PtzMotionCmd ptz_motion_cmd = 110;
    terrahub.device.ptz.PtzLensCmd ptz_lens_cmd = 111;
    terrahub.device.ptz.PtzManualLockTargetCmd ptz_manual_lock = 112;
    terrahub.device.ptz.PtzSwitchTrackCmd ptz_switch_track = 113;
    terrahub.device.ptz.PtzDefogCmd ptz_defog_cmd = 114;
    terrahub.device.ptz.PtzWindowHeatCmd ptz_window_heat_cmd = 115;
    terrahub.device.ptz.PtzIcrCmd ptz_icr_cmd = 116;
    terrahub.device.ptz.PtzCmdResult ptz_cmd_result = 117;

    // ── Radar 设备扩展（field 200+）──
    terrahub.device.radar.RadarTargetList radar_targets = 200;
    terrahub.device.radar.RadarStatus radar_status = 201;
    terrahub.device.radar.RadarDeviceInfo radar_device_info = 202;
    terrahub.device.radar.RadarOnlineNotify radar_online = 203;
    terrahub.device.radar.RadarOfflineNotify radar_offline = 204;
    terrahub.device.radar.RadarDeviceCapability radar_capability = 205;
    terrahub.device.radar.RadarScanModeCmd radar_scan_mode_cmd = 210;
    terrahub.device.radar.RadarTrackCmd radar_track_cmd = 211;
    terrahub.device.radar.RadarCmdResult radar_cmd_result = 212;

    // ── LiveStream 扩展（field 300+）── 预留
    terrahub.livestream.LiveStatus live_status = 300;
    terrahub.livestream.LiveCapacity live_capacity = 301;
    terrahub.livestream.LiveControl live_control = 310;
    terrahub.livestream.ShmRegisterNotify live_shm_register = 311;
    terrahub.livestream.ShmUnregisterNotify live_shm_unregister = 312;
  }

  string additional_information = 13;
}
```

但 AimRT Channel 实际使用时，有两种模式可选（重要：**待确认**）：

#### 模式 A：每个 Channel 直接用具体类型（不使用 TerraHubMessage 信封）

Channel Topic 的消息类型直接是 `PtzStatus`、`PtzMotionCmd` 等具体类型，不套 `TerraHubMessage` 信封。`TerraHubMessage` 仅在 Gateway 对外通信时使用。

```cpp
// PtzModule 发布
aimrt::channel::PublisherRef<terrahub::device::ptz::PtzStatus> status_pub_;

void PtzModule::PublishStatus() {
    terrahub::device::ptz::PtzStatus msg;
    msg.set_device_sn("PTZ-HEPU-001");
    msg.set_timestamp_ms(GetNowMs());
    msg.set_work_status(1);
    msg.set_work_mode(2);
    msg.set_tracking_status(1);
    msg.set_defog_on(true);
    status_pub_.Publish(msg);  // Channel topic: "ptz/status"
}

// WebGateway 订阅 —— 直接拿到 PtzStatus，不需要判断 oneof
void WebGateway::OnPtzStatus(const terrahub::device::ptz::PtzStatus& status) {
    json j;
    j["sn"] = status.device_sn();
    j["workMode"] = status.work_mode();
    ws_server_.Send(j.dump());  // 推给 PC 浏览器
}

// NexusGateway 订阅 —— 需要手动构造 TerraHubMessage/SapientMessage 转发给天盾
void NexusGateway::OnPtzStatus(const terrahub::device::ptz::PtzStatus& status) {
    terrahub::TerraHubMessage msg;
    msg.set_node_id(status.device_sn());
    msg.mutable_timestamp()->set_seconds(status.timestamp_ms() / 1000);
    *msg.mutable_ptz_status() = status;  // 套上信封
    mqtt_client_.Publish("sapient/status", msg.SerializeAsString());
}
```

**特点**：PtzModule 代码简洁；订阅方直接拿到具体类型无需判断；Gateway 对外时再套信封。

#### 模式 B：统一用 TerraHubMessage 信封

所有 AimRT Channel 的消息类型统一为 `TerraHubMessage`，PTZ 业务数据作为 `oneof content` 中的载荷。

```cpp
// PtzModule 发布
aimrt::channel::PublisherRef<terrahub::TerraHubMessage> status_pub_;

void PtzModule::PublishStatus() {
    terrahub::TerraHubMessage msg;
    msg.set_node_id("PTZ-HEPU-001");
    msg.mutable_timestamp()->set_seconds(GetNowSec());
    auto* status = msg.mutable_ptz_status();  // oneof 选中 ptz_status
    status->set_device_sn("PTZ-HEPU-001");
    status->set_work_status(1);
    status->set_work_mode(2);
    status->set_tracking_status(1);
    status->set_defog_on(true);
    status_pub_.Publish(msg);  // Channel topic: "ptz/status"
}

// WebGateway 订阅 —— 需要判断 oneof 分支
void WebGateway::OnPtzStatus(const terrahub::TerraHubMessage& msg) {
    if (msg.content_case() == terrahub::TerraHubMessage::kPtzStatus) {
        const auto& status = msg.ptz_status();
        json j;
        j["sn"] = status.device_sn();
        j["workMode"] = status.work_mode();
        ws_server_.Send(j.dump());
    }
}

// NexusGateway 订阅 —— node_id/timestamp 可直接复用，转换更简单
void NexusGateway::OnPtzStatus(const terrahub::TerraHubMessage& msg) {
    // 信封层直接转发，无需重新构造
    mqtt_client_.Publish("sapient/status", msg.SerializeAsString());
}
```

**特点**：所有模块通信格式统一；NexusGateway 可直接序列化转发；PtzModule 多一层包装代码；订阅方需判断 `content_case()`。

#### 两种模式对比


| 维度                | 模式 A（具体类型）                     | 模式 B（TerraHubMessage 信封）        |
| ----------------- | ------------------------------ | ------------------------------- |
| PtzModule 代码      | 简洁，直接填业务字段                     | 多一层信封包装                         |
| 订阅方代码             | 直接用，无需 `switch`                | 需判断 `content_case()`            |
| Gateway 转 SAPIENT | 需手动构造信封的 `node_id`/`timestamp` | 信封可直接复用，转换更省事                   |
| 格式统一性             | Channel 各不相同                   | 所有 Channel 统一类型                 |
| 后续扩展              | 新增设备加新 proto 即可                | 需在 `TerraHubMessage.oneof` 追加字段 |
| 序列化开销             | 无额外开销                          | 多 ~20-30 字节信封                   |


> **⚠️ 待确认**：AimRT Channel 使用模式 A 还是模式 B，需与领导对齐后确定。

### 13.7 对现有 Proto 设计的影响


| 影响范围                 | 当前设计                               | SAPIENT 对齐后                                                        | 状态                   |
| -------------------- | ---------------------------------- | ------------------------------------------------------------------ | -------------------- |
| Proto 消息结构           | 自定义 `PtzStatus`、`PtzGuidanceCmd` 等 | 保持自定义消息，通过 `TerraHubMessage.oneof` 封装                              | **PtzModule 侧可先行定义** |
| 消息封装                 | 各消息独立                              | 新增 `TerraHubMessage` 信封（`node_id` + `timestamp` + `oneof content`） | **PtzModule 侧可先行定义** |
| SAPIENT 官方 Proto     | 未使用                                | 保持 `protocols/sapient/` 不修改，`TerraHubMessage` 引用其标准类型              | **不修改官方 Proto**      |
| Channel/RPC Topic 命名 | `ptz/status`、`ptz/guidance_cmd` 等  | 保持现有命名，消息类型待确认（具体类型 vs TerraHubMessage）                            | **待确认模式 A/B**        |
| 设备注册流程               | `device/ptz_online` 通知             | 可复用 SAPIENT `Registration` 或保持自定义 `PtzOnlineNotify`                | **PtzModule 侧可先行定义** |
| 目标检测格式               | 自定义 `AiTrackResult`                | 可对齐 SAPIENT `DetectionReport` 或保持自定义                               | **PtzModule 侧可先行定义** |


### 13.8 参考资料


| 来源                                                                                                                                                                 | 说明                                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------- |
| [BSI Flex 335 标准文档](https://knowledge.bsigroup.com/products/sapient-network-of-autonomous-sensors-and-effectors-interface-control-document-specification/standard) | SAPIENT 接口控制文档（ICD）正式标准             |
| [dstl/SAPIENT-Proto-Files (GitHub)](https://github.com/dstl/SAPIENT-Proto-Files)                                                                                   | 官方 Protobuf 定义文件（BSI Flex 335 v2.0） |
| [dstl/Apex-SAPIENT-Middleware (GitHub)](https://github.com/dstl/Apex-SAPIENT-Middleware)                                                                           | SAPIENT 中间件参考实现（消息路由、校验、存档）         |
| [飞书 Wiki — SAPIENT 协议文档](https://vxr5wm8r80r.feishu.cn/wiki/WiE9wfXjmiSrtukIaDncd6lvnfh)                                                                           | 内部 SAPIENT 协议中文解读                   |
| [飞书 Slides — SAPIENT 协议介绍](https://vxr5wm8r80r.feishu.cn/slides/QoOCsA4ZBlKsJ6dDutDchQb9ncb)                                                                       | 内部 SAPIENT 协议演示文稿                   |


---

## 十四、测试与验证

> AimRT 框架通过 CMake `FetchContent` 拉取 **googletest v1.13.0**（含 gtest + gmock），提供 `add_gtest_target()` 宏统一生成测试目标（自动链接 `GTest::gtest`、`GTest::gtest_main`、`GTest::gmock`、`GTest::gmock_main`）。构建时设置 `AIMRT_BUILD_TESTS=ON` 即可启用，测试文件与源码同目录并列，命名规则为 `*_test.cc`。

### 14.1 测试分层策略

```mermaid
flowchart TD
    L1["L1 单元测试\ngtest + gmock\n无硬件依赖"]
    L2["L2 模块集成测试\nAimRT 单进程内\nMock Channel/RPC"]
    L3["L3 系统联调测试\n真实硬件在环\n端到端验证"]

    L1 --> L2 --> L3
```




| 层级            | 工具                        | 运行环境            | 执行频率  | 覆盖目标                       |
| ------------- | ------------------------- | --------------- | ----- | -------------------------- |
| **L1 单元测试**   | gtest + gmock             | 开发机/CI，无硬件      | 每次编译  | 类方法、协议解析、数据转换              |
| **L2 模块集成测试** | gtest + AimRT MockChannel | AGX 开发板，无真实 PTZ | 每日构建  | Channel/RPC 链路、消息序列化、多设备路由 |
| **L3 系统联调测试** | 手动 + 自动化脚本                | AGX + 真实 PTZ 硬件 | 里程碑节点 | 端到端控制、状态上报、异常恢复            |


### 14.2 L1 单元测试用例

测试文件放在源码同级目录，命名格式 `xxx_test.cc`，通过 `add_gtest_target()` 注册。

#### 14.2.1 Proto 消息测试


| 测试文件                | 测试项            | 验证内容                                              |
| ------------------- | -------------- | ------------------------------------------------- |
| `ptz_proto_test.cc` | Proto 序列化/反序列化 | `PtzStatus` 设置字段后序列化→反序列化，字段值一致                   |
|                     | Proto 默认值      | 新建空 `PtzMotionCmd`，所有字段为默认值（0/""/false）           |
|                     | Proto 字段边界     | `horizontal_angle` 设置 ±360°，`zoom` 设置极限值，序列化不丢失精度 |


#### 14.2.2 设备工厂测试


| 测试文件                         | 测试项      | 验证内容                                                       |
| ---------------------------- | -------- | ---------------------------------------------------------- |
| `ptz_device_factory_test.cc` | 工厂创建和普设备 | `createDevice(PTZ_HEPU, config)` 返回 `PtzDeviceHepu` 实例     |
|                              | 工厂创建耐杰设备 | `createDevice(PTZ_NAIJIE, config)` 返回 `PtzDeviceNaijie` 实例 |
|                              | 未知设备类型   | `createDevice(999, config)` 返回 `nullptr`                   |
|                              | 多设备实例    | 同时创建和普+耐杰各一台，SN 不冲突                                        |


#### 14.2.3 耐杰协议解析测试


| 测试文件                      | 测试项    | 验证内容                                     |
| ------------------------- | ------ | ---------------------------------------- |
| `naijie_protocol_test.cc` | 状态报文解析 | 构造已知字节序列 → 解析出正确的方位角/俯仰角/工作状态            |
|                           | 控制指令打包 | 构造 `PtzMotionCmd` → 序列化为 UDP 报文 → 字节对比预期 |
|                           | 异常报文处理 | 短报文/校验错误 → 解析返回错误码，不崩溃                   |
|                           | 多帧粘包   | 连续两帧数据 → 正确拆包解析                          |


#### 14.2.4 和普 SDK 封装测试


| 测试文件                    | 测试项      | 验证内容                                          |
| ----------------------- | -------- | --------------------------------------------- |
| `hepu_ptz_ctrl_test.cc` | 控制指令参数映射 | `ctrlPtzMotion(LEFT, speed=50)` → SDK 调用参数正确  |
|                         | 镜头控制参数   | `ctrlPtzLens(ZOOM_IN, speed=30)` → SDK 调用参数正确 |
|                         | 状态数据转换   | SDK 回调原始数据 → `PtzStatus` Proto 字段映射正确         |


#### 14.2.5 设备 SN 路由测试


| 测试文件                         | 测试项     | 验证内容                                                  |
| ---------------------------- | ------- | ----------------------------------------------------- |
| `ptz_module_routing_test.cc` | SN 路由正确 | 两台设备在线，收到 `PtzMotionCmd{sn="PTZ-HEPU-001"}` → 仅和普设备执行 |
|                              | 不存在的 SN | 收到未知 SN 的控制指令 → 日志告警，不崩溃                              |
|                              | 设备离线后指令 | 设备离线 → 收到该 SN 控制指令 → 返回设备不可达错误                        |


### 14.3 L2 模块集成测试用例

使用 gmock Mock AimRT Channel/RPC 接口，在 AimRT 进程内验证 PtzModule 的完整消息链路。

#### 14.3.1 状态上报链路


| 测试项           | 步骤                                      | 预期结果                                    |
| ------------- | --------------------------------------- | --------------------------------------- |
| 状态 Channel 发布 | 启动 PtzModule → Mock 设备返回状态数据 → 等待 100ms | 收到 `ptz/status` Channel 消息，频率 ≈10Hz     |
| 多订阅者接收        | 同时订阅 `ptz/status` 的 3 个 Mock 消费者        | 3 个消费者均收到相同消息                           |
| 镜头信息同步        | Mock 设备变焦到 10x                          | `ptz/lens_info` 中 `visible_zoom` = 10.0 |
| 方位角精度         | Mock 设备设置 azimuth=123.456°              | `ptz/azimuth_pitch_info` 中精度 ≤0.001°    |


#### 14.3.2 控制链路


| 测试项          | 步骤                                         | 预期结果                                                 |
| ------------ | ------------------------------------------ | ---------------------------------------------------- |
| Channel 控制指令 | 发布 `ptz/motion_cmd` Channel → PtzModule 收到 | Mock 设备的 `ctrlPtzMotion()` 被调用，参数匹配                  |
| AI 跟踪结果      | 发布 `ptz/ai_track_result` Channel           | Mock 设备的 `onAiDetectionResults()` 被调用                |
| 设备直控 RPC     | 调用 `PtzDefogControl` RPC（enable=true）      | Mock 设备透雾开启，返回 `PtzCmdResult{code=0}`                |
| RPC 设备离线     | 设备不在线时调用 RPC                               | 返回 `PtzCmdResult{code=非0, message="device offline"}` |


#### 14.3.3 设备生命周期


| 测试项    | 步骤                | 预期结果                                                        |
| ------ | ----------------- | ----------------------------------------------------------- |
| 设备上线通知 | PtzModule 检测到设备连接 | 发布 `device/ptz_online`（携带 RTSP URL）、`device/ptz_capability` |
| 设备离线通知 | Mock 设备断开         | 发布 `device/ptz_offline`                                     |
| 重连恢复   | 设备断开 5s 后重连       | 重新发布上线通知，状态上报恢复                                             |


### 14.4 L3 系统联调测试用例

需 AGX + 真实 PTZ 硬件环境，人工或脚本驱动。


| 测试项      | 设备     | 步骤                        | 通过标准                             |
| -------- | ------ | ------------------------- | -------------------------------- |
| 和普转台控制   | 和普 PTZ | 下发 LEFT 指令 → 观察云台         | 云台向左转动，`azimuth_pitch_info` 角度变化 |
| 和普变焦控制   | 和普 PTZ | 下发 ZOOM_IN → 停止           | `lens_info.visible_zoom` 值增大     |
| 和普透雾 RPC | 和普 PTZ | RPC 调用 defog=true/false   | 透雾灯开关，RPC 返回 code=0              |
| 耐杰转台控制   | 耐杰 PTZ | 下发 motion_cmd → 观察        | 云台转动，角度反馈变化                      |
| 耐杰协议丢包恢复 | 耐杰 PTZ | 拔网线 3s → 重插               | 状态上报在 5s 内恢复，无崩溃                 |
| 双设备并发    | 和普+耐杰  | 同时控制两台设备                  | 各自独立响应，SN 路由正确                   |
| 状态上报频率   | 任意 PTZ | 统计 10s 内 `ptz/status` 消息数 | 频率 9.5~10.5 Hz                   |
| 长时间稳定性   | 任意 PTZ | 连续运行 24h                  | 无内存泄漏、无崩溃、状态上报持续正常               |


### 14.5 测试代码组织

```
src/02_DevAbsLayer/01_Detector/Ptz/
├── ptz_module.h
├── ptz_module.cc
├── ptz_module_routing_test.cc        ← L1: SN 路由
├── ptz_device_base.h
├── ptz_device_factory.h
├── ptz_device_factory_test.cc        ← L1: 工厂
├── HepuPtz/
│   ├── hepu_ptz_device.h
│   ├── hepu_ptz_device.cc
│   └── hepu_ptz_ctrl_test.cc         ← L1: 和普 SDK 封装
├── NaijiePtz/
│   ├── naijie_ptz_device.h
│   ├── naijie_ptz_device.cc
│   ├── naijie_eth_link.h
│   ├── naijie_eth_link.cc
│   └── naijie_protocol_test.cc       ← L1: 耐杰协议解析
└── test/
    ├── ptz_proto_test.cc             ← L1: Proto 消息
    ├── ptz_channel_test.cc           ← L2: Channel 链路集成
    ├── ptz_rpc_test.cc               ← L2: RPC 直控集成
    └── ptz_lifecycle_test.cc         ← L2: 设备生命周期集成
```

### 14.6 CMake 集成

```cmake
if(AIMRT_BUILD_TESTS)
  add_gtest_target(
    TEST_TARGET ptz_module
    TEST_SRC
      ptz_module_routing_test.cc
      ptz_device_factory_test.cc
      HepuPtz/hepu_ptz_ctrl_test.cc
      NaijiePtz/naijie_protocol_test.cc
      test/ptz_proto_test.cc
      test/ptz_channel_test.cc
      test/ptz_rpc_test.cc
      test/ptz_lifecycle_test.cc
  )
endif()
```

构建与执行：

```bash
cmake -B build -DAIMRT_BUILD_TESTS=ON
cmake --build build
cd build && ctest --output-on-failure
```

