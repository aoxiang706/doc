---
name: AimRT Device Management PTZ
overview: 分析设备管理子系统（devm + topo）设计的合理性并提出改进建议，同时设计和普PTZ设备接入AimRT的迁移方案。
todos:
  - id: analyze-devm-topo
    content: 分析设备管理子系统设计（devm + topo 分离方案评审），已结合设备树结构图和节点接入规则图细化
    status: completed
  - id: define-proto-msgs
    content: 定义 protobuf 消息：设备管理（DeviceOnlineEvent/OfflineEvent/DeviceTreeNode/TopologySnapshot）+ PTZ 控制/状态（对应现有 8 个 skyfend_interfaces msg）
    status: pending
  - id: create-devm-module
    content: 创建 component-devm 组件，实现 DevmModule（物理设备管理：发现/连接/心跳/属性）
    status: pending
  - id: create-topo-module
    content: 创建 component-topo 组件，实现 TopoModule（设备树拓扑：三场景规则/热插拔重组/查询RPC）
    status: pending
  - id: create-ptz-module
    content: 创建 component-driver-ptz-hepu 组件，实现 PtzHepuModule（AimRT Module）
    status: pending
  - id: migrate-device-logic
    content: 将 PtzDeviceHepu 控制逻辑迁移到 PtzHepuDevice，去除 ROS2 依赖
    status: pending
  - id: setup-channels
    content: 配置 AimRT Channel 替代 ROS2 pub/sub，包括 ros2_plugin 桥接
    status: pending
  - id: migrate-video-pipeline
    content: 移植视频管道（GStreamer + SHM），保持独立于 AimRT Channel
    status: pending
  - id: create-pkg-config
    content: 创建 pkg_main.cc 注册 + YAML 运行时配置（devm/topo/ptz 三个模块）
    status: pending
  - id: integration-test
    content: 在 AGX 192.168.3.104 上集成测试验证
    status: pending
isProject: false
---

# AimRT 设备管理子系统分析与和普 PTZ 迁移方案

---

## 零、当前工程子设备接入方式全景分析

基于对 `ptz100_agx` 代码的完整分析，所有子设备按通信协议分为以下几类：

### 0.1 通信协议分类总表


| 设备                          | 枚举值 | 协议                  | 传输层             | AGX 角色              | 代码位置                                           |
| --------------------------- | --- | ------------------- | --------------- | ------------------- | ---------------------------------------------- |
| **SDH100** (近程雷达)           | 1   | ALINK V1/V2         | TCP             | TCP Server (18070+) | `eth_link_server.c`, `alink_order.c`           |
| **耐杰PTZ** (近程)              | 2   | TMCC 私有协议           | UDP             | UDP Client (9966)   | `eth_link_ptz.cpp`, `ptz_protocol/ptz_tmcc.c`  |
| **SRP100** (近程雷视)           | 3   | ALINK               | TCP             | AGX 即主机，C2 TCP 接入   | `eth_link.c`, `c2_network.cpp`                 |
| **TracerP/STP130** (侦测)     | 4   | ALINK V2            | TCP             | TCP Server (18070+) | `alink_track.cpp` (心跳0xEF, UAS 0xE9)           |
| **TRACER_S**                | 5   | ALINK               | TCP             | TCP Server          | `eth_link_server.c`                            |
| **SFL100** (打击)             | 6   | ALINK               | TCP             | TCP Server (18070+) | `eth_link_server.c`                            |
| **SSH110** (固定诱骗)           | 7   | ALINK (经 Sentry 转发) | TCP             | 通过 SFL200 透传        | `alink_sentry.cpp`                             |
| **DPH100** (雷达)             | 8   | Protobuf + ALINK V2 | TCP/UDP         | TCP Server / UDP    | `dhp100_link` ROS 节点, `radar.proto`            |
| **耐杰PTZ** (中程)              | 9   | TMCC 私有协议           | UDP             | UDP Client (9966)   | `eth_link_ptz.cpp`, `ptz_tmcc.c`               |
| **SVH100** (侦测)             | 10  | ALINK (经 SFL200 转发) | TCP             | TCP Server          | `alink_sentry.cpp` (payload 透传)                |
| **SRP230** (雷视)             | 11  | ALINK               | TCP             | AGX 即主机             | `eth_link.c`                                   |
| **DPH120** (中程机扫雷达)         | 12  | Protobuf + UDP      | UDP/TCP         | ROS2 节点             | `dhp100_link/CRadarDPH120.cpp`                 |
| **DPH130** (中程四面阵雷达)        | 13  | Protobuf + UDP      | UDP/TCP         | ROS2 节点             | `dhp100_link/CRadarDPH130.cpp`                 |
| **SRP200** (中程四面阵雷视)        | 14  | ALINK               | TCP             | AGX 即主机             | `eth_link.c`                                   |
| **SRP210** (中程机扫雷视)         | 15  | ALINK               | TCP             | AGX 即主机             | `eth_link.c`                                   |
| **STP120** (侦测)             | 16  | ALINK V2            | TCP             | TCP Server (18070+) | `alink_stp120.cpp` (心跳0x25)                    |
| **Laser HEF100**            | 17  | JSON 私有协议           | UDP             | UDP Client (8010)   | `iotDevices/laserHeSDK/`, `laser_service`      |
| **BR100A** (惯导)             | 18  | GIAVP 私有协议          | TCP             | TCP Client (6666)   | `iotDevices/memsBr100aSDK/`, `br100a` ROS      |
| **BPH110** (雷视激光)           | 19  | ALINK               | TCP             | AGX 即主机             | `alink_bph110.cpp`                             |
| **Laser HEP10**             | 20  | JSON 私有协议           | UDP             | UDP Client (8010)   | `iotDevices/laserHeSDK/`                       |
| **Laser HEP21**             | 21  | JSON 私有协议           | UDP             | UDP Client (8010)   | `iotDevices/laserHeSDK/`                       |
| **Sentry/SFL210**           | 22  | ALINK               | TCP             | AGX 即主机             | `alink_sentry.cpp`                             |
| **PTZ HEPU** (和普非制冷)        | 23  | **HVideo SDK 私有协议** | **TCP** (39020) | TCP Client (SDK)    | `iotDevices/ptzHepuSDK/`, `ptz_service`        |
| **STF200** (Tracer Matrix)  | 24  | ALINK V2 + Protobuf | TCP             | TCP Server (18070+) | `alink_tracerMatrix.cpp`, `TracerMatrix.proto` |
| **STA100** (Tracer Air)     | 25  | ALINK               | TCP             | TCP Server          | 同 TracerP 类                                    |
| **SSF100** (Spotter近程)      | 26  | ALINK               | TCP             | AGX 即主机             | `alink_efence.cpp`                             |
| **SFL200** (Sentry旧款)       | 27  | ALINK               | TCP             | AGX 即主机             | `sfl200_app.cpp`                               |
| **SSF210** (Spotter Pro机扫)  | 28  | ALINK               | TCP             | AGX 即主机             | `alink_efence.cpp`                             |
| **SSF200** (Spotter Pro四面阵) | 29  | ALINK               | TCP             | AGX 即主机             | `alink_efence.cpp`                             |
| **PTZ HEPU COOLED** (和普制冷)  | 30  | **HVideo SDK 私有协议** | **TCP** (39020) | TCP Client (SDK)    | 同 PTZ HEPU                                     |
| **SHH300** (Hunter Max)     | 31  | ALINK               | TCP             | TCP Server (18070+) | `alink_sentry.cpp`                             |
| *TempSensor PT100*          | -   | **Modbus RTU**      | **UART** RS485  | 串口设备                | `iotDevices/tempSensorPT100SDK/`               |


