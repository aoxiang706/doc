# PTZ100_AGX 整体架构深度分析文档

> **文档版本**: V1.0  
> **生成日期**: 2024  
> **产品名称**: PTZ100_AGX (SRP100)  
> **平台**: NVIDIA Jetson AGX Xavier

---

## 目录

- [一、产品定位](#一产品定位)
- [二、整体技术栈](#二整体技术栈)
- [三、顶层目录结构](#三顶层目录结构)
- [四、核心架构：双模式运行](#四核心架构双模式运行)
- [五、src/ 源码层次结构](#五src-源码层次结构)
- [六、核心模块详解](#六核心模块详解)
  - [6.1 alg_app - AI引导算法核心](#61-alg_app---ai引导算法核心)
  - [6.2 ros_app - ROS2消息总线](#62-ros_app---ros2消息总线)
  - [6.3 alink - 自研通信协议框架](#63-alink---自研通信协议框架)
  - [6.4 eth_link - 以太网设备管理](#64-eth_link---以太网设备管理)
- [七、ROS2工作空间节点架构](#七ros2工作空间节点架构)
- [八、IoT设备SDK](#八iot设备sdk)
- [九、整体数据流](#九整体数据流)
- [十、配置与部署体系](#十配置与部署体系)
- [十一、关键设计模式与要点](#十一关键设计模式与要点)

---

## 一、产品定位

**PTZ100_AGX** 是 Skyfend（天巡）公司开发的**智能反无人机系统**，运行在 NVIDIA Jetson AGX 边缘计算平台上。系统内部代号为 **SRP100**（Skyfend Radar PTZ 100）。

### 核心功能

- **多设备接入管理**：接入多种雷达、PTZ光电吊舱、激光、干扰设备等
- **AI智能引导**：通过AI算法对无人机目标进行识别、跟踪和引导
- **统一指控**：通过C2（指控上位机）进行统一管理和指令下发
- **雷视融合**：融合雷达和视觉感知数据，提升目标检测精度

---

## 二、整体技术栈

| 组件 | 技术选型 |
|------|---------|
| **操作系统** | Ubuntu (ARM aarch64, Jetson AGX) |
| **主框架** | ROS2 Humble + C/C++17 混合编程 |
| **构建系统** | CMake (支持 ROS_SUPPORTED 编译开关) |
| **AI推理** | CUDA + TensorRT + OpenCV |
| **视频处理** | GStreamer (主流) / FFmpeg (旧版，已替换) |
| **通信协议** | 自研 alink 二进制协议 / TCP / UDP / MQTT / Protobuf / Modbus |
| **数据库** | SQLite3 (存储标定参数、设备配置) |
| **日志系统** | zlog |
| **媒体服务** | mediamtx (RTSP服务器) |

---

## 三、顶层目录结构

```
ptz100_agx/
├── src/              # 主程序源码（C/C++ 非ROS核心逻辑）
├── ros_ws/           # ROS2工作空间（各ROS节点）
├── iotDevices/       # IoT设备SDK（激光/PTZ/雷达等）
├── public/           # 公共库（MQTT/GStreamer/共享内存等）
├── thirdpart/        # 第三方库（TensorRT/OpenCV/FFmpeg等）
├── config/           # 运行时配置（日志/启动脚本/监控/NTP等）
├── docker/           # Docker运行脚本
└── doc/              # 设计文档
```

### 目录说明

- **src/**: 核心业务逻辑，C/C++混合，不依赖ROS但可编译为ROS节点
- **ros_ws/**: ROS2节点集合，包括设备驱动、融合算法、引导控制等
- **iotDevices/**: 第三方设备SDK封装（和普PTZ、激光、雷达等）
- **public/**: 跨模块公共库（日志、配置、网络、视频等）
- **thirdpart/**: 预编译的第三方库（aarch64架构）
- **config/**: 运行时配置文件、启动脚本、监控配置

---

## 四、核心架构：双模式运行

系统支持两种编译/运行模式，通过 `PTZ100_SUPPORTED_ROS` 宏控制：

### ROS模式（生产环境）

```
entry.cpp → rclcpp::init → ros_app → libmain()
主循环由 rclcpp executor spin() 驱动
```

**特点**：
- 作为ROS2节点运行，可与其他ROS节点通信
- 使用 `rclcpp::MultiThreadedExecutor` 多线程执行器
- 主入口：`ros_ws/src/ptz100_ros/src/entry.cpp`

### 裸机模式（调试/测试）

```
main() → while(!exit_app) { sleep(1); }
主循环由 while 循环驱动
```

**特点**：
- 独立运行，不依赖ROS环境
- 便于调试和单元测试
- 主入口：`src/main.c`

### 启动序列（main.c/libmain）

启动顺序严格，各模块按以下顺序初始化：

```c
1. skyfend_log_init()          // 日志初始化
2. common_init()               // 公共模块（sysport/storage/sqlite/配置）
3. alg_init()                  // AI算法模块 + 图像线程 + 目标队列
4. eth_link_init()             // 以太网链路管理（设备注册发现）
5. load_ptz()                  // PTZ摄像头加载（RTSP/SDK连接）
6. alink_init()                // Alink通信协议框架初始化
7. c2_network_init()           // C2指控网络连接
8. radar_network_init()        // 雷达网络连接
9. eth_link_server_init()       // 以太网Server监听（子设备接入）
10. sfl200_app_init()           // SFL200干扰设备管理
11. electronic_fence_app_init() // 电子围栏
12. ota_app_init()              // OTA升级服务
```

---

## 五、src/ 源码层次结构

```
src/
├── main.c                  # 程序入口
├── libmain.h               # ROS模式导出接口
├── inc/version.h           # 版本号定义
│
├── app/                    # 应用层（业务逻辑）
│   ├── alg_app/            # AI算法应用
│   │   ├── alg_app.cpp/h   # 算法主逻辑
│   │   └── queue/          # 目标队列管理
│   ├── ptz/                # PTZ摄像头控制
│   │   ├── ptz_app.cpp/h   # PTZ应用层
│   │   └── ffmpeg/         # 视频编解码（旧版，已替换）
│   ├── ros_app/            # ROS2消息总线适配器
│   │   └── ros_app.cpp/h   # ROS消息发布/订阅
│   ├── c2_network/          # C2指控网络
│   ├── radars_network/     # 雷达网络管理
│   ├── sfl200_app/         # SFL200/哨兵设备
│   ├── electronic_fence_app/ # 电子围栏
│   └── ota_app/            # OTA升级
│
├── srv/                    # 服务层（通用能力）
│   ├── alink/              # 核心通信协议框架
│   │   ├── alink.c/h       # 协议核心
│   │   ├── analysis/       # 报文解析
│   │   ├── command/        # 指令处理器（system/target/track等）
│   │   ├── upload/         # 数据上传打包
│   │   └── devices_pb/     # Protobuf定义
│   ├── eth_link/           # 以太网链路/设备管理
│   │   ├── eth_link.c/h    # 链路管理
│   │   ├── ptz_protocol/   # PTZ协议解析
│   │   ├── eth_protocol/   # 以太网协议
│   │   └── socket/         # TCP/UDP封装
│   ├── algs/               # 算法接口 + AI引导算法
│   │   ├── alg_interface.c/h # 算法接口
│   │   └── ai_alg/         # AI引导核心（ai_main.cpp）
│   └── log/                # 日志服务
│
└── common/                 # 基础层
    ├── sysport/            # 系统移植（任务/定时器/时间）
    ├── sqlite/             # SQLite标定数据
    ├── storage/            # 文件存储
    ├── config/             # 配置管理（YAML/SQLite）
    └── tools/              # 工具函数
```

---

## 六、核心模块详解

### 6.1 alg_app - AI引导算法核心

**位置**: `src/app/alg_app/alg_app.cpp`

这是系统最核心的业务模块，负责AI目标识别和PTZ引导控制。

#### 线程架构

`alg_init()` 创建5个工作线程：

| 线程名 | 功能 | 数据源/目标 |
|--------|------|------------|
| `ai_alg_thread` | 核心AI引导线程 | 从目标队列取目标 → `ai_alg_run7()` → PTZ引导 |
| `image_get_thread` | 可见光图像获取 | 共享内存(SHM)读帧 → 队列 |
| `image_push_thread` | 可见光图像推流 | 队列 → GstRtspClient RTSP推送 |
| `image_get_thread_infrared` | 红外图像获取 | 共享内存(SHM)读帧 → 队列 |
| `image_push_thread_infrared` | 红外图像推流 | 队列 → GstRtspClient RTSP推送 |

#### 目标数据流

```
雷达/融合节点 
    ↓ ROS callback
fusion_packet_ckb_handle() / ainode_packet_ckb_handle()
    ↓
ai_insert_target_to_head()  // 插入目标链表
    ↓
ai_alg_thread 消费目标
    ↓
ai_alg_run7()  // 核心引导算法
    ↓
send_ptz_control_xxx()  // 控制PTZ
```

#### 工作模式

- **标定模式** (`mark_status=1`): 调用 `ai_alg_calib()`，用于雷达-PTZ标定
- **引导模式** (`mark_status=0`): 调用 `ai_alg_run7()`，正常AI引导跟踪

#### 关键数据结构

```c
typedef struct alg_app_res {
    thread_task_t   *task_list;        // 线程任务列表
    int             task_list_num;     // 线程数量
    ai_input_targets_t ai_targets;     // AI目标链表
    module_target_headers_t modules_targets;  // 模块目标头
    bool release;                      // 释放标志
    void* pvalgtask;                   // AI任务消息队列
    void* fu_pvalgtask;                // 融合任务消息队列
} alg_app_res_t;
```

---

### 6.2 ros_app - ROS2消息总线

**位置**: `src/app/ros_app/ros_app.cpp/h`

`ros_app` 类是整个系统的 **ROS2消息中心**，充当非ROS C代码与ROS2生态的桥梁。

#### 订阅（Subscribe）的关键Topic

| Topic | 来源节点 | 用途 |
|-------|---------|------|
| `rvfusion_objs` | rvfusion_service | 雷视融合目标 |
| `fusionTargetObjs` | ptz100_fusion | 融合目标 |
| `sfl200_objs` | sfl200节点 | 哨兵设备目标 |
| `ptzGuidanceCmd` | ptz_guider_ctl | PTZ引导指令 |
| `ptzTrackCmd` | 引导节点 | PTZ跟踪指令 |
| `dhp120Status` | dhp100_tracker | 中程雷达状态 |
| `bph110Status/Param` | laser_service | 激光状态 |
| `hepuPtzInfo` | ptz_service | 和普PTZ设备信息 |

#### 发布（Publish）的关键Topic

| Topic | 接收方 | 用途 |
|-------|--------|------|
| `radar1/2/3/4Meas` | rvfusion_service | 雷达跟踪数据 |
| `radar1/2/3/4Dectect` | 融合节点 | 雷达检测数据 |
| `ptzStatus/ptzLensInfo` | 引导节点 | PTZ当前状态 |
| `aiMeas` | ptz100_fusion | AI感知结果 |
| `ptzRgbPic/ptzFraredPic` | 算法节点 | 可见光/红外图像 |
| `tracerP_droneid/remoteid` | 融合节点 | RF侦测目标 |
| `devlist` | C2 | 设备列表 |
| `sysHeartbeat` | 系统监控 | 系统心跳 |

#### 回调注册机制

```cpp
// 业务模块可注册ROS订阅的数据回调
ros_register_subscribe_cbk(ROS_FUSION_DATA, fusion_packet_ckb_handle);
ros_register_subscribe_cbk(ROS_AI_DATA, ainode_packet_ckb_handle);
ros_register_subscribe_cbk(ROS_DEV_ATTR_DATA, devattr_packet_ckb_handle);
```

---

### 6.3 alink - 自研通信协议框架

**位置**: `src/srv/alink/`

Alink是整个系统的**私有二进制通信协议框架**，负责AGX与雷达、C2、探测设备之间的通信。

#### 目录结构

```
alink/
├── alink.c/h              # 框架核心（注册/发送/接收）
├── alink_defines.h        # 设备ID枚举（雷达/C2/SRP100/SFL200等）
├── analysis/              # 报文解析
│   ├── alink_order.c      # 指令解析
│   ├── alink_recv.c       # 接收处理
│   └── alink_socket.c     # Socket封装
├── check/                 # 校验和
│   ├── alink_check.c      # 协议校验
│   └── checksum.c         # 校验算法
├── command/               # 指令处理器
│   ├── system/            # 系统指令（心跳/配置/设备信息）
│   ├── target/            # 目标上报
│   ├── track/             # 跟踪控制
│   ├── efence/            # 电子围栏
│   ├── sentry/            # 哨兵设备
│   ├── stp120/            # STP120设备
│   ├── tracerMatrix/      # TracerMatrix干扰矩阵
│   └── bph110/            # BPH110激光
├── upload/                # 数据上传打包
│   ├── alink_package.c     # 打包逻辑
│   └── alink_upload.c     # 上传接口
└── devices_pb/radar/      # 雷达Protobuf定义
    ├── radar.proto        # 雷达消息定义
    └── broadcast.proto    # 广播消息定义
```

#### 设备ID体系（alink_dev_id_t）

| 设备ID | 宏定义 | 说明 |
|--------|--------|------|
| 3 | `ALINK_DEV_ID_RADAR` | 雷达 |
| 4 | `ALINK_DEV_ID_PC` | PC端 |
| 6 | `ALINK_DEV_ID_C2` | 指控上位机 |
| 12 | `ALINK_DEV_ID_SRP100` | 本机（AGX） |
| 0x0d | `ALINK_DEV_ID_SFL200` | 哨兵干扰设备 |
| 0x1f | `ALINK_DEV_ID_BPH110` | 激光 |
| 0x22 | `ALINK_DEV_ID_TRACERP` | TracerP侦测设备 |
| 0x20 | `ALINK_DEV_ID_STP120` | STP120设备 |

#### 核心API

```c
// 初始化
int32_t alink_init(void);

// 注册指令处理器
int32_t alink_register_cmd(alink_cmd_list_t *psCmdList, 
                           uint8_t byOrder, 
                           uint16_t wPayloadLen,
                           void (*pv_cmd_task)(alink_payload_t *psPayload, 
                                               alink_resp_t *psResp));

// 上传数据包
int32_t alink_upload_package(alink_package_list_t *psPackage, void *psImport);

// 上传目标信息
int32_t alink_upload_tracked(void *psObjTrack);
int32_t alink_upload_detected(void *psObjDetect);
```

---

### 6.4 eth_link - 以太网设备管理

**位置**: `src/srv/eth_link/`

管理所有通过以太网接入的子设备，提供统一的设备发现、连接、通信能力。

#### 功能特性

- **TCP客户端/服务端**: 支持主动连接和被动监听
- **UDP Socket**: 支持UDP通信
- **设备在线状态管理**: 维护设备在线/离线状态
- **设备列表维护**: `get_devices_online_info()` 获取在线设备
- **PTZ协议解析**: `ptz_protocol/` 解析PTZ控制协议
- **RTK调试器**: `rtk_debuger/` RTK定位调试

#### 默认网络参数

| 参数 | 值 | 说明 |
|------|-----|------|
| AGX自身IP | `192.168.1.161` | AGX设备IP |
| AGX端口 | `18070` | 默认服务端口 |
| PTZ接入IP | `192.168.2.163` | PTZ设备IP |
| PTZ端口 | `19005` | PTZ通信端口 |
| PTZ RTSP主码流 | `rtsp://192.168.2.4:554/channel=0,stream=0` | 可见光主码流 |
| PTZ RTSP子码流 | `rtsp://192.168.2.4:554/channel=0,stream=1` | 可见光子码流 |
| PTZ RTSP红外 | `rtsp://192.168.2.4:554/channel=1,stream=0` | 红外码流 |

#### 核心API

```c
// 初始化
int eth_link_init(void);
int eth_link_server_init(void);

// 注册设备类型
int eth_link_add_type(uint16_t type, uint8_t net, uint8_t max, 
                      eth_link_cbk_t* (*ps_init)(eth_link_user_t *psUser));

// 获取设备信息
int get_devices_online_info(void *pdevlist, int exclude_devid);
int find_device_info_by_sn(eth_link_device_info_t *devinfo, const char *dest_sn);
```

---

## 七、ROS2工作空间节点架构

**位置**: `ros_ws/src/`

### 节点列表

| 节点名 | 功能 | 状态 |
|--------|------|------|
| `ptz100_ros` | **主节点**，包含libmain，消息总线 | ✅ 运行中 |
| `ptz_service` | PTZ设备驱动（和普Hepu PTZ） | ✅ 运行中 |
| `laser_service` | 激光设备驱动（He BPH110） | ✅ 运行中 |
| `br100a` | BR100A短程小雷达驱动 | ✅ 运行中 |
| `gnss_b3` | GNSS-B3定位模块驱动 | ✅ 运行中 |
| `spoofer` | 干扰设备驱动 | ✅ 运行中 |
| `spoofer_fixed_point` | 定点干扰 | ✅ 运行中 |
| `electronic_fence` | 电子围栏（TracerAir侦测） | ✅ 运行中 |
| `sysmanager` | 系统管理（进程监控/健康检查） | ✅ 运行中 |
| `ptz100_ai` | AI感知节点 | ⚠️ 目录存在，暂空 |
| `ptz100_fusion` | 雷视融合节点 | ⚠️ 目录存在，暂空 |
| `ptz100_guide_ai` | AI引导节点 | ⚠️ 目录存在，暂空 |
| `radar_target_simulation` | 雷达目标仿真测试 | ✅ 测试用 |

### Launch文件启动的节点

**文件**: `ros_ws/launch/ptz100_ros.launch`

```xml
<launch>
    <node pkg="ptz100_ros" exec="ptz100_ros" output="screen"/>
    <node pkg="rvfusion_service" exec="rvfusion_service" output="screen"/>
    <node pkg="multiple_radar_calibration" exec="multiple_radar_calibration" output="screen"/>
    <node pkg="ptz_guider_ctl" exec="ptz_guider_ctl" output="screen"/>
    <node pkg="dhp100_link" exec="dhp100_link" output="screen"/>
    <node pkg="dhp100_tracker" exec="dhp100_tracker" output="screen"/>
</launch>
```

**说明**:
- `ptz100_ros`: 主逻辑节点
- `rvfusion_service`: 雷视融合服务（外部ROS包）
- `multiple_radar_calibration`: 多雷达标定
- `ptz_guider_ctl`: PTZ引导控制（外部ROS包）
- `dhp100_link`: DHP100中程雷视链路
- `dhp100_tracker`: DHP100目标跟踪

---

## 八、IoT设备SDK

**位置**: `iotDevices/`

### SDK列表

| SDK | 设备类型 | 功能 |
|-----|---------|------|
| `laserHeSDK` | He系列激光测距仪 | 激光测距、目标识别 |
| `memsBr100aSDK` | MEMS BR100A微型雷达 | 短程雷达数据采集 |
| `ptzHepuSDK` | 和普（Hepu）PTZ吊舱 | PTZ控制、视频流获取 |
| `tempSensorPT100SDK` | PT100温度传感器 | 温度监测 |

### SDK结构

每个SDK通常包含：
- `include/`: 头文件
- `src/`: 实现文件
- `example/`: 示例代码
- `CMakeLists.txt`: 构建配置
- `README.md`: 使用说明

---

## 九、整体数据流

### 系统数据流图

```
                    ┌─────────────┐
                    │  C2 上位机   │ TCP/alink协议
                    └──────┬──────┘
                           │ c2_network
                           ▼
┌──────────┐    alink   ┌──────────────────────────────────────────┐
│  雷达网络 │──────────→│                  AGX                      │
│(br100a等) │           │                                          │
└──────────┘           │  ┌──────────┐    ROS Topic    ┌────────┐ │
                       │  │ ros_app  │◄───────────────►│ 融合节 │ │
┌──────────┐   RTSP    │  │  (消息   │                 │ 点等   │ │
│ PTZ吊舱  │──────────→│  │  总线)   │                 └────────┘ │
│(可见光+  │  SDK/TCP  │  └────┬─────┘                            │
│ 红外)    │           │       │ 共享内存/ROS                     │
└──────────┘           │  ┌────▼─────┐                            │
                       │  │ alg_app  │ ai_alg_run7() PTZ引导       │
┌──────────┐  alink    │  │ (AI算法) │──────────────────────────→ │ PTZ控制指令
│SFL200干扰│──────────→│  └──────────┘                            │
│ 设备     │           │                                          │
└──────────┘           │  ┌──────────┐                            │
                       │  │  alink   │──────────→ 雷达/C2上报     │
┌──────────┐  USB/UART │  │ 协议层   │                            │
│ TracerP/ │──────────→│  └──────────┘                            │
│电子围栏  │           └──────────────────────────────────────────┘
└──────────┘
```

### 关键数据流说明

1. **雷达数据流**:
   ```
   雷达设备 → eth_link → alink → ros_app → ROS Topic → 融合节点
   ```

2. **PTZ控制流**:
   ```
   AI算法 → send_ptz_control_xxx() → eth_link → PTZ设备
   ```

3. **图像数据流**:
   ```
   PTZ设备 → RTSP流 → image_get_thread → 共享内存 → AI算法
   ```

4. **C2指令流**:
   ```
   C2上位机 → c2_network → alink → 指令处理器 → 业务模块
   ```

---

## 十、配置与部署体系

### 配置文件

| 配置文件 | 路径 | 用途 |
|---------|------|------|
| zlog配置 | `config/log/*.conf` | 各模块日志级别和文件路径 |
| 开机自启 | `config/boot/auto_boot_app.sh` | 系统自启动脚本 |
| monit监控 | `config/monit/monitrc` | 进程守护配置 |
| NTP时间同步 | `config/ntp/ntp.conf` | 对时配置 |
| SQLite数据库 | `config/sqlite/sqlite.db` | 设备类型/标定参数 |
| OTA升级 | `config/tools/ota_app/` | 在线升级脚本 |

### 版本命名规则

版本格式：`PTZ100-ROS-Vxx3.xx2.xx1`

- **xx1**: 同一功能下的优化迭代
- **xx2**: 重大功能增加和致命bug修复
- **xx3**: 重大架构变更

**当前最新版本**: V2.0.1.13 (2024-05-28)

### 打包脚本

使用 `config/tools/publish-version.sh` 打包，生成文件名格式：
```
ptz100_agx-PTZ100-ROS-Vxx3.xx2.xx1-date.tar.gz
```

---

## 十一、关键设计模式与要点

### 1. 双编译模式

通过 `#ifdef PTZ100_SUPPORTED_ROS` 宏区分ROS模式和裸机模式，同一套代码两种运行形态。

**优势**:
- 便于调试（裸机模式不依赖ROS环境）
- 便于单元测试
- 生产环境使用ROS模式，便于集成

### 2. 消息总线模式

`ros_app` 作为C代码与ROS的唯一边界，所有跨进程通信通过ROS topic。

**优势**:
- 解耦ROS层与业务层
- 便于扩展新的ROS节点
- 统一的消息格式

### 3. 共享内存传图

使用 `ShmTransferFrame` 类进行AI节点与alg_app之间的零拷贝图像传输（替代旧的POSIX shm_open方式）。

**优势**:
- 零拷贝，性能高
- 支持多进程共享
- 自动帧同步

### 4. 任务队列模式

使用 `sysport_task` 基于POSIX消息队列（mq）实现异步任务分发。

**优势**:
- 解耦生产者和消费者
- 支持优先级队列
- 线程安全

### 5. 目标链表管理

`ai_insert_target_to_head()` 将各种来源的目标插入链表，`ai_alg_thread` 统一消费。

**优势**:
- 统一的目标管理
- 支持多源融合
- 便于扩展新的目标源

### 6. 回调注册机制

`ros_register_subscribe_cbk()` 允许业务模块注册ROS订阅的数据回调，解耦ROS层与业务层。

**优势**:
- 动态注册回调
- 支持多个回调函数
- 便于模块化设计

### 7. 设备抽象层

通过 `eth_link` 统一管理所有以太网设备，提供统一的设备发现、连接、通信接口。

**优势**:
- 设备类型可扩展
- 统一的设备管理
- 便于设备热插拔

---

## 附录

### A. 关键文件索引

| 文件 | 路径 | 说明 |
|------|------|------|
| 主入口 | `src/main.c` | 程序入口，启动序列 |
| ROS入口 | `ros_ws/src/ptz100_ros/src/entry.cpp` | ROS模式入口 |
| AI算法 | `src/app/alg_app/alg_app.cpp` | AI引导核心 |
| ROS适配 | `src/app/ros_app/ros_app.cpp` | ROS消息总线 |
| Alink协议 | `src/srv/alink/alink.c` | 通信协议核心 |
| PTZ控制 | `src/srv/eth_link/ptz_protocol/ptz_control.c` | PTZ控制协议 |

### B. 关键宏定义

| 宏 | 说明 |
|----|------|
| `PTZ100_SUPPORTED_ROS` | 启用ROS模式编译 |
| `USE_SHM_TRANSFER_API` | 使用共享内存API |
| `USE_NEW_VIDEO_API` | 使用新的视频API（GStreamer） |
| `MONITOR_GUIDE_PROCESS` | 监控引导过程 |
| `MONITOR_AUTEL_AI` | 监控Autel AI |

### C. 版本历史

详见 `release-note.txt` 文件。

---

## 总结

PTZ100_AGX是一个复杂的边缘计算系统，集成了雷达、PTZ、激光、干扰设备等多种硬件，通过AI算法实现智能反无人机功能。系统采用ROS2作为消息总线，C/C++混合编程，支持双模式运行，具有良好的模块化和可扩展性。

**核心特点**:
- ✅ 多设备统一管理
- ✅ AI智能引导
- ✅ 雷视融合感知
- ✅ 统一指控接口
- ✅ 模块化设计
- ✅ 双模式运行

---

**文档维护**: 请根据代码变更及时更新本文档。


 