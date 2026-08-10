---
name: PTZ rotation API latency test (minimal)
overview: 零侵入测量和普 PTZ 2 个生产实际在用的转动 API（controlPtz / setPositionXY）从应用层调用到 SDK 函数返回的耗时，并配套解析 hepu_ptz_sdk.log 的 HVS_xxx() begin/end 时间戳交叉对齐。不修改任何生产代码。
todos:
  - id: bench_tool
    content: 新增独立 bench 可执行 ros_ws/src/ptz_service/tools/ptz_latency_bench.cpp（命令行 + CSV 输出 + 末尾 P50/P90/P99）
    status: pending
  - id: cmake_register
    content: 在 ros_ws/src/ptz_service/CMakeLists.txt 注册 ptz_latency_bench 可执行
    status: pending
  - id: sdk_log_parser
    content: 新增 Python 脚本 ros_ws/src/ptz_service/tools/parse_hepu_sdk_log.py 解析 hepu_ptz_sdk.log
    status: pending
  - id: build_verify
    content: colcon build --packages-select ptz_service 编译，跑 bench + 解析脚本交叉对齐验证
    status: pending
isProject: false
---

# PTZ 转动 API 耗时测量（极简零侵入版）

## 1. 测量范围（用户已确认）

经过对 [ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp](ros_ws/src/ptz_service/src/ptzDevice/ptzDeviceHepu.cpp) 实际调用点 grep 验证，**业务代码只用了下面 2 个 API**：


| API（应用层）                     | 底层厂商 SDK          | 业务调用点                                             |
| ---------------------------- | ----------------- | ------------------------------------------------- |
| `HepuPtzCtrl::controlPtz`    | `HVS_ControlMove` | `ctrlPtzMotion` 行 919-959（方向 0~8，move=true/false） |
| `HepuPtzCtrl::setPositionXY` | `HVS_PositionXY`  | `ctrlPtzGuidance` 行 880（绝对角度引导）                   |


`setPositionX` / `setPositionY` 在生产代码里 **0 调用**（只在 SDK 头/example 出现），不测。

声明见 [iotDevices/ptzHepuSDK/include/ptz_hepu_ctrl.h](iotDevices/ptzHepuSDK/include/ptz_hepu_ctrl.h) 第 43、46 行；实现见 [iotDevices/ptzHepuSDK/src/ptz_hepu_ctrl.cpp](iotDevices/ptzHepuSDK/src/ptz_hepu_ctrl.cpp) 第 325、746 行。

`**controlPtz` 的两面性**：业务里是"启动 + 间隔 + 停止"成对使用（如行 924 `controlPtz(1, true, ...)` 启动向上转，停止时调 `controlPtz(0, false, ...)` 或同方向 `move=false`）。两次调用语义不同（"开始"vs"停止"），bench 应**分开计数**，得到 `controlPtz_start` 和 `controlPtz_stop` 两个分桶。

## 2. 关于"调用 → 命令到达 PTZ"的精确含义

用户原话：

> "可以通过 hepu_ptz_sdk.log 中收到调用时间为到达和普 PTZ 设备时间？"

需要先澄清：

- `hepu_ptz_sdk.log` 是和普 SDK 自身在 [iotDevices/ptzHepuSDK/src/ptz_hepu_ctrl.cpp](iotDevices/ptzHepuSDK/src/ptz_hepu_ctrl.cpp) 第 118 行通过 `HVS_SetLogLevel(... "/home/skyfend/log/hepu_ptz_sdk.log" ...)` 开启的，毫秒级时间戳
- 当前生产配置 `level=1` (INTF)，效果是"≥INTF 的全部级别（含 DEBUG/INFO/WARN/ERROR）都输出"，已确认 `HVS_xxx() begin / end` 这种 DEBUG 行实际在落盘
- 严格说，SDK 日志里的时间戳记的是 **SDK 进程内部时刻**，不是 PTZ 设备时钟
- 但 `HVS_xxx() begin → HVS_xxx() end` 时间差就是关键观测：
  - 如果 SDK 是同步等 PTZ 应答（最可能）：`end - begin` 包含 *单程网络 + PTZ 内部处理 + 单程网络*，可作为"调用 → PTZ 已收到并应答"的合理代理
  - 如果是 fire-and-forget：`end - begin` 只反映本地 socket write，与 PTZ 是否收到关系不大
- 厂商 .so 闭源没法直接看代码，**实测就能验证**：
  - 若中位数稳定在 1~3 ms：fire-and-forget
  - 若在 30~200 ms：同步等 ack（这个数也接近 ICMP ping 192.168.2.4 的往返时间）

这正好是本次测试的副产物之一。

