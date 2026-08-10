---
name: Mediamtx 流媒体服务器部署
overview: 将 mediamtx 流媒体服务器从 ptz100_agx/thirdpart/mediamtx 原样迁移到 TerraHub/deploy/mediamtx/，保持现有配置和启动方式不变。
todos:
  - id: copy-mediamtx-files
    content: 复制 mediamtx 二进制 + mediamtx.yml 到 deploy/mediamtx/
    status: pending
  - id: update-boot-script
    content: 更新启动脚本中的 mediamtx 路径
    status: pending
  - id: verify-deployment
    content: 验证部署：启动服务、推流测试、拉流测试
    status: pending
isProject: false
---

# Mediamtx 流媒体服务器部署方案

## 1. 概述

### 1.1 mediamtx 是什么

[MediaMTX](https://github.com/bluenviron/mediamtx)（原 rtsp-simple-server）是一个零依赖的流媒体服务器，支持 RTSP、RTMP、HLS、WebRTC、SRT 等协议。Go 编写，单二进制文件。

在 TerraHub 系统中，mediamtx 作为 **视频流网关**，接收 AGX 各路 GStreamer 管线通过 UDP+RTP 推送的 H264 视频流，再分发给消费者——天盾经 Tailscale VPN 直接 RTSP 拉流，PC 浏览器通过 WebRTC/HLS 直接拉流（视频流不经 WebGateway/NexusGateway）。

### 1.2 在系统中的位置

```
GStreamer 管线                                消费者
┌────────────────────┐                       ┌──────────────────┐
│ PTZ GstRtspClient  │──RTP/UDP──┐           │ 天盾 Tailscale   │
│ Laser GstRtspClient│──RTP/UDP──┤  mediamtx │ Web webRTC       │
└────────────────────┘           └──►:9554 ──┤ VLC/ffplay 调试  │
                                    :8889   │ HLS 浏览器播放    │
                                    :8888   └──────────────────┘
```

### 1.3 与 AimRT 及外部系统的关系

- mediamtx 是 **独立系统进程**，不在 AimRT 进程内
- **LiveStreamApp** 通过 GStreamer 管线推流到 mediamtx（UDP RTP），LiveStreamApp 负责视频全链路（拉流解码→SHM→编码→推流），PtzModule 不参与视频流
- SysMonitModule 通过端口探测（9554）监控其存活状态
- mediamtx 与 AimRT 之间 **无直接通信**，纯旁路服务

**对外交互路径**：


| 消费者                      | 交互路径                                       | 协议               |
| ------------------------ | ------------------------------------------ | ---------------- |
| 天盾（远程）                   | 天盾浏览器 → Tailscale VPN → AGX MediaMTX :9554 | RTSP 拉流          |
| PC 浏览器（本地）               | 浏览器 → AGX MediaMTX :8889                   | WebRTC (WHEP) 拉流 |
| PC 浏览器（兼容）               | 浏览器 → AGX MediaMTX :8888                   | HLS 拉流           |
| LiveStreamApp → MediaMTX | GstRtspClient → UDP RTP → :5400-5420       | 推流入口（仅内部）        |


> **注意**：天盾和 PC 浏览器的**视频流**直接从 MediaMTX 拉取，不经过 WebGateway/NexusGateway。Gateway 只负责**控制面和状态面**（非视频数据）。

---

## 2. 现有部署方式（ptz100_agx）

### 2.1 启动方式

```bash
# config/boot/auto_boot_app.sh 第 106 行
nohup ${MEDIAMCTX_SCRIPT_PATH}/mediamtx ${MEDIAMCTX_SCRIPT_PATH}/mediamtx.yml &
```

- 二进制和配置放在 `thirdpart/mediamtx/` 目录
- `nohup &` 后台启动
- sysmonit 通过端口探测（9554）检测存活

### 2.2 现有 mediamtx.yml 关键配置


| 配置项               | 当前值                   | 说明                 |
| ----------------- | --------------------- | ------------------ |
| logLevel          | info                  | 日志级别               |
| RTSP 端口           | **9554**（非默认 8554）    | 避免与系统其他服务冲突        |
| RTMP 端口           | 1935                  | 默认，已开启             |
| HLS 端口            | 8888                  | 默认，Low-Latency HLS |
| webRTC 端口         | 8889                  | 默认                 |
| SRT 端口            | 8890                  | 默认                 |
| rtspTransports    | [udp, multicast, tcp] | 三种传输方式均开启          |
| udpReadBufferSize | 1048576 (1MB)         | 防高码率瞬间丢包           |
| hlsVariant        | lowLatency            | 低延迟 HLS            |
| overridePublisher | true                  | 允许推流端断线重连后覆盖       |
| api               | false                 | Control API 未开启    |


### 2.3 现有流路径

```yaml
paths:
  test/ch0:
    source: udp+rtp://127.0.0.1:5420

  laser/zoom/ch0:
    source: udp+rtp://127.0.0.1:5400
  laser/zoom/ch1:
    source: udp+rtp://127.0.0.1:5401

  laser/ir/ch0:
    source: udp+rtp://127.0.0.1:5402

  ptz/zoom/ch0:
    source: udp+rtp://127.0.0.1:5410

  ptz/ir/ch0:
    source: udp+rtp://127.0.0.1:5411
```

所有路径使用 `udp+rtp` 接收 H264 RTP 封装视频流，`sourceOnDemand: no`（常驻接收）。

---

## 3. TerraHub 迁移方案

### 3.1 迁移原则

**只搬迁，不改造**。现有配置已在生产环境验证过，保持原样迁移：

- 不新增 systemd 服务（现有 `nohup &` 方式够用）
- 不新增 install.sh（由启动脚本统一管理）
- 不关闭 RTMP/SRT（原有配置已开启，不删除避免影响兼容性）
- 不去掉 multicast（天盾拉流等场景可能用到）

### 3.2 目标目录结构

```
TerraHub/deploy/mediamtx/
├── mediamtx                 # 二进制（aarch64，从现有 thirdpart/ 复制）
└── mediamtx.yml             # 配置文件（从现有 thirdpart/ 复制，仅改必要项）
```

### 3.3 mediamtx.yml 迁移变更

与 `ptz100_agx/thirdpart/mediamtx/mediamtx.yml` 相比，**仅做以下最小变更**：


| 变更项 | 原值  | 新值  | 原因        |
| --- | --- | --- | --------- |
| 无   | —   | —   | 原样复制，不做变更 |


> 如果后续有需要调整的配置，在此表格追加。当前阶段 **原样复制**。

### 3.4 启动方式

沿用现有 `nohup &` 方式，在 TerraHub 启动脚本中加入：

```bash
MEDIAMTX_PATH="$(dirname $0)/../../deploy/mediamtx"
nohup ${MEDIAMTX_PATH}/mediamtx ${MEDIAMTX_PATH}/mediamtx.yml &
```

---

## 4. 推流方式

### 4.1 统一使用 UDP+RTP

所有视频流均通过 **UDP+RTP** 方式推送到 mediamtx（低延迟、无握手开销）：

```
GStreamer 管线：
... → nvv4l2h264enc → rtph264pay → udpsink host=127.0.0.1 port=<端口>
```

mediamtx 侧配置对应路径的 `source: udp+rtp://127.0.0.1:<端口>`。

### 4.2 推流编码

统一使用 **H264** 编码。

### 4.3 推流注意事项

- **必须设置固定帧率**：否则 mediamtx 会严重丢包。mediamtx 需要均匀的 RTP 时间戳来正确重封装，gstRtspServer 直通 RTP 无此影响。
- **UDP 缓冲区**：系统需设置 `net.core.rmem_max >= 1048576`（启动脚本中已有 `sysctl -w net.core.rmem_max=4194304`）

### 4.4 UDP 端口分配表（与现有一致）


| 端口   | 设备  | 流类型       | 编码   |
| ---- | --- | --------- | ---- |
| 5400 | 激光  | 可见光变焦 ch0 | H264 |
| 5401 | 激光  | 可见光变焦 ch1 | H264 |
| 5402 | 激光  | 红外 ch0    | H264 |
| 5410 | PTZ | 可见光变焦 ch0 | H264 |
| 5411 | PTZ | 红外 ch0    | H264 |
| 5420 | 测试  | 测试通道 ch0  | H264 |


---

## 5. 消费者拉流方式


| 消费者           | 协议                   | 拉流地址示例                                    | 说明                  |
| ------------- | -------------------- | ----------------------------------------- | ------------------- |
| 天盾 Nexus      | RTSP via Tailscale   | `rtsp://<tailscale_ip>:9554/ptz/zoom/ch0` | 通过 Tailscale VPN 访问 |
| AGX Web 门户    | WebRTC               | `http://<agx_ip>:8889/ptz/zoom/ch0`       | 浏览器低延迟播放            |
| 远程运维          | WebRTC via Tailscale | 通过 Tailscale VPN 访问 WebRTC 端口             | —                   |
| 浏览器兼容         | HLS (LL-HLS)         | `http://<agx_ip>:8888/ptz/zoom/ch0`       | 延迟较高，兼容性好           |
| VLC/ffplay 调试 | RTSP                 | `rtsp://<agx_ip>:9554/ptz/zoom/ch0`       | 开发调试用               |


---

## 6. SysMonitModule 监控

沿用现有方式——端口探测：

```cpp
bool mediamtx_up = check_port(agx_ip, 9554);
```

---

## 7. 部署验证清单

- mediamtx 二进制在 AGX 上可执行（aarch64）
- `nohup mediamtx mediamtx.yml &` 正常启动
- 端口监听正常：`ss -tlnp | grep -E '9554|8889|8888'`
- UDP+RTP 推流测试：`gst-launch-1.0 videotestsrc ! x264enc ! rtph264pay ! udpsink host=127.0.0.1 port=5420`
- RTSP 拉流测试：`ffplay rtsp://localhost:9554/test/ch0`
- WebRTC 拉流测试：浏览器访问 `http://<agx_ip>:8889/ptz/zoom/ch0`

---

## 8. 注意事项

- **RTSP 端口 9554**：非默认端口（默认 8554），与 ptz100_agx 保持一致
- **固定帧率推流**：GStreamer 向 mediamtx 推流必须设置固定帧率
- **UDP 缓冲区**：启动脚本需在 mediamtx 启动前执行 `sysctl -w net.core.rmem_max=4194304`

