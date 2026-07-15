# Spotter Pro 天盾断流问题排查与修复总结

**文档日期：** 2026-07-01  
**设备 SN：** SSF200B00S211001  
**设备名称：** 沙色 (001) / Spotter Pro  
**涉及分支：** `user/2.1.0.0_dev21_fix20260528_v9`  
**修复人员：** 袁伟健（设备端排查与修复）

---

## 1. 问题现象

| 侧 | 现象 |
|---|---|
| **C2（本地）** | 视频流正常 |
| **天盾（云端）** | 黑屏，报 `{"code":-400,"msg":"stream not found"}` |
| **设备遥测** | MQTT 在线，功率/雷达/PTZ 开关正常，但码率 0 Mbps、帧率 0 |

典型表现：**设备在线、C2 有画面，天盾无流。**

---

## 2. 排查结论

### 2.1 根因（设备端）

**主因：`nexus_gateway` 向云端 RTMP 推流失败后，TCP 连接僵死在 `CLOSE-WAIT`，本地 socket 未正确释放，推流线程无法有效重连，云端无活跃 publish 流。**

```
C2 本地 RTSP (127.0.0.1:9554)  →  正常 ✅
        ↓
CloudPusher RTMP 推流 (1935)   →  失败，CLOSE-WAIT 残留 ❌
        ↓
云端无活跃流                    →  天盾 stream not found ❌
```

### 2.2 已排除

- ❌ 不是摄像头/编码故障（C2 本地 RTSP 一直正常）
- ❌ 不是当前网络完全不通（ping/1935/30010 端口可达）
- ❌ 不是 PTZ SN 或流地址变化（缓存地址与历史一致）

### 2.3 历史诱因（需云端侧关注）

| 诱因 | 说明 |
|---|---|
| DNS 解析失败 | 日志：`Error resolving "cn.cloud.skyfend.com"` |
| `Already publishing` | 云端旧 publish session 未清理，新连接被拒 |
| 推流线程卡死 | GStreamer 未收到 ERROR，不再进入重连循环 |

---

## 3. 现场证据

### 3.1 修复前

- RTMP 连接：**3 条 CLOSE-WAIT**，**0 条 ESTABLISHED**
- 发送量：仅 handshake 级别（~3~5 KB）
- `nexus_gateway.log` 反复出现：`Connection error`、`Already publishing`
- 最后推流相关日志停在 6/30 14:13，进程自 6/27 起未正确恢复

### 3.2 流地址（未变化）

```json
{
  "ready": true,
  "zoom": "rtmp://cn.cloud.skyfend.com:1935/live/dev/SSF200B00S211001/PTZ-SN-lrmzvoPiCGf3/1",
  "ir":   "rtmp://cn.cloud.skyfend.com:1935/live/dev/SSF200B00S211001/PTZ-SN-lrmzvoPiCGf3/4"
}
```

缓存文件：`/tmp/nexus_stream_urls.json`

### 3.3 修复后

- RTMP CLOSE-WAIT：**0 条**
- RTMP ESTABLISHED：**2 条**（zoom + ir）
- bytes_sent 持续增长（560MB+），lastsnd < 20ms
- 天盾视频流恢复 ✅

---

## 4. 修复方案（设备端 P0）

### 4.1 修改文件（4 个）

| 文件 | 改动要点 |
|---|---|
| `public/gstNvDeeps/gstCloudPusher/gstCloudPusher.h` | 新增 `destroyPipeline()`、stall 看门狗参数、`isWorkerActive()` |
| `public/gstNvDeeps/gstCloudPusher/gstCloudPusher.cpp` | 完整 pipeline teardown、stall 检测强制重连、context drain、startPush 强制重启 |
| `ros_ws/src/nexus_gateway/src/service/ServiceRequestor.h` | 健康监控线程、`m_pushersMutex` |
| `ros_ws/src/nexus_gateway/src/service/ServiceRequestor.cpp` | 启动前 stop 旧实例、30s 健康检查自动 restart |

### 4.2 核心改动说明

