---
name: Fix ptzDevicesCfg parsing
overview: 解决 sysmonit 中 ptzDevicesCfg.yaml 解析失败的问题。对比两种方案，推荐直接调用已有的 PtzDevicesCfg API。
todos:
  - id: cmake
    content: 修改 sysmonit CMakeLists.txt：添加 yaml-cpp 依赖、ptzDevicesCfg 源文件和 include 路径
    status: completed
  - id: video-perf
    content: 替换 build_video_perf_json() 中手写 YAML 解析为 g_ptzDevCfgApi.readList()
    status: completed
  - id: sub-json
    content: 替换 get_devices_sub_json() 中手写 YAML 解析为 g_ptzDevCfgApi.readList()
    status: completed
  - id: shm-info
    content: 替换 build_shm_info_json() 中手写 YAML 解析为 g_ptzDevCfgApi.readList()
    status: completed
  - id: build-test
    content: 编译 sysmonit 并验证 /api/video 返回正确数据
    status: completed
isProject: false
---

# 修复 sysmonit 解析 ptzDevicesCfg.yaml 失败

## 问题根因

`build_video_perf_json()` 源码中的通用解析器看起来正确（检测 `"- "` 开头），但当前 **运行中的二进制可能仍是旧版**（用 `"- sn:"` 匹配）。YAML 格式从 `- sn:` 开头变为 `- enable:` 开头后，旧解析器匹配不到任何条目，`pdevs` 为空，`streams` 返回空数组。

此外，另有 **2 处仍然使用 `"- sn:"` 的硬编码匹配**：

- 第 503 行 `get_devices_sub_json()` — PTZ 设备警告检查
- 第 1028 行 `build_shm_info_json()` — 计算配置设备数量

## 两种方案对比

### 方案 A：继续手写解析（当前做法的修正）

保持现有通用解析器，确保编译部署，并修复另外 2 处 `"- sn:"` 硬编码。

- 优点：不引入新依赖，改动小
- 缺点：手写解析脆弱，YAML 字段增减、格式变化都需要同步修改 sysmonit；多处重复解析逻辑

### 方案 B（推荐）：调用 `PtzDevicesCfg` API

在 sysmonit 中直接 `#include "ptzDevicesCfg.h"` 并调用 `g_ptzDevCfgApi.readList(list, true)`，一行代码取代所有手写解析。

- 优点：
  - 解析逻辑统一，YAML 格式变化时只需改 `ptzDevicesCfg.cpp`，所有消费方自动兼容
  - 支持 `enable`、`port` 等新字段，无需在 sysmonit 重复定义
  - `readFromFile` 使用 yaml-cpp 正规解析，字段顺序无关、容错性好
- 缺点：
  - sysmonit 需要链接 `yaml-cpp` 和编译 `ptzDevicesCfg.cpp`、`configCommDef` 等文件
  - 引入 `g_ptzDevCfgApi` 全局单例，构造时会 `initCheck()`（读文件 + 可能自动回写补全缺失字段），对 sysmonit 无副作用

**结论**：方案 B 更优。`PtzDevicesCfg::readList(list, true)` 每次从文件重新读取（`flag=true`），所以配置文件任何变动都能即时识别。

## 方案 B 实施步骤

### 1. 修改 CMakeLists.txt

- `find_package(yaml-cpp REQUIRED)`
- 添加源文件：`ptzDevicesCfg.cpp` (和它依赖的 `configCommDef.cpp` 如有)
- 添加 include 路径：`public/config/yamlConfig`、`public/config/configUtils`、`public/appLog`
- 链接 `yaml-cpp`

### 2. 修改 main.cpp

- 添加 `#include "ptzDevicesCfg.h"`
- 替换 `build_video_perf_json()` 中 50 行手写解析为：

```cpp
std::vector<PtzDeviceParam> pdevs;
g_ptzDevCfgApi.readList(pdevs, true);
```

- 后续使用 `dev.sn`、`dev.ip`、`(int)dev.type`、`dev.online`、`dev.with_hepu_ai_box` 即可，结构体字段完全匹配
- 同样替换 `get_devices_sub_json()` 和 `build_shm_info_json()` 中的手写 YAML 解析

### 3. 编译验证

`colcon build --packages-select sysmonit`，重启 sysmonit 节点验证 `/api/video` 返回正确的 streams。