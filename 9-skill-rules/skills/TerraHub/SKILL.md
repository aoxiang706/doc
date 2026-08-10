# TerraHub 架构与开发速查

TerraHub（地枢）反无人机系统嵌入式软件架构速查，基于《Jetson AGX Orin 反无系统软件架构设计文档 V4.1》。
覆盖负责的开发任务：PTZ/Radar 设备抽象、视频直播服务、Mediamtx 部署、SysMonit、TimeSync、三方库与日志接口。

## 使用场景

- 开发 `src/02_DevAbsLayer/` 下的 PTZ / Radar Module
- 开发 `src/03_InfraLayer/` 下的 SysMonit / TimeSync / 三方库封装
- 开发 `src/01_SolutionLayer/` 下的视频直播服务
- 编写 `protocols/` 下的 Protobuf 消息定义
- 编写 `deploy/` 下的部署 YAML 配置
- 配置和部署 mediamtx 流媒体服务

---

## 1. 架构全景

### 1.1 五层架构

```
┌─────────────────────────────────────────────────┐
│  01_SolutionLayer  解决方案层                      │
│  Fusion / TargetManager / ThreatAssess /         │
│  TargetAssign / StrikeManager / PtzGuidance /    │
│  NexusGateway / SysCali / GeoEnv / EmEnv /       │
│  LocalDecision / TracerMatrix / WebGateway        │
├─────────────────────────────────────────────────┤
│  02_DevAbsLayer  设备抽象层                        │
│  01_Detector: PTZ(Hepu/Naijie) / Radar / Tracer │
│  02_Striker:  Hunter / Spoofer / Laser / Thunder │
│  03_Support:  PowerBox / IMU / GPS / TempControl │
├─────────────────────────────────────────────────┤
│  03_InfraLayer  基础设施层                         │
│  SysMonit / TimeSync / FaultManager / OTA /      │
│  HealthCheck / DeviceManager / WebGateway /       │
│  skyfendlibs / thirdpartylibs                     │
├─────────────────────────────────────────────────┤
│  AimRT Framework (只读不写)                        │
│  Channel / RPC / Executor / Logger / Plugin       │
├─────────────────────────────────────────────────┤
│  OS + Hardware                                    │
│  Linux / Jetson AGX Orin / mosquitto / mediamtx  │
└─────────────────────────────────────────────────┘
```

**依赖单向性**：上层可依赖下层，下层不能依赖上层。

### 1.2 进程模型

- **aimrt_main**：单进程多 Module，所有业务 Module 运行在同一进程内
- **mosquitto**：MQTT Broker，系统独立进程，`systemctl enable mosquitto`
- **mediamtx**：RTSP/webRTC 流媒体网关，系统独立进程
- **caddy**：Web 入口（TLS/静态文件/反向代理），系统独立进程

### 1.3 通信选型

| 模式 | 占比 | 适用场景 |
|------|------|----------|
| **Channel**（发布/订阅） | ~85% | OODA 数据流、设备状态、设备指令、反馈、系统事件 |
| **RPC**（请求/响应） | ~15% | PowerBox 控制、OTA 指令、参数调整 |

### 1.4 通信协议

| 通信路径 | 协议 |
|----------|------|
| AGX 内部 Module 间 | AimRT Channel（local backend） |
| AGX ↔ 塞防自研设备 | MQTT + Protobuf |
| AGX ↔ 第三方设备（Radar/PTZ/Laser） | ETH + UDP + 厂商私有协议 |
| AGX ↔ Nexus（天盾） | MQTT + Protobuf |
| 视频流 | RTSP（mediamtx）+ GPU 共享内存 |

### 1.5 数据优先级

| 优先级 | 含义 | Executor | MQTT QoS |
|--------|------|----------|----------|
| P-Critical | 必达指令（打击 command） | simple_thread + SCHED_FIFO | QoS 2 |
| P-High | 核心数据（融合目标、威胁评估） | asio_thread（专用池） | QoS 1 |
| P-Normal | 常规数据（设备状态、PTZ 状态） | asio_thread（共享池） | QoS 0 |
| P-Low | 辅助数据（系统监控、日志） | asio_thread（共享池） | QoS 0 |

---

## 2. PTZ Module 开发指南

### 2.1 设备分类

| Module | 厂商 | 通信方式 | 编码格式 |
|--------|------|----------|----------|
| HepuPtzModule | 和普 | ETH + UDP + 厂商私有协议 | H.265 |
| NaijiePtzModule | 耐杰 | ETH + UDP + 厂商私有协议 | H.264 |

Module 名带厂商名，但 **Topic 名统一用编号**：`ptz/01/...`、`ptz/02/...`，上层不感知厂商。

### 2.2 Topic 定义

