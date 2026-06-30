# 和普 clientTrack 跟踪抖动问题分析与修复总结

## 1. 问题背景

### 1.1 现象

现场反馈和普 PTZ 在 AI 跟踪阶段出现画面/云台**晃动（抖动）**。典型日志时段：`ptz_service-20260101.01.log` 中 **12:32:14** 前后，可见光锁定目标后跟踪不稳定。

和普供应商（qlc）说明：`ivpClientTracking`（clientTrack）正常节拍约为 **25fps（~40ms/帧）**。

### 1.2 影响范围

- 设备：和普 PTZ（场景 C，`enableClientTrack`）
- 路径：AI 发布 `/visiblelight_track_objs`、`/infrared_track_objs` → `ptz_service` → SDK `clientTrack` + `HVS_PositionView`
- 表现：跟踪框滞后、云台顿挫，长间隔后更明显

---

## 2. 根因分析

### 2.1 日志统计（改前）

对 `ptz_service-20260101.01.log` 分析：

| 场景 | `clientTrack` 单次耗时 | 说明 |
|------|------------------------|------|
| 无 FOV | **45–55ms** | `ivpClientTracking` IPC 阻塞 |
| 有 FOV（`next_view_valid=1`） | **100–110ms** | 叠加 `HVS_PositionView`（+50–60ms） |

稳定段（12:29:10–20）中 >60ms 尖峰约占 **4.4%**，多与 `setPositionView` 同期出现。

### 2.2 架构层原因

改前 `onAiDetectionResultsTrack()` 在 **ROS 订阅回调线程**内同步执行：

```
ROS 回调 onAiDetectionResultsTrack
  ├── clientTrack()          ~50ms（阻塞）
  └── setPositionView()      ~50ms（阻塞，当 next_view_valid=1）
  合计可达 ~100ms+
```

叠加因素：

1. **AI 发布快于处理**：跟踪话题约 25fps，单次处理 50–110ms，消息在 `KeepLast(10)` 队列中堆积。
2. **处理旧帧**：回调排队导致下发框滞后，表现为跟踪晃动。
3. **FOV 与 clientTrack 串行**：变倍时拉长单帧处理时间，形成周期性顿挫。
4. **无效 AI 图像尺寸**（次要）：`image_width` 偶发异常值（如 43690），虽 fallback 到 1920×1080，但增加日志噪声；已改为固定标定分辨率。

### 2.3 与供应商沟通结论

和普建议将 **clientTrack** 与 **HVS_PositionView** 解耦；FOV 后续可考虑 `sendCommonCmd` 异步 fire-and-forget（Phase 3，本次未实施）。

---

## 3. 解决方案

### 3.1 设计原则

| 原则 | 做法 |
|------|------|
| ROS 回调快速返回 | 只投递最新 AI 帧，不做阻塞 IO |
| clientTrack 独立线程 | 阻塞 IPC 在 worker 中执行 |
| FOV 独立线程 | `setPositionView` 不阻塞 clientTrack 路径 |
| Latest-only | 处理期间新帧覆盖旧帧，避免排队滞后 |
| 信任 AI FOV | 去掉视场差过滤、200ms 限速（AI 已 1Hz） |
| 固定分辨率 | 使用 `1920×1080` / `640×512` 宏，不读 AI `image_width/height` |

### 3.2 架构（改后）

```
ROS 回调 onAiDetectionResultsTrack()     [<1ms，仅投递]
        │
        ▼
clientTrack worker 线程
  └── processClientTrackFrame()
        ├── clientTrack()               [~45–55ms，阻塞 IPC]
        └── postFovRequest()            [非阻塞投递]
                    │
                    ▼
              FOV worker 线程
                └── setPositionView()   [~50–60ms，独立执行]
```

### 3.3 涉及文件

| 文件 | 改动要点 |
|------|----------|
| `ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.h` | worker 线程、mutex/cv、latest 队列、`lastClientTrackDone_` 耗时统计 |
| `ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp` | `startClientTrackWorkers` / `stopClientTrackWorkers`、`clientTrackWorkerLoop`、`fovWorkerLoop`、`processClientTrackFrame`、`postFovRequest` |
| `ros_ws/src/ptz_service/src/rosService/rosService.cpp` | 跟踪订阅回调保留 `took ms` 诊断；可选 `track_qos KeepLast(1)` |

生命周期：`startVideoPipeline()` 启动 worker，`stopVideoPipeline()` 停止并清空 pending。

---

## 4. 可观测性

### 4.1 日志字段

改后新增 worker 侧 DEBUG 日志：

```
PtzHepu: clientTrack done vt=0 call_ms=48 since_last_ms=41
```

| 字段 | 含义 |
|------|------|
| `call_ms` | 本次 `clientTrack()` IPC 阻塞耗时 |
| `since_last_ms` | 距该通道上次成功下发的间隔 |

