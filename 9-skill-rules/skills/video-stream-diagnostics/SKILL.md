---
name: video-stream-diagnostics
description: 视频流故障诊断指南，通过帧率日志定位视频流异常环节。Use when diagnosing video stream issues, FPS drops, RTSP failures, or video pipeline problems.
---

# 视频流故障诊断指南

## 视频流链路

```
PTZ设备 → 原始RTSP流 → ptz_app解码 → 共享内存 → AI模块处理 → 共享内存 → alg_app读取 → RTSP推流 → C2客户端
```

## 关键日志与检查点

| 检查点 | 日志位置 | 关键字 | 正常值 |
|--------|----------|--------|--------|
| 原始帧率 | `agx_ptz.log` | `camera X, WH:...FPS:` | ~25fps |
| AI处理后帧率 | `agx_ptz.log` | `AI_input_FPS=` | ~25fps |
| RTSP推流帧率 | `agx_ptz.log` | `RTSP_push_FPS=` | ~25fps |
| 帧超时警告 | `agx_ptz.log` | `input frame timeout` | 无或偶发 |
| 帧不连续 | `agx_ptz.log` | `process frame is too low` | 无 |

## 故障定位矩阵

| 原始帧率 | AI_input_FPS | RTSP_push_FPS | C2检测 | 问题定位 |
|----------|--------------|---------------|--------|----------|
| ❌ 异常 | ❌ 异常 | ❌ 异常 | Failed | **PTZ设备/原始RTSP流问题** |
| ✅ 正常 | ❌ 异常 | ❌ 异常 | Failed | **AI模块处理异常** |
| ✅ 正常 | ✅ 正常 | ❌ 异常 | Failed | **RTSP编码推流问题** |
| ✅ 正常 | ✅ 正常 | ✅ 正常 | Failed | **网络/mediamtx问题** |
| ✅ 正常 | ✅ 正常 | ✅ 正常 | Success | 正常 |

## 诊断步骤

### 1. 确定故障时间点

从C2端检测日志或用户反馈获取故障发生的具体时间。

### 2. 查看原始帧率

```bash
grep "camera.*FPS:" /home/skyfend/log/agx_ptz.log | grep "故障时间"
```

正常输出示例：
```
camera 0, WH: [ 1920 1080 ], totalDataSize: 6220800, FPS: 25.00
camera 1, WH: [ 640 512 ], totalDataSize: 983040, FPS: 25.00
```

### 3. 查看AI处理后帧率

```bash
grep "AI_input_FPS\|RTSP_push_FPS" /home/skyfend/log/agx_ptz.log | grep "故障时间"
```

正常输出示例：
```
Visible: AI_input_FPS=25.0, RTSP_push_FPS=25.0, frameId=12345
Infrared: AI_input_FPS=25.0, RTSP_push_FPS=25.0, frameId=12345
```

### 4. 检查超时和丢帧

```bash
grep -E "timeout|too low" /home/skyfend/log/agx_ptz.log | grep "故障时间"
```

## 常见问题及解决方案

### 问题1: 原始帧率异常

**现象**: `camera X...FPS:` 低于20fps或无打印

**可能原因**:
- PTZ设备网络不稳定
- RTSP流源异常
- 解码器资源不足

**解决方案**:
- 检查PTZ设备网络连接
- 检查PTZ设备Web界面是否正常
- 重启PTZ设备或ptz_app服务

### 问题2: AI处理帧率异常

**现象**: 原始帧率正常，但 `AI_input_FPS` 低或出现 `readNewFrame timeout`

**可能原因**:
- AI模块处理慢或卡死
- GPU资源不足
- 共享内存读写异常

**解决方案**:
- 检查AI模块日志
- 检查GPU使用率 (`tegrastats` 或 `nvidia-smi`)
- 重启AI模块

### 问题3: RTSP推流帧率异常

**现象**: `AI_input_FPS` 正常，但 `RTSP_push_FPS` 低

**可能原因**:
- 编码器问题
- 推流网络拥塞
- mediamtx服务异常

**解决方案**:
- 检查编码器日志
- 检查网络带宽
- 重启mediamtx服务

## 日志文件位置

| 模块 | 日志路径 |
|------|----------|
| ptz_app/alg_app | `/home/skyfend/log/agx_ptz.log` |
| ptz_service (和普) | `/home/skyfend/log/ptz_service.log` |

## 相关代码文件

- 原始帧率打印: `src/app/ptz/ptz_app.cpp` (onVideoFrameCb)
- AI处理后帧率打印: `src/app/alg_app/alg_app.cpp` (image_get_thread/image_get_thread_infrared)
- 和普视频流: `ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp`
