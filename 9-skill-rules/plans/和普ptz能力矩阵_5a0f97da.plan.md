---
name: 和普PTZ能力矩阵
overview: 在代码中新增基于 PtzType 的和普 PTZ 外围能力查询（雨刷/除霜/透雾/日夜切换），附供应商能力表注释；生产仅 Z50+DMA35，不测距、不 C2 拦截。
todos:
  - id: add-cap-header
    content: 新增 hepuPtzCapabilities.h：能力结构体、静态表（Z50/DMA35 生产型号）、hepuPtzGetCapabilities()
    status: completed
  - id: update-ptz-type-comments
    content: 更新 ptzDevicesCfg.h 中三种和普 PtzType 注释，引用能力表
    status: cancelled
  - id: startup-log
    content: PtzDeviceHepu 启动时根据 type 打印 capabilities 摘要 LOG（不含 ranging）
    status: completed
  - id: build-verify
    content: colcon build ptz_service 验证编译
    status: in_progress
isProject: false
---

# 和普 PTZ 型号能力矩阵落地

## 生产范围确认（本次迭代）

现场**仅使用 Z50 与 DMA35**，且**未加装激光测距**。因此：

- **不做 C2 下发运行时拦截**（`alink_system.cpp` / `ctrlPtzLens` 保持现状）；Z50 与 DMA35 在除霜/透雾/日夜切换上能力一致，配错 `type` 的主要风险在 FOV 表与制冷热像分支，不在外围设备拦截。
- **不测距能力**：能力结构体与启动日志**暂不包含 ranging**；供应商表中测距列仅作头文件注释存档，待将来实装激光或接入 Z201/DMS15 再扩展。
- **不扩展 Z201/DMS15 枚举**（留 TODO 注释）。

## 供应商完整能力表（存档）


| 型号            | 雨刷  | 除霜  | 透雾  | 日夜切换(dayNightStatus) | 测距      |
| ------------- | --- | --- | --- | -------------------- | ------- |
| Z50III 制冷/非制冷 | Y   | Y   | Y   | Y                    | 无       |
| Z50IV 制冷/非制冷  | Y   | Y   | Y   | Y                    | 可选装 5km |
| DMA35         | Y   | Y   | Y   | Y                    | 有       |
| Z201          | N   | N   | Y   | Y                    | 可选装 1km |
| DMS15         | Y   | N   | Y   | Y                    | 无       |


## 生产型号映射（本次实现范围）


| `PtzType`             | 配置注释       | 生产对应    | 外围能力（雨刷/除霜/透雾/日夜） |
| --------------------- | ---------- | ------- | ----------------- |
| `PTZ_HEPU` (4)        | 三型 Z50 非制冷 | Z50 非制冷 | 全支持               |
| `PTZ_HEPU_COOLED` (6) | 四型 Z50 制冷  | Z50 制冷  | 全支持               |
| `PTZ_HEPU_DMA35` (7)  | DMA35 近程   | DMA35   | 全支持               |


Z50 制冷/非制冷差异在**热像通道与 FOV 表**，不在雨刷/除霜/透雾/日夜切换；三种生产 `PtzType` 外围能力相同，能力表可共用一行逻辑。

日夜切换：已实现 `dayNightStatus` 回读（`PtzDeviceHepu` → `getDayNightInfo` → `PtzStatus.day_night_status`）。

雨刷：SDK 有 `AUX_WIPER`，0x8b 未接入；能力表记录 `wiper=true`，控制链路 TODO。

## SDK `HVS_GetDeviceAbility` 与供应商表对照

接口：`[HVS_GetDeviceAbility](thirdpart/hepuSdk/include/module/idevicecfg.h)` → `[DeviceAbilityInfo_t](thirdpart/hepuSdk/include/datdefs.h)`（工程内**尚未调用**）。


| 供应商表项               | `DeviceAbilityInfo_t` 字段                      | 能否用 API 查「能力」 | 说明                                                                                                     |
| ------------------- | --------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------ |
| 雨刷                  | `wiper` (0=不支持, 1/2=支持)                       | **可以**        | 0 表示无雨刷硬件                                                                                              |
| 除霜/窗口加热             | `defogCtrl` (1=32板, 2=hisi)                   | **可以**（命名易混）  | SDK 注释写的是**除霜**，对应我们 `AUX_DEFROST` / cmd 12/13，**不是透雾**                                                |
| 透雾                  | 无独立 bool                                      | **不能**        | 仅有 `visibleLensType` 表示镜头是否支持**光学透雾**；我们 `setDefog` 走的是 `visibleCfgGet` 的 `mode`（彩色透雾三），属于运行时配置，不在能力集里 |
| 日夜切换 dayNightStatus | 无                                             | **不能**        | 能力集无 ICR/日夜字段；现状用 `visibleCfgGet` 读 `dayNightMode`/`dayNightStatus`（**状态回读**，非能力探测）                    |
| 测距                  | `laserRanging` (0=不支持), `laserMeasureSupport` | **可以**        | 本次不测距，不接入                                                                                              |