## 3. 实现方案（零侵入）

```mermaid
flowchart LR
    bench[ptz_latency_bench<br/>独立可执行] -->|chrono 打点| call[HepuPtzCtrl::controlPtz<br/>etc]
    call --> sdk[HVS_ControlMove<br/>HVS_PositionX/Y/XY]
    sdk --> ptz[(和普 PTZ)]
    sdk -.写日志.-> log[(hepu_ptz_sdk.log)]
    bench -->|CSV| out1[/tmp/ptz_lat.csv]
    log -->|parse_hepu_sdk_log.py| out2[/tmp/sdk_lat.csv]
    out1 -.对齐验证.- out2
```



不修改任何生产代码，新增两个独立工具：

### 3.1 bench 可执行：[ros_ws/src/ptz_service/tools/ptz_latency_bench.cpp](ros_ws/src/ptz_service/tools/ptz_latency_bench.cpp)

参考 [iotDevices/ptzHepuSDK/example/test.cpp](iotDevices/ptzHepuSDK/example/test.cpp) 的最小骨架，直接构造 `HepuPtzCtrl ctrl;` + `ctrl.startup(ip);`（不走 `HepuPtz` 大封装，免起视频流/共享内存）。

命令行参数：

- `--ip 192.168.2.4`（必填）
- `--api {controlPtz | setPositionXY | both}`（默认 both，依次跑两个 API）
- `--count 100`（每个 API 的采样数，默认 100）
- `--interval-ms 1500`（两次调用间隔，绝对定位至少留够 PTZ 走完上一动作；速度模式可短一些）
- `--csv /tmp/ptz_latency.csv`（默认）
- `--pan-range -30,30` `--tilt-range -15,15`（绝对定位的角度扫描范围，避免撞限位）
- `--speed 50`（速度参数，setPositionXY 范围 0-200；controlPtz 范围 1-200）

行为：

1. 构造 `HepuPtzCtrl ctrl; ctrl.startup(ip)`，等 `ctrl.isReallyConnected()` 为 true（最多等 10s，超时退出）
2. `**setPositionXY` 模式**：循环 N 次
  - 在 pan/tilt 区间内锯齿扫描出下一目标角 (px, ty)
  - `t0 = steady_clock::now(); ctrl.setPositionXY(px, ty, speed); t1 = steady_clock::now();`
  - 记录 `{seq, t0_ms, "setPositionXY", px, ty, ret, call_dur_us}`
  - sleep `interval-ms`
3. `**controlPtz` 模式**：循环 N 次（每次包含一对 start/stop，得到 2*N 条样本）
  - 选下一方向 dir ∈ {1,2,3,4} 轮换
  - `t0_a = ...; ctrl.controlPtz(dir, true, speed, speed); t1_a = ...;`  → 记 `controlPtz_start`
  - sleep 600ms 让 PTZ 转一会
  - `t0_b = ...; ctrl.controlPtz(0, false, 1, 1); t1_b = ...;`           → 记 `controlPtz_stop`
  - sleep `interval-ms`
4. 末尾输出 CSV + stdout 摘要：

```
api                       count  avg_us   p50_us  p90_us  p99_us  max_us
HepuPtzCtrl::controlPtz_start  100   2150     2030    3120    4500    6200
HepuPtzCtrl::controlPtz_stop   100   2080     1990    2950    4300    5800
HepuPtzCtrl::setPositionXY     100  34250    32100   45800   58200   72100
```

CSV 列：`seq,t0_unix_ms,api,p1,p2,p3,p4,ret,call_dur_us`（不用的参数列留空）

### 3.2 解析脚本：[ros_ws/src/ptz_service/tools/parse_hepu_sdk_log.py](ros_ws/src/ptz_service/tools/parse_hepu_sdk_log.py)

Python3 标准库（re / argparse / csv / datetime / collections）。

用法：

```bash
python3 parse_hepu_sdk_log.py /home/skyfend/log/hepu_ptz_sdk.log \
    --apis HVS_ControlMove HVS_PositionXY \
    --since "2026-05-19 09:00:00" \
    --csv /tmp/sdk_lat.csv
```

算法：

1. 逐行 regex：`^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+\w+\s+\w+\s+T:([0-9A-F]+)\s+(HVS_\w+)\(\)\s+(begin|end)\b`
2. 用 `dict[(thread_id, api_name)] -> begin_ts` 维护"待 end"队列
3. 遇到 `end`，与 `begin` 配对，计算 `dur_ms = (end - begin) ms`
4. 按 API 聚合，输出 P50/P90/P99/avg/max + 写 CSV

CSV 列：`begin_unix_ms,end_unix_ms,thread_id,api,sdk_dur_ms`