### 0.2 按协议族归类

#### A. ALINK 协议族（TCP 传输，最大类）

ALINK 是 AGX 与大多数子设备通信的核心协议，分 V1 和 V2 两个版本。

```mermaid
flowchart TD
    subgraph transport [eth_link 传输层]
        eth_client["eth_link.c\nTCP Client → C2\n192.168.2.163:19005"]
        eth_server["eth_link_server.c\nTCP Server 18070+\n接受设备连接"]
        udp_bc["UDP broadcast\n1800/1810\n设备自动发现"]
    end

    subgraph protocol [alink 协议层]
        recv["alink_recv.c\n解析数据包"]
        order["alink_order.c\n按 msgid 分发"]
        upload["alink_upload.c\n组装上行包"]
    end

    subgraph handlers [command 设备命令处理]
        sentry_cmd["sentry/\nSFL200 SVH100 SHH300"]
        efence_cmd["efence/\nSSF100/200/210"]
        bph_cmd["bph110/\nBPH110 + Laser"]
        track_cmd["track/\nTracerP STP130"]
        matrix_cmd["tracerMatrix/\nSTF200"]
        stp_cmd["stp120/\nSTP120"]
    end

    transport --> recv
    recv --> order
    order --> handlers
    handlers --> upload
    upload --> transport
```



**设备发现流程**：

1. `eth_link_server.c` 每 2s 在 eth1 UDP 1800 端口广播 lookup (0xBA V1/V2)
2. 子设备响应 0xBB (LOOKUP_RESP)，携带 SN、类型等信息
3. AGX 解析响应，创建 TCP Server 端口，发送 request-connect
4. 子设备 TCP 连接到 AGX，进入 ALINK 通信

**ALINK 设备 ID 映射** (`alink.h`)：

```
C2=6, Radar=3(V1)/0xF3(V2), SFL100=11, SRP100=12, SFL200=0x0D,
SFL210=0x21, STP120=0x20, STF200=0x2A, SRP230=0x11, SRP210=0x14,
SRP200=0x1D, BPH110=0x1F, SVH100=0x16, SHH300=0x27,
SSF100=0x1B, SSF200=0x23, SSF210=0x24, TracerP=0x22
```

#### B. 私有 SDK 协议族（非 ALINK）


| 设备            | SDK                  | 协议               | 传输   | 端口                  | 代码                                         |
| ------------- | -------------------- | ---------------- | ---- | ------------------- | ------------------------------------------ |
| **和普 PTZ**    | `ptzHepuSDK`         | HVideo SDK (TCP) | TCP  | 39020               | `ptz_hepu_ctrl.cpp` via `HVS_Connect()`    |
| **和普 PTZ AI** | `ptzHepuSDK`         | 自定义 UDP          | UDP  | 39080               | `ptz_hepu_smart.cpp`                       |
| **耐杰 PTZ**    | `thirdpart/naijie/`  | TMCC 协议          | UDP  | 9966                | `eth_link_ptz.cpp`, `ptz_tmcc.c`           |
| **Laser HE**  | `laserHeSDK`         | JSON over UDP    | UDP  | 8009/8010/8020-8022 | `laserHeCtrl.cpp`, `laserHeCtrlSwitch.cpp` |
| **BR100A**    | `memsBr100aSDK`      | GIAVP NMEA帧      | TCP  | 6666                | `memsBr100a.cpp` via `SocketTcpClient`     |
| **PT100**     | `tempSensorPT100SDK` | Modbus RTU       | UART | /dev/ttysWK0        | `tempSensorPT100.cpp` via `UartService`    |


#### C. Protobuf 混合协议（ALINK 传输 + Protobuf 编码）


| 设备                | proto 文件                                     | 传输      |
| ----------------- | -------------------------------------------- | ------- |
| 雷达 (SDH100/DPH系列) | `devices_pb/radar/radar.proto`               | TCP/UDP |
| 设备发现广播            | `devices_pb/radar/broadcast.proto`           | UDP     |
| STF200            | `devices_pb/TracerMatrix/TracerMatrix.proto` | TCP     |


