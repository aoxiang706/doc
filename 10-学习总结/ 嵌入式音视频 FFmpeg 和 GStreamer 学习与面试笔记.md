# 嵌入式音视频 / FFmpeg & GStreamer 学习与面试笔记

> **背景：** 嵌入式 / 音视频开发，C/C++，机器人、IPC、视频编解码；侧重工程实战，不堆空文档。  
> **对照仓库：** `ptz100_agx`  
> - 现主路径：**GStreamer**（`public/gstNvDeeps/`）  
> - 遗留路径：**FFmpeg 4.3.1**（`src/app/ptz/ffmpeg/`，`thirdpart/ffmpeg`）  
> - 推流出口常接 **MediaMTX**（`:9554`）或 **GstRtspServer**（如 `:8600`）  
> 整理自工程学习会话，日期参考：2026-08

---

## 目录

- [〇、仓库视频架构速览](#〇仓库视频架构速览)
- [一、FFmpeg 学习重点](#一ffmpeg-学习重点)
- [二、GStreamer 学习重点](#二gstreamer-学习重点)
- [三、FFmpeg vs GStreamer](#三ffmpeg-vs-gstreamer)
- [四、嵌入式音视频通用面试题](#四嵌入式音视频通用面试题)
- [五、学习路线建议](#五学习路线建议)
- [六、gstNvDeeps 四模块实战对照](#六gstnvdeeps-四模块实战对照)
- [七、工程排障与代码修复对照](#七工程排障与代码修复对照)
- [八、资料与命令速查](#八资料与命令速查)

---

## 〇、仓库视频架构速览

```text
相机 RTSP
  → GstSourceDecode（拉流硬解 → BGR → 业务/AI）
  → GstRtspClient（BGR → 硬编 → RTP/UDP）
  → MediaMTX(:9554) 或 GstRtspServer(:8600)
  → 播放器 / C2

旁路：MediaMTX RTSP → GstCloudPusher（免转码 FLV）→ RTMP 上云

遗留：src/app/ptz/ffmpeg/（demux + NvVideoDecoder/NvEncodec + 可选 AvH264 软编）
```

| 要点 | 本仓库 |
|---|---|
| 主路径开关 | `USE_NEW_VIDEO_API` 走 GStreamer |
| 树内 FFmpeg | **4.3.1**（非 5.x） |
| GStreamer 头 | 约 **1.20.x** |
| DeepStream | 可不装；L4T 的 `nvv4l2*` / `nvvidconv` 仍可用 |
| AI | 多进程 SHM + TensorRT，不是 DeepStream 管线内 `nvinfer` |

---

## 一、FFmpeg 学习重点

### 1.1 核心模块（必须吃透）

#### libavformat — 封装 / 解封装

| 概念 / API | 作用 |
|---|---|
| `AVFormatContext` | 输入/输出上下文（文件或网络流） |
| `AVInputFormat` / `AVOutputFormat` | 容器格式 |
| `avformat_open_input` | 打开输入（文件 / RTSP / …） |
| `avformat_find_stream_info` | 探测流信息 |
| `av_read_frame` | 读出一个 `AVPacket` |
| `av_write_frame` / `av_interleaved_write_frame` | 写出 packet |
| `AVStream` | 一条流；含 `time_base`、`codecpar` |
| `AVPacket` | 压缩后的一包数据 |

容器：mp4、rtsp、rtmp、h264/h265 裸流等。

**本仓库映射：** `ffmpegservice.cpp` 中 `avformat_open_input`、`rtsp_transport=tcp`、按 `stream_index` 分路；推流侧 `av_rescale_q` 写 PTS/DTS。

#### libavcodec — 编解码

| 概念 / API | 作用 |
|---|---|
| `AVCodecContext` / `AVCodec` | 编解码器上下文 / 实现 |
| `AVPacket` → `AVFrame` | 解码方向 |
| `AVFrame` → `AVPacket` | 编码方向 |
| **新 API（重点）** | `avcodec_send_packet` / `avcodec_receive_frame`；编码对偶 `send_frame` / `receive_packet` |
| 旧 API | `avcodec_decode_video2` **已废弃**，面试要会对比 |

硬解：NVDEC、V4L2、CUDA 等（平台相关）。

**本仓库映射：**

- 软编：`AvH264.cpp` 使用 `avcodec_send_frame` / receive + `av_rescale_q`
- 主解码路径曾走 **NvVideoDecoder**（硬解），不是纯 `receive_frame` 软解

#### libavutil — 工具 / 内存 / 像素格式

| 概念 | 要点 |
|---|---|
| `AVFrame` | `data[]` / `linesize[]`；YUV420P、NV12 等 |
| 分配 | `av_frame_alloc` / `av_frame_free`；常用 `av_frame_unref` 复用 |
| Packet | `av_packet_unref`（减引用清内容）；`av_packet_free` 释放指针本身 |

#### libswscale — 图像转换 / 缩放

`SwsContext`：YUV ↔ RGB、缩放。  
**本仓库：** 有 `AVFrameToCvMat`（YUV420P→BGR）一类路径；`AvH264` 创建过 Sws，实际编码侧也常用 OpenCV `cvtColor`。

#### libswresample / libavfilter

- **swresample：** 音频重采样（本业务视频主线较少用）
- **avfilter：** 滤镜图（水印、缩放链等）；了解场景即可

---

### 1.2 工程重点（面试最爱问）

#### 内存管理

| 对象 | 何时 unref | 何时 free |
|---|---|---|
| `AVPacket` | 每读完/用完一包 `av_packet_unref` | `av_packet_free` 释放 alloc 出的指针 |
| `AVFrame` | 每帧处理完 `av_frame_unref` 便于复用 | 最终 `av_frame_free` |

**易漏点（本仓库曾出现类似模式）：** `av_packet_alloc` 与错误 free 混用、析构为空、循环里只 alloc 不 unref、把 `malloc(AVPacket)` 当正规 API。

#### 时间戳 PTS / DTS / time_base / av_rescale_q（重中之重）

| 概念 | 含义 |
|---|---|
| PTS | Presentation：显示顺序时间 |
| DTS | Decode：解码顺序时间 |
| time_base | 该流的时间单位（分数）；同一数值在不同流含义不同 |
| `av_rescale_q(a, bq, cq)` | 把时间戳从时间基 `bq` 换到 `cq` |

**B 帧：** 解码顺序 ≠ 显示顺序 → DTS 与 PTS 可能不同；无 B 帧时常 `dts = pts`（本仓库多处如此）。

**本仓库：** `ffmpeg_push_frame` / `AvH264::encode` 里 `av_rescale_q` 写到输出流 `time_base`。

#### 流处理完整流程

```text
解封装 av_read_frame
  → Packet
  → 解码 send_packet / receive_frame → Frame
  → （可选 swscale）
  → 编码 send_frame / receive_packet → Packet
  → 封装 write_frame
```

#### 硬编硬解

| | 软解/软编 | 硬解/硬编 |
|---|---|---|
| 优点 | 格式灵活、易移植 | CPU 占用低、多路扛得住 |
| 缺点 | CPU 高 | 格式/会话数受限、坑多 |
| 何时硬 | — | 嵌入式实时、多路 1080p |

坑：帧拷贝（GPU↔CPU）、仅支持部分格式（如 NV12）、会话上限、驱动/设备节点（Jetson 需 NVDEC）。

#### 网络流 RTSP/RTMP

- `rtsp_transport=tcp`（本仓库有设）vs UDP  
- 超时、interrupt callback、断流重连  
- TCP：穿 NAT/防火墙更稳，延迟可能略高；UDP：低延迟，易丢包  

#### 错误处理

`av_strerror`、负返回值判断、open/read/decode 各阶段失败路径。

#### 命令行

转码、推流、拉流、抽裸 H.264、简单 filter——用于验证，再对照 API。

---

### 1.3 FFmpeg 高频面试题（简答）

**Q1. AVFrame 和 AVPacket 区别？内存如何管理？为何 unref？**  
Packet = 压缩数据；Frame = 解码后裸数据（或编码前像素）。引用计数：用完 unref 归还缓冲池/减引用，避免泄漏；free 释放对象本身。

**Q2. PTS、DTS、time_base、av_rescale_q？B 帧影响？**  
见上表。跨流写容器必须 rescale。B 帧导致 DTS≠PTS。

**Q3. 解码完整流程？新/旧 API？**  
open → find_stream_info → 找视频流 → open codec → read_frame → **send_packet/receive_frame** 循环。旧 `decode_video2` 一次调用耦合，新 API 支持多帧输出与硬件异步。

**Q4. YUV420P 和 NV12？linesize？**  
均为 4:2:0。YUV420P 三平面 Y/U/V；NV12 为 Y + UV 交错。`linesize` 是每行字节跨度（可有对齐 padding），不等于宽度。

**Q5. 硬解 vs 软解？何时硬解？坑？**  
实时多路用硬解。坑：格式、拷贝、设备节点、会话数。

**Q6. RTSP 拉流？TCP/UDP？断流？**  
open_input + 选项；TCP 稳、UDP 快。断流：检测读失败/超时 → 关闭上下文 → 延迟重连。

**Q7. 转码 API 顺序？**  
打开输入 → 找流 → 解码 →（swscale）→ 编码 → 写输出头 → write packet → trailer。

**Q8. 常见内存泄漏？**  
Packet/Frame 未 unref；字典未 free；SwsContext 未 free；错误路径跳过释放；错误使用 `av_free` 代替 `av_packet_unref`。

**Q9. avfilter？**  
滤镜图做缩放、叠加、格式转换等；复杂处理链可用，本仓库业务主路径较少直接用。

**Q10. MP4 vs 裸 H.264？为何 MP4 不能当裸流播？**  
裸流是 annex-B NAL 连续；MP4 是容器（moov/mdat、采样表、时间戳）。播放器按容器解析，不能把 mp4 文件当成纯 elementary stream 直接当 `.h264` 用（需 demux）。

---

## 二、GStreamer 学习重点

GStreamer：插件化管道；嵌入式、IPC、摄像头流水线用得多。

### 2.1 核心概念（必背）

| 概念 | 含义 |
|---|---|
| **Pipeline** | 总容器，统一状态与时钟 |
| **Element** | 元件：source / filter / sink |
| **Pad** | 输入输出端口：src-pad / sink-pad |
| **Caps** | 能力协商：分辨率、帧率、编码格式等 |
| **Buffer** | 承载数据（压缩或裸像素）+ PTS 等；**不是**固定等于 AVPacket |
| **Sample** | Buffer + Caps（appsink 交付） |
| **Bus** | 消息总线：ERROR、EOS、STATE（工程重点） |
| **状态机** | NULL → READY → PAUSED → PLAYING |

**Element 分类举例：**

| 类型 | 例子 |
|---|---|
| source | `v4l2src`、`rtspsrc`、`filesrc`、`appsrc`、`uridecodebin` |
| filter | `videoconvert`、`capsfilter`、`h264parse`、`nvvidconv` |
| sink | `appsink`、`filesink`、`autovideosink`、`udpsink`、`rtmpsink` |

**Pad 链接：**

- **静态 pad：** 创建即有，可 `gst_element_link`
- **动态 pad（sometimes）：** 运行/协商后才出现；典型 `rtspsrc`、`uridecodebin` → 需 **pad-added**

### 2.2 关键元件（必熟）

`rtspsrc`、`v4l2src`、`h264parse`、`capsfilter`、`videoconvert`、`appsink`、`appsrc`，以及 Jetson：`nvvidconv`、`nvv4l2decoder`、`nvv4l2h264enc`。

**appsink / appsrc：** 应用与管道交换数据（面试高频）≈ 业务拿/喂原始 buffer。

### 2.3 引用计数（工程必会）

| 类型 | 释放 |
|---|---|
| Element / Pipeline / Pad / Bus | `gst_object_unref` |
| Buffer / Caps / Sample | `gst_buffer_unref` / `gst_caps_unref` / `gst_sample_unref` |

习惯：

- `get_by_name` / `get_bus` / `get_static_pad` → 多一份 ref，用完 unref  
- `gst_app_src_push_buffer`：**成功不 unref；失败必须 unref**  
- appsink：`pull_sample` → 用完 `gst_sample_unref`  

常用头：`<gst/gst.h>`、`<gst/app/gstappsrc.h>`、`<gst/app/gstappsink.h>`、`<gst/video/video.h>`。

### 2.4 工程实战重点

| 主题 | 要点 |
|---|---|
| 建管 | `gst-launch`；C 手搓 `factory_make`+link；或 `gst_parse_launch` |
| Bus | ERROR/EOS → quit → 重建 |
| 动态 pad | pad-added 里按 caps 判断再 `gst_pad_link` |
| Caps 失败 | 最常见坑；用 **capsfilter** 卡死格式（如 NV12+NVMM、BGRx） |
| appsink | `gst_app_sink_pull_sample` → Sample → Buffer |
| 时间戳 / EOS | Buffer PTS；EOS=流结束，直播当断线重连 |
| 多线程 | 内部 streaming / queue / 编解码线程；回调勿做重活 |
| 嵌入式硬解 | Jetson 用 `nvv4l2decoder`（桌面常见 `v4l2h264dec` 是另一路）；注意 NVMM、DPB |

**建管口诀：**

```text
建元件 → 设 caps/属性 → add+link（源动态则 pad-added）
→ PLAYING → 听 Bus → NULL + unref
```

### 2.5 NVMM / Caps / NV12（本仓库高频）

- **NVMM：** Jetson GPU/DMA 缓冲；`video/x-raw(memory:NVMM)`  
- **NV12：** YUV420 半平面（Y + UV 交错）；硬编常用  
- **硬编前卡死：** `video/x-raw(memory:NVMM),format=NV12`（`GstRtspClient`）  
- **解码给业务：** `BGRx` → `BGR`（`GstSourceDecode`）  

### 2.6 动态 Pad 与 gst-launch

`rtspsrc` **不能**在建管时可靠 `link` 到 depay：pad 尚未创建。

```bash
# 正确：必须有 ! 与完整下游 + sink
gst-launch-1.0 rtspsrc location=rtsp://127.0.0.1:8600/test/ch0 protocols=tcp ! \
  rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink

# 或
gst-launch-1.0 playbin uri=rtsp://127.0.0.1:8600/test/ch0
```

| 错误 | 现象 |
|---|---|
| 只有 rtspsrc / 无 sink | `not-linked` |
| `rtspsrc location=... rtph264depay !`（漏 `!`） | depay 被当成属性 → not-linked |
| `rtspsrc ! autovideosink` | RTP≠raw → Delayed linking failed |
| 去掉 avdec | H264 无法 link 到 videoconvert |

**demo 端口：** `./videoRtspClientTest` 无参数 → Server **:8600**；带参数 → MediaMTX **:9554**（UDP 5420）。

### 2.7 GStreamer 高频面试题（简答）

**Q1. Pipeline / Element / Pad / Caps？**  
总容器；处理单元；端口；格式协商合同。

**Q2. 四状态？PAUSED vs PLAYING？**  
NULL→READY→PAUSED→PLAYING。PAUSED 已 preroll、时钟不推进；PLAYING 走时钟实时推。退出须 NULL。

**Q3. rtspsrc 为何不能直接 link？动态 pad？pad-added？**  
协商后才有 src pad；回调里 `gst_pad_link` 到下游。

**Q4. Bus？错误？EOS？**  
消息总线；`gst_bus_add_watch` + parse_error；EOS=流结束，直播当断流重建。

**Q5. appsink / appsrc？**  
pull_sample 取帧；push_buffer 喂帧。Decode / Client。

**Q6. Caps 协商失败？**  
上下游交集为空。查格式/NVMM/分辨率；`GST_DEBUG=GST_CAPS:6`；capsfilter 强制路径。

**Q7. GstBuffer？PTS/DTS？**  
数据+时间戳+可选 meta。PTS 显示时间。

**Q8. gst-launch RTSP 显示？**  
见 §2.6。

**Q9. 线程模型？**  
源收包、queue、编解码、appsink 回调线程、应用 GMainLoop 线程。

**Q10. 卡死/卡顿/断流？**  
见 [第七章](#七工程排障与代码修复对照)。

---

## 三、FFmpeg vs GStreamer

| 对比项 | FFmpeg | GStreamer |
|---|---|---|
| 定位 | 编解码库，自己写代码串联逻辑 | 流媒体框架，插件化流水线 |
| 开发模式 | 手动管理 packet/frame，调用 API | 配置 pipeline，element 自动流转 buffer |
| 擅长 | 自定义深度处理、编解码、文件转码 | 实时流水线、摄像头、RTSP，快速搭链路 |
| 内存 | 完全自己管理 AVFrame/AVPacket | 框架管理 GstBuffer；appsink/appsrc 拿/喂数据 |
| 调试 | 命令行 `ffmpeg` | `gst-launch-1.0`、`GST_DEBUG` |
| 本仓库 | 遗留 `src/app/ptz/ffmpeg/` | 现主路径 `public/gstNvDeeps/` |

**面试标准答案：**

> 需要精细控制每帧、深度自定义算法 → 选 **FFmpeg libav\***；  
> 快速搭建流媒体链路、多路流、摄像头、RTSP → 优先 **GStreamer**，用 **appsink** 导出数据做业务（或 **appsrc** 喂帧）。  

补充：GStreamer 部分插件内部也会调 FFmpeg；二者是编排方式差异，不是完全互斥。

---

## 四、嵌入式音视频通用面试题

| 题 | 要点 / 本仓库 |
|---|---|
| NV12 / YUV420P 内存布局 | 均 4:2:0；I420 三平面，NV12 的 UV 交错；硬编多用 NV12+NVMM |
| PTS 漂移、音画不同步 | 时间基、sync 等待、丢包、Caps 无 framerate、B 帧；直播常 `sync=false`；推 MTX 写死 framerate |
| 硬解优缺点与坑 | 省 CPU；格式限制、GPU↔CPU 拷贝、会话数、DPB/B 帧、属性须创建时设置 |
| RTSP 卡顿/花屏/丢包 | 卡顿→sync/queue；花屏→disable-dpb+B 帧；丢包→UDP/SPS/MTX 帧率 |
| EOS | 流结束；直播 → Bus quit → 延迟重连 |
| 内存泄漏 | Gst：get/push/sample/watch 规则；FFmpeg：packet/frame unref；`valgrind`、长期 RSS |

**FLV 与其它「协议/容器」别混：** FLV 是容器（常配 RTMP）；RTSP 是会话（媒体多在 RTP）；HLS 是 HTTP+切片；SRT 是传输；WebRTC 是 RTP 实时框架。CloudPusher：`flvmux` + RTMP 是匹配天盾上云，不是「所有推流都要 FLV」。

---

## 五、学习路线建议（嵌入式 C++）

### FFmpeg

1. 先跑命令行（转码 / 拉 RTSP）  
2. 官方 `demuxing_decoding` 示例  
3. 手写：解封装 + 解码完整 demo  
4. 再做编码、转码；吃透 **PTS / av_rescale_q**  
5. 对照本仓库 `AvH264`、`ffmpegservice` 看泄漏与 `rtsp_transport`  

### GStreamer

1. 熟悉 `gst-launch`，弄清 `!`、sink、Caps  
2. 官方 appsink 示例  
3. 手写：`rtspsrc` + pad-added + appsink 取帧  
4. 再写：appsrc → enc → pay → udpsink（= Client）  
5. 对照本仓库顺序建议：**CloudPusher（短）→ SourceDecode → RtspClient → RtspServer**  

### 重点工程坑（两者共通）

时间戳、内存管理、动态 pad（Gst）/ 流索引（FFmpeg）、异常断流与重连。

### 极简 C 提纲（Gst 拉流取帧）

```text
gst_init
→ 建 rtspsrc + depay + parse + decode + convert + appsink
→ pad-added 链接（或 parse_launch）
→ bus watch ERROR/EOS
→ new-sample: pull_sample → map → 业务 → sample_unref
→ PLAYING + g_main_loop_run
→ NULL + 摘 watch + unref
```

Jetson：软解换成 `nvv4l2decoder ! nvvidconv ! BGRx` 即 Decode 雏形。

---

## 六、gstNvDeeps 四模块实战对照

### 6.1 总表

| | SourceDecode | RtspClient | CloudPusher | RtspServer |
|---|---|---|---|---|
| 方向 | 拉流→业务 | 业务→推流 | RTSP→RTMP 透传 | RTSP 服务外壳 |
| 应用桥 | appsink | appsrc | 无 | 挂载点 |
| Pad | 半动态 uridecodebin | 全静态 | 半动态 rtspsrc | 库内 |
| 特点 | DPB/硬解注释深 | 配置全、易臃肿 | 运维最强 | 多 mount + pay0 |

### 6.2 管道草图

**Decode**

```text
uridecodebin ──pad-added──► nvvidconv → caps(BGRx) → videoconvert → appsink(BGR)
```

**Client**

```text
appsrc → videoconvert → nvvidconv → caps(NV12+NVMM)
       → nvv4l2h264enc → h264parse → rtph264pay → udpsink
```

**CloudPusher**

```text
rtspsrc ──pad-added──► rtph264depay → h264parse → queue → flvmux → rtmp(2)sink
```

默认 Param：`latencyMs=300`，`reconnectDelayMs=5000`，`stallTimeoutMs=30000`，`stateChangeTimeoutMs=5000`。  
`startPush` 已在跑时：`stopPush` 再递归 `startPush` = 换 URL 强制重启。

**Server**

```text
udpsrc(RTP) ! depay ! rtph264pay name=pay0  → 对外 rtsp://ip:port/path
```

私有 `GMainContext` + `gst_rtsp_server_attach`（反复重启必须独立 context）。

### 6.3 isOnStream vs Watchdog

| | Decode/Client `isOnStream` | CloudPusher watchdog |
|---|---|---|
| 看什么 | 最近出帧 / pushFrame | parse 上 buffer probe |
| 超时 | 2s | 30s（约每 10s 查） |
| 行为 | **只读探活** | **超时 quit→重连** |

目的都是「有没有新媒体」；一个给业务问，一个自愈。

### 6.4 综合评价

- **CloudPusher：** 职责窄、私有 context、stall、drain teardown — 运维样板  
- **SourceDecode：** 业务入口、appsink + 硬解配置范文  
- **RtspClient：** 编码推流瑞士军刀；名字易误解（实为 UDP RTP）  
- **RtspServer：** 多挂载实用；自定义 `GstElement*` 工厂标注未充分测试  

---

## 七、工程排障与代码修复对照

### 7.1 六类现象 → 先看什么

| 现象 | 先看 |
|---|---|
| 卡死、teardown 挂 | 未到 NULL；Bus watch 未摘；默认 GMainContext 冲突（CloudPusher 私有 context+drain） |
| 卡顿、延迟涨 | `sync=true`；queue 堆积；无 `drop`；DPB/B 帧；CPU 软转 |
| 断流 | Bus ERROR/EOS；watchdog；`isOnStream` 2s |
| 花屏 | `disable-dpb` 遇上 B 帧 |
| 有流无画 | SPS/PPS（`config-interval`）；Caps 无 framerate（MediaMTX） |
| 协商失败 | 硬编前不是 NV12+NVMM |

命令：`GST_DEBUG=3`、`gst-launch` 分段、`gst-inspect`、查 UDP/TCP、关键帧间隔。

### 7.2 对应本仓库「修复点」

| # | 模块与位置 | 手段 |
|---|---|---|
| 1 teardown | CloudPusher `destroyPipeline`/`drain`；Server 独立 context；Decode/Client `g_source_remove`+NULL | 生命周期 |
| 2 延迟 | Decode appsink `sync=false,drop,max-buffers=5`；Client udpsink `sync=false` | 实时参数 |
| 3 断流 | 共同 Bus quit 重拉；CloudPusher watchdog；Decode/Client `isOnStream` | 探活/自愈 |
| 4 花屏 | Decode `child-added` 设 `disable-dpb` | 创建时设置 |
| 5 无画 | Client/Server/CloudPusher `config-interval=-1`；Client `framerate` | SPS + MTX |
| 6 协商 | Client capsfilter NV12+NVMM；Decode BGRx | capsfilter |

**已知缺口：** Decode/Client 仍默认 GMainContext；CloudPusher 的 `watchdogSourceId` 宜对称 remove；假活自动重连仅 CloudPusher 做满。

### 7.3 面试 1 分钟收束

> 直播不是点播。概念四件套 + 动态 pad + Bus + appsrc/appsink 所有权 + capsfilter 卡 NVMM。  
> 排障：销毁看状态与 Loop；延迟看 sync/queue；断流 Bus+无帧看门狗；花屏 DPB；无画看 SPS/帧率。  
> 项目：Decode 限深丢帧，Client 硬编 NV12+NVMM，CloudPusher 私有 context 与 stall，Server 挂 UDP RTP 对外 RTSP。

---

## 八、资料与命令速查

### 官方

| 资源 | URL |
|---|---|
| GStreamer 官网 | https://gstreamer.freedesktop.org/ |
| 官方教程 | https://gstreamer.freedesktop.org/documentation/tutorials/index.html |
| 应用开发手册 | https://gstreamer.freedesktop.org/documentation/application-development/index.html |
| RTSP Server 文档 | https://gstreamer.freedesktop.org/documentation/gst-rtsp-server/index.html |
| GStreamer GitLab | https://gitlab.freedesktop.org/gstreamer/gstreamer |
| FFmpeg 官网 / 文档 | https://ffmpeg.org/ |

GStreamer **不是**某单一公司产品，而是 Freedesktop 开源社区项目（LGPL）；NVIDIA 提供 Jetson 加速插件。可在 Linux/Windows/macOS/嵌入式使用，**不绑死英伟达**（`nv*` 才是 Jetson 路径）。

### 安装（Ubuntu 示例）

```bash
sudo apt install -y gstreamer1.0-tools gstreamer1.0-plugins-{base,good,bad,ugly} \
  gstreamer1.0-libav libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
```

Jetson 硬编硬解随 **JetPack/L4T**，用 `gst-inspect-1.0 nvv4l2h264enc` 确认。

### examples

```bash
# 无参数 → GstRtspServer :8600
./videoRtspClientTest
gst-launch-1.0 playbin uri=rtsp://127.0.0.1:8600/test/ch0

# 带参数 → MediaMTX :9554（需已启动，UDP 5420）
./videoRtspClientTest 1
gst-discoverer-1.0 -v rtsp://127.0.0.1:9554/test/ch0
```

### 模块路径

```text
public/gstNvDeeps/
  gstSourceDecode/
  gstRtspClient/
  gstCloudPusher/
  gstRtspServer/
  examples/
src/app/ptz/ffmpeg/          # 遗留 FFmpeg
thirdpart/mediamtx/          # MediaMTX 配置
```

---

*文档路径：`public/gstNvDeeps/GStreamer学习与面试笔记.md`*  
*定位：学习提纲 + 面试简答 + 本仓库映射；以工程实战为主。*