### 3.3 CMake 接入

[ros_ws/src/ptz_service/CMakeLists.txt](ros_ws/src/ptz_service/CMakeLists.txt)：

```cmake
add_executable(ptz_latency_bench tools/ptz_latency_bench.cpp)
target_link_libraries(ptz_latency_bench ptz_hepu)
target_include_directories(ptz_latency_bench PRIVATE
    ${CMAKE_SOURCE_DIR}/../../iotDevices/ptzHepuSDK/include)
install(TARGETS ptz_latency_bench DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS tools/parse_hepu_sdk_log.py DESTINATION lib/${PROJECT_NAME})
```

具体的依赖路径以现有 CMakeLists.txt 中 `ptz_hepu` 库的 alias 名为准，编译时若 link 失败再细调。

## 4. 文件改动清单

新增（仅 3 个）：

- [ros_ws/src/ptz_service/tools/ptz_latency_bench.cpp](ros_ws/src/ptz_service/tools/ptz_latency_bench.cpp)
- [ros_ws/src/ptz_service/tools/parse_hepu_sdk_log.py](ros_ws/src/ptz_service/tools/parse_hepu_sdk_log.py)
- 修改 [ros_ws/src/ptz_service/CMakeLists.txt](ros_ws/src/ptz_service/CMakeLists.txt)：注册 bench 可执行 + 安装脚本

不修改：

- HepuPtzCtrl / HepuPtz（生产代码不动）
- ptz_service main / RosService / PtzDeviceHepu（生产代码不动）
- 任何配置文件

## 5. 验证步骤

```bash
# (1) 编译
cd ~/workspace/ptz100_agx/ros_ws
colcon build --packages-select ptz_service --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo

# (2) 跑 bench (PTZ 在线时执行; 注意 ptz_service 不能同时连同一个 PTZ)
sudo monit unmonitor ptz_service       # 防止现有 ptz_service 抢占连接
killall -9 ptz_service 2>/dev/null
: > /home/skyfend/log/hepu_ptz_sdk.log  # 清空 SDK 日志, 让本次 bench 的日志干净

source install/setup.bash

# 一次性跑两个 API (默认 both)
ros2 run ptz_service ptz_latency_bench \
    --ip 192.168.2.4 --count 100 --csv /tmp/ptz_lat.csv

# 或单独测一个
ros2 run ptz_service ptz_latency_bench --ip 192.168.2.4 --api setPositionXY --count 100 --csv /tmp/ptz_lat_setXY.csv
ros2 run ptz_service ptz_latency_bench --ip 192.168.2.4 --api controlPtz   --count 100 --csv /tmp/ptz_lat_ctrlPtz.csv

# (3) 解析 SDK 日志做交叉对齐
python3 src/ptz_service/tools/parse_hepu_sdk_log.py \
    /home/skyfend/log/hepu_ptz_sdk.log \
    --apis HVS_ControlMove HVS_PositionXY \
    --csv /tmp/sdk_lat.csv

# (4) 恢复生产
sudo monit monitor ptz_service
```

## 6. 预期与解读

预期数量级（aarch64 千兆有线，PTZ 同网段）：


| API                    | bench `call_dur_us` | SDK `sdk_dur_ms` | 含义            |
| ---------------------- | ------------------- | ---------------- | ------------- |
| controlPtz_start/_stop | 1k ~ 10k µs         | 1 ~ 5 ms         | 速度命令通常更快      |
| setPositionXY          | 30k ~ 200k µs       | 30 ~ 200 ms      | 若 SDK 同步等 ack |


判读规则：

- bench `call_dur_us / 1000` ≈ SDK `sdk_dur_ms` ⇒ 我们应用层与 SDK 内部时延一致，几乎无冗余开销
- SDK `sdk_dur_ms` ≈ ping RTT (`ping -c 100 192.168.2.4` 的 avg) ⇒ SDK 是同步等 ack；end 时刻 ≈ "PTZ 收到并应答"
- SDK `sdk_dur_ms` < 5 ms 且远小于 ping RTT ⇒ SDK 是 fire-and-forget；end 时刻仅代表 SDK 把包写入本地内核，不能等同于 PTZ 收到

## 7. 不在范围内

- 厂商 SDK 内部 TCP send 与 PTZ ack 的细分（闭源）
- PTZ 端命令排队 / 内部处理时延
- 镜头 / 聚焦 / 激光 / 跟踪 / 预置位 等非"转动" API
- 应用层 `PtzDeviceHepu::ctrlPtz*` 业务层耗时（用户已明确不需要）
- 不动任何生产代码，跑完即弃；如后续要常态化在线监测再评估是否做埋点

