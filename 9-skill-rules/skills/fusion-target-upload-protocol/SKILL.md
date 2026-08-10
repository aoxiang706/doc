---
name: fusion-target-upload-protocol
description: >-
  融合目标数据上报协议全景图，覆盖 SSF(0xEA)、SRP(0xE6)、Sentry/SFL200(0xE1) 三条
  AGX→C2 上报路径的代码入口、序列化回调、结构体差异和互斥关系。
  适用于调试融合数据丢包、C2 显示异常、协议新增/修改、设备类型判断，以及排查
  因大包导致的 TCP 阻塞或 mutex 竞争问题。
---

# 融合目标上报协议 — 完整梳理

## 协议总览

| 设备类型 | 协议 ID | 上报函数 | 序列化回调 | 注册文件 | 每项字节 |
|---------|--------|---------|-----------|---------|---------|
| **SRP** (SRP100/200/210) | **0xE6** | `alink_upload_new_fusion_target` | `track_pkg_fusion_target_new` | `alink_target.c` | ~134B (`fusion_object_items_net_t`) |
| **SSF** (SSF100/200/210) | **0xEA** | `alink_upload_efence_fusion_data` | `efence_fusion_data_proc` | `alink_efence.cpp` | ~286B (`alink_fusion_obj_item_t`) |
| **Sentry/SFL200** | **0xE1** | `alink_transfer_sfl200_to_c2` | `transfer_sfl200_package_c2` | `alink_sentry.cpp` | ~286B (`fusion_object_items_t`，与 0xEA 字节布局一致) |

> **注意：** SFL200 的 `fusion_object_items_t` 定义在 `sfl200_embed_api.h`（扁平结构，~286B），与 SSF 的 `alink_fusion_obj_item_t` 字节布局完全一致。`embed_api.h` 中也有一个同名的 `fusion_object_items_t`（嵌套结构，~544B，含 radar/ptz/spectrum 等子结构），但那是用于内部处理，不是线上格式。

三条路径**互斥**——同一时刻只有一条路径实际发送数据，由 `get_agx_device_type()` 和 `s_efence_init_flag` / `s_is_sfl200_online` 运行时决定。

## 路径 1: SRP → 0xE6

```
/fusiontg_objs_c2 (ROS topic, FusionTargetPack)
  → fusiontg_callback                      (ros_app.cpp ~434)
    → sub_cbk_objs[ROS_FUSION_NEW_DATA].cbk (ros_app.cpp ~489)
      → fusion_packet_ckb_handle            (alg_app.cpp ~277)
        → sysport_task_func                 [异步 → 独立工作线程]
          → fusion_thread_handler           (alg_app.cpp ~248)
            → alink_upload_new_fusion_target (alink_target.c ~461)
              → alink_upload_package → track_pkg_fusion_target_new
                → mutex → TCP 发送, msgid=0xE6
```

### 关键守卫

```c
// alink_target.c — SSF 和 SFL200 在线时跳过
int32_t alink_upload_new_fusion_target(void *psObjTargetInfo)
{
    if (ALINK_DEV_ID_SSF100 == s_agx_device_type ||
        ALINK_DEV_ID_SSF200 == s_agx_device_type ||
        ALINK_DEV_ID_SSF210 == s_agx_device_type) {
        return 0;  // 电子围栏 → 走 0xEA
    }
    if (s_is_sfl200_online) {
        return 0;  // SFL200 → 走 0xE1
    }
    return alink_upload_package(&sAlinkPackage_TargetInfo_Fusion_new, psObjTargetInfo);
}
```

### 数据结构

- 载荷: `fusion_objects_net_t` → `fusion_object_items_net_t` 数组
- 每项 ~134B，header 18B
- 注册: `alink_register_package(..., 0xE6, 0, track_pkg_fusion_target_new)`
- C2 连接: `c2_network.cpp` → `alink_connect_send(..., 0xE6, ALINK_DEV_ID_C2, ...)`

## 路径 2: SSF → 0xEA

```
/fusiontg_objs_c2 (ROS topic, FusionTargetPack)
  → fusiontg_callback                         (ros_app.cpp ~434)
    → alink_upload_efence_fusion_data          (ros_app.cpp ~555) [同步, ROS 回调线程]
      → alink_upload_package → efence_fusion_data_proc
        → mutex → TCP 发送, msgid=0xEA
        → (可选) udp_forward_send              UDP 旁路转发
```

### 关键守卫

```c
// alink_efence.cpp — 仅电子围栏初始化后才发送
int32_t alink_upload_efence_fusion_data(void *packet)
{
    if (!s_efence_init_flag) { return 0; }
    return alink_upload_package(&sAlinkPackage_efence_fusion_data, packet);
}
```

