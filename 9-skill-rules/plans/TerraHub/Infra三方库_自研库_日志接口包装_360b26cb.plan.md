---
name: Infra 三方库+自研库+日志接口包装
overview: 将 ptz100_agx/thirdpart 和 ptz100_agx/public 中必要的三方库和自研库迁移到 TerraHub/src/03_InfraLayer/ 下，建立 skyfendlibs（自研）和 thirdpartylibs（三方）两个目录，同时创建日志接口包装层。
todos:
  - id: create-dir-structure
    content: 创建 skyfendlibs/ 和 thirdpartylibs/ 目录结构，包括所有子目录和 CMakeLists.txt
    status: completed
  - id: migrate-thirdparty
    content: 复制三方库：zlog/NvidiaVideoSdk/sqlite/cjson/gstreamer-1.0/hepuSdk/naijie 到 thirdpartylibs/（xxhash 不迁移，用 std::hash 替代）
    status: completed
  - id: migrate-skyfendlibs
    content: 复制自研库：appLog/geoUtils/shmTransferFrame/gstNvDeeps/socket*/utils/tools/sysportMqTask/config 到 skyfendlibs/
    status: completed
  - id: migrate-deploy
    content: 将 mediamtx 二进制+配置归入 thirdpartylibs
    status: completed
  - id: create-log-wrapper
    content: 创建日志接口包装层 app_log.h（zlog + AimRT Logger 双模式）
    status: completed
  - id: cmake-integration
    content: 修改根 CMakeLists.txt，新建 src/CMakeLists.txt 和 03_InfraLayer/CMakeLists.txt，串联整个构建链
    status: completed
  - id: verify-build
    content: 验证构建是否通过（至少 cmake configure 成功）
    status: completed
isProject: false
---

# Infra 三方库 + 自研库 + 日志接口包装设计方案

## 当前状态

### ptz100_agx 库清单

