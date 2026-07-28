# Spotter/Spotter Pro上云协议

## 约定

1. **result**：`0`成功 `1`失败 `2`超时 `3`离线 `4`状态冲突 `5`重启中

## 公共 CloudMessage 定义

3 份上云协议文档（Spotter/Spotter Pro、SDH100、Tracer）统一使用以下 `CloudMessage` 作为外层信封。各协议只需定义业务 payload message，通过 `google.protobuf.Any` 承载在 `data` 字段中，`type_url` 标识具体 payload 类型。

3 份协议均 `import "cloud_message.proto"`，共用同一外层信封。

```protobuf
syntax = "proto3";
import "google/protobuf/any.proto";

package cloud;

// 外层信封，3 份上云协议文档全部用这一个
message CloudMessage {
  string tid       = 1;  // 事务 UUID
  string bid       = 2;  // 业务 UUID
  int64  timestamp = 3;  // 毫秒时间戳
  string gateway   = 4;  // 设备 SN
  string method    = 5;  // "spotter_fusion_targets" / "sdh100_xxx" / ...
  google.protobuf.Any data = 6;  // 业务载荷，type_url 标识具体类型
}
```

**字段顺序**（元数据 → 路由 → 载荷）：

- 元数据：`tid`, `bid`, `timestamp`

- 路由：`gateway`, `method`

- 载荷：`data` \(Any\)

**请求/应答区分**：不加 direction / ack 字段，靠 Topic 区分——`/services` = 请求，`/services_reply` = 应答。请求与应答共享同一 method 值。

**data 内部平铺**：payload 字段直接平铺在 data 内部，不嵌套 `{request}` / `{response}` 一层。

**JSON 编码**：`data` 字段使用 protobuf Any 的标准 JSON 编码，以 `@type` 标识具体类型：

```json
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_device_heart",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterDeviceHeartData",
    "sn": "SSF100_SN_001",
    "timestamp": 1667220873800,
    "state": 1,
    "longitude": 114.0579,
    "latitude": 22.5431
  }
}
```

**Any 路线 vs Struct 路线 — 关键 Trade\-off**

- ✅ **类型安全**：`unpack(SpotterFusionTargetsData.class)` 编译期校验 payload 类型

- ✅ **code\-gen 强类型**：所有语言 SDK 一行 unpack 拿到强类型字段

- ✅ **跨语言 SDK 自动**：protobuf 工具链覆盖 C\+\+/Java/Go/Python

- ✅ **wire 编码零损耗**：payload 是原 message 编码

- ✅ **调试可读**：`.toString()` 是结构化 protobuf text format

- ⚠️ **加 method 需改外层 proto 重生成代码**（可控、低频）

- ⚠️ **type\_url 是字符串约定**，写错类型 unpack 失败靠 runtime 报错

**⚠️ Wire Format 大变更**
CloudMessage 完全替代原外层 message（如 `DeviceHeartOsd` / `FusionTargetsOsd` / `SrpWorkModeRequest` 等），是 wire\-format 大变更。所有现存 device/cloud 解析代码全部失效，需同步改造。

---

## **2\. 协议一览**

|CMD|method|Topic|说明|**修订**|
|---|---|---|---|---|
|0x77|`device_heart`<br>|thing/product/\{Spotter设备SN\}/osd|设备系统状态/心跳|`device_heart`<br>|
|0xEA|`device_uav`|thing/product/\{Spotter设备SN\}/osd|融合目标上报 10Hz|device\_uav|
|0xE3|`device_uav_video`<br>|thing/product/\{Spotter设备SN\}/uav|视觉感知锁定包|**device\_uav\_video**|
|0xEC|`device_heart`|thing/product/\{ptz设备SN\}/osd|PTZ 基础状态 5Hz|device\_heart<br>|
|0xE4|`device_posture`|thing/product/\{Spotter设备SN\}/osd|转台/雷达伺服角 10Hz|device\_posture<br>|
|0xE0|`spotter_device_fault`|thing/product/\{Spotter设备SN\}/osd|主/子设备故障码|device\_fault|
|0xE2|`spotter_work_mode`<br>|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|设置主设备工作参数<br>||
|0x81|`spotter_select_track_target`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|选择引导跟踪目标<br>||
|0x82|`device_track`|thing/product/\{Spotter设备SN\}/osd|目标跟踪状态上报|device\_track<br>|
|0x86|`spotter_get_stream_info`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|获取 PTZ/激光视频流信息<br>||
|0x71|`spotter_set_global_pose`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|设置全局位置姿态||
|0x72|`spotter_get_global_pose`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|获取全局位置姿态||
|0x8A|`spotter_ptz_control`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|PTZ/激光转台控制||
|0x8B|`spotter_ptz_zoom`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|PTZ 变焦聚焦<br>||
|0x8C|`spotter_ptz_ctl_mode`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|PTZ 手动/自动模式||
|0x73|`spotter_device_position`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|查询/设置子设备位姿<br>||
|0x74|`spotter_position_sync`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|一键位置同步<br>||
|0x91|`spotter_calib_confirm`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|标定确认<br>||
|0x92|<br>spotter\_get\_calib\_status<br>|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply  |获取标定状态<br>||
|0x92|**`device_calibration_status`**|thing/product/\{Spotter设备SN\}/state|标定完成状态上报<br>|**device\_calibration\_status**|
|0x93|**`device_calibration_data`**<br>|thing/product/\{Spotter设备SN\}/state|标定过程数据上报<br>|**device\_calibration\_data**|
|0x9A|`spotter_calib_ctrl`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|启动/停止/查询标定<br>||
|0x95|`spotter_calib_pixel`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|选择视频画面像素点目标<br>||
|0x97|`spotter_upset_mask`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|新增或修改 mask 区域<br>||
|0x98|`spotter_delete_mask`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|删除 mask 区域<br>||
|0x99|spotter\_get\_mask\_list<br>|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply  |查询mask 区域|<br>|
|0x99|**`device_mark`**|thing/product/\{Spotter设备SN\}/state|上报 mask 区域|**device\_mark**|
|0x9E|`spotter_time_sync_set`<br>|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|设置时间同步参数||
|0x9F|`spotter_time_sync_get`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply  <br>|时间同步参数||
|0x9F|device\_time\_sync|thing/product/\{Spotter设备SN\}/osd|时间同步状态主动上报||
|0xC6|`device_heart`<br>|thing/product/\{惯导设备SN\}/osd|惯导信息上报|device\_heart<br>|
|0xCA|`spotter_set_relative_xyz`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|下发子设备相对坐标<br>||
|0xCB|`spotter_get_relative_xyz`<br>|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|获取子设备相对坐标<br>||
|0xD5|`spotter_get_whitelist`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|获取白名单<br>||
|0xD6|`spotter_set_whitelist`|thing/product/\{Spotter设备SN\}/services  <br>thing/product/\{Spotter设备SN\}/services\_reply|增减白名单||

> 上表 CMD 已给出 Protobuf \+ JSON 示例（标定扩展/激光/OTA 等见文末「其余协议」表）。
> 
> 

## Method → Payload 字段映射表

本协议所有 method 对应的业务 payload type。请求/应答共享同一 method 值，靠 Topic 区分方向（`/services` = 请求，`/services_reply` = 应答，`/osd` = 上报）。

|method|payload type \(请求\)|payload type \(应答/上报\)|Topic|note|
|---|---|---|---|---|
|`device_heart`|—|cloud\.SpotterDeviceHeartData|/osd|0x77 设备系统状态/心跳|
|`device_uav`|—|cloud\.SpotterFusionTargetsData|/osd|0xEA 融合目标上报 10Hz|
|**`device_uav_video`**|—|cloud\.SpotterVisionLockData|thing/product/\{Spotter设备SN\}/uav|0xE3 视觉感知锁定包|
|`device_heart`|—|cloud\.SpotterPtzStatusData|/osd|0xEC PTZ 基础状态 5Hz|
|`device_posture`|—|cloud\.SpotterServoAngleData|/osd|0xE4 转台/雷达伺服角 10Hz|
|`device_fault`|—|cloud\.DeviceFaultData|/osd|0xE0 主/子设备故障码|
|`spotter_work_mode`|cloud\.SpotterWorkModeReqData<br>|cloud\.SpotterWorkModeReplyData|/services \& /services\_reply|0xE2 设置主设备工作参数|
|`spotter_select_track_target`|cloud\.SpotterSelectTrackTargetReqData|cloud\.SpotterSelectTrackTargetReplyData|/services \& /services\_reply|0x81 选择引导跟踪目标|
|`device_track`|—|cloud\.SpotterTrackStatusData|/osd|0x82 目标跟踪状态上报|
|`spotter_get_stream_info`|cloud\.SpotterGetStreamInfoReqData|cloud\.SpotterGetStreamInfoReplyData|/services \& /services\_reply|0x86 获取 PTZ/激光视频流信息|
|`spotter_get_stream_url`|cloud\.SpotterDeviceStreamUrlReqData|cloud\.SpotterDeviceStreamUrlReplyData|/services \& /services\_reply|设备获取推流地址|
|`spotter_set_global_pose`|cloud\.SpotterSetGlobalPoseReqData|cloud\.SpotterSetGlobalPoseReplyData|/services \& /services\_reply|0x71 设置全局位置姿态|
|`spotter_get_global_pose`|cloud\.SpotterGetGlobalPoseReqData|cloud\.SpotterGetGlobalPoseReplyData|/services \& /services\_reply|0x72 获取全局位置姿态|
|`spotter_ptz_control`|cloud\.SpotterPtzControlReqData|cloud\.SpotterPtzControlReplyData|/services \& /services\_reply|0x8A PTZ/激光转台控制|
|`spotter_ptz_zoom`|cloud\.SpotterPtzZoomReqData|cloud\.SpotterPtzZoomReplyData|/services \& /services\_reply|0x8B PTZ 变焦聚焦|
|`spotter_ptz_ctl_mode`|cloud\.SpotterPtzCtlModeReqData|cloud\.SpotterPtzCtlModeReplyData|/services \& /services\_reply|0x8C PTZ 手动/自动模式|
|`spotter_device_position`|cloud\.SpotterDevicePositionReqData|cloud\.SpotterDevicePositionReplyData|/services \& /services\_reply|0x73 查询/设置子设备位姿|
|`spotter_position_sync`|cloud\.SpotterPositionSyncReqData|cloud\.SpotterPositionSyncReplyData|/services \& /services\_reply|0x74 一键位置同步|
|`spotter_calib_confirm`|cloud\.SpotterCalibConfirmReqData|cloud\.SpotterCalibConfirmReplyData|/services \& /services\_reply|0x91 标定确认|
|**`spotter_get_calib_status`**|cloud\.SpotterCalibStatusReqData|cloud\.SpotterCalibStatusReplyData|/services \& /services\_reply |0x92 标定状态|
|**device\_calibration\_status**||SpotterCalibStatusReplyData |thing/product/\{Spotter设备SN\}/state|0x92 主动上报标定状态|
|**`device_calibration_data`**|—|cloud\.SpotterCalibDataPayload|thing/product/\{Spotter设备SN\}/state|0x93 标定过程数据上报|
|`spotter_calib_ctrl`|cloud\.SpotterCalibCtrlReqData|cloud\.SpotterCalibCtrlReplyData|/services \& /services\_reply|0x9A 启动/停止/查询标定|
|`spotter_calib_pixel`|cloud\.SpotterCalibPixelReqData|cloud\.SpotterCalibPixelReplyData|/services \& /services\_reply|0x95 选择视频画面像素点目标|
|`spotter_upset_mask`|cloud\.SpotterMaskItemData|cloud\.SpotterUpsetMaskReplyData|/services \& /services\_reply|0x97 新增或修改 mask 区域|
|`spotter_delete_mask`|cloud\.SpotterDeleteMaskReqData|cloud\.SpotterDeleteMaskReplyData|/services \& /services\_reply|0x98 删除 mask 区域|
|**`dspotter_get_mask_list`**|SpotterGetMaskListReqData |SpotterGetMaskListReplyData |/services \& /services\_reply|0x99 查询 mask 区域<br>|
|**`device_mark`**||SpotterGetMaskListOutput |thing/product/\{Spotter设备SN\}/state|0x99 主动上报 mask 区域|
|`spotter_time_sync_set`|cloud\.SpotterTimeSyncSetReqData|cloud\.SpotterTimeSyncSetReplyData|/services \& /services\_reply|0x9E 设置时间同步参数|
|`spotter_time_sync_get`|SpotterTimeSyncGetReqData|SpotterTimeSyncGetReplyData|/services \& /services\_reply |0x9F 时间同步参数/状态查询<br>|
|device\_time\_sync||SpotterTimeSyncStatusOutput |thing/product/\{Spotter设备SN\}/osd|0x9F 主动上报时间同步状态|
|`device_heart`|—|cloud\.SpotterInsHeartData|/osd|0xC6 惯导信息上报|
|`spotter_set_relative_xyz`|cloud\.SpotterSetRelativeXyzReqData<br>|cloud\.SpotterSetRelativeXyzReplyData|/services \& /services\_reply|0xCA 下发子设备相对坐标|
|`spotter_get_relative_xyz`|cloud\.SpotterGetRelativeXyzReqData|cloud\.SpotterGetRelativeXyzReplyData|/services \& /services\_reply|0xCB 获取子设备相对坐标|
|`spotter_get_whitelist`|cloud\.SpotterGetWhitelistReqData|cloud\.SpotterGetWhitelistReplyData|/services \& /services\_reply|0xD5 获取白名单|
|`spotter_set_whitelist`|cloud\.SpotterSetWhitelistReqData<br>|cloud\.SpotterSetWhitelistReplyData|/services \& /services\_reply|0xD6 增减白名单|
|`spotter_set_dph_config`|cloud\.SpotterDphConfigData<br>|cloud\.SpotterSetDphConfigReplyData|/services \& /services\_reply|0xA6 设置雷达配置|
|`spotter_get_dph_config`|cloud\.SpotterGetDphConfigReqData|cloud\.SpotterGetDphConfigReplyData|/services \& /services\_reply|0xA7 获取雷达配置|

