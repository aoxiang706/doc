---
name: ICR via Guider and Status
overview: ICR 控制改为经引导节点中转（复用跟踪源切换的 /cmd_set 模式），新增 ICR 状态上报（icr_mode + icr_value），通过 PtzDetectCameraStatus.msg 和 0xEC 协议回传 C2。
todos:
  - id: update-msg
    content: PtzDetectCameraStatus.msg 新增 icr_mode + icr_value 字段和枚举
    status: completed
  - id: add-icr-cmd-id
    content: CmdEnum.msg 新增 CMD_ID_SETTING_USER_PTZ_ICR=55
    status: completed
  - id: icr-via-cmdset
    content: alink_system.cpp 中 PTZ_CTRL_ICR 改为走 /cmd_set
    status: completed
  - id: update-0xec-icr
    content: alink_system.h 中 alink_ptz_info_t 新增 icr_mode + icr_value + 全局缓存声明
    status: completed
  - id: add-icr-globals
    content: alink_system.cpp 新增 g_icr_mode + g_icr_value 定义
    status: completed
  - id: rosapp-icr-fill
    content: ros_app.cpp 订阅回调更新 ICR 缓存 + 0xEC 填充
    status: completed
  - id: aimain-icr-fill
    content: ai_main.cpp 耐杰 0xEC 填充 icr_mode + icr_value
    status: completed
  - id: delete-pub-icr
    content: 删除 ros_app_pub_ptz_icr 函数（声明+定义）
    status: completed
  - id: build-verify
    content: 编译验证：先 skyfend_interfaces 再 ptz100_ros
    status: completed
isProject: false
---

# ICR 经引导节点控制 + 状态上报方案

## 一、需求变更总结

1. ICR 控制下发：从直接发 `/ptz_lens_cmd` 改为经引导节点（`/cmd_set`）
2. ICR 状态上报：引导节点发布 `icr_mode` + `icr_value`，嵌入式订阅后通过 0xEC 上报 C2
3. 复用已有的 `PtzDetectCameraStatus.msg` 和订阅回调机制

## 二、修改文件清单

### Step 1: PtzDetectCameraStatus.msg -- 新增 ICR 字段

文件: [ros_ws/src/srp100_message/skyfend_interfaces/msg/ptz_msg/PtzDetectCameraStatus.msg](ros_ws/src/srp100_message/skyfend_interfaces/msg/ptz_msg/PtzDetectCameraStatus.msg)

当前只有 `detect_camera_mode` + `detect_camera`，需要新增 `icr_mode` + `icr_value`：

```
# ICR mode enum
uint8 ICR_MODE_AUTO = 0      # ICR 自动模式
uint8 ICR_MODE_MANUAL = 1    # ICR 手动模式

# ICR value enum
uint8 ICR_VALUE_ON = 0       # ICR 开（夜视模式，黑白）
uint8 ICR_VALUE_OFF = 1      # ICR 关（白天模式，彩色）

uint8 icr_mode   # referring to ICR mode enum
uint8 icr_value  # referring to ICR value enum
```

### Step 2: CmdEnum.msg -- 新增 ICR 的 CMD_ID

文件: [ros_ws/src/srp100_message/skyfend_interfaces/msg/common_msg/CmdEnum.msg](ros_ws/src/srp100_message/skyfend_interfaces/msg/common_msg/CmdEnum.msg)

在 `CMD_ID_SETTING_USER_PTZ_CONTROLLER_DETECT_CAMERA = 54` 之后新增：

```
uint8 CMD_ID_SETTING_USER_PTZ_ICR = 55
```

### Step 3: alink_system.cpp -- ICR 下发改走 /cmd_set

文件: [src/srv/alink/command/system/alink_system.cpp](src/srv/alink/command/system/alink_system.cpp) 第 632~637 行

将 `PTZ_CTRL_ICR` case 从直接调用 `ros_app_pub_ptz_icr()` 改为通过 `/cmd_set` 发给引导节点：

```cpp
case PTZ_CTRL_ICR : {  // ICR 日夜切换，经引导节点
    if (!sendToLaserPtzGuidance) {
        uint8_t icr_mode = (req->icr <= 2) ? req->icr : 0;
        int32_t cmd_id = skyfend_interfaces::msg::CmdEnum::CMD_ID_SETTING_USER_PTZ_ICR;
        ros_app::ros_app_cmd_set(cmd_id, 0, sizeof(icr_mode), &icr_mode);
    }
} break;
```

### Step 4: alink_system.h -- 0xEC 结构体新增 ICR 字段 + 全局缓存

文件: [src/srv/alink/command/system/alink_system.h](src/srv/alink/command/system/alink_system.h)

(a) `alink_ptz_info_t` 从 `reserve[8]` 再拆出 2 字节（结构体总大小不变）：

```cpp
    uint8_t  detect_camera_mode;  // 跟踪源模式: 0=自动, 1=手动
    uint8_t  detect_camera;       // 当前跟踪源: bit0=可见光, bit1=红外
    uint8_t  icr_mode;            // ICR模式: 0=自动, 1=手动
    uint8_t  icr_value;           // ICR状态: 0=开(夜视/黑白), 1=关(白天/彩色)
    uint8_t  reserve[6];          // 剩余 6 字节
```

(b) 新增全局缓存变量声明（与 `g_detect_camera_*` 同组）：

```cpp
extern uint8_t g_icr_mode;   // 0=自动, 1=手动
extern uint8_t g_icr_value;  // 0=ICR开(黑白), 1=ICR关(彩色)
```

### Step 5: alink_system.cpp -- 新增全局缓存定义

在 `g_detect_camera` 定义之后新增：

```cpp
uint8_t g_icr_mode  = 0;
uint8_t g_icr_value = 0;
```

### Step 6: ros_app.cpp -- 订阅回调更新 + 0xEC 填充

(a) `ptzDetectCameraStatus_callback` 新增读取 `icr_mode` / `icr_value` 并写入全局缓存

(b) 和普 0xEC 上报（`cb_sub_hepuPtzInfo`）填充 `ptzInfo.icr_mode` / `ptzInfo.icr_value`

### Step 7: ai_main.cpp -- 耐杰 0xEC 上报填充

`ptz_pitch_azimuth()` 中新增：

```cpp
aptz.icr_mode  = g_icr_mode;
aptz.icr_value = g_icr_value;
```

### Step 8: 删除 ros_app_pub_ptz_icr 函数

ICR 不再直接发 `/ptz_lens_cmd`，删除 `ros_app_pub_ptz_icr()` 的声明和定义（`ros_app.h` + `ros_app.cpp`）。

### Step 9: 编译验证

先编译 `skyfend_interfaces`，再编译 `ptz100_ros`。