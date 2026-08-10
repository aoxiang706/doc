---
name: TerraHub Skills and Rules
overview: 基于《Jetson AGX Orin 反无系统软件架构设计文档 V4.1》，为袁伟健负责的开发任务创建 TerraHub 相关的 Cursor skills 和 rules，帮助后续开发过程中快速对齐架构规范和技术方案。
todos:
  - id: create-skill-dir
    content: 创建 /home/skyfend/.cursor/skills/TerraHub/ 目录并编写 SKILL.md
    status: completed
  - id: create-rule-arch
    content: 创建 terrahub-architecture.mdc — 架构原则规约
    status: completed
  - id: create-rule-naming
    content: 创建 terrahub-naming.mdc — 命名规范
    status: completed
  - id: create-rule-module
    content: 创建 terrahub-module-dev.mdc — Module 开发规范
    status: completed
isProject: false
---

# TerraHub Skills and Rules 创建计划

## 背景

基于架构文档 V4.1 和分工表，袁伟健负责以下 7 项任务（按时间排序）：

- **Infra 三方库+自研库+日志接口包装** (P0, 4/7-4/9)
- **DeviceAbs PTZ** (P0, 4/10-4/13)
- **DeviceAbs Radar 中程雷达** (P0, 4/13-4/15)
- **SolutionLayer 视频直播服务** (P0, 4/14-4/18)
- **Mediamtx 进程部署** (P0, 4/15)
- **Infra sysmonit** (P1, 4/20-4/21)
- **Infra TimeSync** (P2, 4/22-4/23)

## 一、Skills 创建（`/home/skyfend/.cursor/skills/TerraHub/`）

创建 1 个 TerraHub 综合 skill 目录，包含 1 个 SKILL.md，覆盖所有与袁伟健任务相关的架构知识。

### SKILL.md 内容要点

**1. 架构全景速查**

- 五层架构（SolutionLayer / DevAbsLayer / InfraLayer / AimRT Framework / OS+HW）
- 进程模型：单进程多 Module（aimrt_main）+ 系统独立进程（mosquitto/mediamtx/caddy）
- OODA 数据流（Observe→Orient→Decide→Act→反馈）
- 通信选型：Channel ~85%（发布/订阅）、RPC ~15%（请求/响应）

**2. PTZ Module 开发指南**（DeviceAbs PTZ）

- 设备分类：HepuPtzModule / NaijiePtzModule，Topic 名用编号 `ptz/01/...`
- 接入方式：ETH + UDP + 厂商私有协议
- 核心接口：`ptz_move()`, `zoom_control()`, `auto_track()`
- 上报 Topic：`ptz/*/ai_targets`(5Hz), `ptz/*/status`(1Hz)
- 指令 Topic：`ptz/*/guide_command`
- AI 子模块：GStreamer 解码 → appsink → TensorRT 推理 → OSD 叠加
- 视频管线：RTSP 拉流 → nvv4l2decoder → tee → (AI/OSD推流/录像)
- 设备状态机：OFFLINE → ONLINE → BUSY → FAULT → OFFLINE

**3. 中程雷达 Module 开发指南**（DeviceAbs Radar）

- Module 名：MiddleRangeRadarModule
- 接入方式：ETH + 厂商私有协议（第三方研发）
- 上报 Topic：`radar/*/targets`(10-20Hz, P-High)
- 核心接口：`start_tracking()`, `set_scan_mode()`
- SDK 放在 Module 目录内，不放公共库

**4. 视频直播服务 + Mediamtx 部署指南**（SolutionLayer + 3.2）

- mediamtx 独立进程，绑定核 10-11
- 协议输出：RTSP(8554), webRTC(8889), HLS(8888)
- 流路径命名：`/ptz/01/raw`, `/ptz/01/annotated`
- AGX 推流方式：GStreamer `rtspclientsink` → mediamtx
- 带宽估算：1080p@30fps H.265 ≈ 4Mbps
- 多路调度策略和动态降级

**5. 基础设施层指南**（Infra：SysMonit / TimeSync / 三方库）

- SysMonitModule：CPU/内存/GPU/温度/磁盘监控，上报 `system/health`(P-Low)
- TimeSyncModule：NTP 多设备时间对齐
- 三方库管理：`src/03_InfraLayer/thirdpartylibs/` + `skyfendlibs/`
- 日志：统一使用 AimRT Logger 接口

**6. 目录结构约定**

- `src/01_SolutionLayer/` — 解决方案层
- `src/02_DevAbsLayer/01_Detector/Ptz/`, `Radar/MiddleRangeRadar/` — 设备抽象层
- `src/03_InfraLayer/` — 基础设施层
- `protocols/` — Protobuf 消息定义
- `deploy/` — 部署 YAML 配置

## 二、Rules 创建（`/home/skyfend/.cursor/rules/`）

### Rule 1: `terrahub-architecture.mdc`

**触发范围**: `src/`**, `protocols/`**, `deploy/**`, `pkgs/**`

核心规约（源自第二十七章）：

- 所有设备网口接入，禁止串口/SPI/I2C 直连
- 每个 Topic 唯一发布者，Topic 名用编号不用品牌
- 设备私有 SDK 跟 Module 走，不放公共库
- Module 不直接调用 AimRT 三方库，面向 CoreRef 接口编程
- Module 是设备代理，设备离线时 Module 不退出
- 一个 YAML = 一个产品
- AimRT 框架代码仓只读不写
- 依赖单向性：下层不能依赖上层
- 管理面走 Web，业务面走 MQTT
- 高危指令仅走 MQTT 业务 Topic 既定链路

### Rule 2: `terrahub-naming.mdc`

**触发范围**: `src/`**, `protocols/`**

命名规范（源自 27.2 + 16.1）：

- Module 类名：驼峰 + Module 后缀（如 `FusionModule`、`HepuPtzModule`）
- Topic 名：小写/斜杠/编号（如 `radar/01/targets`）
- Proto package：点分隔（如 `skyfend.proto`）
- Proto message：驼峰（如 `RadarTargetList`）
- 配置文件：小写下划线（如 `spotter_pro.yaml`）
- 数据优先级：P-Critical / P-High / P-Normal / P-Low

### Rule 3: `terrahub-module-dev.mdc`

**触发范围**: `src/01_SolutionLayer/`**, `src/02_DevAbsLayer/`**, `src/03_InfraLayer/**`

Module 开发规范：

- Module 生命周期：`Info()` → `Initialize(CoreRef)` → `Start()` → `Shutdown()`
- Pkg 注册：一个 .so 可注册多个命名 Module 实例
- Executor 线程隔离：每个 Module 可绑不同 Executor
- Channel（发布/订阅）vs RPC（请求/响应）选型
- MQTT + Protobuf 统一协议（塞防自研设备）
- 厂商私有协议在 Module 内部消化（第三方设备）
- 目录结构：每个 Module 包含 `module_name.h`, `module_name.cc`, `CMakeLists.txt`, 可选 `sdk/`