---

## 0x77 设备系统状态上报

### 协议概要

### Protobuf

`Topic: thing/product/{Spotter设备SN}/osd`
`method: device_heart`

```Java
// Topic: thing/product/{Spotter设备SN}/osd
// method: device_heart
// 对应设备协议: 0x77 上报设备系统状态数据
// 外层使用 CloudMessage（见文档开头公共定义），data payload 类型: cloud.SpotterDeviceHeartData

message SpotterDeviceHeartData {
  string sn = 1; // 主设备 sn
  int64 timestamp = 2; // 毫秒时间戳
  uint32 type = 3; //主设备类型
  string ip = 4; // 主设备 IP
  string version = 5; // 软件版本
  uint32 state = 6; // 0x01开机 0x02休眠 0x03左边开机 0x04右边开机
  double longitude = 7; // 经度 (°)
  double latitude = 8; // 纬度 (°)
  float altitude = 9; // 海拔高度 (m)
  uint32 err_code = 10; // 系统故障码 0x00：无故障 0x01：时间未同步 0x02：CPU负载过大 0x03：内存占用过大
  float env_temp = 11; // 内部环境温度 (°C)，无效 0xFFFF
  float shell_top_temp = 12; // 顶部壳体温度 (°C)
  float shell_bottom_temp = 13; // 底部壳体温度 (°C)
  float edge_power_temp = 14; // 边缘计算模块供电单元温度 (°C)
  float edge_shell_temp = 15; // 边缘计算模块外壳温度 (°C)
  float ptz_power_temp = 16; // PTZ 供电单元温度 (°C)
  float radar_power_temp = 17; // 雷达供电单元温度 (°C)
  float radar_shell_temp = 18; // 雷达主控单元壳体温度 (°C)
  uint32 main_fan_speed = 19; // 主腔体风扇转速 (%)
  uint32 edge_fan_speed = 20; // 边缘计算模块风扇转速 (%)
  uint32 progress = 21; // 开机进度 0~100%
  float edge_cpu_temp = 22; // 边缘计算 CPU 核心板温度 (°C)
  float main_power_temp = 23; // 综合供电单元温度 (°C)
  uint32 detection_mode_status = 24; // 探测模式 0小飞机 1大飞机 2自动
  float global_heading = 25; // 全局航向角 (°)
  float global_pitch = 26; // 全局俯仰角 (°)
  float global_roll = 27; // 全局横滚角 (°)
  float speed = 28; // 车体速度
  uint32 vehicle_mode = 29; // 0固定 1车载
  uint32 drive_mode = 30; // 0停止 1驾驶
  uint32 num = 31; // 子设备数量 (= sub_device_list.length)
  repeated SpotterSubDevice sub_device_list = 32; // 子设备列表
}

message SpotterSubDevice {
  string sn = 1; // 子设备 sn
  uint32 type = 2; // 子设备类型（附录：雷达/PTZ/无线电等）
  string ip = 3; // 子设备 IP
  string version = 4; // 子设备版本
  uint32 online = 5; // 0离线 1在线
  uint32 state = 6; // 0x01工作 0x02休眠 0x03离线
  double longitude = 7; // 经度 (°)
  double latitude = 8; // 纬度 (°)
  float altitude = 9; // 海拔高度 (m)
  uint32 err_code = 10; // 子设备故障码 0x00：无故障 0x01：时间未同步
}
```

### 上报示例

```JSON
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "device_heart",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterDeviceHeartData",
    "sn": "SSF100_SN_001",
    "timestamp": 1667220873800,
    "type": 19,
    "ip": "192.168.1.10",
    "version": "V1.2.3",
    "state": 1,
    "longitude": 114.0579,
    "latitude": 22.5431,
    "altitude": 50.0,
    "err_code": 0,
    "main_fan_speed": 40,
    "edge_fan_speed": 35,
    "progress": 100,
    "detection_mode_status": 0,
    "vehicle_mode": 0,
    "drive_mode": 0,
    "num": 1,
    "sub_device_list": [
      {
        "sn": "RADAR_SN_001",
        "type": 8,
        "ip": "192.168.1.20",
        "version": "1.0.0",
        "online": 1,
        "state": 1,
        "longitude": 114.0579,
        "latitude": 22.5431,
        "altitude": 50.0,
        "err_code": 0
      }
    ]
  }
}
```

---

## 0xEA 上报融合目标

### 协议概要

### Protobuf

`Topic: thing/product/{Spotter设备SN}/osd`
`method: device_uav`

```Java
// Topic: thing/product/{Spotter设备SN}/osd
// method: device_uav
// 对应设备协议: 0xEA 上报融合目标
// 外层使用 CloudMessage（见文档开头公共定义），data payload 类型: cloud.SpotterFusionTargetsData

message SpotterFusionTargetsData {
  uint64 timestamp = 1; // 毫秒时间戳
  uint32 fusion_tracker_num = 2; // 跟踪目标个数
  repeated SpotterFusionTarget target_list = 3; // 融合目标列表（长度 = fusion_tracker_num）
}

message SpotterFusionTarget {
  uint32 id = 1; // 融合目标 ID
  string drone_name = 2; // 无人机名称
  string serial_num = 3; // 无人机 SN
  uint32 source = 4; // 数据来源位：b0 PTZ b1协议 b2雷达 b3频谱 b4~b7预留 b8打击处置 b9诱骗干扰 b10~b31预留
  uint32 state_type = 5; // 0无效 1稳态 2暂态 3丢失 9合并
  uint32 existing_prob = 6; // 存在概率 0~100 (%)
  float lifetime = 7; // 首次侦测至今寿命 (s) 0~86400
  float forcast_time = 8; // 最近侦测至今时间 (s) 0~3600
  uint32 classification = 9; // 0未识别 1无人机 2单兵 3车辆 4鸟 5轻航空器
  uint32 classification_prob = 10; // 类别概率 0~100
  uint32 geo_valid = 11; // 地理位置有效 0无效 1有效
  double longitude = 12; // 经度 (°)，无效/未知置 0
  double latitude = 13; // 纬度 (°)，无效/未知置 0
  double altitude = 14; // 几何/气压高度 (m)，无效 -1000
  double height = 15; // 距地高度 AGL (m)，无效 -1000
  float orientation_angle = 16; // 航迹角 (°)，真北顺时针，无效 361
  float absolute_speed = 17; // 地速 (m/s)，无效 255
  float vertical_speed = 18; // 垂直速度 (m/s)，向上为正，无效 63
  uint32 motion_type = 19; // 0未识别 1静止 2悬停 3靠近 4远离 5左 6右 7上 8下 9炸机
  double home_longitude = 20; // 返航点经度 (°)
  double home_latitude = 21; // 返航点纬度 (°)
  double pilot_longitude = 22; // 飞手经度 (°)
  double pilot_latitude = 23; // 飞手纬度 (°)
  double pilot_altitude = 24; // 飞手高度 (m)
  float frequency = 25; // 频率 (MHz)，无效 0
  uint32 load_level = 26; // 挂载 0未识别 1多 2少 3无
  uint32 danger_level = 27; // 危险等级 0未识别 1非常危险 2较轻 3无
  uint32 priority = 28; // 引导优先级，越大越高
  float target_range = 29; // 相对基准点空间距离 (m)
  float target_azimuth = 30; // 相对基准点方位角 (°)，真北为 0
  float target_elevation = 31; // 相对基准点俯仰角 (°)
  float target_arrival_time = 32; // 预计到达时间 (s)
  //B0：白名单标志 （当前已实现）
  //B1：正被视觉引导标志
  //B2：正被视觉锁定标志
  //B3：正被干扰锁定标志
  //B4：正被干扰处置标志 （目标处于干扰中）
  //B5：精确打击有效标志（目标是否支持精确打击）（当前已实现）
  //B6：GNSS干扰有效标志
  //B7：正被GNSS诱骗处置标志
  //B8：数据预测标志
  //B9：数据融合标志
  //B10：目标坠毁标志 （当前已实现）
  //B11：干扰有效标志（目标是否支持干扰）（当前已实现）
  //B12：诱骗有效标志（目标是否支持诱骗）（当前已实现）
  //B13:  正被雷达TAS跟踪标志（20260203 by zgd）（当前已实现）
  uint32 proc_status = 33;
  uint32 flag_time = 34; // 图像周期结束点数（精准打击）
  uint32 jamming_accruate_type = 35; // 精准打击类型
  float rf_singal_power = 36; // 无人机信号功率 (0.1dBm)
  float rf_noise_power = 37; // 噪声功率 (0.1dBm)
  uint32 rf_snr = 38; // 信噪比 (dB)
  uint32 rf_detection_cnt = 39; // 侦测次数
  uint32 rf_singal_type = 40; // 0无效 1数字图传 2模拟图传 3WIFI 4飞控下行 5飞控上行
  float target_local_range = 41; // 局部坐标系空间距离 (m)
  float target_local_azimuth = 42; // 局部坐标系方位角 (°)
  float target_local_elevation = 43; // 局部坐标系俯仰角 (°)
  uint32 debug_status = 44; // 0正式 10视觉调试 20协议 30雷达 40频谱 41 TRACER_AIR 90 GNSS；非0不上报天盾
  uint32 antenna_type = 45; // 0位置 1四正源干扰天线
  float ground_distance_error = 46; // 地面距离误差 (m)
  float range_error = 47; // 三维距离误差 (m)
  float azimuth_error = 48; // 方位角误差
  float elevation_error = 49; // 俯仰角误差
  double falling_longitude = 50; // 坠落点经度 (°)
  double falling_latitude = 51; // 坠落点纬度 (°)
  uint32 protocol_msg_type = 52; // 协议类型 bit0 DID解密 bit1 DID加密 bit2 RID-WiFi bit3 RID-蓝牙
  float track_bw = 53; // 信号带宽 (MHz)
  float track_ct = 54; // 特征时间 (μs)
  uint32 geo_precision_level = 55; // 0无效 1高精度(雷达+视觉) 2协议辅助 3雷达TAS 4雷达TWS 5仅光电 6不可靠
  uint32 guidance_safety = 56; // 0无效 1 SAFE 2 WARNING高度异常 3 WARNING类别异常 4 DANGER高度过低停引导
}
```