1. **`destroyPipeline()`**：ERROR/EOS/停止时统一 `GST_STATE_NULL` + 等待状态落地 + 移除 bus watch + drain context，避免 fd 泄漏。
2. **Stall 看门狗**：30s 无媒体数据强制 quit 主循环并重连，避免半死连接卡死在 `g_main_loop_run`。
3. **`startPush()` 强制重启**：已在运行时先 `stopPush()` 再启动，避免旧线程/旧 fd 残留。
4. **`MonitorCloudPushHealth()`**：每 30s 检查 worker/pipeline 状态，异常时 `restartPush()`。

### 4.3 断流后流地址策略

- **不换地址。** 断流后继续使用云端下发的同一 RTMP URL 重试推流。
- `stream not found` 是拉流侧找不到活跃流，不是地址变更。

---

## 5. 编译与部署

### 5.1 编译

```bash
cd /home/skyfend/workspace/ptz100_agx/ros_ws
source /opt/ros2/local_setup.bash
source install/setup.bash
colcon build --packages-select nexus_gateway --cmake-args -DCMAKE_BUILD_TYPE=Release
```

> 注：若 colcon 报 `/builds/ssg/...` 路径错误，需 patch `skyfend_interfaces` 的 `package.sh` 中 CI 路径，或使用独立 `build_fix` 目录编译。

### 5.2 部署

```bash
/home/skyfend/workspace/ptz100_agx/config/boot/skyfend-ptz100.sh -s nexus_gateway -e restart
```

**本次现场恢复方式：** 重启 `nexus_gateway` 释放僵死 CLOSE-WAIT 连接；代码修复后应能自动重连，不必每次人工重启。

---

## 6. 验证结果

| 用例 | 修复前 | 修复后 | 结果 |
|---|---|---|---|
| RTMP CLOSE-WAIT 数量 | 3 | 0 | ✅ PASS |
| RTMP ESTABLISHED | 0 | 2 | ✅ PASS |
| bytes_sent 持续增长 | 否 | 是（~60Mbps） | ✅ PASS |
| 流地址不变 | - | zoom/ir 路径一致 | ✅ PASS |
| 本地 RTSP | 正常 | 正常 | ✅ PASS |
| MQTT 在线 | 正常 | 正常 | ✅ PASS |
| 天盾播放 | stream not found | 有视频流 | ✅ PASS |
| 重启后推流 ERROR | 有 | 0 条新错误 | ✅ PASS |

---

## 7. 三方职责对齐

| 侧 | 职责 | 本次状态 |
|---|---|---|
| **设备端** | CLOSE-WAIT 修复、推流自愈、同地址重试 | ✅ 已修复并验证 |
| **云端流媒体** | 同 key 以最后一次 publish 为准；session 及时清理 | 杨荣钲确认：以最后一次为准（非 SRS）；建议确认 idle 超时 |
| **天盾播放端** | 按 SN 固定 path 拉流，无需改地址逻辑 | 无需修改 |

### 7.1 常见问题答复

**Q：怎么恢复的？需要重启进程吗？**  
A：本次通过重启 `nexus_gateway` 释放残留 fd 恢复。代码修复后正常断线应自动重连，不必每次人工重启。

**Q：重启后推流地址会变吗？**  
A：不会。SN 和 RTMP path 不变，设备用同一 URL 重试。

**Q：只改云端不改设备端可以吗？**  
A：不可以。本次根因在设备端 CLOSE-WAIT 泄漏和推流卡死，云端 takeover 无法替代设备端修复。

**Q：只改设备端不改云端可以吗？**  
A：大多数情况可以（已验证天盾恢复）。极端断线场景可能因 `Already publishing` 出现短暂空窗，建议云端确认 session 清理策略。

---

## 8. 附录：关键命令

```bash
# 查看 RTMP 连接状态
ss -tn state close-wait '( dport = :1935 )'
ss -tn state established '( dport = :1935 )'

# 查看推流 URL 缓存
cat /tmp/nexus_stream_urls.json

# 查看 nexus_gateway 日志
tail -f /home/skyfend/log/nexus_gateway.log

# 重启推流节点
/home/skyfend/workspace/ptz100_agx/config/boot/skyfend-ptz100.sh -s nexus_gateway -e restart
```

---

## 9. 修订记录

| 日期 | 版本 | 说明 |
|---|---|---|
| 2026-07-01 | v1.0 | 初版：问题排查、修复方案、验证结果、三方对齐 |
