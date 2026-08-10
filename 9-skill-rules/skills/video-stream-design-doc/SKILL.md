---
name: video-stream-design-doc
description: Maintains and extends the PTZ100 video stream design document (e.g. docs/video-stream-design.md). Use when editing that document, adding or updating device descriptions, GStreamer pipeline diagrams, Mermaid flowcharts, or device comparison tables. Ensures consistent terminology (耐杰/和普/激光 PTZ, ptz100_ros/ptz_service/laser_service), correct Mermaid syntax for special characters, and scope limited to video stream processing (no ROS2 control topics or boot sequence).
---

# 视频流设计文档维护

## 何时使用

- 用户编辑或扩展 `docs/video-stream-design.md`（或同类视频流设计文档）
- 用户要求更新设备说明、数据流图、GStreamer 管道、设备对比表
- 用户询问文档中某章节是否与「视频流处理」相关（用于判断是否保留/删除）

## 文档范围

- **包含**：拉流、解码、SHM 传图、AI 处理、编码推流、MediaMTX、设备配置、三类设备对比、现状与可选优化、端口与文件索引
- **不包含**：ROS2 控制 Topic、启动流程/启动顺序（与视频流处理无直接关系，可删）

## 三类设备约定

| 设备 | ROS2 节点 | 代码位置 | 视频框架 |
|------|-----------|----------|----------|
| 耐杰 PTZ | `ptz100_ros` | `src/app/ptz/ptz_app.cpp`（拉流）、`src/app/alg_app/alg_app.cpp`（推流） | GStreamer（**已从 FFmpeg 切换**） |
| 和普 PTZ | `ptz_service` | `ros_ws/src/ptz_service/` | GStreamer |
| 激光 PTZ | `laser_service` | `ros_ws/src/laser_service/` | GStreamer |

- **耐杰**：描述中必须写「已从 FFmpeg 切换到 GStreamer」，不可只写「使用 GStreamer」。可见光分辨率 1920x1080，红外 640x512。推流端口 5410/5411。
- **和普**：可见光 1920x1080，红外 640x512；推流 5410/5411。
- **激光**：三路（粗跟踪/精跟踪/红外），512x512；推流 5400/5401/5402。

## Mermaid 图约定

- **特殊字符**：含 `:`, `@`, `//`, `*` 的节点或连线文字用**双引号**包起来，例如 `|"rtsp://admin:***@ip:554"|`、`MTX["MediaMTX<br/>RTSP :9554"]`，否则易解析报错。
- **布局**：优先 `flowchart LR` 横向、subgraph 左右排布，减少纵向占用。
- **节点文字**：可适当精简（如「GstRtspClient x2」「MediaMTX」），避免过长导致图过大。

## 文档结构（可作目录参考）

1. 概述（背景、模块目标）
2. 系统架构（整体数据流、设备工厂模式）
3. 设备详细说明（耐杰 / 和普 / 激光，每类含属性表 + 数据流图）
4. 视频框架演进（FFmpeg → GStreamer，当前状态图含「已迁移」箭头）
5. GStreamer 组件串联详解（端到端流程、Element 详解、Jetson vs x86、管道生命周期）
6. MediaMTX
7. 共享内存传输
8. 设备配置管理
9. 三类设备对比（表格）
10. 现状说明与可选优化（耐杰两种方案：保持现状 / 迁入 ptz_service）
11. 附录（端口、关键源文件索引、播放地址速查）

## 关键术语与路径

- **组件**：GstSourceDecode、GstRtspClient、ShmTransferFrame、MediaMTX
- **SHM 名称**：SHM_TRANSFER_ZOOM_CAMERA0、SHM_TRANSFER_INFRARED_CAMERA0、SHM_TRANSFER_AI_RESULT_*
- **代码**：`public/gstNvDeeps/`（GStreamer）、`src/app/ptz/ffmpeg/`（FFmpeg 已弃用）、`thirdpart/gstreamer-1.0/`、`thirdpart/mediamtx/mediamtx.yml`

## 增删章节时

- 新增章节若与「视频流处理」无关（如 ROS2 控制、启动流程），建议不写或标注为可选/运维文档。
- 删除章节后记得顺延后续章节编号（如「十一」→「十」）。
