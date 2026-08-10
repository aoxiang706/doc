---
name: 0x8C PTZ Control Mode
overview: 将 ptz_ctl_mode 控制从 0xE2 迁移到新的独立 0x8C 命令，0xE2 恢复为仅处理待机/开机。涉及 alink_system.h/.cpp 的结构体和处理函数修改，其余基础设施（CmdEnum.msg、PtzDetectCameraStatus.msg、ros_app.cpp、ai_main.cpp、0xEC 上报）保持不变。
todos:
  - id: revert-0xe2
    content: 恢复 0xE2：alink_system.h 结构体回退 + alink_system.cpp 移除 ptz_ctl_mode 解析
    status: completed
  - id: add-0x8c
    content: 新增 0x8C：alink_system.h 定义请求结构体 + alink_system.cpp 实现 handler + 注册命令
    status: completed
  - id: update-comment
    content: CmdEnum.msg 注释更新 from 0xE2 -> from 0x8C（可选）
    status: completed
  - id: build-verify
    content: 编译验证
    status: in_progress
isProject: false
---

# PTZ 控制模式迁移：0xE2 -> 0x8C

## 变更范围分析

当前 ptz_ctl_mode 嵌入在 0xE2 (set_work_mode) 中处理，协议更新后需要：

- **0xE2 恢复原样**：`mode(1B) + reverse[256]`，移除 ptz_ctl_mode 解析逻辑
- **新增 0x8C 命令**：独立处理 PTZ 控制模式设置，payload 含 SN 字段（64B 请求 / 4B 应答）
- **保留不变**：0xEC 上报（`alink_ptz_info_t.ptz_ctl_mode`）、全局变量 `g_ptz_ctl_mode`、ROS 消息定义、ros_app/ai_main 中的上报填充

## 0x8C 协议结构

请求 (C2 -> AGX, 64B):

```
| 字节 | Name          | Type      |
|------|---------------|-----------|
| 25   | sn            | uint8_t   |
| 1    | ptz_ctl_mode  | uint8_t   |
| 38   | reserver      | uint8_t   |
```

应答 (AGX -> C2, 4B):

```
| 字节 | Name   | Type    |
|------|--------|---------|
| 4    | result | int32_t |
```

## 参照模式

新 0x8C handler 参照现有 0x8A (`alink_ctrl_ptz`) 的模式：

- `alink_ptz_ctrl_req_t` 含 SN 字段，handler 根据 `g_ptzDevCfgApi.getFirstDevType()` 判断是否发送到激光引导节点
- 注册方式：`alink_register_cmd(&sAlinkCmd_..., 0x8c, 0, handler)`

## 改动文件清单（仅 2 个文件）

### 1. [alink_system.h](src/srv/alink/command/system/alink_system.h)

- **恢复 0xE2 结构体**（第 353-359 行）：
  - `alink_system_set_work_mode_t`：移除 `ptz_ctl_mode`，恢复 `reverse[256]`
- **新增 0x8C 结构体**（在 `alink_ptz_zoom_ctrl_req_t` 之后，约第 225 行）：

```cpp
#pragma pack(1)
typedef struct {
    char    sn[SLAVE_DEVICES_SN_LEN]; // PTZ/激光设备SN
    uint8_t ptz_ctl_mode;             // 0=AI自动, 1=全手动
    uint8_t reserver[38];
} alink_ptz_ctl_mode_req_t;
#pragma pack()
```

### 2. [alink_system.cpp](src/srv/alink/command/system/alink_system.cpp)

- **恢复 `alink_set_work_mode()`**（第 1449-1464 行）：
  - 删除 ptz_ctl_mode 解析逻辑（第 1449-1464 行新增的代码块）
  - 恢复日志为 `cmd->mode:%d`（不含 ptz_ctl_mode）
- **新增 handler 函数** `alink_set_ptz_ctl_mode()`：
  - 解析 `alink_ptz_ctl_mode_req_t`，提取 SN 和 ptz_ctl_mode
  - 更新 `g_ptz_ctl_mode`
  - 根据设备类型（激光 vs 普通 PTZ）调用 `ros_app_cmd_set` 或 `ros_app_pub_laser_cmd_set` 通知引导节点
  - 应答 result=0（成功）
- **新增 static 变量**：`static alink_cmd_list_t sAlinkCmd_ptzCtlMode = { 0 };`
- **注册命令**：在 `alink_system_init()` 中 0x8b 行之后加 `alink_register_cmd(&sAlinkCmd_ptzCtlMode, 0x8c, 0, alink_set_ptz_ctl_mode);`

### 不改动的文件

以下文件已有 ptz_ctl_mode 支持，无需修改：

- `CmdEnum.msg` -- CMD_ID=56 和 STATE_CODE 已定义（仅注释从 "from 0xE2" 改为 "from 0x8C"，可选）
- `PtzDetectCameraStatus.msg` -- ptz_ctl_mode 字段已存在
- `ros_app.cpp` -- callback 读取和 0xEC 上报填充已就绪
- `ai_main.cpp` -- 耐杰 0xEC 上报填充已就绪
- `alink_ptz_info_t`（0xEC）-- ptz_ctl_mode 字段保留不变