#### D. ROS2 节点通信（进程内/间）


| 设备         | ROS 包              | 接入方式               |
| ---------- | ------------------ | ------------------ |
| DPH120/130 | `dhp100_link`      | ROS 节点，内部用 UDP 连雷达 |
| BR100A     | `br100a`           | ROS 节点，内部用 TCP     |
| Laser HE   | `laser_service`    | ROS 节点，内部用 UDP     |
| 和普 PTZ     | `ptz_service`      | ROS 节点，内部用 TCP     |
| 电子围栏       | `electronic_fence` | ROS 节点 + MQTT      |
| AI         | `ptz100_ai`        | ROS 节点，SHM 接收视频帧   |


### 0.3 通信架构示意图

```mermaid
flowchart TB
    subgraph external [外部上位机]
        C2["C2 / 天盾云平台\n192.168.2.163:19005"]
    end

    subgraph agx [AGX 主控]
        eth_link["eth_link 传输层\neth_link.c / alink.c"]
    end

    subgraph discovery [UDP 广播发现\neth1:1800/1810]
        lookup["lookup 0xBA/0xBB\n设备自动注册\n触发TCP连接"]
    end

    subgraph alink_tcp [TCP Server 18070+\nALINK 协议]
        alink_devs["SDH100 / SFL100\nTracerP / STP120\nSVH100 / SHH300\nSTF200"]
    end

    subgraph private_proto [私有协议直连]
        hepu_ptz["和普PTZ TCP:39020"]
        naijie_ptz["耐杰PTZ UDP:9966"]
        laser["Laser UDP:8010"]
        br100a["BR100A TCP:6666"]
        pt100["PT100 UART RS485"]
    end

    C2 <-->|"TCP Client\nALINK V1/V2"| eth_link
    eth_link --> discovery
    eth_link --> alink_tcp
    eth_link --> private_proto
```



### 0.4 对 devm 模块设计的影响

分析结果表明，devm 需要管理 **三类物理连接**：

1. **ALINK TCP 连接**（最多 ~20 个设备）：AGX 作为 TCP Server 或 Client
2. **私有协议连接**（~6 种 SDK）：各 SDK 自带连接管理
3. **UART 串口连接**（1 个设备）：PT100 温度传感器

**设计建议**：

- devm 不需要自己实现所有协议的连接管理
- devm 通过 **统一的设备注册接口** 接收各驱动模块的上线/下线通知
- 各驱动模块（如 `PtzHepuModule`、`LaserModule`）自己管理物理连接
- devm 维护 **设备注册表**（在线设备列表 + 属性）

```mermaid
flowchart LR
    subgraph devm_module [devm 设备注册中心]
        registry["DeviceRegistry\n在线设备表"]
        udp_disc["UDP 广播发现\nALINK 设备"]
        hb_monitor["心跳监测"]
    end

    subgraph drivers [各驱动模块 - 独立管理连接]
        ptz["PtzHepuModule\nTCP 39020"]
        laser["LaserModule\nUDP 8010"]
        br100a["Br100aModule\nTCP 6666"]
        alink_dev["AlinkDeviceModule\nTCP Server 18070+"]
    end

    ptz -->|"DeviceOnline/Offline"| registry
    laser -->|"DeviceOnline/Offline"| registry
    br100a -->|"DeviceOnline/Offline"| registry
    alink_dev -->|"DeviceOnline/Offline"| registry
    udp_disc --> registry
    hb_monitor --> registry
```



---

## 一、设备管理子系统设计分析

### 1.1 总体评价：设计方向正确，devm + topo 分离合理

你提出的"管理面/数据面/控制面"三面划分是成熟的系统架构思路。`devm` + `topo` 双模块分离职责清晰。

**子系统范围确认**：

- 设备管理子系统 = **devm + topo** 两个 AimRT Module
- ALINK 协议、时间同步（C2 ↔ AGX）**不属于**设备管理子系统，由上层其他模块负责
- devm/topo 是 AimRT **Module**（业务逻辑层），打包为 pkg `.so`，不是 Plugin（框架扩展层）

### 1.2 设计优点（保留）

- **devm/topo 分离**：`devm` 管物理连接，`topo` 管逻辑拓扑，关注点分离
- **设备树管理**：用树形结构反映真实硬件拓扑（Sentry > Spotter > 子设备），符合三场景组网
- **热插拔 + 动态重组**：支持设备在线接入/移除后自动调整树结构
- **被动数据提供者**：topo 不主动与 C2 通信，上层（ALINK 模块等）按需向 topo 查询拓扑

### 1.3 devm 与 topo 的职责边界

```
devm（物理层 - 设备管理模块）        topo（逻辑层 - 拓扑管理模块）
────────────────────────            ──────────────────────────
UDP 广播监听（1810/1800端口）        订阅 devm 的 DeviceOnline/Offline 事件
TCP/UART 连接建立与管理              根据设备类型 + 优先级规则构建设备树
心跳检测 & 超时判定                  维护父子关系（三场景规则）
设备属性采集（SN/IP/类型/版本）      热插拔触发树重组
在线设备注册表维护                   拓扑快照查询 RPC 接口

发布 Channel:                       发布 Channel:
  - device_online                     - topology_changed
  - device_offline                  提供 RPC:
  - device_status_update              - GetTopologySnapshot
                                      - GetDeviceChildren
                                      - GetRootDevice
```

**关键原则**：devm 不感知"谁是谁的父设备"，topo 不感知"设备如何连接"。

### 1.4 设备树三场景拓扑规则（topo 核心逻辑）

基于设备树节点接入规则和结构示意图，topo 需实现以下三场景：

#### 场景 1：仅 Sentry（两层树）

