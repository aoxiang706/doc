---
name: video-stream-debugging
description: 视频流开发调试指南，包含 GStreamer、cv::VideoCapture 线程安全、RTSP/RTMP 拉流推流问题排查。用于调试段错误、视频流无法打开、多线程并发问题时使用。
---

# 视频流开发调试指南

## 一、常见问题速查

| 现象 | 可能原因 | 排查方向 |
|------|----------|----------|
| 段错误 (SIGSEGV) | cv::VideoCapture 并发调用 | 检查多线程场景 |
| 视频流无法打开 | URL 格式错误 / 网络不通 | 验证 URL 可达性 |
| 帧率异常 | 解码器性能 / 缓冲区配置 | 检查 GStreamer pipeline |
| 推流失败 | 编码参数不匹配 | 检查 mediamtx 日志 |

---

## 二、cv::VideoCapture 线程安全问题

### 问题描述

`cv::VideoCapture` 使用 FFmpeg 后端时**不是线程安全**的，多线程并发调用 `VideoCapture::open()` 或构造函数会导致段错误。

### 典型场景

```cpp
// ❌ 危险：多线程并发调用
void thread1() { cv::VideoCapture cap("rtsp://..."); }
void thread2() { cv::VideoCapture cap("rtsp://..."); }

// 两个线程同时执行 → 段错误
```

### 解决方案

```cpp
// ✅ 正确：使用互斥锁保护
bool isVideoUrlOk(const std::string& url) {
    if (url.empty()) return false;
    
    // 静态互斥锁，确保同一时刻只有一个线程执行
    static std::mutex s_videoCaptureMutex;
    std::lock_guard<std::mutex> lock(s_videoCaptureMutex);
    
    cv::VideoCapture cap(url);
    return cap.isOpened();
}
```

### GDB 调试确认

```bash
ros2 run --prefix 'gdb -ex run --args' ptz_service ptz_service
# 段错误后执行
(gdb) bt
# 查看是否有 cv::VideoCapture 相关帧
```

---

## 三、GStreamer Pipeline 调试

### 关键类

| 类 | 用途 | 文件 |
|----|------|------|
| `GstSourceDecode` | RTSP/文件解码 | `gstSourceDecode.cpp` |
| `GstRtspClient` | RTSP 拉流 | `gstRtspClient.cpp` |
| `GstEncodePush` | 编码推流 | `gstEncodePush.cpp` |

### 常用环境变量

```bash
# 启用 GStreamer 调试日志
export GST_DEBUG=3
export GST_DEBUG_FILE=/tmp/gst.log

# 指定硬件解码
export GST_VAAPI_ALL_DRIVERS=1
```

### Pipeline 示例

```cpp
// RTSP 拉流解码 (NVDEC 硬解)
"rtspsrc location=rtsp://... ! rtph264depay ! h264parse ! nvv4l2decoder ! nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! appsink"

// 编码推流 (NVENC 硬编)
"appsrc ! videoconvert ! nvvidconv ! nvv4l2h264enc ! h264parse ! rtph264pay ! udpsink host=... port=..."
```

---

## 四、RTSP/RTMP 问题排查

### URL 格式验证

```cpp
// 支持的格式
// file:///home/test.mp4
// rtmp://example.com/live/stream
// rtsp://192.168.2.4:554/channel=0,stream=0
```

### 快速测试

```bash
# 测试 RTSP 可达性
ffprobe -v error -show_streams rtsp://192.168.2.4:554/channel=0

# 测试 GStreamer pipeline
gst-launch-1.0 rtspsrc location=rtsp://... ! fakesink

# 查看 mediamtx 日志
journalctl -u mediamtx -f
```

---

## 五、调试检查清单

排查视频流问题时按此顺序：

- [ ] 确认 URL 格式正确且网络可达
- [ ] 检查是否有多线程并发调用 `cv::VideoCapture`
- [ ] 使用 GDB 获取段错误堆栈
- [ ] 检查 GStreamer 日志 (`GST_DEBUG=3`)
- [ ] 确认硬件解码器状态 (`nvgstplayer-1.0 测试`)
- [ ] 检查 mediamtx 服务状态和日志

---

## 六、相关文件位置

| 功能 | 文件路径 |
|------|----------|
| GStreamer 解码封装 | `public/gstNvDeeps/gstSourceDecode/` |
| GStreamer 推流封装 | `public/gstNvDeeps/gstEncodePush/` |
| PTZ 设备视频流 | `ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp` |
| 视频测试 demo | `public/gstNvDeeps/examples/` |