ROS 回调侧 `onAiDetectionResultsTrack took X ms` 现在量的是**投递耗时**（通常 0ms），不再反映真实 IPC 时间；应以 worker 日志为准。

### 4.2 现场统计命令（132 实机）

```bash
# 下发节拍 → 等效 fps
grep "clientTrack done vt=0" /home/skyfend/log/ptz_service.log | tail -200 | \
  grep -oP 'since_last_ms=\K\d+' | \
  awk '{s+=$1;n++} END{printf "avg_since_last=%.1fms => %.1f fps\n", s/n, 1000/(s/n)}'

# 单次 IPC 耗时
grep "clientTrack done vt=0" /home/skyfend/log/ptz_service.log | tail -200 | \
  grep -oP 'call_ms=\K\d+' | \
  awk '{s+=$1;n++} END{printf "avg_call_ms=%.1fms\n", s/n}'
```

---

## 5. 验证结果（192.168.2.132 实机）

### 5.1 功能验证

| 项 | 结果 |
|----|------|
| 编译部署 | 通过 |
| ROS 回调非阻塞 | `onAiDetectionResultsTrack took 0 ms` |
| worker 异步 clientTrack | `processClientTrackFrame` 与回调分离 |
| FOV 异步 | `fovWorkerLoop: setPositionView` 不阻塞 clientTrack |
| 可见光锁定跟踪 | `hepu_valid=1 hepu=1`，画面稳定 |
| **晃动问题** | **现场测试认为已解决** |

### 5.2 性能数据

多次采样最近 200 条 `clientTrack done vt=0`：

| 指标 | 典型值 |
|------|--------|
| `since_last_ms` 平均 | **44.5–46.3ms** |
| 折算下发帧率 | **~21.6–22.5 fps** |
| `call_ms`（慢档） | **45–55ms** |
| `call_ms`（drain 快档） | **7–10ms** |
| AI 输入（`cb_visible_track`） | **~25fps（~40ms）** |

### 5.3 为何 AI 25fps、下发 ~22fps

并非回调阻塞，而是 **单 worker 串行 + IPC ~50ms** 的吞吐上限：

- AI 每 **~40ms** 进一帧（25fps）
- worker 每 **~45–50ms** 才能成功下发一帧（~20–22fps）
- 差额由 **latest-only** 丢弃中间旧帧，保留最新框

这是用「略跳帧」换「低延迟、不排队」，改前同样受 IPC 耗时限制，但还会叠加队列滞后与 FOV 串行，体感更差。

---

## 6. 改前 vs 改后对比

| 维度 | 改前 | 改后 |
|------|------|------|
| ROS 回调耗时 | 44–110ms | **~0ms** |
| FOV 与 clientTrack | 同线程串行 | **独立线程** |
| 消息队列 | 易堆积旧帧 | **latest-only** |
| 跟踪滞后 | 框越来越旧 | 始终跟最新框 |
| 下发帧率 | ~20fps 且不稳定 | **~22fps 且稳定** |
| 晃动 | 明显 | **现场验证已消除** |

---

## 7. 已知限制与后续

### 7.1 当前限制

1. **SDK `m_device_mutex`**：clientTrack 与 `setPositionView` 仍可能互抢锁，偶发 `call_ms` 偏高。
2. **下发帧率上限**：在 `call_ms≈50ms` 未降低前，难以稳定达到 25fps 全量下发。
3. **回调 `took ms` 语义变化**：仅表示投递耗时，排查 IPC 需看 `clientTrack done` 日志。

### 7.2 后续可选优化（未实施）

| 阶段 | 内容 |
|------|------|
| Phase 3 | FOV 改 `sendCommonCmd` fire-and-forget（需和普确认协议） |
| 供应商侧 | 缩短 `ivpClientTracking` IPC 至 ≤40ms |
| AI 侧 | 跟踪话题降至 20fps，与下发能力对齐，减少无效跳帧 |
| 简化 | `track_qos KeepLast(1)` 可改回统一 `qos`（worker 已 latest-only） |

---

## 8. 结论

本次问题的本质是 **ROS 回调线程被 clientTrack / setPositionView 同步阻塞**，叠加消息排队导致跟踪框滞后，表现为云台晃动。

通过 **双 worker 异步化 + latest-only 投递**，将阻塞 IO 移出 ROS 回调，FOV 与 clientTrack 解耦，实机验证跟踪稳定，晃动问题**已解决**。

下发帧率约 **22fps**（低于 AI 25fps）是当前 IPC 耗时的物理上限，不影响「跟最新框」的跟踪质量；若需进一步提升至 25fps，需和普侧缩短 IPC 或采用异步 fire-and-forget 方案。

---

**文档版本**：v1.0  
**问题日志**：`ptz_service-20260101.01.log`（12:32:14 时段）  
**验证环境**：192.168.2.132，2026-06-30 实机跟踪测试  
**主要改动模块**：`ptz_service` / `PtzDeviceHepu`