```
根节点: Sentry
├── SFL100
├── 中程雷达
├── Hunter（枪）
├── STP120（电侦）
├── TracerP
└── Spoofer
```

- Sentry 直接对接 C2/天盾
- 无 Spotter，设备树共两层

#### 场景 2：仅 Spotter（两层树）

```
根节点: Spotter
├── 近程雷达 (1~4个)
├── 近程 PTZ
└── STP130（电侦）
```

- 无 Sentry 时，Spotter 作为根节点直接对接 C2/天盾
- Spotter Pro（中程）支持 1R1V 或 4R1V 配置
- SRP 系列将逐步被 Spotter 替代

#### 场景 3：Sentry + Spotter（三层树）

```
根节点: Sentry
├── Spoofer
├── Hunter
├── Tracer
├── Spotter-A ──┬── PTZ1
│               ├── Radar1
│               └── Tracer1
├── Spotter-B ──┬── PTZ2
│               ├── Radar2
│               └── Tracer2
└── SFL100 等其他子设备
```

- Spotter 作为虚拟子设备挂载到 Sentry，**不直接**对接 C2/云端
- Spotter 的子设备规则同场景 2
- 设备树共三层，Sentry 为核心中转节点，Spotter 信息统一通过 Sentry 上报

#### topo 根节点判定算法

```
1. 在线设备中存在 Sentry（sfl200/sentry/sfl210）？
   → 是：Sentry 为根节点（场景 1 或 3）
   → 否：继续

2. 在线设备中存在 Spotter/泛雷视？
   按优先级：srp100 > srp200 > srp210 > srp230 > ssf100 > ssf200 > ssf210 > bph110
   → 是：第一个在线的为根节点（场景 2）
   → 否：无主设备

3. 当 Sentry 上线时，若之前 Spotter 为根：
   → Spotter 从根降级为 Sentry 的子节点（动态重组）

4. 当 Sentry 下线时，若存在 Spotter：
   → Spotter 从子设备升级为根节点（动态重组）
```

### 1.5 改进后的架构设计

```
aimrt_main (AGX 192.168.3.104 上运行，配置驱动加载)
│
├── [Plugins 层 - 框架扩展]
│   ├── net_plugin          # TCP/UDP 底层通信
│   └── ros2_plugin         # ROS2 桥接（渐进迁移，与现有 AI 节点兼容）
│
├── [Pkg: component-devm]   ──────────────────────────────────────┐
│   └── DevmModule  （物理设备管理模块）                           │
│       ├── UdpDiscoveryService     - UDP 广播监听（1810/1800）    │ 设备管理
│       ├── ConnectionManager       - TCP/UART 连接池              │ 子系统
│       ├── HeartbeatMonitor        - 心跳超时检测                 │
│       ├── DeviceRegistry          - 在线设备注册表               │
│       └── Channel 发布:                                         │
│           device_online / device_offline / device_status          │
│                                                                  │
├── [Pkg: component-topo]   ──────────────────────────────────────┘
│   └── TopoModule  （设备树拓扑模块）
│       ├── TopologyBuilder         - 三场景树构建
│       ├── RootNodeResolver        - 根节点优先级判定
│       ├── HotPlugHandler          - 热插拔动态重组
│       ├── Channel 发布: topology_changed
│       └── RPC 提供: GetTopologySnapshot / GetDeviceChildren
│
├── [Pkg: component-driver-ptz-hepu]   # PTZ 驱动包（独立组件）
│   └── PtzHepuModule
│       ├── 封装 ptzHepuSDK（HepuPtz/HepuPtzCtrl）
│       ├── 订阅: ptz_guidance / ptz_track / ptz_motion / ptz_lens ...
│       ├── 发布: ptz_status / ptz_lens_info / ptz_azimuth_pitch / ptz_device_info
│       └── 视频管道（GStreamer + SHM，模块内部管理，不暴露给 AimRT）
│
├── [其他子系统的模块 - 不属于设备管理子系统]
│   ├── AlinkModule         # ALINK 协议（向 topo 查询拓扑，自己组装上报）
│   └── TimeSyncModule      # 时间同步（C2 ↔ AGX）
│
└── [未来迁移的模块]
    ├── AI 算法模块
    ├── 融合模块
    └── 电子围栏模块
```

### 1.6 消息定义（protobuf）

#### 设备管理消息 - `device_msgs.proto`

```protobuf
syntax = "proto3";
package skyfend.device;

// ===== devm 发布的消息 =====

message DeviceInfo {
  string device_id = 1;          // 唯一标识（通常为 SN 或 IP）
  string device_type = 2;        // "sentry", "ssf100", "ptz_hepu" 等
  string ip = 3;
  uint32 port = 4;
  string sn = 5;
  string firmware_version = 6;
  string sw_version = 7;
  double longitude = 8;          // 经度
  double latitude = 9;           // 纬度
  double altitude = 10;          // 海拔
}

message DeviceOnlineEvent {
  DeviceInfo device = 1;
  uint64 timestamp_ms = 2;
}

message DeviceOfflineEvent {
  string device_id = 1;
  string device_type = 2;
  string reason = 3;             // "heartbeat_timeout", "disconnect", "manual"
  uint64 timestamp_ms = 4;
}

message DeviceStatusUpdate {
  string device_id = 1;
  DeviceInfo device = 2;
  bool online = 3;
  uint64 timestamp_ms = 4;
}

// ===== topo 发布/RPC 的消息 =====

enum DeviceRole {
  ROLE_UNKNOWN = 0;
  ROLE_ROOT = 1;                 // 根节点（主设备）
  ROLE_INTERMEDIATE = 2;         // 中间节点（如 Sentry 下的 Spotter）
  ROLE_LEAF = 3;                 // 叶子节点（子设备）
}

message DeviceTreeNode {
  string device_id = 1;
  string device_type = 2;
  DeviceRole role = 3;
  DeviceInfo info = 4;
  repeated DeviceTreeNode children = 5;
}

message TopologySnapshot {
  DeviceTreeNode root = 1;
  uint64 version = 2;            // 拓扑版本号，每次变更递增
  uint64 timestamp_ms = 3;
  string scenario = 4;           // "sentry_only", "spotter_only", "sentry_spotter"
}

message TopologyChangedEvent {
  TopologySnapshot snapshot = 1;
  string change_type = 2;        // "device_added", "device_removed", "root_changed", "tree_reorganized"
  string affected_device_id = 3;
}

// RPC 请求/响应
message GetTopologyRequest {}
message GetTopologyResponse {
  TopologySnapshot snapshot = 1;
}

message GetDeviceChildrenRequest {
  string parent_device_id = 1;
}
message GetDeviceChildrenResponse {
  repeated DeviceTreeNode children = 1;
}
```