| Topic | 消息类型 | 频率 | 优先级 | 方向 |
|-------|----------|------|--------|------|
| `ptz/*/ai_targets` | PtzAiTargetList | 5Hz | P-High | 上报 → Fusion |
| `ptz/*/status` | PtzStatus | 1Hz | P-Normal | 上报 → TargetAssign, PtzGuidance |
| `ptz/*/guide_command` | PtzGuideCommand | — | P-High | PtzGuidance → PTZ |
| `ptz/*/track_result` | PtzTrackResult | — | P-High | PTZ → TargetManager |

### 2.3 核心接口

```cpp
// 侦测类设备代理接口
ptz_move(pan, tilt, speed);
zoom_control(zoom_level);
auto_track(target_id);
```

### 2.4 设备状态机

```
OFFLINE → ONLINE → BUSY → FAULT → OFFLINE
```

设备离线/故障时 Module 不退出，只更新状态为 OFFLINE/FAULT。

### 2.5 视频管线（GStreamer）

```
rtspsrc → rtph26Xdepay → h26Xparse → nvv4l2decoder
    → tee ─┬→ appsink (AI 推理, drop=true, max-buffers=2)
            ├→ nvdsosd → nvv4l2h265enc → rtspclientsink (推流到 mediamtx)
            └→ splitmuxsink (录像存储)
```

- 解码输出：NvBufSurface（GPU 显存零拷贝）
- AI 推理跳帧：常规 1:6（5fps），跟踪 1:3（10fps），打击 1:2~1:1
- OSD 叠加：nvdsosd（GPU 加速），叠加检测框/ID/威胁等级/时间戳

### 2.6 AI 子模块

| 项目 | 说明 |
|------|------|
| 模型格式 | `.engine`（TensorRT，从 ONNX 离线转换） |
| 输入 | RGBA 640×640 |
| 输出 | [x, y, w, h, confidence, class_id] |
| 精度 | FP16（Jetson 默认） |

### 2.7 目录结构

```
src/02_DevAbsLayer/01_Detector/Ptz/
├── HepuPtz/
│   ├── sdk/              # 和普 SDK（私有，不放公共库）
│   ├── hepu_ptz_module.h
│   ├── hepu_ptz_module.cc
│   └── CMakeLists.txt
└── NaijiePtz/
    ├── sdk/              # 耐杰 SDK
    ├── naijie_ptz_module.h
    ├── naijie_ptz_module.cc
    └── CMakeLists.txt
```

---

## 3. 中程雷达 Module 开发指南

### 3.1 基本信息

| 项目 | 说明 |
|------|------|
| Module 名 | MiddleRangeRadarModule |
| 研发方 | 第三方 |
| 通信方式 | ETH + 厂商私有协议 |
| 上报 Topic | `radar/*/targets` |
| 上报频率 | 10-20Hz |
| 优先级 | P-High |

### 3.2 核心接口

```cpp
start_tracking();
set_scan_mode(mode);
```

### 3.3 设计原则

- SDK 放在 Module 目录内部（`src/02_DevAbsLayer/01_Detector/Radar/MiddleRangeRadar/sdk/`）
- 厂商私有协议在 Module 内部消化，上层统一收 `radar/*/targets`
- 设备离线时 Module 不退出，更新状态为 OFFLINE
- 多实例支持：通过 Pkg 预注册不同名字（如 `MiddleRangeRadarModule_01`、`_02`）

### 3.4 Proto 消息

```protobuf
// protocols/radar/radar_target.proto
message RadarTarget {
  // 位置、速度、RCS 等
}
message RadarTargetList {
  repeated RadarTarget targets = 1;
}
```

### 3.5 目录结构

```
src/02_DevAbsLayer/01_Detector/Radar/MiddleRangeRadar/
├── sdk/                           # 厂商 SDK
├── middle_range_radar_module.h
├── middle_range_radar_module.cc
└── CMakeLists.txt
```

---

## 4. 视频直播服务 + Mediamtx 部署

### 4.1 mediamtx 部署

| 项目 | 说明 |
|------|------|
| 部署方式 | 系统独立进程 |
| CPU 核绑定 | 核 10-11（与 mosquitto/caddy 共享） |
| RTSP 端口 | 8554 |
| webRTC 端口 | 8889 |
| HLS 端口 | 8888 |

### 4.2 流路径命名

| 流类型 | 路径示例 | 内容 | 消费者 |
|--------|----------|------|--------|
| 原始流 | `/ptz/01/raw` | 无标注原始画面 | 录像存储 |
| 标注流 | `/ptz/01/annotated` | 叠加检测框/ID/威胁等级 | 天盾/Web/运维 |

### 4.3 AGX 推流方式

GStreamer 管线通过 `rtspclientsink` 推送到 mediamtx：

```
... → nvv4l2h265enc → rtspclientsink location=rtsp://localhost:8554/ptz/01/annotated
```

### 4.4 带宽估算

| 分辨率 | 帧率 | 编码 | 典型码率 |
|--------|------|------|----------|
| 1920x1080 | 30fps | H.265 | 4 Mbps |
| 1920x1080 | 30fps | H.264 | 6 Mbps |
| 704x576 | 15fps | H.265 | 1 Mbps |