**thirdpart/**（12 个三方库，均为 headers + 预编译二进制，无 CMakeLists）：


| 库              | 用途                                        | 依赖它的 public 模块                                                    |
| -------------- | ----------------------------------------- | ----------------------------------------------------------------- |
| zlog           | C 日志库                                     | appLog (及间接依赖 appLog 的 ~20 个模块)                                   |
| ~~xxhash~~     | ~~快速哈希~~                                  | **不迁移**，用 C++ `std::hash` 替代（仅 `skyfend_get_string_hash()` 1 处使用） |
| sqlite         | SQLite3                                   | config/sqliteConfig, config/yamlConfig                            |
| cjson          | JSON 解析（纯 C 库）                            | src/ 下 ~10 个文件（旧协议解析/ota/rtk 等，注：新架构已无 Alink 协议）                  |
| mosquitto      | MQTT C 客户端库 libmosquitto（注意：不含 Broker 进程） | public/mqtt                                                       |
| gstreamer-1.0  | 视频管线 (~690 个头文件 + 预编译库)                   | gstNvDeeps（离线构建回退依赖）                                              |
| NvidiaVideoSdk | NVIDIA 视频辅助 (源码)                          | gstNvDeeps, 业务层                                                   |
| ffmpeg         | 视频编解码                                     | src/app/ptz/ffmpeg                                                |
| hepuSdk        | 和普 PTZ SDK（24 个头文件）                       | src/srv/eth_link                                                  |
| naijie         | 耐杰 PTZ SDK                                | src/srv/eth_link                                                  |
| eSDKOBS        | 华为 OBS 云存储                                | src/app/alg_app, ptz_app                                          |
| mediamtx       | 流媒体服务器（RTSP/WebRTC/HLS 网关），Go 单二进制        | `thirdpart/mediamtx/`                                             |


**public/**（15 个自研模块）：


| 模块                   | 用途                                                                           | 核心依赖                                                         |
| -------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **appLog**           | zlog 封装                                                                      | zlog                                                         |
| **geoUtils**         | 地理坐标工具                                                                       | Eigen3                                                       |
| **shmTransferFrame** | 共享内存传帧                                                                       | OpenCV                                                       |
| **gstNvDeeps/**      | GStreamer 视频 (3 子模块)                                                         | GStreamer, OpenCV, appLog                                    |
| **socketTcpClient**  | TCP 客户端                                                                      | appLog                                                       |
| **socketUdpService** | UDP 服务                                                                       | appLog                                                       |
| **utils**            | 工具函数 (Queue/FileUtil 等)                                                      | appLog                                                       |
| **tools**            | C 工具 (skyfend_tools + skyfend_error，~45 个文件依赖)                               | 无                                                            |
| mqtt                 | MQTT 客户端封装（MqttClient）                                                       | libmosquitto                                                 |
| config/configUtils   | 配置公共头（configCommDef / devicesCfgBase / singleCfgBase / vectorCfgBase 等）      | 无                                                            |
| config/oldConfig     | 旧版配置（cfg.h/cpp + sqlite3_main），已被 sqliteConfig/yamlConfig 替代                 | sqlite3                                                      |
| config/sqliteConfig  | SQLite 配置（maskListCfg / whiteListCfg / sqliteFunc）                           | sqlite3, appLog                                              |
| config/yamlConfig    | YAML 配置（hostDeviceCfg / ptzDevicesCfg / subDevicesCfg / sentryv_calibrate 等） | yaml-cpp, sqlite3, appLog                                    |
| modbusEncode         | Modbus 编码                                                                    | 无                                                            |
| uartService          | 串口                                                                           | appLog                                                       |
| **sysportMqTask**    | 基于 POSIX MQ 的内核级优先级任务队列（高优先级任务抢占消费），AimRT Executor 仅 FIFO 无此能力，有独立价值         | appLog。迁移到 skyfendlibs/，旧 C 版 `src/common/sysport/task/` 不迁移 |
| ~~timerTaskManager~~ | ~~定时器~~                                                                      | **不迁移**，后续如需要再评估                                             |


### TerraHub 当前状态

- `src/03_InfraLayer/` 下只有 `WebGateway/`（HelloWorld 样例）
- **没有** `skyfendlibs/`、`thirdpartylibs/` 目录
- 根 CMakeLists.txt 只 add_subdirectory `AimrtFramework` 和 `demo`，**未 add `src/`**

---

## 迁移决策

### 需要迁移的（10 个自研 + 8 个三方 + 2 个部署配置）

按架构文档 V4.1 第二十六章目录结构，分为三个目标位置：

**skyfendlibs/**（跨 Module 共享的自研公共库）：


| 源路径                           | 目标路径                                | 说明                                                                                                                                      |
| ----------------------------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `public/appLog/`              | `skyfendlibs/app_log/`              | 日志封装（保留 zlog 底层，第一阶段并存）                                                                                                                 |
| `public/geoUtils/`            | `skyfendlibs/geo_utils/`            | 地理坐标计算                                                                                                                                  |
| `public/shmTransferFrame/`    | `skyfendlibs/shm_transfer_frame/`   | 共享内存传帧                                                                                                                                  |
| `public/gstNvDeeps/`          | `skyfendlibs/gst_nv_deeps/`         | GStreamer 视频管线（3 个子模块）                                                                                                                  |
| `public/socketTcpClient/`     | `skyfendlibs/socket_tcp_client/`    | TCP 客户端（第三方设备通信）                                                                                                                        |
| `public/socketUdpService/`    | `skyfendlibs/socket_udp_service/`   | UDP 服务（第三方设备通信）                                                                                                                         |
| `public/utils/`               | `skyfendlibs/utils/`                | 工具函数                                                                                                                                    |
| `public/tools/`               | `skyfendlibs/tools/`                | C 工具函数                                                                                                                                  |
| `public/config/configUtils/`  | `skyfendlibs/config/config_utils/`  | 配置公共头（configCommDef / devicesCfgBase / singleCfgBase / vectorCfgBase 等）                                                                 |
| `public/config/oldConfig/`    | `skyfendlibs/config/old_config/`    | 旧版配置封装（cfg.h + sqlite3_main），已被新 config 替代，仅过渡保留                                                                                        |
| `public/config/sqliteConfig/` | `skyfendlibs/config/sqlite_config/` | SQLite 配置（~10 个 src 文件依赖，先迁移保持兼容，后续逐步切换 AimRT YAML）                                                                                     |
| `public/config/yamlConfig/`   | `skyfendlibs/config/yaml_config/`   | YAML 配置（hostDeviceCfg / ptzDevicesCfg / subDevicesCfg 等）                                                                                |
| `public/sysportMqTask/`       | `skyfendlibs/sysport_mq_task/`      | 基于 POSIX MQ 的内核级优先级任务队列（`mq_send` 的 `msg_prio` 实现抢占式消费），AimRT Executor 全部为 FIFO 队列无此能力，没有优先级，有独立迁移价值。替代旧 C 版 `src/common/sysport/task/` |


**thirdpartylibs/**（第三方预编译库 / SDK）：


| 源路径                         | 目标路径                             | 说明                                           |
| --------------------------- | -------------------------------- | -------------------------------------------- |
| `thirdpart/zlog/`           | `thirdpartylibs/zlog/`           | 日志库（appLog 依赖）                               |
| `thirdpart/NvidiaVideoSdk/` | `thirdpartylibs/NvidiaVideoSdk/` | NVIDIA 视频辅助（源码编译）                            |
| `thirdpart/sqlite/`         | `thirdpartylibs/sqlite/`         | SQLite3（config 模块依赖）                         |
| `thirdpart/cjson/`          | `thirdpartylibs/cjson/`          | JSON 解析（纯 C 库，API 与 nlohmann_json 不兼容，需逐步替换） |
| `thirdpart/gstreamer-1.0/`  | `thirdpartylibs/gstreamer-1.0/`  | GStreamer 头文件 + 预编译库（系统缺失时的离线构建回退）           |
| `thirdpart/hepuSdk/`        | `thirdpartylibs/hepuSdk/`        | 和普 PTZ SDK（暂放此处，PTZ 任务时移到 Module sdk/ 目录）    |
| `thirdpart/naijie/`         | `thirdpartylibs/naijie/`         | 耐杰 PTZ SDK（暂放此处，PTZ 任务时移到 Module sdk/ 目录）    |


### 不迁移的（有替代方案）


| 旧库                         | 原因                                                              | 新架构替代                            |
| -------------------------- | --------------------------------------------------------------- | -------------------------------- |
| `xxhash/`                  | 仅 1 个函数使用（`skyfend_get_string_hash`），C++ 系统基础库自带                | `std::hash<std::string>`         |
| `uartService/`             | 架构禁止串口直连                                                        | ETH + UDP                        |
| `modbusEncode/`            | 串口协议不再需要                                                        | —                                |
| `src/common/sysport/task/` | 旧 C 版 sysport 任务队列，已被 `public/sysportMqTask/`（C++ 重写，支持优先级队列）替代 | `sysportMqTask/` 迁移到 skyfendlibs |
| `timerTaskManager/`        | crontab 式定时器，当前无业务代码使用，后续如有需要再评估引入                              | AimRT `executor::CreateTimer`    |


### 延后评估的


| 库           | 说明                                                                                                                  |
| ----------- | ------------------------------------------------------------------------------------------------------------------- |
| `eSDKOBS/`  | 华为云存储，非核心链路，后续按需引入                                                                                                  |
| `ffmpeg/`   | 旧 PTZ 编码用，新架构用 NVENC 硬编码，后续评估是否需要                                                                                   |
| `mosquitto` | 目前只用于与mqtt客户端。Mqtt EdgeBroker进程部署由 **@鲍利华** 负责,libmosquitto 客户端库是否迁移取决于 Broker 部署方案和 AimRT mqtt_plugin 覆盖范围，整体延后评估。 |


### cjson 与 nlohmann_json 的关系说明

cjson（纯 C 库）和 nlohmann_json（C++ header-only 库）**API 完全不兼容**，不能直接替换：

- **cjson**：`cJSON_Parse()` / `cJSON_GetObjectItem()` / `cJSON_Delete()` — 手动内存管理
- **nlohmann_json**：`json j = json::parse(str); j["key"]` — 自动内存管理，C++ 风格

当前 `src/` 下约 10 个文件使用 cjson（旧协议解析、ota_app、rtk_debuger 等），保留 cjson 在 thirdpartylibs，**逐步替换为 nlohmann_json**。注：新架构已无 C2 app 和 Alink 协议，原 alink 相关的 cjson 使用将随模块废弃而消除。

---

## 目标目录结构

```
TerraHub/
├── src/03_InfraLayer/
│   ├── skyfendlibs/
│   │   ├── CMakeLists.txt              # 聚合所有自研库
│   │   ├── app_log/                    # 日志封装
│   │   │   ├── app_log.h               # 统一日志头（包装 zlog + 预留 AimRT Logger 切换）
│   │   │   ├── skyfend_log.h
│   │   │   ├── skyfend_log.cpp
│   │   │   └── CMakeLists.txt
│   │   ├── geo_utils/
│   │   │   ├── skyfend_geo_utils.h
│   │   │   ├── skyfend_geo_utils.cpp
│   │   │   └── CMakeLists.txt
│   │   ├── shm_transfer_frame/
│   │   │   ├── shmTransferFrame.h
│   │   │   ├── shmTransferFrame.cpp
│   │   │   └── CMakeLists.txt
│   │   ├── gst_nv_deeps/
│   │   │   ├── CMakeLists.txt          # 聚合 3 个子模块
│   │   │   ├── gst_rtsp_client/
│   │   │   ├── gst_source_decode/
│   │   │   └── gst_rtsp_server/
│   │   ├── socket_tcp_client/
│   │   ├── socket_udp_service/
│   │   ├── utils/
│   │   ├── tools/
│   │   ├── sysport_mq_task/            # POSIX MQ 优先级任务队列（C++ 版）
│   │   └── config/                     # 配置模块（过渡期保留，后续切换 AimRT YAML）
│   │       ├── CMakeLists.txt
│   │       ├── config_utils/           # configUtils 公共头（configCommDef / devicesCfgBase 等）
│   │       ├── old_config/             # 旧版配置（cfg.h + sqlite3_main），过渡保留
│   │       ├── sqlite_config/          # SQLite 配置
│   │       └── yaml_config/            # YAML 配置
│   ├── thirdpartylibs/
│   │   ├── CMakeLists.txt              # 聚合所有三方库
│   │   ├── zlog/                       # 头文件 + aarch64 预编译库
│   │   ├── NvidiaVideoSdk/             # 源码
│   │   # xxhash 不迁移（用 std::hash 替代）
│   │   ├── sqlite/                     # 头文件 + 预编译库
│   │   ├── cjson/                      # 头文件（逐步替换为 nlohmann_json）
│   │   ├── gstreamer-1.0/             # 头文件 + 预编译库（离线构建回退）
│   │   ├── hepuSdk/                    # 和普 PTZ SDK（PTZ 任务时移到 Module sdk/）
│   │   └── naijie/                     # 耐杰 PTZ SDK（PTZ 任务时移到 Module sdk/）
│   └── WebGateway/                     # 已有
# deploy/ 目录不在本文档范围（mediamtx 见部署方案文档，mosquitto 由 @鲍利华 负责）
```

---

## CMake 集成方案

### 根 CMakeLists.txt 修改

在 [CMakeLists.txt](TerraHub/CMakeLists.txt) 中增加 `add_subdirectory(src)`:

```cmake
# AimRT framework
add_subdirectory(AimrtFramework/AimRT-1.7.0)

# TerraHub source (InfraLayer, DevAbsLayer, SolutionLayer)
add_subdirectory(src)

# Demo programs
add_subdirectory(demo)
```

### src/CMakeLists.txt（新建）

```cmake
add_subdirectory(03_InfraLayer)
```

### src/03_InfraLayer/CMakeLists.txt（新建）

```cmake
add_subdirectory(skyfendlibs)
add_subdirectory(thirdpartylibs)
```

### skyfendlibs/CMakeLists.txt（新建）

```cmake
add_subdirectory(app_log)
add_subdirectory(geo_utils)
add_subdirectory(shm_transfer_frame)
add_subdirectory(gst_nv_deeps)
add_subdirectory(socket_tcp_client)
add_subdirectory(socket_udp_service)
add_subdirectory(utils)
add_subdirectory(tools)
add_subdirectory(config)
```

---

## 日志接口包装方案（第一阶段）

保留 zlog 底层，`app_log.h` 提供统一宏，预留 AimRT Logger 切换开关：

```cpp
// app_log.h — 统一日志入口
#pragma once

#ifdef USE_AIMRT_LOGGER
  // 第二阶段：切换到 AimRT Logger
  #include "aimrt_module_cpp_interface/logger/logger.h"
  #define SKYFEND_INFO(fmt, ...)  AIMRT_INFO(GetLogger(), fmt, ##__VA_ARGS__)
  #define SKYFEND_ERROR(fmt, ...) AIMRT_ERROR(GetLogger(), fmt, ##__VA_ARGS__)
  // ...
#else
  // 第一阶段：继续使用 zlog
  #include "skyfend_log.h"
  #define SKYFEND_INFO(fmt, ...)  skyfend_log_info(fmt, ##__VA_ARGS__)
  #define SKYFEND_ERROR(fmt, ...) skyfend_log_error(fmt, ##__VA_ARGS__)
  // ...
#endif
```

---

## 与上层模块的关系

Infra 层（`skyfendlibs` + `thirdpartylibs`）是**纯库层**，不是 AimRT Module，不参与 AimRT Channel/RPC 通信，不与天盾或 PC 浏览器交互。

**被上层模块依赖的关系**：


| 上层模块           | 依赖的 skyfendlibs 库                                                     | 说明     |
| -------------- | --------------------------------------------------------------------- | ------ |
| PtzModule      | `socketUdpService`（耐杰 UDP）、`socketTcpClient`（和普 TCP）、`appLog`、`tools` | 设备通信   |
| LiveStreamApp  | `gstNvDeeps`（GStreamer 管线）、`shmTransferFrame`（SHM 传帧）、`appLog`        | 视频全链路  |
| RadarModule    | `socketUdpService`（雷达 UDP）、`appLog`、`tools`                           | 设备通信   |
| AI Module      | `shmTransferFrame`（SHM 读帧）、`appLog`                                   | 帧读取    |
| DeviceManager  | `appLog`、`config/yamlConfig`                                          | 设备配置读取 |
| SysMonitModule | `appLog`、`tools`                                                      | 系统监控   |


**依赖方向**：上层 → Infra（单向），Infra 不依赖任何上层 Module。

---

## 迁移注意事项

- **头文件路径适配**：旧代码 `#include "appLog.h"` 需改为 `#include "app_log/app_log.h"` 或通过 CMake `target_include_directories` 兼容
- **zlog 预编译库**：需确认 `thirdpart/zlog/aarch64/lib/` 下的 `.so` 文件是否在 git 中（当前扫描未发现，可能被 .gitignore 忽略），如果不在需要从 AGX 设备上拷贝
- **系统依赖**：OpenCV、Eigen3、CUDA/TensorRT 仍使用系统安装的版本（`find_package` / `pkg-config`）；GStreamer 优先系统 pkg-config，回退到 thirdpartylibs/gstreamer-1.0
- **不修改源文件内容**：第一阶段只做目录搬迁和 CMake 重组，不改 `.cpp`/`.h` 的实现逻辑
- **AimRT 已提供的能力不重复引入**：yaml-cpp（AimRT 已内置）、protobuf（AimRT 已内置）不需要放在 thirdpartylibs
- **config 模块过渡策略**：sqliteConfig 和 yamlConfig 先原样迁移到 skyfendlibs/config/，保持现有业务代码兼容；后续逐步将配置结构改为 AimRT YAML Configurator 风格
- **cjson 逐步替换**：cjson（纯 C）与 nlohmann_json（C++）API 完全不兼容，先保留 cjson，新代码统一用 nlohmann_json，旧代码逐模块替换
- **PTZ SDK 临时位置**：hepuSdk 和 naijie 暂放 thirdpartylibs，PTZ Module 开发任务（4/10-4/13）时移到 `src/02_DevAbsLayer/01_Detector/Ptz/{HepuPtz,NaijiePtz}/sdk/`
- **mosquitto 相关（延后）**：Broker 进程部署由 @鲍利华 负责（Mqtt EdgeBroker P0, 4/9），libmosquitto 客户端库迁移延后评估，本方案当前不含此部分