### 上报示例

```JSON
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "device_uav",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterFusionTargetsData",
    "timestamp": 1667220873800,
    "fusion_tracker_num": 1,
    "target_list": [
      {
        "id": 42,
        "drone_name": "DJI Mini",
        "serial_num": "DRONE_SN_001",
        "source": 7,
        "state_type": 1,
        "existing_prob": 95,
        "classification": 1,
        "geo_valid": 1,
        "longitude": 114.06,
        "latitude": 22.54,
        "altitude": 120.0,
        "height": 80.0,
        "absolute_speed": 5.2,
        "geo_precision_level": 1,
        "guidance_safety": 1
      }
    ]
  }
}
```

---

## 0xE3 上报视觉感知锁定数据包

### 协议概要

### Protobuf

`Topic: thing/product/{Spotter设备SN}/uav`
`method: `**`device_uav_video`**

```Java
// Topic: thing/product/{Spotter设备SN}/uav
// method: **device_uav_video**
// 对应设备协议: 0xE3 上报视觉感知锁定数据包

// 外层使用 CloudMessage（见文档开头公共定义），data payload 类型: cloud.SpotterVisionLockData
message SpotterVisionLockData {
  uint64 timestamp = 1; // 毫秒时间戳
  uint32 dev_id = 2; // 设备 ID
  string sn = 3; // PTZ/感知设备 sn
  uint64 guidance_count = 4; // 引导帧序号
  uint32 working_state = 5; // PTZ锁定状态信息 空闲：0；引导转动：1；搜索目标：2；锁定：3
  int32 vision_target_id = 6; // 视觉目标 ID
  int32 vision_target_u = 7; // 视觉目标宽度方向像素坐标
  int32 vision_target_v = 8; // 视觉目标高度方向像素坐标
  float vision_target_velocity_u = 9; // 宽度方向像素速度
  float vision_target_velocity_v = 10; // 高度方向像素速度
  uint32 fusion_target_id = 11; // 融合目标 ID
  float target_local_range = 12; // 融合目标相对径向距离 (m)
  float target_local_horizontal_range = 13; // 融合目标相对水平面距离 (m)
  double height = 14; // 融合目标对地高度 (m)
  float guiding_local_azimuth = 15; // PTZ 水平角度 (°)
  float guiding_local_elevation = 16; // PTZ 俯仰角度 (°)
  double longitude = 17; // 目标经度 (°)
  double latitude = 18; // 目标纬度 (°)
  double altitude = 19; // 目标海拔 (m)
  uint32 fusion_target_classification = 20; // 0未知 1无人机 2行人 3车辆 4鸟 5客机 100其他 127无效
  uint32 pip_is_valid = 21; // 画中画 0开启 1未开启
  uint32 vision_target_w = 22; // 视觉目标框宽度（像素），0无效
  uint32 vision_target_h = 23; // 视觉目标框高度（像素），0无效
  uint32 video_source = 24; // 0可见光 1热像
}

```

### 上报示例

```JSON
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "**device_uav_video**",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterVisionLockData",
    "timestamp": 1667220873800,
    "sn": "PTZ_SN_001",
    "working_state": 3,
    "fusion_target_id": 42,
    "vision_target_u": 960,
    "vision_target_v": 540,
    "longitude": 114.06,
    "latitude": 22.54,
    "altitude": 120.0,
    "video_source": 0
  }
}
```

---

## 0xEC 上报 PTZ 基础状态

### 协议概要

### Protobuf

`Topic: thing/product/{ptz设备SN}/osd`
`method: device_heart`

```Java
// Topic: thing/product/{ptz设备SN}/osd
// method: device_heart
// 对应设备协议: 0xEC 上报PTZ基础状态数据

// 外层使用 CloudMessage（见文档开头公共定义），data payload 类型: cloud.SpotterPtzStatusData
message SpotterPtzStatusData {
  string sn = 1; // PTZ sn
  uint64 timestamp = 2; // 毫秒时间戳
  float longitude = 3; // PTZ 经度
  float latitude = 4; // PTZ 纬度
  float height = 5; // PTZ 高度 (m)
  float azimuth = 6; // 方位角 (°)
  float elevation = 7; // 俯仰角 (°)
  float omega_az = 8; // 方位角速度 (°/s)
  float omega_el = 9; // 俯仰角速度 (°/s)
  float zoom = 10; // 变倍
  float visible1_h_fov = 11; // 可见光1 水平视场角 (°)
  float visible1_v_fov = 12; // 可见光1 垂直视场角 (°)
  float ir1_h_fov = 13; // 热像1 水平视场角 (°)
  float ir1_v_fov = 14; // 热像1 垂直视场角 (°)
  float visible2_h_fov = 15; // 可见光2 水平视场角 (°)
  float visible2_v_fov = 16; // 可见光2 垂直视场角 (°)
  uint32 ir1_focus = 17; // 热像1 聚焦值
  uint32 visible1_focus = 18; // 可见光1 聚焦值
  uint32 visible2_focus = 19; // 可见光2 聚焦值
  uint32 detect_camera_mode = 20; // 当前控制切换跟踪相机的模式：0-自动，1-手动
  uint32 detect_camera = 21; // 当前侦测相机
  uint32 icr_mode = 22; // ICR 模式
  uint32 icr_value = 23; // ICR 值
  uint32 ptz_ctl_mode = 24; // 当前PTZ控制模式: 0-自动；1- 全手动 针对PTZ云台转向、zoom和focus
  uint32 defog_enable = 25; // 透雾: 0=关 1=开(2026.5.25 add，目前仅和普支持)
  uint32 win_heat_enable = 26; // 除霜(窗口加热): 0=关 1=开(2026.5.25 add，目前仅和普支持)

}

```

### 上报示例

```JSON
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "device_heart",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterPtzStatusData",
    "sn": "PTZ_SN_001",
    "timestamp": 1667220873800,
    "azimuth": 120.5,
    "elevation": 10.0,
    "zoom": 8.0,
    "ptz_ctl_mode": 0,
    "detect_camera": 1
  }
}
```

---

## 0xE4 上报转台伺服角度

### 协议概要

### Protobuf

`Topic: thing/product/{Spotter设备SN}/osd`
`method: device_posture`

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/osd
// method: device_posture
// 对应设备协议: 0xE4 上报转台伺服角度

// 外层使用 CloudMessage（见文档开头公共定义），data payload 类型: cloud.SpotterServoAngleData
message SpotterServoAngleData {
  string sn = 1; // 转台/伺服 sn
  float cur_servo = 2; // 当前伺服角度，0~360°，（单位°）
  float servo_ap = 3; // 伺服角速度 (°/s)

}

```

### 上报示例

```JSON
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "SRP200_SN_001",
  "method": "device_posture",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterServoAngleData",
    "sn": "SERVO_SN_001",
    "cur_servo": 90.0,
    "servo_ap": 12.5
  }
}
```

---

## 0xE0 上报主/子设备故障码

### 协议概要

### Protobuf

`Topic: thing/product/{Spotter设备SN}/osd`
`method: device_fault`

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/osd
// method: device_fault
// 对应设备协议: 0xE0 上报主设备和子设备故障码

// 外层使用 CloudMessage（见文档开头公共定义），data payload 类型: cloud.DeviceFaultData
message DeviceFaultData {
  string sn = 1; // 主设备或子设备 sn
  uint32 err_num = 2; // 错误条目数量
  repeated FaultFirstClass err_list = 3; // 故障分级列表
}

message FaultFirstClass {
  uint32 first_level_code = 1; // 一级错误码
  uint32 second_level_code = 2; // 二级错误码
  uint32 third_level_code = 3; // 三级错误码
  uint32 four_err_num = 4; // 四级错误码数量
  repeated FaultSecondClass second_level_class = 5; // 四级错误明细列表
}

message FaultSecondClass {
  uint32 four_level_code = 1; // 四级业务错误码
  string four_level_msg = 2; // 四级错误描述
}

```

### 上报示例

```JSON
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "device_fault",
  "data": {
    "@type": "type.googleapis.com/cloud.DeviceFaultData",
    "sn": "SSF100_SN_001",
    "err_num": 1,
    "err_list": [
      {
        "first_level_code": 1,
        "second_level_code": 2,
        "third_level_code": 3,
        "four_err_num": 1,
        "second_level_class": [
          {
            "four_level_code": 1001,
            "four_level_msg": "码流异常"
          }
        ]
      }
    ]
  }
}
```

---

## 0xE2 设置主设备工作参数

### 协议概要

### Protobuf

`请求Topic: thing/product/{Spotter设备SN}/services`

`应答Topic：thing/product/{Spotter设备SN}/services_reply`
`method: spotter_work_mode`

```ProtoBuf
// 请求Topic: thing/product/{Spotter设备SN}/services
// 应答Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_work_mode
// 对应设备协议: 0xE2 下发设置主设备工作参数
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterWorkModeReqData
// 应答 data payload 类型: cloud.SpotterWorkModeReplyData

// === 请求 payload ===
message SpotterWorkModeReqData {
  uint32 cmd = 1; // 0待机 1开机 2左边开机 3右边开机 5探测模式 6车载模式 7驾驶模式
  uint32 detection_mode = 2; // cmd=5: 0小飞机 1大飞机 2自动
  uint32 vehicle_mode = 3; // 0固定 1车载
  uint32 drive_mode = 4; // 0停止 1驾驶
}

// === 应答 payload ===
message SpotterWorkModeReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterWorkModeOutput output = 2; // 设备侧应答
}

message SpotterWorkModeOutput {
  uint32 result = 1; // 设备侧 0失败 1成功
  uint32 error_code = 2; // 设备错误码
}
```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_work_mode",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterWorkModeReqData",
    "cmd": 1,
    "detection_mode": 0,
    "vehicle_mode": 0,
    "drive_mode": 0
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_work_mode",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterWorkModeReplyData",
    "result": 0,
    "output": {"result": 1, "error_code": 0}
  }
}
```

---

## 0x81 用户选择引导跟踪目标

### 协议概要

### Protobuf

`请求 Topic: thing/product/{Spotter设备SN}/services`

`应答 Topic：thing/product/{Spotter设备SN}/services_reply`
`method: spotter_select_track_target`

```Java
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_select_track_target
// 对应设备协议: 0x81

