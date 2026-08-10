---
name: hepu power-off memory
overview: 在 ptz_service 节点连接到和普 PTZ 后，自动检查"断电记忆"使能状态：未启用则下发启用，仅在每次重连后下发一次。直接复用 SDK 已封装的二进制接口 HVS_GetPowerOffMemoryEnable / HVS_EnablePtzFunction(PTZ_POWEROFFMEMORY)，不走 sendCommonCmd JSON。
todos:
  - id: sdk-api
    content: 在 HepuPtzCtrl 新增 getPowerOffMemoryEnable / setPowerOffMemoryEnable，包装 SDK HVS_GetPowerOffMemoryEnable 与 HVS_EnablePtzFunction(PTZ_POWEROFFMEMORY)
    status: completed
  - id: ptz-flag
    content: 在 ptzDeviceHepu.h 添加 hasInitPowerOffMemory 标志，并在 resetHepuPostConnectConfigState 中清零
    status: completed
  - id: ptz-call
    content: 在 configureOnceAfterConnected 末尾追加'读-比较-按需置 1-成功置位'逻辑，失败保留标志为 false 等下次回调重试
    status: completed
  - id: build-verify
    content: colcon build ptz_service 通过；连接日志中出现一次 power-off memory ENABLED/already ENABLED；重启 PTZ 后再次出现
    status: completed
isProject: false
---

## 关键背景

- SDK 已封装好二进制接口（[thirdpart/hepuSdk/include/module/iptz.h](thirdpart/hepuSdk/include/module/iptz.h)），约定 `enable: 1=启用 / 0=关闭`：

```c
SDK_EXPORT bool HVS_GetPowerOffMemoryEnable(DevHandle h, int* enable);
SDK_EXPORT bool HVS_EnablePtzFunction(DevHandle h, PtzFunction_e type, bool enable);
// PtzFunction_e::PTZ_POWEROFFMEMORY = 0  (datdefs.h:111)
```

- 应用层"连接后只下发一次"的统一入口在 `PtzDeviceHepu::configureOnceAfterConnected()`（[ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp:1667](ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp)），断连时 `resetHepuPostConnectConfigState()` 清掉 `hasInit*` 标志重连再下发。

## 改动 1：SDK 控制类增加两个方法

文件：
- [iotDevices/ptzHepuSDK/include/ptz_hepu_ctrl.h](iotDevices/ptzHepuSDK/include/ptz_hepu_ctrl.h)
- [iotDevices/ptzHepuSDK/src/ptz_hepu_ctrl.cpp](iotDevices/ptzHepuSDK/src/ptz_hepu_ctrl.cpp)

在 `HepuPtzCtrl`「云台控制」分组（紧邻 `setPosition*` / `setIcr` / `getDayNightMode`）新增：

```cpp
// 断电记忆使能：和普协议 ptzGetPowerOffEnable / ptzSetPowerOffEnable
//   enable: 1=启用断电记忆, 0=关闭 (与 SDK HVS_GetPowerOffMemoryEnable 输出语义一致)
int32_t getPowerOffMemoryEnable(int32_t& enable);
int32_t setPowerOffMemoryEnable(bool enable);
```

实现风格完全比照 `setIcr` / `getDayNightMode`：
- 先 `if (!isReallyConnected()) return -1;`
- `std::lock_guard<std::mutex> lock(this->m_device_mutex);`
- 直接调 `HVS_GetPowerOffMemoryEnable(device_, &raw)` / `HVS_EnablePtzFunction(device_, PTZ_POWEROFFMEMORY, enable)`
- 失败用 `HVS_GetLastErrMsg(device_)` 打 `LOG_ERROR`，成功打 `LOG_INFO`，返回 `0/-1`
- `getPowerOffMemoryEnable` 出参用 `int raw=-1` 初值兜底（与 SDK 文档示例一致），仅在 SDK 返回 true 时才把 `raw` 赋给出参 `enable`

## 改动 2：PtzDeviceHepu 在连接后下发并维护一次性标志

文件：
- [ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.h](ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.h)
- [ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp](ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp)

在头文件 `hasInit*` 一组成员里加：

```cpp
bool hasInitPowerOffMemory{false};  // 断电记忆已校准/下发过 (本次连接周期)
```

在 `resetHepuPostConnectConfigState()` 里加：`hasInitPowerOffMemory = false;`，并补到 LOG 列表。

在 `configureOnceAfterConnected()` 末尾（紧跟 `setStreamFrameRate` 之后、`hasInitSmartServer` CAS 之前）追加一段，复用现有"先 get 比较再 set"的模式：

```cpp
if (!hasInitPowerOffMemory) {
    int32_t curEnable = -1;
    int32_t rGet = deviceApi_->ctrl->getPowerOffMemoryEnable(curEnable);
    if (rGet == 0 && curEnable == 1) {
        LOG_INFO("PtzHepu: power-off memory already ENABLED (enable=%d), no push needed", curEnable);
        hasInitPowerOffMemory = true;
    } else {
        if (rGet != 0) {
            LOG_WARN("PtzHepu: getPowerOffMemoryEnable failed, will push enable=1 unconditionally");
        } else {
            LOG_WARN("PtzHepu: power-off memory currently DISABLED (enable=%d), pushing enable=1", curEnable);
        }
        int32_t rSet = deviceApi_->ctrl->setPowerOffMemoryEnable(true);
        if (rSet == 0) {
            LOG_INFO("PtzHepu: power-off memory ENABLED (this PTZ connect session)");
            hasInitPowerOffMemory = true;
            // 不强求二次回读: 与 setStreamFrameRate 等其它一次性配置一致, 失败则下次 status 回调重试
        } else {
            LOG_ERROR("PtzHepu: setPowerOffMemoryEnable(true) failed, ret=%d (will retry on next status callback)", rSet);
        }
    }
}
```

要点：
- 仅在"首次连接 / 重连后一次"被触发：`onPtzStatusCallback` 已经按 `status.connected` 边沿调用 `configureOnceAfterConnected()`，断连边沿走 `resetHepuPostConnectConfigState()` 把 `hasInitPowerOffMemory` 清回 false。
- 失败时不置位 `hasInitPowerOffMemory`，下一次 10Hz status 回调再进 `configureOnceAfterConnected()` 自动重试，与 `setSmartServerInfo` / `enableTrackAbility` 等同套机制。
- 不修改 `PtzStatus.msg`，不发布到 ROS2 话题；只是设备侧一次性配置。

## 不做的事 (避免 scope 蔓延)

- 不引入新的 ROS2 服务/话题/参数。
- 不动 `powerOffDelayTime`（断电记忆触发后的"上电定位延时"，是另一概念）。
- 不去同时启用 `PTZ_DEBUGMODE` / `PTZ_HORSTABLIZER` / `PTZ_VERSTABLIZER`，本任务只针对断电记忆。
- 不在管线启动 (`startVideoPipeline`) 阶段直接调，原因同 [ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp:271-274](ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp) 的注释：此时 SDK TCP 通道未真正连上，调用会被 `isReallyConnected()` 拦截；正确时机是 `onPtzStatusCallback(connected=true)`。

## 验证

- `colcon build --packages-select ptz_service` 通过；
- 设备首次连上后 `journalctl/ptz_service.log` 中应看到 `power-off memory already ENABLED` 或 `pushing enable=1` + `power-off memory ENABLED` 一次；
- 重启 PTZ 后日志再次出现一次（验证 reset/重新下发路径）；
- 在和普 PTZ Web 上确认"断电记忆"开关已打开。
