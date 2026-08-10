---
name: Hepu PTZ NTP Config
overview: 在和普 PTZ 连接成功后，自动通过 SDK 接口 HVS_GetSysTime / HVS_SetSysTime 配置 NTP 校时，NTP 服务器地址动态获取 AGX 与 PTZ 同网段的本机 IP。
todos:
  - id: add-ntp-method
    content: 在 HepuPtzCtrl 中新增 configureNtp() 方法（.h 声明 + .cpp 实现）
    status: completed
  - id: call-ntp-init
    content: 在 ptzDeviceHepu.cpp initDevice() 中动态获取 AGX IP 并调用 configureNtp
    status: completed
isProject: false
---

# 和普 PTZ 初始化后自动配置 NTP 校时

## 背景

和普 SDK 提供了 `SystemTimeInfo_t` 结构体和 `HVS_GetSysTime` / `HVS_SetSysTime` 接口，可以在代码中配置 NTP 参数（对应 PTZ Web 界面的"时间设置"页面）。目前代码中没有调用这些接口，需要手动在 web 界面配置。

## SDK 接口

- `HVS_GetSysTime(DevHandle h, PSystemTimeInfo_t system_time)` -- 获取当前时间配置
- `HVS_SetSysTime(DevHandle h, PSystemTimeInfo_t system_time)` -- 设置时间配置

关键字段（[datdefs.h](thirdpart/hepuSdk/include/datdefs.h) line 1779-1785）：

```cpp
int   mandateType;        // 授时方式：0:手动 1:NTP
char  ntpServer1[128];    // ntp服务器1
int   ntpPort1;           // 端口1（默认123）
int   ntpUpdateCycle;     // 更新周期(days)
```

## 修改方案

### 1. 在 HepuPtzCtrl 中新增 NTP 配置方法

文件：[ptz_hepu_ctrl.h](iotDevices/ptzHepuSDK/include/ptz_hepu_ctrl.h) / [ptz_hepu_ctrl.cpp](iotDevices/ptzHepuSDK/src/ptz_hepu_ctrl.cpp)

新增 public 方法：

```cpp
int32_t configureNtp(const std::string& ntp_server, int ntp_port = 123);
```

实现逻辑：

- 调用 `HVS_GetSysTime` 读取当前配置（读-改-写，保留其他字段）
- 设置 `mandateType = 1`（NTP 授时）
- 设置 `ntpServer1` 为传入的 `ntp_server`
- 设置 `ntpPort1` 为 `ntp_port`（默认 123）
- 调用 `HVS_SetSysTime` 写回

### 2. 在 PtzDeviceHepu 初始化流程中调用

文件：[ptzDeviceHepu.cpp](ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp)

在 `initDevice()` 的步骤 9（注册状态回调）之后，新增步骤 10（NTP 配置）：

- 根据 PTZ 的 `deviceIp`_ 动态获取 AGX 同网段本机 IP（复用 `getifaddrs` 逻辑，与 `time_sync_manager.cpp:68` 中 `get_local_ip_for_peer_nbo` 相同的思路）
- 调用 `deviceApi_->ctrl->configureNtp(agx_local_ip)` 配置 NTP
- 配置失败仅打印 WARN 日志，不影响设备初始化流程

### 动态 IP 获取

不写死 `192.168.2.132`，而是根据 PTZ 设备 IP（如 `192.168.2.4`）遍历本机网卡，找到与 PTZ 同子网的 AGX IP 作为 NTP 服务器地址。这样多网段部署时也能自动适配。