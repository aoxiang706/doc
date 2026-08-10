---
name: GStreamer 视频实时性测试方案
overview: 基于纯 GStreamer 命令，对 SSF-003/005/007 三条 PTZ 视频实时性需求提供可量化、可复现的测试步骤；以和普 PTZ 与 mediaMTX 拉流为例，所有命令可直接交给测试同事执行，无需改工程代码。
todos: []
isProject: false
---

# 纯 GStreamer 视频实时性测试方案（和普 PTZ + mediaMTX）

## 测试环境与 URL 约定

**和普 PTZ 原始流（相机源）：**

| 通道 | URL |
|------|-----|
| 可见光 | `rtsp://admin:Abc.12345@192.168.2.4:554/ch0/stream1` |
| 红外   | `rtsp://admin:Abc.12345@192.168.2.4:554/ch1/stream1` |

**C2 拉流 mediaMTX（AGX 板子）：**  
将下面示例中的 `192.168.3.104` 换成当前 AGX 的 eth0 IP。

| 通道 | URL |
|------|-----|
| 可见光 | `rtsp://192.168.3.104:9554/ptz/zoom/ch0` |
| 红外   | `rtsp://192.168.3.104:9554/ptz/ir/ch0` |

**前置条件：** 测试机已安装 GStreamer 1.0（`gst-launch-1.0`、`gst-inspect-1.0` 可用）；测 mediaMTX 时 AGX 上 PTZ 服务与 mediaMTX 已启动且能拉通流。

---

## SSF-003：内部图像数据传输实时性（≤10ms，≥30FPS）

**目标：** 用 GStreamer 模拟「解码→编码」整段路径，得到**参考延迟**（单位 ms）与**帧率**，供与 10ms/30FPS 对比。

**思路：** 从和普 PTZ 原始 RTSP 拉流，经解码→编码→fakesink，用 `identity report-latency=true` 打印流延迟（ns），换算成 ms；用 `identity` 或解码器统计帧率。

**推荐命令（可见光，可按需改 URL 为红外）：**

```bash
# 将 IP/路径改为实际和普相机地址
gst-launch-1.0 -e rtspsrc location="rtsp://admin:Abc.12345@192.168.2.4:554/ch0/stream1" latency=0 ! \
  rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! \
  identity report-latency=true single-segment=true ! \
  x264enc tune=zerolatency speed-preset=ultrafast ! fakesink sync=false 2>&1 | tee /tmp/ssf003.log
```

- **延迟：** 日志中会出现 `latency` 等字样及数值（一般为纳秒）。**换算：** 延迟(ms) = 数值(ns) / 1_000_000。运行约 10–30 秒，取多帧的延迟做**最大值、平均值**，与 10ms 对比。
- **帧率：** 可另开终端用 `gst-launch-1.0` 仅解码到 fakesink，统计一段时间内通过的 buffer 数除以时间得到 FPS，或使用插件（如部分环境的 `nvoverlay`/统计元素）若可用；无则可通过「延迟数值出现频率」粗估是否接近 30fps（约每 33ms 一帧）。

**量化输出建议：** 在测试报告中记录「decode→encode 段」的 **最大延迟(ms)**、**平均延迟(ms)**、**估算 FPS**，并注明「满足/不满足 SSF-003：≤10ms，≥30FPS」。

---

## SSF-005：获取视频流实时性（点击播放→首帧，≤200ms）

**目标：** 测量「开始拉流→收到首帧」的时间（可视为「点击播放到画面出来」的代理），得到**首帧延迟(ms)**。

**思路：** 从 mediaMTX（AGX）拉流，用 `time` 命令 + 管道在收到首帧后立即结束，用 `time` 的 real 时间作为首帧延迟的近似。

**推荐命令（可见光，AGX_IP 改为实际 AGX eth0）：**

```bash
# 首帧延迟：管道在收到首包/首帧后很快退出，real 时间即近似“点击到首帧”
time (timeout 15 gst-launch-1.0 -e rtspsrc location="rtsp://192.168.3.104:9554/ptz/zoom/ch0" latency=0 ! \
  fakesink sync=false 2>&1 | head -1)
```