### 4.5 多路调度与动态降级

| 优先级 | 类型 | 帧率 | 降级策略 |
|--------|------|------|----------|
| P-High | 打击引导路 | 30~60fps | 不降级 |
| P-High | AI 推理路 | 30fps 解码 / 5~10fps 推理 | 仅降推理帧率 |
| P-Normal | 态势监控路 | 15fps | 降帧→降分辨率→暂停 |
| P-Low | 天盾远程路 | 15fps | 跨公网主动限码率 2Mbps |

动态降级触发：GPU >85% → AI 降至 5fps；CPU 核 6-7 >90% → 子码流暂停。

### 4.6 视频访问场景

| 场景 | 拉流方式 | 延迟 |
|------|----------|------|
| 天盾（局域网） | RTSP 直连 | <100ms |
| AGX 门户（局域网） | webRTC | <200ms |
| 远程运维 | Tailscale + webRTC | 200~500ms |

---

## 5. 基础设施层

### 5.1 SysMonitModule

| 项目 | 说明 |
|------|------|
| 职责 | CPU/内存/GPU/温度/磁盘监控 |
| 上报 Topic | `system/health` |
| 优先级 | P-Low |
| 消费者 | NexusGateway |

### 5.2 TimeSyncModule

| 项目 | 说明 |
|------|------|
| 职责 | NTP 多设备时间对齐 |
| 机制 | 基于 NTP 协议 |

### 5.3 三方库与自研库管理

```
src/03_InfraLayer/
├── skyfendlibs/         # 塞防自研公共库
│   ├── gstNvDeeps/      # 视频处理封装
│   ├── shm_transfer_frame/  # 共享内存传帧
│   └── geo_utils/       # 地理坐标工具
├── thirdpartylibs/      # 第三方库
│   ├── gstreamer/
│   ├── NvidiaVideoSdk/
│   ├── mediamtx/
│   ├── sqlite/
│   ├── xxhash/
│   └── mongoose/        # WebGateway HTTP/WS 组件
```

### 5.4 日志规范

统一使用 **AimRT Logger 接口**，不再使用 appLog / zlog 等自研或第三方日志库。

```cpp
// 通过 CoreRef 获取 Logger
auto logger = core.GetLogger();
AIMRT_INFO(logger, "Device {} online, IP: {}", device_id, ip);
```

---

## 6. 目录结构约定

```
TerraHub/
├── src/
│   ├── 01_SolutionLayer/        # 解决方案层
│   ├── 02_DevAbsLayer/          # 设备抽象层
│   │   ├── 01_Detector/         # 侦测类
│   │   │   ├── Ptz/HepuPtz/
│   │   │   ├── Ptz/NaijiePtz/
│   │   │   ├── Radar/MiddleRangeRadar/
│   │   │   └── Tracer/
│   │   ├── 02_Striker/          # 打击类
│   │   └── 03_Support/          # 辅助类
│   └── 03_InfraLayer/           # 基础设施层
│       ├── skyfendlibs/
│       ├── thirdpartylibs/
│       ├── SysMonit/
│       ├── TimeSync/
│       └── ...
├── protocols/                   # Protobuf 消息定义
│   ├── common/
│   ├── radar/
│   ├── ptz/
│   ├── fusion/
│   ├── strike/
│   └── system/
├── pkgs/                        # Pkg 打包
│   ├── device_pkg/
│   ├── solution_pkg/
│   └── infra_pkg/
├── deploy/                      # 部署 YAML
│   ├── spotter_pro.yaml
│   ├── sentry.yaml
│   └── topic_dictionary.yaml
├── web/                         # Caddy 静态资源
├── AimrtFramework/              # AimRT 框架（只读不写）
└── CMakeLists.txt
```

---

## 7. 快速参考

### CPU 核分配（AGX Orin 12 核）

| 核 | 用途 | 优先级 |
|----|------|--------|
| 0-1 | 融合/决策算法 | P-Critical |
| 2-3 | AI 推理 | P-High |
| 4-5 | 设备驱动/通信 | P-Normal |
| 6-7 | 视频解码调度 | P-Normal |
| 8-9 | AimRT 框架 | P-High |
| 10-11 | 系统服务（mosquitto/mediamtx/caddy） | P-Normal |

### IP 网段规划

| 范围 | 用途 | 分配 |
|------|------|------|
| .1~.9 | 网络基础设施（路由器/交换机） | 静态 |
| .10~.19 | AGX / 本地 Nexus | 静态 |
| .20~.199 | 反无设备 + 运维 PC | DHCP |
| .200~.254 | 预留 | — |

网段：**192.168.100.x/24**

### MQTT 设备组网

- 设备上线：发布 `device/{type}/{id}/online`（retained=true）
- 设备掉线：MQTT 遗嘱消息自动发布 `device/{type}/{id}/offline`
- AGX 订阅：`device/+/+/online`（通配符）
- Broker 地址：`192.168.100.10:1883`（AGX #1）