### 1.7 devm 内部设计

```mermaid
stateDiagram-v2
    [*] --> Initialize
    Initialize --> Start: 配置加载完成

    state Initialize {
        [*] --> ReadConfig: 读取端口/超时/重连配置
        ReadConfig --> RegisterChannels: 注册 Publisher
        RegisterChannels --> InitRegistry: 初始化 DeviceRegistry
    }

    state Start {
        [*] --> UdpDiscovery: 启动 UDP 广播监听 1810/1800
        [*] --> HeartbeatMonitor: 启动心跳超时扫描
        [*] --> ConnectionManager: 管理 TCP/UART 连接
    }

    Start --> Running
    Running --> Shutdown: 收到关闭信号
```



```mermaid
flowchart LR
    subgraph UdpDiscoveryService
        udp_recv["收到 UDP 广播"] --> parse["解析设备信息"]
        parse --> is_new{"新设备?"}
        is_new -->|是| add_reg["DeviceRegistry.add()"]
        add_reg --> pub_online["发布 DeviceOnlineEvent"]
        is_new -->|否| update_hb["更新心跳时间戳"]
    end

    subgraph HeartbeatMonitor
        timer["定时扫描"] --> check["检查最后心跳时间"]
        check --> timeout{"超时?"}
        timeout -->|是| remove_reg["DeviceRegistry.remove()"]
        remove_reg --> pub_offline["发布 DeviceOfflineEvent"]
        timeout -->|否| skip["跳过"]
    end
```



**DeviceRegistry 接口**:

- `map<device_id, DeviceInfo>` 在线设备表
- `add(DeviceInfo)` / `remove(device_id)`
- `getAll()` / `getByType(type)` / `getById(id)`

### 1.8 topo 内部设计

#### topo 设备上线处理流程

```mermaid
flowchart TD
    OnlineEvent["收到 DeviceOnlineEvent"] --> Evaluate["RootNodeResolver.evaluate()\n判断是否需切换根节点"]
    Evaluate --> DevType{"设备类型?"}

    DevType -->|Sentry| SetRoot["设为根节点"]
    SetRoot --> HasSpotter{"现有 Spotter\n是根?"}
    HasSpotter -->|是| Demote["Spotter 降级\n为 Sentry 子节点"]
    HasSpotter -->|否| IncVer1["递增拓扑版本号"]
    Demote --> IncVer1

    DevType -->|Spotter| CheckSentry{"Sentry\n在线?"}
    CheckSentry -->|是| MountToSentry["挂载到 Sentry 下"]
    CheckSentry -->|否| SetSpotterRoot["设为根节点"]
    MountToSentry --> IncVer2["递增拓扑版本号"]
    SetSpotterRoot --> IncVer2

    DevType -->|子设备| MountToParent["根据类型挂载到\n对应父节点"]
    MountToParent --> IncVer3["递增拓扑版本号"]

    IncVer1 --> Publish["发布 TopologyChangedEvent"]
    IncVer2 --> Publish
    IncVer3 --> Publish
```

#### topo 设备下线处理流程

```mermaid
flowchart TD
    OfflineEvent["收到 DeviceOfflineEvent"] --> RemoveNode["从树中移除设备节点"]
    RemoveNode --> NodeType{"移除的是?"}

    NodeType -->|根节点| FindNew["RootNodeResolver.evaluate()\n寻找新的根"]
    FindNew --> HasCandidate{"有候选\n根设备?"}
    HasCandidate -->|是| Promote["候选升级为根\n树重组"]
    HasCandidate -->|否| EmptyTree["设备树为空"]

    NodeType -->|中间节点| HandleChildren["处理其子设备\n移除或重挂"]

    NodeType -->|叶子节点| DirectRemove["直接移除"]

    Promote --> IncVer["递增拓扑版本号"]
    EmptyTree --> IncVer
    HandleChildren --> IncVer
    DirectRemove --> IncVer
    IncVer --> PubEvent["发布 TopologyChangedEvent"]
```

#### topo RPC 接口

- `GetTopologySnapshot` → 返回当前完整拓扑快照
- `GetDeviceChildren` → 返回指定设备的子设备列表

### 1.9 devm 与 topo 的交互时序

```mermaid
sequenceDiagram
    participant SubDev as 子设备
    participant devm as DevmModule
    participant topo as TopoModule
    participant upper as 上层模块(ALINK等)

    SubDev->>devm: UDP 广播响应 (Sentry 上线)
    devm->>topo: DeviceOnlineEvent (type=sentry)
    Note over topo: evaluate root<br/>set sentry as root
    topo->>upper: TopologyChangedEvent (root_changed)

    upper->>topo: GetTopologySnapshot RPC
    topo-->>upper: TopologySnapshot 响应

    Note over devm: Sentry 心跳超时...
    devm->>topo: DeviceOfflineEvent (sentry timeout)
    Note over topo: remove sentry<br/>promote spotter to root
    topo->>upper: TopologyChangedEvent (tree_reorganized)

    SubDev->>devm: 和普PTZ 注册上线
    devm->>topo: DeviceOnlineEvent (type=ptz_hepu)
    Note over topo: 挂载到当前根节点下
    topo->>upper: TopologyChangedEvent (device_added)
```