**结论**：你的判断基本正确——`HVS_GetDeviceAbility` **不能完整替代**供应商能力表，尤其**透雾**和**日夜切换**没有对应能力位；**窗口加热**可通过 `defogCtrl!=0` 间接判断，但字段名 `defogCtrl` 实际指除霜。

**与本次方案的关系**：

- 生产仅 Z50+DMA35 且外围能力一致 → **仍用 `PtzType` 静态表 + 注释** 即可，不增加连接后 `GetDeviceAbility` 调用（避免多一次 SDK 依赖与连接时序）。
- 将来接入 Z201/DMS15 或需自检时，可**混合模式**：静态表作默认 + 连接后 `HVS_GetDeviceAbility` 校验 `wiper`/`defogCtrl`/`laserRanging`/`cooledThermal`，透雾/日夜仍依赖配置回读或静态表。

### 1. 新增能力定义头文件（header-only）

新建 `[public/config/yamlConfig/hepuPtzCapabilities.h](public/config/yamlConfig/hepuPtzCapabilities.h)`：

```cpp
struct HepuPtzCapabilities {
    bool wiper;            // 雨刷（0x8b 未接入，仅文档）
    bool window_heat;      // 除霜 cmd 12/13
    bool defog;            // 透雾 cmd 10/11
    bool day_night_status; // dayNightStatus 回读
};

const HepuPtzCapabilities& hepuPtzGetCapabilities(PtzDeviceParam::PtzType type);
bool hepuPtzIsHepuType(PtzDeviceParam::PtzType type);
const char* hepuPtzTypeName(PtzDeviceParam::PtzType type); // 启动日志用
```

- 三种和普 `PtzType` 均返回 `{true, true, true, true}`
- 非和普类型返回全 `false`
- 文件顶部注释附供应商完整矩阵 + Z201/DMS15/ranging 待扩展说明

**不含** `HepuRangingSupport` 枚举（推迟到测距实装阶段）。

### 2. 更新 `ptzDevicesCfg.h` 枚举注释

在 `PTZ_HEPU` / `PTZ_HEPU_COOLED` / `PTZ_HEPU_DMA35` 行注明：

- 供应商型号对应关系
- 外围能力见 `hepuPtzCapabilities.h`
- 生产环境仅用 Z50 + DMA35

### 3. 启动时打印能力摘要

在 `[PtzDeviceHepu::loadPtzConfigBySn](ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp)` 成功后打一条纯 ASCII INFO：

```
PtzHepu capabilities(sn=..., type=PTZ_HEPU_DMA35): wiper=1 defog=1 win_heat=1 day_night=1
```

便于核对 `ptzDevicesCfg.yaml` 中 `type` 是否配对。

### 4. 本次不做

- C2 / alink 运行时能力拦截
- `alink_system.cpp`、`ctrlPtzLens` 中的 TODO 拦截钩子（无生产需求，避免噪音）
- 测距能力与 `controlLaser` 相关改动
- Z201/DMS15 新枚举
- 雨刷控制链路

## 数据流

```mermaid
flowchart LR
    yaml["ptzDevicesCfg.yaml type"]
    cfg["PtzDevicesCfg / PtzType"]
    cap["hepuPtzGetCapabilities"]
    log["ptz_service startup LOG_INFO"]
    yaml --> cfg --> cap --> log
```



## 验证

- `colcon build --packages-select ptz_service` 编译通过
- 启动 ptz_service，log 出现 capabilities 摘要（Z50/DMA35 均为四项全 1）

## 将来扩展（仅注释预留，不在本次实现）


| 触发条件            | 扩展内容                                                       |
| --------------- | ---------------------------------------------------------- |
| 接入 Z201/DMS15   | 新 `PtzType` + 能力表分行（Z201 无除霜，DMS15 无除霜）                    |
| 现场加装激光测距        | 加 `HepuRangingSupport` + 可选 yaml `laser_ranging_installed` |
| C2 需明确拒绝不支持 cmd | `hepuPtzGetCapabilities` 用于 alink / ctrlPtzLens 前置校验       |