// 上位机直连设备
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterSelectTrackTargetReqData 
// 应答 data payload 类型: cloud.SpotterSelectTrackTargetReplyData
message SpotterSelectTrackTargetReqData {
  uint32 type = 1; // 0选PTZ跟踪 2敌军标定 3友军标定 4取消PTZ跟踪 6雷达TAS跟踪 7取消TAS
  int32 obj_id = 2; // 雷达目标 ID
  int32 x = 3; // 雷达目标x (/1e6) （单位m，默认0）
  int32 y = 4; // 雷达目标y (/1e6) （单位m，默认0
  int32 z = 5; // 雷达目标z或tracer无人机就高度 (/1e6) （单位m，默认0）
  string sn = 6; // 无人机 SN 
  int32 latitude = 7; // 无人机纬度 (/1e7) （单位°，默认0）
  int32 longitude = 8; // 无人机经度 (/1e7)（单位°，默认0）
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_select_track_target
// 对应设备协议: 0x81 应答

message SpotterSelectTrackTargetReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterSelectTrackTargetOutput output = 2; // 设备侧应答
}

message SpotterSelectTrackTargetOutput {
  uint32 type = 1; // 与请求 type 对应
  uint32 control_status = 2; // 0无效 1成功 2失败 3TAS列表满

}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_select_track_target",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterSelectTrackTargetReqData",
    "type": 0,
    "obj_id": 42,
    "sn": "DRONE_SN_001",
    "x": 0,
    "y": 0,
    "z": 0,
    "latitude": 0,
    "longitude": 0
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_select_track_target",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterSelectTrackTargetReplyData",
    "result": 0,
    "output": {
      "type": 0,
      "control_status": 1
    }
  }
}
```

---

## 0x82 目标跟踪状态上报

### 协议概要

### Protobuf

`Topic: thing/product/{Spotter设备SN}/osd`
`method: device_track`

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/osd
// method: device_track
// 对应设备协议: 0x82

// 外层使用 CloudMessage（见文档开头公共定义），data payload 类型: cloud.SpotterTrackStatusData
message SpotterTrackStatusData {
  uint32 type = 1; // 0 PTZ 1激光PTZ
  int32 obj_id = 2; // 雷达目标ID
  string sn = 3; // 无人机 SN
  uint32 status = 4; // 0自动引导 1手动引导 2匹配成功 3停止 4空闲 5搜索 6跟踪 12匹配失败 15搜索失败 16跟踪失败

}

```

### 上报示例

```JSON
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "device_track",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterTrackStatusData",
    "type": 0,
    "obj_id": 42,
    "sn": "DRONE_SN_001",
    "status": 6
  }
}
```

---

## 0x86 获取 PTZ/激光视频流信息

### 协议概要

### Protobuf

`请求Topic: thing/product/{Spotter设备SN}/services`

`应答Topic：thing/product/{Spotter设备SN}/services_reply`
`method: spotter_get_stream_info`

```Java
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_get_stream_info
// 对应设备协议: 0x86

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterGetStreamInfoReqData
// 应答 data payload 类型: cloud.SpotterGetStreamInfoReplyData
message SpotterGetStreamInfoReqData {
  string sn = 1; // PTZ SN 或激光 SN
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_get_stream_info
// 对应设备协议: 0x86 应答

message SpotterGetStreamInfoReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterGetStreamInfoOutput output = 2; // 设备侧应答
}

message SpotterGetStreamInfoOutput {
  uint32 status = 1; // 设备状态：0正常（后续字段有效）；其他见附录错误码
  string ip = 2; // IP 地址（设备侧 uint8[4]，上云用点分字符串）
  uint32 port = 3; // 通信端口号
  string sn = 4; // PTZ/激光 sn（设备侧 25 字节）
  uint32 stream_num = 5; // 当前流数量（= stream_list.length）
  repeated SpotterStreamCameraInfo stream_list = 6; // 码流列表
}

message SpotterStreamCameraInfo {
  uint32 camera_id = 1; // 摄像头 ID
  string url = 2; // 视频流地址（设备侧 char[128]）
  uint32 type = 3; // 类型（与摄像头 ID 一致），参照附录 A: 相机编号
  uint32 width = 4; // 视频分辨率宽，无效值 0
  uint32 height = 5; // 视频分辨率高，无效值 0
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_get_stream_info",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterGetStreamInfoReqData",
    "sn": "PTZ_SN_001"
  }
}
```

### **应答示例**

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_get_stream_info",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterGetStreamInfoReplyData",
    "result": 0,
    "output": {
      "status": 0,
      "ip": "192.168.1.30",
      "port": 554,
      "sn": "PTZ_SN_001",
      "stream_num": 2,
      "stream_list": [
        {
          "camera_id": 1,
          "url": "rtsp://192.168.1.30:554/stream1",
          "type": 1,
          "width": 1920,
          "height": 1080
        },
        {
          "camera_id": 0,
          "url": "rtsp://192.168.1.30:554/stream0",
          "type": 0,
          "width": 640,
          "height": 512
        }
      ]
    }
  }
}
```

## 设备获取推流地址

### 协议概要

### Protobuf

`请求Topic: thing/product/{PTZ_设备 SN}/requests`

`应答Topic：thing/product/{PTZ_设备 SN}/requests_reply`
`method: device_stream_url`

```Java
// Topic: thing/product/{PTZ设备SN}/requests
// method: device_stream_url
// 设备向云平台申请推流地址

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterDeviceStreamUrlReqData
// 应答 data payload 类型: cloud.SpotterDeviceStreamUrlReplyData

message SpotterDeviceStreamUrlReqData {
  // JSON key 为 "Camera"（首字母大写）
  SpotterCameraInfo camera = 1 [json_name = "Camera"];
}

message SpotterCameraInfo {
  // zoom:变焦 / wide:广角 / normal:普通 / ir:红外 / night:夜视
  string type = 1;
  string camera_id = 2; // 摄像头标识
}

// Topic: thing/product/{设备SN}/requests_reply
// method: device_stream_url

message SpotterDeviceStreamUrlReplyData {
  int32 result = 1;                    // 0 成功，非 0 失败
  SpotterDeviceStreamUrlOutput output = 2;
}

message SpotterDeviceStreamUrlOutput {
  repeated SpotterStreamInfo streams = 1;
}

message SpotterStreamInfo {
  string type = 1;       // 与请求 Camera.type 对应，如 "zoom"
  string stream_url = 2 [json_name = "stream_url"];  // 推流地址，JSON key 为 "stream_url"
}
```

### 请求示例

```Go
{
        "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74", //创建一个全局唯一标识符(UUID), 长度小于50的字符串
        "bid": "65717bf1-aee7-4abb-8ea3-789854512232", 
        "timestamp": 1667220873846, //设备utc时间，精确到毫秒 整型long
        "method": "device_stream_url",
        "gateway": {Spooter Pro设备 SN}
        "data": {
                "Camera" :[{
                      "type": "zoom",  //zoom-变焦 wide-广角  normal-普通  ir-红外 night-夜视
                      "camera_id": 摄像头ID
                 }]


 }
}
```

### 应答示例

```JSON
{
        "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74", //创建一个全局唯一标识符(UUID), 长度小于50的字符串
        "bid": "65717bf1-aee7-4abb-8ea3-789854512232", 
        "timestamp": 1667220873846, //设备utc时间，精确到毫秒 整型long
        "method": "device_stream_url"
         "data":
         {
             "result":0  //0-成功，非0-失败
             "output": {
                 "streams":[{
                       "type": "zoom",
                       "stream_url": "rtmp://127.232.245:1985/xxxx/xxxx",
                  }]
             }
         }
}
```

## 0x71 设置全局位置姿态

### 协议概要

### Protobuf

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_set_global_pose
// 对应设备协议: 0x71

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterSetGlobalPoseReqData 
// 应答 data payload 类型: cloud.SpotterSetGlobalPoseReplyData
message SpotterSetGlobalPoseReqData {
  float heading = 1; // 方位角 / 航向 (°，相对真北)
  double longitude = 2; // 经度 (°)
  double latitude = 3; // 纬度 (°)
  double altitude = 4; // 绝对海拔 (m)
  float rolling = 5; // 横滚角 (°)
  float pitching = 6; // 俯仰角 (°)
  float height = 7; // 相对地面高度 AGL (m)
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_set_global_pose
// 对应设备协议: 0x71 应答

message SpotterSetGlobalPoseReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterSetGlobalPoseOutput output = 2; // 设备侧应答
}

message SpotterSetGlobalPoseOutput {
  uint32 result = 1; // 0成功 1见附录错误码
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_set_global_pose",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterSetGlobalPoseReqData",
    "heading": 90.0,
    "longitude": 114.0579,
    "latitude": 22.5431,
    "altitude": 50.0,
    "rolling": 0,
    "pitching": 0,
    "height": 10.0
  }
}
```

### **应答示例**

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_set_global_pose",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterSetGlobalPoseReplyData",
    "result": 0,
    "output": {
      "result": 0
    }
  }
}
```

## 0x72 获取全局位置姿态

### 协议概要

### Protobuf

`请求Topic: thing/product/{Spotter设备SN}/services`

`应答Topic： thing/product/{Spotter设备SN}/services_reply`
`method: spotter_get_global_pose`

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_get_global_pose
// 对应设备协议: 0x72 请求（设备侧 payload 为空）

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterGetGlobalPoseReqData
// 应答 data payload 类型: cloud.SpotterGetGlobalPoseReplyData
message SpotterGetGlobalPoseReqData {
  string sn = 1; //spotter sn
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_get_global_pose
// 对应设备协议: 0x72 应答 / SRPSendGetCalibrationResponse

message SpotterGetGlobalPoseReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterGetGlobalPoseOutput output = 2; // 设备侧应答
}

message SpotterGetGlobalPoseOutput {
  float heading = 1; // 朝向角 (°)，默认 0
  double longitude = 2; // 经度 (°)，默认 0
  double latitude = 3; // 纬度 (°)，默认 0
  double altitude = 4; // 绝对海拔高度 (m)，默认 0
  float rolling = 5; // 横滚角 (°)，默认 0
  float pitching = 6; // 俯仰角 (°)，默认 0
  float height = 7; // 相对高度 (m)，默认 0
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_get_global_pose",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterGetGlobalPoseReqData"
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_get_global_pose",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterGetGlobalPoseReplyData",
    "result": 0,
    "output": {
      "heading": 90.0,
      "longitude": 114.0579,
      "latitude": 22.5431,
      "altitude": 50.0,
      "rolling": 0,
      "pitching": 0,
      "height": 10.0
    }
  }
}
```

## 0x8A PTZ/激光转台控制