---

## 二、和普 PTZ 迁移到 AimRT 方案

### 2.1 难度评估：中等偏低


| 维度     | 难度  | 说明                                                 |
| ------ | --- | -------------------------------------------------- |
| SDK 封装 | 低   | `ptzHepuSDK` 已有良好抽象，`HepuPtz` / `HepuPtzCtrl` 接口清晰 |
| 控制逻辑迁移 | 中   | 需将 ROS2 订阅/发布改为 AimRT Channel，逻辑本身不变               |
| 视频管道   | 低   | GStreamer 管道保持独立，仅控制逻辑入 AimRT                      |
| 消息格式转换 | 中   | `skyfend_interfaces::msg::*` → protobuf            |
| 配置迁移   | 低   | YAML → AimRT YAML 模块配置                             |
| 共享内存   | 低   | `ShmTransferFrame` 保持独立，不走 AimRT Channel           |


**预估工作量**：2-3 周（1 人），含测试调试。主要工作量在消息格式转换和 Channel 对接。

### 2.2 组件结构设计

按照 `GITLAB_REPOSITORY_PLAN.md` 的组件模板：

```
component-driver-ptz-hepu/
├── CMakeLists.txt
├── README.md
├── src/
│   ├── CMakeLists.txt
│   └── ptz_hepu/
│       ├── ptz_hepu_module.h          # AimRT Module 主类
│       ├── ptz_hepu_module.cc
│       ├── ptz_hepu_device.h          # 设备控制（原 PtzDeviceHepu 重构）
│       ├── ptz_hepu_device.cc
│       ├── ptz_hepu_video_pipeline.h  # 视频管道管理（GStreamer + SHM）
│       ├── ptz_hepu_video_pipeline.cc
│       └── ptz_hepu_converter.h       # Hepu SDK 状态 ↔ protobuf 转换工具
├── pkg/
│   └── ptz_hepu_pkg/
│       ├── CMakeLists.txt
│       └── pkg_main.cc               # AIMRT_PKG_MAIN 注册
├── proto/
│   ├── ptz_control.proto             # PTZ 控制消息定义
│   └── ptz_status.proto              # PTZ 状态消息定义
├── config/
│   └── default.yaml                  # 默认模块配置
├── tests/
└── docs/
```

### 2.3 PTZ protobuf 消息定义

```protobuf
// ptz_control.proto - 对应现有 skyfend_interfaces::msg 的 PTZ 控制消息
syntax = "proto3";
package skyfend.ptz;

message PtzGuidanceCmd {
  uint32 cmd_type = 1;           // 引导类型（对应 CmdEnum）
  float azimuth = 2;             // 方位角
  float pitch = 3;               // 俯仰角
  float distance = 4;            // 距离
}

message PtzTrackCmd {
  uint32 camera_index = 1;       // 0=可见光, 1=红外
  int32 x = 2;                   // 像素坐标 x
  int32 y = 3;                   // 像素坐标 y
  int32 width = 4;               // 跟踪框宽
  int32 height = 5;              // 跟踪框高
  uint32 track_mode = 6;         // 跟踪模式
}

message PtzMotionCmd {
  uint32 action = 1;             // 动作类型
  int32 pan_speed = 2;           // 水平速度
  int32 tilt_speed = 3;          // 垂直速度
}

message PtzLensCmd {
  uint32 camera_index = 1;
  uint32 action = 2;             // zoom_in/zoom_out/focus_near/focus_far/...
  int32 speed = 3;
}

message PtzManualLockTargetCmd {
  uint32 camera_index = 1;
  int32 x = 2;
  int32 y = 3;
}

message PtzSwitchTrackingSourceCmd {
  uint32 source = 1;             // 0=可见光, 1=红外
}

message AiTargetInfo {
  uint32 camera_index = 1;
  repeated AiTarget targets = 2;
}

message AiTarget {
  uint32 id = 1;
  float x = 2;
  float y = 3;
  float width = 4;
  float height = 5;
  float confidence = 6;
  uint32 class_id = 7;
}

// ptz_status.proto - PTZ 状态上报消息
message PtzStatus {
  bool connected = 1;
  bool tracking = 2;
  uint32 tracking_source = 3;
  float pan_position = 4;
  float tilt_position = 5;
  uint64 timestamp_ms = 6;
}

message PtzLensInfo {
  uint32 camera_index = 1;
  float zoom_ratio = 2;
  float focus_value = 3;
  uint32 zoom_position = 4;
}

message PtzAzimuthPitchInfo {
  float azimuth = 1;             // 方位角 (度)
  float pitch = 2;               // 俯仰角 (度)
  uint64 timestamp_ms = 3;
}

message PtzDeviceInfo {
  string device_id = 1;
  string model = 2;
  string firmware_version = 3;
  string sn = 4;
  bool online = 5;
}
```

### 2.4 核心代码映射

#### 当前 ROS2 架构 → AimRT 架构