`alink_efence_init()` 仅在 `get_agx_device_type() ∈ {SSF100, SSF200, SSF210}` 时执行，同时注册：

| 消息 ID | 功能 | 频率 |
|--------|------|------|
| 0x77 | 电子围栏心跳（设备状态+子设备列表） | 1Hz（独立线程） |
| 0x78 | 系统使能配置 | 按需，C2→AGX |
| 0x79 | 系统参数配置 | 按需，C2→AGX |
| 0x9D | 时间同步 | 按需，双向 |
| 0xEA | 融合目标数据 | 10Hz |

### 数据结构

- 载荷: `alink_fusion_objs_t` → `alink_fusion_obj_item_t` 数组
- 每项 ~286B（比 0xE6 多 `serialnum`、`home/pilot` 经纬高、射频字段等）
- header: `EFENCE_CMD_0XEA_MIN_PAYLOAD_LEN` = 18B
- 最大目标数: `(65535 - 18) / 286 ≈ 229`
- 注册: `alink_register_package(..., ALINK_SSF100_MSG_ID_FUSION_DATA, 0, efence_fusion_data_proc)`
- C2 连接: `c2_network.cpp` → `alink_connect_send(..., ALINK_SSF100_MSG_ID_FUSION_DATA, ...)`（仅 SSF）

### 与 SRP 的关键差异

| 方面 | SRP (0xE6) | SSF (0xEA) |
|------|-----------|-----------|
| 执行线程 | `sysport_task_func` 工作线程（异步） | ROS 回调线程（同步） |
| 每项字节 | ~134B | ~286B（×2.1） |
| 额外消息 | 无 | 0x77 心跳 + 0x9D 时间同步 |
| C2 connect 额外注册 | 无 | 0x77 / 0xEA / 0x9D |
| 时间同步回退 | `alink_request_settime` | `efence_time_sync_start`（独立线程） |

## 路径 3: Sentry/SFL200 → 0xE1

```
SFL200 ROS 节点 → updateC2_0xE1_SFL200()          (sfl200App.cpp ~931)
  → ROS publish (sfl200_objs_pub_)
    → sfl200Objs_callback                           (ros_app.cpp ~294)
      → sfl200_packet_ckb_handle                    (sfl200_app.cpp)
        → alink_transfer_sfl200_to_c2               (alink_sentry.cpp ~667)
          → alink_upload_package                     注册 msgid=0xFF(transfer)
            → transfer_sfl200_package_c2             线上 msgid=实际 transfer_cmd(0xE1)
              → mutex → TCP 发送
```

### 0xE1 名称碰撞

AGX **同时**在 `alink_system.cpp` 中以 `alink_register_package(..., 0xE1, ...)` 注册了 `HeartBeatHostStatus`（主机状态心跳，1Hz，~580B），与 SFL200 融合数据共用 msgid 0xE1。SFL200 融合走 transfer 通道（0xFF 注册），在 `alink_upload_send_package` 中动态替换 `msgid = tpack.transfer_cmd` 实现真正的 0xE1 发送。

## 共享数据来源

三条路径的融合目标数据均来自同一个 ROS topic：

```
rvfusion_service (融合算法)
  → /fusiontg_objs_c2 (FusionTargetPack)
    → fusiontg_callback (ros_app.cpp)
      ├─ 构建 fusion_target_info_packages_t → ROS_FUSION_NEW_DATA → 0xE6 (SRP)
      └─ 构建 alink_fusion_objs_t → alink_upload_efence_fusion_data → 0xEA (SSF)

SFL200 ROS 节点自行产生融合数据 → 独立 topic → 0xE1
```

## 共享 mutex 与 TCP 连接

所有上报路径最终调用 `alink_upload_send_package`（`alink_upload.c`），共享同一个 `pthread_mutex_lock`。0xEC（PTZ 状态，10Hz）也经过同一 mutex。大包（如 SSF 的 0xEA ~55KB）持锁期间会阻塞其他消息发送。

## 常用排查场景

| 场景 | 检查点 |
|------|--------|
| C2 收不到融合目标 | 1. `get_agx_device_type()` 返回值是否正确 2. 对应路径的 init 是否执行 3. `s_efence_init_flag` / `s_is_sfl200_online` 状态 |
| C2 画面闪烁 | 检查 0xEA 数据量（目标数 × 286B × 10Hz），以及与 0xEC 的 mutex 竞争 |
| 融合数据丢包/截断 | `uint16_t` 返回值上限 65535B → 最多 229 个目标（0xEA） |
| 新设备类型接入 | 确认 `alink.h` 中 `ALINK_DEV_ID_*` 与 `configCommDef.h` 中 `HostDevType` 一致 |