### 协议概要

### Protobuf

`请求 Topic: thing/product/{Spotter设备SN}/services`

`应答 Topic: thing/product/{Spotter设备SN}/services_reply`
`method: spotter_ptz_control`

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_ptz_control
// 对应设备协议: 0x8A 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterPtzControlReqData 
// 应答 data payload 类型: cloud.SpotterPtzControlReplyData
message SpotterPtzControlReqData {
  string sn = 1; // PTZ SN 或激光 SN（设备侧 char[48]）
  uint32 cmd = 2; // 1绝对位置 2速度等级 3只控俯仰 4只控方位 5俯仰方位手动 6角速度
  uint32 yaw = 3; // cmd=1:方位角(°)；cmd=2/3/4:水平速度等级0~63；cmd=6:水平角速度×0.01°/s
  uint32 pitch = 4; // cmd=1:俯仰角(°)；cmd=2/3/4:俯仰速度等级0~63；cmd=6:俯仰角速度×0.01°/s
  int32 direction = 5; // cmd=2/6有效：0停 1左 2右 3上 4下 5左上 6左下 7右上 8右下
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_ptz_control
// 对应设备协议: 0x8A 应答

message SpotterPtzControlReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterPtzControlOutput output = 2; // 设备侧应答
}

message SpotterPtzControlOutput {
  int32 result = 1; // 0成功；其他见附录错误码
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_ptz_control",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterPtzControlReqData",
    "sn": "PTZ_SN_001",
    "cmd": 1,
    "yaw": 90,
    "pitch": 10,
    "direction": 0
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "method": "spotter_ptz_control",
  "gateway": "SSF100_SN_001",
  "data": {
    "result": 0,
    "output": {
      "result": 0
    }
  }
}
```

---

## 0x8B PTZ/激光相机变焦聚焦控制

### 协议概要

### Protobuf

```Java
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_ptz_zoom
// 对应设备协议: 0x8B 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterPtzZoomReqData
// 应答 data payload 类型: cloud.SpotterPtzZoomReplyData
message SpotterPtzZoomReqData {
  string sn = 1; // PTZ SN 或激光 SN
  uint32 cmd = 2; // 0停止 1放大 2缩小 3跳变倍 4聚焦远 5聚焦近 6设聚焦值 7闭环零点 8跟踪相机模式 9切换跟踪相机 10透雾开 11透雾关 12窗加热开 13窗加热关 14 ICR 15相机校正
  int32 zoom = 3; // cmd=1/2:速度0~100；cmd=3:倍率0~100
  uint32 camera_id = 4; // 相机 ID（附录 A）
  uint32 focus = 5; // cmd=4/5:速度；cmd=6:聚焦值
  uint32 zero_x = 6; // 闭环零点 X（像素）
  uint32 zero_y = 7; // 闭环零点 Y（像素）
  uint32 detect_camera_mode = 8; // cmd=8: 0自动 1手动
  uint32 detect_camera = 9; // cmd=9: bit0可见光 bit1红外
  uint32 icr = 10; // cmd=14: 0自动 1开(夜视) 2关(彩色)
  uint32 correction = 11; // cmd=15: 0背景 1快门 2虚焦

}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_ptz_zoom
// 对应设备协议: 0x8B 应答

message SpotterPtzZoomReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterPtzZoomOutput output = 2; // 设备侧应答
}

message SpotterPtzZoomOutput {
  int32 result = 1; // 0成功；其他见附录错误码
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_ptz_zoom",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterPtzZoomReqData",
    "sn": "PTZ_SN_001",
    "cmd": 3,
    "zoom": 10,
    "camera_id": 1,
    "focus": 0,
    "zero_x": 0,
    "zero_y": 0,
    "detect_camera_mode": 0,
    "detect_camera": 0,
    "icr": 0,
    "correction": 0
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_ptz_zoom",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterPtzZoomReplyData",
    "result": 0,
    "output": {
      "result": 0
    }
  }
}
```

---

## 0x8C 设置 PTZ 控制模式

### 协议概要

### Protobuf

```Java
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_ptz_ctl_mode
// 对应设备协议: 0x8C 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterPtzCtlModeReqData
// 应答 data payload 类型: cloud.SpotterPtzCtlModeReplyData
message SpotterPtzCtlModeReqData {
  string sn = 1; // PTZ SN 或激光 SN
  uint32 cmd = 2; // 1=配置手动/自动模式
  uint32 ptz_ctl_mode = 3; // cmd=1: 0 AI自动 1手动
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_ptz_ctl_mode
// 对应设备协议: 0x8C 应答

message SpotterPtzCtlModeReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterPtzCtlModeOutput output = 2; // 设备侧应答
}

message SpotterPtzCtlModeOutput {
  int32 result = 1; // 0成功 1失败
  string sn = 2; // PTZ/激光 sn
  uint32 cmd = 3; // 回显命令类型
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_ptz_ctl_mode",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterPtzCtlModeReqData",
    "sn": "PTZ_SN_001",
    "cmd": 1,
    "ptz_ctl_mode": 1
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_ptz_ctl_mode",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterPtzCtlModeReplyData",
    "result": 0,
    "output": {
      "result": 0,
      "sn": "PTZ_SN_001",
      "cmd": 1
    }
  }
}
```

---

## 0x73 查询/设置子设备位姿参数

### 协议概要

### Protobuf

```Java
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_device_position
// 对应设备协议: 0x73 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterDevicePositionReqData
// 应答 data payload 类型: cloud.SpotterDevicePositionReplyData
message SpotterDevicePositionReqData {
  uint32 cmd = 1; // 1查询全部子设备位姿 2设置单个子设备位姿
  string sn = 2; // 子设备 sn
  uint32 type = 3; // 子设备类型（附录 A）
  double longitude = 4; // 经度 (°)
  double latitude = 5; // 纬度 (°)
  float altitude = 6; // 绝对海拔 (m)
  float heading = 7; // 航向角 (°)
  float rolling = 8; // 横滚角 (°)
  float pitching = 9; // 俯仰角 (°)
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_device_position
// 对应设备协议: 0x73 应答

message SpotterDevicePositionReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterDevicePositionOutput output = 2; // 设备侧应答
}

message SpotterDevicePositionOutput {
  int32 result = 1; // 0成功；其他见附录错误码
  uint32 cmd = 2; // 回显 1查询 2设置
  uint32 num = 3; // 子设备数量
  repeated SpotterDevicePositionItem devices = 4; // 子设备位姿列表
}

message SpotterDevicePositionItem {
  string sn = 1; // 子设备 sn
  uint32 type = 2; // 子设备类型
  double longitude = 3;
  double latitude = 4;
  float altitude = 5;
  float heading = 6;
  float rolling = 7;
  float pitching = 8;

}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_device_position",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterDevicePositionReqData",
    "cmd": 1,
    "sn": "",
    "type": 0,
    "longitude": 0,
    "latitude": 0,
    "altitude": 0,
    "heading": 0,
    "rolling": 0,
    "pitching": 0
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_device_position",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterDevicePositionReplyData",
    "result": 0,
    "output": {
      "result": 0,
      "cmd": 1,
      "num": 1,
      "devices": [
        {
          "sn": "RADAR_SN_001",
          "type": 8,
          "longitude": 114.0579,
          "latitude": 22.5431,
          "altitude": 50,
          "heading": 90,
          "rolling": 0,
          "pitching": 0
        }
      ]
    }
  }
}
```

---

## 0x74 一键位置同步校准

### 协议概要

### Protobuf

```Java
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_position_sync
// 对应设备协议: 0x74 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterPositionSyncReqData
// 应答 data payload 类型: cloud.SpotterPositionSyncReplyData
message SpotterPositionSyncReqData {
  uint32 cmd = 1; // 0查询同步结果 1设为不同步 2设为同步
  string sn = 2; // cmd=2: 主设备 sn；空表示同步本机位置给其他子设备
  uint32 type = 3; // cmd=2: 主设备类型；0=本机
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_position_sync
// 对应设备协议: 0x74 应答

message SpotterPositionSyncReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterPositionSyncOutput output = 2; // 设备侧应答
}

message SpotterPositionSyncOutput {
  int32 result = 1; // 0应答成功；其他失败
  uint32 status = 2; // 0未同步 1同步失败 2同步成功
  string sn = 3; // status=1/2: 主设备 sn
  uint32 type = 4; // status=1/2: 主设备类型

}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_position_sync",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterPositionSyncReqData",
    "cmd": 2,
    "sn": "",
    "type": 0
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_position_sync",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterPositionSyncReplyData",
    "result": 0,
    "output": {
      "result": 0,
      "status": 2,
      "sn": "SSF100_SN_001",
      "type": 0
    }
  }
}
```

## 0x91 标定确认

### 协议概要

### Protobuf

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_calib_confirm
// 对应设备协议: 0x91 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterCalibConfirmReqData
// 应答 data payload 类型: cloud.SpotterCalibConfirmReplyData
message SpotterCalibConfirmReqData {
  uint32 request = 1; // 1开始标定 2中断标定 3结果确认 4进手动锁 5出手动锁 6结果取消 7手动选雷达目标 8自动选雷达目标
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_calib_confirm
// 对应设备协议: 0x91 应答

message SpotterCalibConfirmReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterCalibConfirmOutput output = 2; // 设备侧应答
}

message SpotterCalibConfirmOutput {
  uint32 status = 1; // 0成功；其他见错误码
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_calib_confirm",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterCalibConfirmReqData",
    "request": 1
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_calib_confirm",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterCalibConfirmReplyData",
    "result": 0,
    "output": {
      "status": 0
    }
  }
}
```

---

## 0x92 获取标定状态

### 协议概要

### Protobuf

```Java
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_get_calib_status
// 对应设备协议: 0x92 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterCalibStatusReqData
// 应答 data payload 类型: cloud.SpotterCalibStatusReplyData
message SpotterCalibStatusReqData {
  uint32 state = 1; // 固定 0
}

// Topic：thing/product/{Spotter设备SN}/services_reply
// method: spotter_get_calib_status
// 对应设备协议: 0x92 获取标定状态 或 标定完成上报

message SpotterCalibStatusReplyData {
  uint64 timestamp = 1; // 时间戳
  string sn = 2; // 雷达 sn
  uint32 calib_ongoing_state = 3; // 标定进行态（见 PDF 枚举）
  uint32 calib_state = 4; // 标定状态
  float recommend_uav_height = 5; // 建议无人机高度
  float recommend_uav_fly_direction = 6; // 建议飞行方向
  uint32 calib_progress_bar = 7; // 进度 0~100
  uint32 yaw_valid_flag = 8;
  float yaw_mean = 9;
  float yaw_variance = 10;
  float yaw_max_fiff = 11;
  uint32 pitch_valid_flag = 12;
  float pitch_mean = 13;
  float pitch_variance = 14;
  float pitch_max_fiff = 15;
  float yaw_offset = 16; // 偏航偏移 (°)
  float pitch_offset = 17;
  float roll_offset = 18;
  float height_offset = 19; // PTZ 与雷达距离
  uint32 valid_flag = 20; // bit: yaw/pitch 有效
  float yaw_error_mean = 21;
  float yaw_error_std = 22;
  float yaw_error_max_diff = 23;
  float pitch_error_mean = 24;
  float pitch_error_std = 25;
  float pitch_error_max_diff = 26;
  float roll_error_mean = 27;
  float roll_error_std = 28;
  float roll_error_max_diff = 29;

}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "method": "spotter_get_calib_status",
  "gateway": "SSF100_SN_001",
  "data": {
    "state": 0
  }
}
```