| 当前（ROS2）                                      | 迁移后（AimRT）                      | 变化                  |
| --------------------------------------------- | ------------------------------- | ------------------- |
| `RosService`（单例，ROS2 节点）                      | `PtzHepuModule`（AimRT Module）   | 生命周期由 AimRT 管理，去掉单例 |
| `rclcpp::Subscription<PtzGuidanceCmd>`        | `aimrt::channel::SubscriberRef` | 订阅控制命令              |
| `rclcpp::Publisher<PtzStatus>`                | `aimrt::channel::PublisherRef`  | 发布设备状态              |
| `skyfend_interfaces::msg::*` (8个)             | protobuf 消息 (上述定义)              | AimRT 原生支持          |
| `PtzDeviceBase` + `PtzDeviceHepu`             | `PtzHepuDevice`（内部类）            | 去掉工厂模式（单设备类型单模块）    |
| `PtzDevicesCfg` (YAML读取)                      | AimRT `GetConfigFilePath()`     | 配置统一由 AimRT 管理      |
| 共享内存 `ShmTransferFrame`                       | 保持独立使用                          | 视频帧不走 AimRT Channel |
| GStreamer `GstSourceDecode` / `GstRtspClient` | `PtzHepuVideoPipeline` 内部管理     | 不暴露给 AimRT          |


#### PtzHepuModule 类设计

```cpp
class PtzHepuModule : public aimrt::ModuleBase {
 public:
  ModuleInfo Info() const override {
    return ModuleInfo{.name = "PtzHepuModule"};
  }

  bool Initialize(aimrt::CoreRef core) override;
  bool Start() override;
  void Shutdown() override;

 private:
  aimrt::CoreRef core_;

  // 设备控制（封装 HepuPtz + HepuPtzCtrl）
  std::unique_ptr<PtzHepuDevice> device_;

  // 视频管道（GStreamer + SHM，模块内部管理）
  std::unique_ptr<PtzHepuVideoPipeline> pipeline_;

  // AI 智能分析（UDP 发送检测结果到 PTZ）
  std::unique_ptr<PtzHepuSmart> ai_smart_sender_;

  // === Channel 发布 ===
  aimrt::channel::PublisherRef<PtzStatus> pub_status_;
  aimrt::channel::PublisherRef<PtzLensInfo> pub_lens_;
  aimrt::channel::PublisherRef<PtzAzimuthPitchInfo> pub_azimuth_pitch_;
  aimrt::channel::PublisherRef<PtzDeviceInfo> pub_device_info_;

  // === Channel 订阅 ===
  aimrt::channel::SubscriberRef<PtzGuidanceCmd> sub_guidance_;
  aimrt::channel::SubscriberRef<PtzTrackCmd> sub_track_;
  aimrt::channel::SubscriberRef<PtzMotionCmd> sub_motion_;
  aimrt::channel::SubscriberRef<PtzLensCmd> sub_lens_;
  aimrt::channel::SubscriberRef<PtzManualLockTargetCmd> sub_manual_lock_;
  aimrt::channel::SubscriberRef<PtzSwitchTrackingSourceCmd> sub_switch_track_;
  aimrt::channel::SubscriberRef<AiTargetInfo> sub_visible_ai_;
  aimrt::channel::SubscriberRef<AiTargetInfo> sub_infrared_ai_;
};
```

### 2.5 配置文件设计

```yaml
# ptz_hepu_cfg.yaml
aimrt:
  log:
    core_lvl: INFO
    backends:
      - type: console
  module:
    pkgs:
      - path: ./libptz_hepu_pkg.so
    modules:
      - name: PtzHepuModule
        log_lvl: INFO

PtzHepuModule:
  device:
    ip: "192.168.2.4"
    sn: "DEHEPU-PTZ-001"
    type: "ptz_hepu"              # ptz_hepu / ptz_hepu_cooled
    tcp_port: 39020
    ai_smart_udp_port: 39080
    reconnect_interval_sec: 5
    heartbeat_timeout_ms: 5000
  video:
    visible:
      rtsp_url: "rtsp://admin:Abc.12345@192.168.2.4:554/ch0/stream1"
      resolution: [1920, 1080]
      bitrate_kbps: 4000
      push_udp_port: 5410
    thermal:
      rtsp_url: "rtsp://admin:Abc.12345@192.168.2.4:554/ch1/stream1"
      resolution: [640, 512]
      bitrate_kbps: 2000
      push_udp_port: 5411
  shm:
    visible_raw: "ZOOM_CAM0_RAW"
    thermal_raw: "IR_CAM0_RAW"
    visible_ai: "AI_ZOOM_CAM0"
    thermal_ai: "AI_IR_CAM0"
```

### 2.6 PTZ 视频管道数据流（迁移后保持不变）

```mermaid
flowchart LR
    subgraph hepu_device [和普 PTZ 设备 192.168.2.4]
        vis_stream["可见光 RTSP\nch0/stream1\n1920x1080"]
        ir_stream["红外 RTSP\nch1/stream1\n640x512"]
    end

    subgraph ptz_module [PtzHepuModule 内部]
        decoder_vis["GstSourceDecode\n可见光解码"]
        decoder_ir["GstSourceDecode\n红外解码"]
        shm_vis_raw["SHM: ZOOM_CAM0_RAW\n原始可见光帧"]
        shm_ir_raw["SHM: IR_CAM0_RAW\n原始红外帧"]
        shm_vis_ai["SHM: AI_ZOOM_CAM0\nAI处理后帧"]
        shm_ir_ai["SHM: AI_IR_CAM0\nAI处理后帧"]
        rtsp_vis["GstRtspClient\nUDP:5410 推流"]
        rtsp_ir["GstRtspClient\nUDP:5411 推流"]
    end

    subgraph ai_module [AI 模块]
        ai["AI 推理"]
    end

    vis_stream -->|RTSP| decoder_vis
    ir_stream -->|RTSP| decoder_ir
    decoder_vis --> shm_vis_raw
    decoder_ir --> shm_ir_raw
    shm_vis_raw -->|SHM| ai
    shm_ir_raw -->|SHM| ai
    ai --> shm_vis_ai
    ai --> shm_ir_ai
    shm_vis_ai --> rtsp_vis
    shm_ir_ai --> rtsp_ir
```

### 2.7 迁移步骤（按优先级排序）

