---
name: Video Livestream Service Doc
overview: 为产品设计文档撰写「6.3.5 视频直播服务」章节，参考 DJI Cloud API 直播设计模式，基于当前 GStreamer + MediaMTX 视频链路，面向 AimRT 架构和"本地 Web + 上云（天盾）"双播放场景进行重新设计。
todos:
  - id: func-desc
    content: 撰写 6.3.5.1 功能说明：定位、两种播放场景、能力模型、三类接口定义、底层依赖
    status: completed
  - id: startup-flow
    content: 撰写 6.3.5.2 启动流程：AimRT 生命周期、Pipeline 创建策略、本地/上云链路
    status: completed
  - id: interaction-seq
    content: 撰写 6.3.5.3 交互时序：状态上报、参数设置、参数获取的时序图与说明
    status: completed
isProject: false
---

# 6.3.5 视频直播服务 — 文档撰写方案

## 背景与约束

- **当前现状**：视频链路为 GstSourceDecode → SHM → AI → GstRtspClient → MediaMTX（RTSP 9554 / WebRTC 8889），sysmonit 的 `/api/video` 只做基础状态展示
- **未来架构**：从 ROS2 迁移到 **AimRT**；不再有 C2 上位机
- **两种播放方式**：(1) AGX 本地 Web（WHEP/WebRTC via MediaMTX）；(2) 上云/天盾（RTMP/WHIP 推流到云平台）
- **App 形式**：视频直播作为独立 App（AimRT Module），对外提供三类接口
- **参考**：DJI Cloud API 的 live_capacity / live_start_push / live_set_quality 设计模式

## 文档结构（3 个子章节）

### 6.3.5.1 功能说明

- 直播服务的定位与职责（独立 AimRT App/Module）
- 支持的两种播放场景：本地 Web（WebRTC/WHEP）+ 上云天盾（RTMP/WHIP）
- 直播能力模型（参考 DJI live_capacity）：设备列表、相机列表、码流列表、可切换镜头类型
- 三类核心接口定义：
  - **直播状态上报**（live_status）：当前各路直播状态、码率、分辨率、在线/离线
  - **直播参数设置**（live_set_param）：开始/停止推流、画质切换、镜头切换、目标地址设置
  - **直播参数请求获取**（live_get_param）：查询当前直播配置、设备能力、可选画质列表
- 底层依赖：GstSourceDecode（拉流解码）、GstRtspClient（编码推流）、MediaMTX（协议转换）、ShmTransferFrame（AI 传图）

### 6.3.5.2 启动流程

- AimRT App 注册与生命周期（Initialize → Start → Shutdown）
- 启动时序：加载配置 → 枚举设备/相机 → 构建 live_capacity → 上报初始状态
- 视频 Pipeline 创建：按需创建（收到 live_start_push 后才建 Pipeline）vs 常驻
- 本地 WebRTC 链路：GstRtspClient → MediaMTX → WHEP（被动，客户端拉流触发）
- 上云 RTMP/WHIP 链路：GstRtspClient → 云端 RTMP/WHIP 地址（主动推流，需 live_start_push 触发）

### 6.3.5.3 交互时序

- **直播状态上报时序**：App 周期/事件驱动上报 live_status → 北向接口（HTTP/MQTT）→ 云平台/本地 Web
- **直播参数设置时序**：云/Web → live_start_push / live_stop_push / live_set_quality / live_lens_change → App → 修改 Pipeline 参数
- **直播参数请求获取时序**：云/Web → live_get_capacity / live_get_status → App → 返回设备能力与当前状态

## 关键设计要素

- 接口定义参考 DJI 的 `video_id = {sn}/{camera_index}/{video_index}` 标识每路流
- 画质定义：流畅（960x540 512Kbps）、标清（1280x720 1Mbps）、高清（1280x720 1.5Mbps）、超清（1920x1080 3Mbps）、自适应
- 本地 Web 场景下 live_start_push 不需要（MediaMTX 常驻，WHEP 被动拉流）；上云场景下需要 live_start_push 指定目标 URL
- AimRT Channel 替代 ROS2 Topic / Alink 协议，用于内部通信
- 北向接口（对云/Web）使用 HTTP REST + WebSocket（状态推送）

## 输出文件

- 新建 `doc/视频直播服务设计文档.md`，包含上述 3 个子章节
- 含 Mermaid 图：架构图、启动流程图、3 类交互时序图