### 响应示例

```JSON
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_get_calib_status",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterCalibStatusReplyData ",
    "timestamp": 1667220873800,
    "sn": "RADAR_SN_001",
    "calib_ongoing_state": 8,
    "calib_state": 0,
    "calib_progress_bar": 50,
    "yaw_offset": 0.5,
    "pitch_offset": 0.2,
    "valid_flag": 3
  }
}
```

## 0x92 主动上报标定状态

### 协议概要

### Protobuf

```Java
// Topic: thing/product/{Spotter设备SN}/state
// method: **device_calibration_status**
// 对应设备协议: 0x92 标定完成上报

message SpotterCalibStatusReplyData {
  uint64 timestamp = 1; // 时间戳
  string sn = 2; // 雷达 sn
  uint32 calib_ongoing_state = 3; // 标定进行态（见 PDF 枚举）
  uint32 calib_state = 4; // 标定状态
  float recommend_uav_height = 5; // 建议无人机高度
  float recommend_uav_fly_direction = 6; // 建议飞行方向
  uint32 calib_progress_bar = 7; // 进度 0~100
  uint32 yaw_valid_flag = 8;
  float yaw_mean = 9;
  float yaw_variance = 10;
  float yaw_max_fiff = 11;
  uint32 pitch_valid_flag = 12;
  float pitch_mean = 13;
  float pitch_variance = 14;
  float pitch_max_fiff = 15;
  float yaw_offset = 16; // 偏航偏移 (°)
  float pitch_offset = 17;
  float roll_offset = 18;
  float height_offset = 19; // PTZ 与雷达距离
  uint32 valid_flag = 20; // bit: yaw/pitch 有效
  float yaw_error_mean = 21;
  float yaw_error_std = 22;
  float yaw_error_max_diff = 23;
  float pitch_error_mean = 24;
  float pitch_error_std = 25;
  float pitch_error_max_diff = 26;
  float roll_error_mean = 27;
  float roll_error_std = 28;
  float roll_error_max_diff = 29;

}
```

### 上报示例

```JSON
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "**device_calibration_status**",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterCalibStatusReplyData",
    "timestamp": 1667220873800,
    "sn": "RADAR_SN_001",
    "calib_ongoing_state": 8,
    "calib_state": 0,
    "calib_progress_bar": 50,
    "yaw_offset": 0.5,
    "pitch_offset": 0.2,
    "valid_flag": 3
  }
}
```

---

## 0x93 标定过程数据上报

### 协议概要

### Protobuf

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/state
// method: **device_calibration_data**
// 对应设备协议: 0x93 主动上传设备标定数据

// 外层使用 CloudMessage（见文档开头公共定义），data payload 类型: cloud.SpotterCalibDataPayload
message SpotterCalibDataPayload {
  uint64 timestamp = 1; // 标定数据时间
  uint32 number = 2; // list 数量（= list.length）
  string sn = 3; // 设备 sn
  repeated SpotterCalibDataItem calib_data_list = 4; // 标定过程数据列表
}

message SpotterCalibDataItem {
  double ptz_pitch = 1; // PTZ 俯仰角 (°)
  double ptz_yaw = 2; // PTZ 方位角 (°)
  double radar_yaw = 3; // 雷达方位角 (°)
  double radar_pitch = 4; // 雷达俯仰角 (°)

}

```

### 上报示例

```JSON
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "**device_calibration_data**",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterCalibDataPayload",
    "timestamp": 1667220873800,
    "number": 1,
    "sn": "SSF100_SN_001",
    "calib_data_list": [
      {
        "ptz_pitch": 5.2,
        "ptz_yaw": 120.5,
        "radar_yaw": 118.0,
        "radar_pitch": 4.8
      }
    ]
  }
}
```

---

## 0x9A 启动/停止/查询标定

### 协议概要

### Protobuf

```Java
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_calib_ctrl
// 对应设备协议: 0x9A 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterCalibCtrlReqData
// 应答 data payload 类型: cloud.SpotterCalibCtrlReplyData
message SpotterCalibCtrlReqData {
  uint32 cmd = 1; // 1启动标定 2停止标定 3添加标定方位角 4删除标定方位角 5查询所有雷达历史标定结果
  string sn = 2; // 标定设备 sn（协议/激光/雷达 sn）；cmd=5 时为空
  uint32 angle = 3; // 标定方位角，数值=实际角度×1000；cmd=1/3/4 有效
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_calib_ctrl
// 对应设备协议: 0x9A 应答

message SpotterCalibCtrlReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterCalibCtrlOutput output = 2; // 设备侧应答
}

message SpotterCalibCtrlOutput {
  int32 result = 1; // 0成功；其他见附录错误码
  uint32 cmd = 2; // 回显：1启动 2停止 3添加 4删除 5查询历史
  string sn = 3; // 标定设备 sn；cmd=5 时为空
  uint32 num = 4; // 历史标定方位角数量（= list.length）
  repeated SpotterCalibHistoryItem calib_history_list = 5; // 历史标定列表（cmd=5 时有效）
}

message SpotterCalibHistoryItem {
  string sn = 1; // 标定设备 sn
  uint32 type = 2; // 标定设备类型（附录 A 子设备类型）
  uint32 angle = 3; // 历史标定角度，数值=实际角度×1000
  uint64 calib_timestamp = 4; // 标定角度时间戳 (ms)
  uint32 state_flag = 5; // 0未初始化 1初始化 2标定完成
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_calib_ctrl",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterCalibCtrlReqData",
    "cmd": 1,
    "sn": "RADAR_SN_001",
    "angle": 90000
  }
}
```

### 应答示例（启动/停止）

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "method": "spotter_calib_ctrl",
  "gateway": "SSF100_SN_001",
  "data": {
    "result": 0,
    "output": {
      "result": 0,
      "cmd": 1,
      "sn": "RADAR_SN_001"
      "num": 0,
      "calib_history_list": []
    }
  }
}
```

### 应答示例（cmd=5 查询历史）

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "method": "spotter_calib_ctrl",
  "gateway": "SSF100_SN_001",
  "data": {
    "result": 0,
    "output": {
      "result": 0,
      "cmd": 5,
      "sn": ""
      "num": 1,
      "calib_history_list": [
        {
          "sn": "RADAR_SN_001",
          "type": 8,
          "angle": 90000,
          "calib_timestamp": 1667220870000,
          "state_flag": 2
        }
      ]
    }
  }
}
```

---

## 0x95 选择视频画面像素点目标

### 协议概要

### Protobuf

```Java
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_calib_pixel
// 对应设备协议: 0x95 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterCalibPixelReqData
// 应答 data payload 类型: cloud.SpotterCalibPixelReplyData
message SpotterCalibPixelReqData {
  string sn = 1; // 设备SN（PTZ SN或 激光SN）
  uint32 video_source_enum = 2; // 相机 ID：0红外 1可见光(粗跟踪) 2可见光(精跟踪)
  uint32 pixel_max_u = 3; // 目标框左上角 U
  uint32 pixel_max_v = 4; // 目标框左上角 V
  uint32 pixel_min_u = 5; // 目标框右下角 U
  uint32 pixel_min_v = 6; // 目标框右下角 V
  uint32 pixel_aim_x = 7; // 目标相对整图 X（激光相机）
  uint32 pixel_aim_y = 8; // 目标相对整图 Y（激光相机）
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_calib_pixel
// 对应设备协议: 0x95 应答

message SpotterCalibPixelReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterCalibPixelOutput output = 2; // 设备侧应答
}

message SpotterCalibPixelOutput {
  uint32 status = 1; // 0成功；其他失败
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_calib_pixel",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterCalibPixelReqData",
    "sn": "ptz sn",
    "video_source_enum": 1,
    "pixel_max_u": 100,
    "pixel_max_v": 80,
    "pixel_min_u": 200,
    "pixel_min_v": 180,
    "pixel_aim_x": 150,
    "pixel_aim_y": 130
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_calib_pixel",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterCalibPixelReplyData",
    "result": 0,
    "output": {
      "status": 0
    }
  }
}
```

---

## 0x97 新增或修改 mask 区域

### 协议概要

### Protobuf

```Java
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_upset_mask
// 对应设备协议: 0x97 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterMaskItemData
// 应答 data payload 类型: cloud.SpotterUpsetMaskReplyData
message SpotterMaskItemData {
  string mask_name = 1; // mask 名称
  uint32 mask_id = 2; // mask id
  uint32 used = 3; // 局部生效 0失效 1生效
  float height_s = 4; // 高度起始
  float height_e = 5; // 高度结束
  float velocity_s = 6; // 速度起始
  float velocity_e = 7; // 速度结束
  float rcs_s = 8; // RCS 起始
  float rcs_e = 9; // RCS 结束
  float velocity_as = 10; // 速度角度起始
  float velocity_ae = 11; // 速度角度结束
  uint32 target_type = 12; // 目标类别
  uint32 data_len = 13; // 多边形字节长度（= geometry 字节数）
  string data = 14; // 多边形数据（设备侧原始字节的上云字符串/JSON 表达）
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_upset_mask
// 对应设备协议: 0x97 应答

message SpotterUpsetMaskReplyData {
  int32 result = 1; // 天盾结果
  SpotterUpsetMaskOutput output = 2;
}

message SpotterUpsetMaskOutput {
  uint32 result = 1; // 0成功；其他失败
  string mask_name = 2;
  uint32 mask_id = 3;
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_upset_mask",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterMaskItemData",
    "mask_name": "zone1",
    "mask_id": 1,
    "used": 1,
    "height_s": 0,
    "height_e": 500,
    "velocity_s": 0,
    "velocity_e": 100,
    "rcs_s": 0,
    "rcs_e": 10,
    "velocity_as": 0,
    "velocity_ae": 360,
    "target_type": 1,
    "data_len": 0,
    "data": ""
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_upset_mask",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterUpsetMaskReplyData",
    "result": 0,
    "output": {
      "result": 0,
      "mask_name": "zone1",
      "mask_id": 1
    }
  }
}
```

---

## 0x98 删除 mask 区域

### 协议概要

### Protobuf

```Java
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_delete_mask
// 对应设备协议: 0x98 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterDeleteMaskReqData
// 应答 data payload 类型: cloud.SpotterDeleteMaskReplyData
message SpotterDeleteMaskReqData {
  uint32 delete_all = 1; // 0删除指定 1删除全部 2全局失效 3全局生效
  uint32 mask_num = 2; // 删除数量
  repeated SpotterMaskKey mask_list = 3; // 待删 mask 列表
}