1. **定义 protobuf 消息**：将 `skyfend_interfaces::msg::PtzGuidanceCmd` 等 8 个消息类型转为 `ptz_control.proto` + `ptz_status.proto`
2. **创建 PtzHepuModule 骨架**：实现 `Initialize/Start/Shutdown` 生命周期，接入 AimRT 配置和日志
3. **移植设备控制逻辑**：`PtzDeviceHepu` → `PtzHepuDevice`，去掉 ROS2 依赖，保留 `ptzHepuSDK` 调用
4. **接入 AimRT Channel**：替换 ROS2 订阅/发布为 AimRT Channel（protobuf 消息）
5. **移植视频管道**：`startVideoPipeline/stopVideoPipeline` → `PtzHepuVideoPipeline`，逻辑不变，仅改生命周期管理
6. **创建 pkg 注册**：`pkg_main.cc` + `AIMRT_PKG_MAIN(aimrt_module_register_array)`
7. **编写 YAML 配置**：模块配置 + AimRT 运行时配置
8. **集成测试**：在 AGX (192.168.3.104) 上验证全链路

### 2.7 依赖关系

```mermaid
flowchart TD
    PtzHepuPkg["component-driver-ptz-hepu"]

    subgraph aimrt_deps [AimRT Framework]
        module_if["aimrt_module_cpp_interface\nModule 基类"]
        pkg_if["aimrt_pkg_c_interface\nPkg 模式宏"]
    end

    subgraph hepu_deps [和普 SDK]
        hepu_sdk["ptzHepuSDK\n源码"]
        hepu_so["thirdpart/hepuSdk\n闭源 .so aarch64"]
    end

    subgraph sys_deps [系统库]
        gst["GStreamer\n视频管道"]
        opencv["OpenCV\n图像处理"]
        yaml["yaml-cpp\nAimRT 已内置"]
    end

    shm["ShmTransferFrame\n共享内存传输"]

    PtzHepuPkg --> aimrt_deps
    PtzHepuPkg --> hepu_deps
    PtzHepuPkg --> sys_deps
    PtzHepuPkg --> shm
    hepu_sdk --> hepu_so
```



### 2.8 风险点与应对


| 风险             | 影响                                     | 应对策略                           |
| -------------- | -------------------------------------- | ------------------------------ |
| SHM 与 AI 模块兼容  | 若 AI 未迁移到 AimRT，SHM 接口必须保持不变           | ShmTransferFrame 保持独立，不改接口     |
| hepuSdk 闭源 .so | 仅 aarch64，需确保 AimRT 构建系统能链接            | CMake 中 `find_library` 指定路径    |
| GStreamer 线程模型 | GStreamer 有自己的线程池，与 AimRT Executor 需协调 | 视频管道使用独立线程，不托管给 AimRT Executor |
| 视频延迟           | 视频帧走 Channel 序列化会增加延迟                  | 视频帧继续走 SHM 直传，只有控制/状态走 Channel |
| 渐进迁移期兼容        | 部分模块仍在 ROS2，需要通信                       | 使用 AimRT `ros2_plugin` 桥接      |


---

## 三、推荐的消息格式策略

**建议：protobuf + ros2_plugin 桥接（渐进迁移）**

- **新模块**（devm / topo / ptz）内部统一用 protobuf
- **现有 ROS2 节点**（AI 算法等）通过 AimRT 的 `ros2_plugin` 自动桥接
- 模块代码本身不依赖 ROS2，部署更灵活
- 后续 AI 等模块迁移完成后，可去掉 ros2_plugin

---

## 四、整体部署配置示例（所有模块联合运行）

```yaml
# anti_drone_system.yaml - AGX 上完整部署配置
aimrt:
  log:
    core_lvl: INFO
    backends:
      - type: console
  plugin:
    plugins:
      - name: net_plugin
        path: ./libaimrt_net_plugin.so
        options: { ... }
      - name: ros2_plugin                  # 渐进迁移期桥接
        path: ./libaimrt_ros2_plugin.so
  module:
    pkgs:
      - path: ./libdevm_pkg.so             # 设备管理
      - path: ./libtopo_pkg.so             # 拓扑管理
      - path: ./libptz_hepu_pkg.so         # PTZ 驱动
    modules:
      - name: DevmModule
        log_lvl: INFO
      - name: TopoModule
        log_lvl: INFO
      - name: PtzHepuModule
        log_lvl: INFO
  channel:
    backends:
      - type: local                        # 进程内通信
      - type: ros2                         # 桥接到 ROS2（渐进迁移期）

DevmModule:
  discovery:
    listen_ports: [1810, 1800]
    heartbeat_timeout_ms: 5000
    scan_interval_ms: 1000

TopoModule:
  root_priority:
    - "sentry"
    - "sfl200"
    - "sfl210"
    - "srp100"
    - "srp200"
    - "srp210"
    - "srp230"
    - "ssf100"
    - "ssf200"
    - "ssf210"
    - "bph110"

PtzHepuModule:
  device:
    ip: "192.168.2.4"
    sn: "DEHEPU-PTZ-001"
    type: "ptz_hepu"
    tcp_port: 39020
    ai_smart_udp_port: 39080
  video:
    visible:
      rtsp_url: "rtsp://admin:Abc.12345@192.168.2.4:554/ch0/stream1"
      resolution: [1920, 1080]
      bitrate_kbps: 4000
      push_udp_port: 5410
    thermal:
      rtsp_url: "rtsp://admin:Abc.12345@192.168.2.4:554/ch1/stream1"
      resolution: [640, 512]
      bitrate_kbps: 2000
      push_udp_port: 5411
  shm:
    visible_raw: "ZOOM_CAM0_RAW"
    thermal_raw: "IR_CAM0_RAW"
    visible_ai: "AI_ZOOM_CAM0"
    thermal_ai: "AI_IR_CAM0"
```