- 若 `timeout` 不可用，可改为：`time gst-launch-1.0 -e rtspsrc location="rtsp://192.168.3.104:9554/ptz/zoom/ch0" latency=0 ! fakesink sync=false`，运行后**人工在首帧出现时 Ctrl+C**，看 `time` 输出的 **real** 作为该次首帧延迟。
- **建议：** 重复 5–10 次，记录每次 **real(s)**，换算为 ms，报**平均值、P95、最大值**，与 200ms（或内部 1s）对比。

**量化输出建议：** 报告中写「首帧延迟：平均 X ms，P95 Y ms，最大 Z ms」，并给出「满足/不满足 SSF-005：≤200ms」及可选「1s 内出画比例」。

---

## SSF-007：域控给 C2 的视频流实时性（≤500ms，≥30FPS）

**目标：** 从 C2 侧（或任意拉流端）用 GStreamer 拉 mediaMTX 流，得到**端到端流延迟(ms)** 与**帧率**，供与 500ms/30FPS 对比。

**思路：** 用 `rtspsrc latency=0` 拉 mediaMTX，经 `identity report-latency=true` 打印每条流的延迟（ns），换算成 ms；同一管道内可观察通过帧率。

**推荐命令（可见光，AGX_IP 改为实际 AGX eth0）：**

```bash
gst-launch-1.0 -e rtspsrc location="rtsp://192.168.3.104:9554/ptz/zoom/ch0" latency=0 ! \
  identity report-latency=true single-segment=true ! fakesink sync=false 2>&1 | tee /tmp/ssf007.log
```

- **延迟：** 日志中的 latency 数值为纳秒，**延迟(ms) = 数值 / 1_000_000**。运行 10–30 秒，取多帧的延迟算**最大、平均**，与 500ms 对比。
- **帧率：** 通过日志中 latency 打印频率或 buffer 数量/时间估算 FPS，与 30FPS 对比。

**红外通道：** 将 URL 改为 `rtsp://192.168.3.104:9554/ptz/ir/ch0`，其余同上。

**量化输出建议：** 报告中写「域控→C2 流延迟：最大 X ms，平均 Y ms」「估算 FPS：Z」，并给出「满足/不满足 SSF-007：≤500ms，≥30FPS」。

---

## 交付物与使用说明（给测试同事）

1. **一份测试说明文档**（可由本方案整理而成），包含：
   - 上述三组命令及 URL 替换说明（和普 PTZ 原始 URL、mediaMTX 的 AGX IP）；
   - 如何从日志/`time` 输出中读取「延迟(ns→ms)」「首帧时间(real)」「FPS」；
   - 每个指标与 SSF-003/005/007 的判定关系（≤10ms、≤200ms、≤500ms 及 ≥30FPS）。

2. **可选：** 将三条测试的推荐命令写成三条独立 shell 脚本（如 `ssf003_gst.sh`、`ssf005_gst.sh`、`ssf007_gst.sh`），脚本内用占位符或环境变量（如 `AGX_IP`）区分环境，便于测试同事一键执行与填表。

3. **不依赖本仓库代码修改**：全部使用系统/安装的 GStreamer 与 bash，无需改 ptz100_agx 工程代码。

---

## 小结

| 条目 | 数据源 | 主要 GStreamer 用法 | 量化数据 |
|------|--------|---------------------|----------|
| SSF-003 | 和普 PTZ 原始 RTSP | rtspsrc→decode→identity report-latency→encode→fakesink | 延迟(ns→ms)、估算 FPS |
| SSF-005 | mediaMTX（AGX） | time + rtspsrc→fakesink（首帧即停） | 首帧延迟(real→ms) |
| SSF-007 | mediaMTX（AGX） | rtspsrc→identity report-latency→fakesink | 流延迟(ns→ms)、估算 FPS |

所有测试均以和普 PTZ 为例；若后续更换为其他 PTZ，仅需替换「原始 RTSP URL」和（若适用）mediaMTX 路径，命令结构不变。