message SpotterMaskKey {
  string mask_name = 1;
  uint32 mask_id = 2;
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_delete_mask
// 对应设备协议: 0x98 应答

message SpotterDeleteMaskReplyData {
  int32 result = 1; // 天盾结果
  SpotterDeleteMaskOutput output = 2;
}

message SpotterDeleteMaskOutput {
  uint32 delete_all = 1; // 0：删除指定mask 1：删除所有mask 2:  全局失效 3：全局生效
  uint32 delete_all_result = 2; // 0成功 1失败
  uint32 mask_num = 3;
  repeated SpotterDeleteMaskItem delete_mask_list = 4;
}

message SpotterDeleteMaskItem {
  uint32 result = 1; // 0成功；其他失败
  string mask_name = 2;
  uint32 mask_id = 3;
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_delete_mask",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterDeleteMaskReqData",
    "delete_all": 0,
    "mask_num": 1,
    "mask_list": [
      {
        "mask_name": "zone1",
        "mask_id": 1
      }
    ]
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_delete_mask",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterDeleteMaskReplyData",
    "result": 0,
    "output": {
      "delete_all": 0,
      "delete_all_result": 0,
      "mask_num": 1,
      "delete_mask_list": [
        {
          "result": 0,
          "mask_name": "zone1",
          "mask_id": 1
        }
      ]
    }
  }
}
```

---

## 0x99 查询 mask 区域

### 协议概要

### Protobuf

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_get_mask_list
// 对应设备协议: 0x99 请求（设备侧 payload 为空）

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterGetMaskListReqData
// 应答 data payload 类型: cloud.SpotterGetMaskListReplyData
message SpotterGetMaskListReqData {
  string sn = 1; //spotter sn
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_get_mask_list
// 对应设备协议: 0x99 应答

message SpotterGetMaskListReplyData {
  int32 result = 1; // 天盾结果
  SpotterGetMaskListOutput output = 2;
}

message SpotterGetMaskListOutput {
  uint32 mask_num = 1; // mask 数量
  uint32 all_used = 2; // 全局 2失效 3生效
  repeated SpotterMaskItemData mask_list = 3;
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_get_mask_list",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterGetMaskListReqData"
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "method": "spotter_get_mask_list",
  "gateway": "SSF100_SN_001",
  "data": {
    "result": 0,
    "output": {
      "mask_num": 1,
      "all_used": 3,
      "mask_list": [
        {
          "mask_name": "zone1",
          "mask_id": 1,
          "used": 1,
          "height_s": 0,
          "height_e": 500,
          "target_type": 1,
          "data_len": 0,
          "data": ""
        }
      ]
    }
  }
}
```

## 0x99 主动上报 mask 区域

### 协议概要

### Protobuf

```Plain Text
//复用 0x97 新增、修改mask结构
// Topic: thing/product/{Spotter设备SN}/state
// method: **device_mark**
// 对应设备协议: 0x99 主动上报（结构同 SpotterGetMaskListOutput）
message SpotterGetMaskListOutput {
  uint32 mask_num = 1; // mask 数量
  uint32 all_used = 2; // 全局 2失效 3生效
  repeated SpotterMaskItemData mask_list = 3;
}

message SpotterMaskItemData {
  string mask_name = 1; // mask 名称
  uint32 mask_id = 2; // mask id
  uint32 used = 3; // 局部生效 0失效 1生效
  float height_s = 4; // 高度起始
  float height_e = 5; // 高度结束
  float velocity_s = 6; // 速度起始
  float velocity_e = 7; // 速度结束
  float rcs_s = 8; // RCS 起始
  float rcs_e = 9; // RCS 结束
  float velocity_as = 10; // 速度角度起始
  float velocity_ae = 11; // 速度角度结束
  uint32 target_type = 12; // 目标类别
  uint32 data_len = 13; // 多边形字节长度（= geometry 字节数）
  string data = 14; // 多边形数据（设备侧原始字节的上云字符串/JSON 表达）
}
```

### 上报示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "method": "**device_mark**",
  "gateway": "SSF100_SN_001",
  "data": {
    "result": 0,
    "output": {
      "mask_num": 1,
      "all_used": 3,
      "mask_list": [
        {
          "mask_name": "zone1",
          "mask_id": 1,
          "used": 1,
          "height_s": 0,
          "height_e": 500,
          "target_type": 1,
          "data_len": 0,
          "data": ""
        }
      ]
    }
  }
}
```

## 0x9E 设置时间同步参数

### 协议概要

### Protobuf

```Java
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_time_sync_set
// 对应设备协议: 0x9E 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterTimeSyncSetReqData
// 应答 data payload 类型: cloud.SpotterTimeSyncSetReplyData
message SpotterTimeSyncSetReqData {
  uint32 mode = 1; // 授时模式 0自动 1手动
  uint32 set_time_source = 2; // 仅 mode=1：0 GNSS_PPS 1 GNSS 2 NTP 3手动设时
  uint64 set_timestamp = 3; // 手动系统时间(ms)；mode=1 且 source=3 有效
  uint32 set_timezone = 4; // UTC 偏移小时（东为正）；mode=1 且 source=3 有效
  string set_ntp_address = 5; // NTP "IP:Port" 或域名
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_time_sync_set
// 对应设备协议: 0x9E 应答

message SpotterTimeSyncSetReplyData {
  int32 result = 1; // 天盾结果
  SpotterTimeSyncSetOutput output = 2;
}

message SpotterTimeSyncSetOutput {
  uint32 result = 1; // 0成功 2写JSON失败 3更新chrony失败 4重启chrony失败 5设时失败 6设时区失败 7非法NTP 8非法mode 9非法时间源 10非法时间戳 11非法时区
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_time_sync_set",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterTimeSyncSetReqData",
    "mode": 1,
    "set_time_source": 2,
    "set_timestamp": 0,
    "set_timezone": 8,
    "set_ntp_address": "ntp.aliyun.com:123"
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "method": "spotter_time_sync_set",
  "gateway": "SSF100_SN_001",
  "data": {
    "result": 0,
    "output": {"result": 0}
  }
}
```

---

## 0x9F 时间同步参数/状态查询

### 协议概要

### Protobuf

```Java
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_time_sync_get
// 对应设备协议: 0x9F 请求（设备侧 payload 为空）

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterTimeSyncGetReqData
// 应答 data payload 类型: cloud.SpotterTimeSyncGetReplyData
message SpotterTimeSyncGetReqData {
  string sn = 1; //spotter sn
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_time_sync_get
// 对应设备协议: 0x9F 应答

message SpotterTimeSyncGetReplyData {
  int32 result = 1; // 天盾结果
  SpotterTimeSyncStatusOutput output = 2;
}

message SpotterTimeSyncStatusOutput {
  uint32 mode = 1; // 0自动 1手动
  uint32 user_selected_time_source = 2; // mode=1: 0 GNSS_PPS 1 GNSS 2 NTP 3手动；mode=0 填 0xFF
  uint32 sync_time_source = 3; // 当前使用：0 GNSS_PPS 1 GNSS 2 NTP 3 LOCAL
  uint64 timestamp = 4; // 当前系统时间(ms)
  uint32 time_zone = 5; // UTC 偏移小时（东为正）
  string ntp_address = 6; // NTP 地址
  uint32 satellite = 7; // 卫星数
  uint32 gnss_work_status = 8; 
  uint32 gnss_pps_time_source_status= 9; // 见 GNSS PPS 状态枚举
  uint32 gnss_time_source_status = 10; // 见 GNSS 状态枚举
  uint32 ntp_time_source_status = 11; // 0 N/A 1初始化 2不可达 3假时钟 4可达 5同步中 6已同步 7错误

}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_time_sync_get",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterTimeSyncGetReqData"
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_time_sync_get",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterTimeSyncGetReplyData",
    "result": 0,
    "output": {
      "mode": 0,
      "user_selected_time_source": 255,
      "sync_time_source": 0,
      "timestamp": 1667220873846,
      "time_zone": 8,
      "ntp_address": "",
      "satellite": 12,
      "gnss_work_status": 1,
      "gnss_pps_time_source_status": 5,
      "gnss_time_source_status": 0,
      "ntp_time_source_status": 0
    }
  }
}
```

## 0x9F 时间同步状态上报

### 协议概要

### Protobuf

```Plain Text
// Topic: thing/product/{Spotter设备SN}/osd
// method: device_time_sync
// 对应设备协议: 0x9F 主动上报

//复用 SpotterTimeSyncStatusOutput 结构
message SpotterTimeSyncStatusOutput {
  uint32 mode = 1; // 0自动 1手动
  uint32 user_selected_time_source = 2; // mode=1: 0 GNSS_PPS 1 GNSS 2 NTP 3手动；mode=0 填 0xFF
  uint32 sync_time_source = 3; // 当前使用：0 GNSS_PPS 1 GNSS 2 NTP 3 LOCAL
  uint64 timestamp = 4; // 当前系统时间(ms)
  uint32 time_zone = 5; // UTC 偏移小时（东为正）
  string ntp_address = 6; // NTP 地址
  uint32 satellite = 7; // 卫星数
  uint32 gnss_work_status = 8; 
  uint32 gnss_pps_time_source_status= 9; // 见 GNSS PPS 状态枚举
  uint32 gnss_time_source_status = 10; // 见 GNSS 状态枚举
  uint32 ntp_time_source_status = 11; // 0 N/A 1初始化 2不可达 3假时钟 4可达 5同步中 6已同步 7错误

}
```

### 上报示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "device_time_sync",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterTimeSyncStatusOutput",
    "result": 0,
    "output": {
      "mode": 0,
      "user_selected_time_source": 255,
      "sync_time_source": 0,
      "timestamp": 1667220873846,
      "time_zone": 8,
      "ntp_address": "",
      "satellite": 12,
      "gnss_work_status": 1,
      "gnss_pps_time_source_status": 5,
      "gnss_time_source_status": 0,
      "ntp_time_source_status": 0
    }
  }
}
```

## 0xD5 获取白名单列表

### 协议概要

### Protobuf

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_get_whitelist
// 对应设备协议: 0xD5 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterGetWhitelistReqData
// 应答 data payload 类型: cloud.SpotterGetWhitelistReplyData
message SpotterGetWhitelistReqData {}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_get_whitelist
// 对应设备协议: 0xD5 应答

message SpotterGetWhitelistReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterGetWhitelistOutput output = 2; // 设备侧应答
}

message SpotterGetWhitelistOutput {
  uint32 status = 1; //0x00：失败 0x01：成功

  uint32 num = 2; // 白名单条数
  repeated SpotterWhitelistItem white_list = 3;
}

message SpotterWhitelistItem {
  string sn = 1; // 无人机 SN

}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_get_whitelist",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterGetWhitelistReqData"
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_get_whitelist",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterGetWhitelistReplyData",
    "result": 0,
    "output": {
      "status": 1,
      "num": 1,
      "white_list": [
        {
          "sn": "DRONE_SN_001"
        }
      ]
    }
  }
}
```

---

## 0xD6 增减白名单

### 协议概要

### Protobuf

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_set_whitelist
// 对应设备协议: 0xD6 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterSetWhitelistReqData
// 应答 data payload 类型: cloud.SpotterSetWhitelistReplyData
message SpotterSetWhitelistReqData {
  uint32 cmd_type = 1; // 0增加白名单(友军) 1删除白名单(敌军)
  uint32 num = 2; // 白名单内无人机总数
  repeated SpotterWhiteDataList white_data_list = 3;
}

message SpotterWhiteDataList {
  string sn = 1; // 无人机 SN
  uint32 id = 2; //无人机id

}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_set_whitelist
// 对应设备协议: 0xD6 应答

message SpotterSetWhitelistReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterSetWhitelistOutput output = 2; // 设备侧应答
}

message SpotterSetWhitelistOutput {
  uint32 status = 1; // 0失败 1成功

}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_set_whitelist",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterSetWhitelistReqData",
    "cmd_type": 0,
    "num": 1,
    "white_data_list": [
      {
        "sn": "DRONE_SN_001",
        "id": 42
      }
    ]
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_set_whitelist",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterSetWhitelistReplyData",
    "result": 0,
    "output": {
      "status": 1
    }
  }
}
```

## 0xC6 惯导信息上报

### 协议概要

### Protobuf

`Topic: thing/product/{惯导设备SN}/osd`
`method: device_heart`

```ProtoBuf
// Topic: thing/product/{惯导设备SN}/osd
// method: device_heart
// 对应设备协议: 0xC6 / AgxInsHeartInfo

// 外层使用 CloudMessage（见文档开头公共定义），data payload 类型: cloud.SpotterInsHeartData
message SpotterInsHeartData {
  uint32 subtype = 1; // 子设备类型，差分GPS惯导=18
  uint32 sub_msg_id = 2; // 子消息 ID，固定 0x01
  string sn = 3; // 惯导子设备 sn
  uint32 cnt = 4; // 循环计数
  uint32 sys_status = 5; // 系统状态 bit0在线 bit1异常
  uint32 work_status = 6; // 0待机 1开机
  uint64 timestamp_ms = 7; // 收到 GPS 数据时间戳 (ms)
  uint64 gps_timestamp_ms = 8; // GPS 原始时间戳 (ms)
  float heading = 9; // 航向角 0~360 (°)
  float pitch = 10; // 俯仰角 -90~90 (°)
  float roll = 11; // 横滚角 -180~180 (°)
  double latitude = 12; // 纬度 (°)
  double longitude = 13; // 经度 (°)
  float altitude = 14; // 海拔 (m)
  float v_e = 15; // 东向速度 (m/s)
  float v_n = 16; // 北向速度 (m/s)
  float v_u = 17; // 天向速度 (m/s)
  float baseline = 18; // 基线长度 (m)
  uint32 nsv1 = 19; // 天线1 卫星数
  uint32 nsv2 = 20; // 天线2 卫星数
  uint32 gps_status = 21; // 0未定位 1单点 2RTD 3RTK浮点 4RTK固定
  uint32 speed_status = 22; // 0无车体速度 1有车体速度
  float vehicle_speed = 23; // 车体速度 (km/h)
  float acc_x = 24; // 加速度 X (m/s²)
  float acc_y = 25; // 加速度 Y (m/s²)
  float acc_z = 26; // 加速度 Z (m/s²)
  float gyro_x = 27; // 陀螺 X (°/s)
  float gyro_y = 28; // 陀螺 Y (°/s)
  float gyro_z = 29; // 陀螺 Z (°/s)
}

```

### 上报示例

```JSON
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "method": "device_heart",
  "gateway": "SRP200_SN_001",
  "data": {
    "subtype": 18,
    "sub_msg_id": 1,
    "sn": "INS_SN_001",
    "heading": 90.0,
    "latitude": 22.5431,
    "longitude": 114.0579,
    "altitude": 50.0,
    "gps_status": 4,
    "vehicle_speed": 0
  }
}
```

## 0xCA 下发子设备相对坐标

### 协议概要

### Protobuf

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_set_relative_xyz
// 对应设备协议: 0xCA 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterSetRelativeXyzReqData
// 应答 data payload 类型: cloud.SpotterSetRelativeXyzReplyData
message SpotterSetRelativeXyzReqData {
  uint64 timestamp = 1; // 毫秒时间戳
  uint32 num = 2; // 子设备数量
  repeated SpotterRelativeXyzItem relative_xyz_list = 3;
}

message SpotterRelativeXyzItem {
  string sn = 1; // 子设备 sn
  uint32 devid = 2; // 子设备类型
  float x = 3; // x相对坐标
  float y = 4; //y相对坐标
  float z = 5; //z相对坐标
  float heading = 6; // 航向 0~360
  float pitch = 7; // 俯仰 -90~90
  float roll = 8; // 横滚 -180~180
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_set_relative_xyz
// 对应设备协议: 0xCA 应答

message SpotterSetRelativeXyzReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterSetRelativeXyzOutput output = 2; // 设备侧应答
}

message SpotterSetRelativeXyzOutput {
  uint32 status = 1; // 0成功；其他失败
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_set_relative_xyz",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterSetRelativeXyzReqData",
    "timestamp": 1667220873800,
    "num": 1,
    "relative_xyz_list": [
      {
        "sn": "RADAR_SN_001",
        "dev_id": 8,
        "x": 1,
        "y": 0,
        "z": 0,
        "heading": 90,
        "pitch": 0,
        "roll": 0
      }
    ]
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_set_relative_xyz",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterSetRelativeXyzReplyData",
    "result": 0,
    "output": {
      "status": 0
    }
  }
}
```

---

## 0xCB 获取子设备相对坐标

### 协议概要

### Protobuf

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_get_relative_xyz
// 对应设备协议: 0xCB 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterGetRelativeXyzReqData
// 应答 data payload 类型: cloud.SpotterGetRelativeXyzReplyData
message SpotterGetRelativeXyzReqData {
  uint64 timestamp = 1; // 毫秒时间戳
  uint32 num = 2; //下发sn个数
  repeated SpotterRelativeXyzQueryItem relative_xyz_query_list = 3;
}

message SpotterRelativeXyzQueryItem {
  string sn = 1; //设备sn
  uint32 devid = 2; //设备id
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_get_relative_xyz
// 对应设备协议: 0xCB 应答

message SpotterGetRelativeXyzReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterGetRelativeXyzOutput output = 2; // 设备侧应答
}

message SpotterGetRelativeXyzOutput {
  uint32 num = 1;
  repeated SpotterRelativeXyzItem list = 2; // 复用 0xCA 请求结构RelativeXyzItem
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_get_relative_xyz",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterGetRelativeXyzReqData",
    "timestamp": 1667220873800,
    "num": 1,
    "relative_xyz_query_list": [
      {
        "sn": "RADAR_SN_001",
        "dev_id": 8
      }
    ]
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_get_relative_xyz",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterGetRelativeXyzReplyData",
    "result": 0,
    "output": {
      "num": 1,
      "list": [
        {
          "sn": "RADAR_SN_001",
          "dev_id": 8,
          "x": 1,
          "y": 0,
          "z": 0,
          "heading": 90,
          "pitch": 0,
          "roll": 0
        }
      ]
    }
  }
}
```

## 0xA6 设置雷达配置

### 协议概要

### Protobuf

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_set_dph_config
// 对应设备协议: 0xA6 请求

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterDphConfigData
// 应答 data payload 类型: cloud.SpotterSetDphConfigReplyData
message SpotterDphConfigData {
  string sn = 1; // 雷达前端 sn（DPH120/130）
  uint32 frequency = 2; // 工作频点 0~20：0=9.2GHz … 20=9.8GHz
  int32 range_compe = 3; // 距离补偿，精度0.1, 默认填0
  int32 azi_compe = 4; // 方位角补偿，精度0.1 -180°~180° ，默认填0
  int32 pitch_compe = 5; // 俯仰角补偿，精度0.1 -180°~180° , 默认填0
  double lot = 6; // 经度，单位度, 无效值 0xFFFF
  double lat = 7; // 纬度，单位度, 无效值 0xFFFF
  double height = 8; // 高度，单位米，绝对海拔高度, 无效值 0xFFFF
  uint32 range = 9; // 量程 0x11:7.5Km 0x22:15Km
  int32 min_height_under_3km = 10; // 3Km 以内高度下限
  int32 min_height_beyond_3km = 11; // 3Km 以外高度下限
  int32 max_height = 12; // 高度上限
  float max_speed = 13; // 速度上限
  float min_speed = 14; // 速度下限
  uint32 max_range = 15; // 距离上限
  uint32 min_range = 16; // 距离下限
  float azimuth_angle = 17; // 方位角（PTZ 法线与雷达法线夹角）
  float roll_angle = 18; // 阵面横滚角
  float pitch_angle = 19; // 阵面俯仰角
  float north_angle = 20; // 较北角
  float servo_direct = 21; // 伺服指向
  float scan_cycle = 22; // 扫描周期
  uint32 maskzone1_enable = 23; // 静默区1使能 0不使能、1使能
  float maskzone1_start = 24; // 静默区1起始角
  float maskzone1_end = 25; // 静默区1结束角
  uint32 maskzone2_enable = 26; // 静默区2使能：0不使能、1使能
  float maskzone2_start = 27;
  float maskzone2_end = 28;
  uint32 detect_ctrl = 29; // 0关闭侦测 1开启侦测
  uint32 use_mode = 30; // 0对空 1对地
  uint32 identify_enable = 31; // 识别使能 0不使能 1使能 （默认）

}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_set_dph_config
// 对应设备协议: 0xA6 应答

message SpotterSetDphConfigReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterSetDphConfigOutput output = 2; // 设备侧应答
}

message SpotterSetDphConfigOutput {
  uint32 result = 1; // 0失败 1成功
  uint32 error_code = 2; // 错误码
}

```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SSF100_SN_001",
  "method": "spotter_set_dph_config",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterDphConfigData",
    "sn": "DPH120_SN_001",
    "frequency": 10,
    "range": 17,
    "detect_ctrl": 1,
    "use_mode": 0
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_set_dph_config",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterSetDphConfigReplyData",
    "result": 0,
    "output": {
      "result": 1,
      "error_code": 0
    }
  }
}
```

## 0xA7 获取雷达配置

### 协议概要

### Protobuf

`请求Topic: thing/product/{Spotter设备SN}/services`

`应答Topic: thing/product/{Spotter设备SN}/services_reply`
`method: spotter_get_dph_config`

```ProtoBuf
// Topic: thing/product/{Spotter设备SN}/services
// method: spotter_get_dph_config
// 对应设备协议: 0xA7

// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.SpotterGetDphConfigReqData
// 应答 data payload 类型: cloud.SpotterGetDphConfigReplyData
message SpotterGetDphConfigReqData {
  string sn = 1; // 雷达前端 sn（DPH120/130）
}

// Topic: thing/product/{Spotter设备SN}/services_reply
// method: spotter_get_dph_config
// 对应设备协议: 0xA7 应答

message SpotterGetDphConfigReplyData {
  int32 result = 1; // 天盾结果 0成功 1失败 2超时 3离线 4状态冲突 5重启中
  SpotterDphConfigData output = 2; // 设备侧配置应答
}

//复用 0xA6设置参数
```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "SRP200_SN_001",
  "method": "spotter_get_dph_config",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterGetDphConfigReqData",
    "sn": "DPH120_SN_001"
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "SSF100_SN_001",
  "method": "spotter_get_dph_config",
  "data": {
    "@type": "type.googleapis.com/cloud.SpotterGetDphConfigReplyData",
    "result": 0,
    "output": {
      "sn": "DPH120_SN_001",
      "frequency": 10,
      "range": 17,
      "detect_ctrl": 1,
      "use_mode": 0
    }
  }
}
```

## [雷达SDH100上云协议](https://vxr5wm8r80r.feishu.cn/wiki/E2l4wMeogioRzskhcffcLADqnCh)

## [Tracer matrix直接上云协议](https://vxr5wm8r80r.feishu.cn/wiki/F9onwnzwdibU8Mk1lo0cSG5anrf)

