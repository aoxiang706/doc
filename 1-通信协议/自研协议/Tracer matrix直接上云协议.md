# Tracer matrix直接上云协议

## 通用约定

### 1\.1 JSON 示例：

```JSON
{
  "tid": "<uuid>",
  "bid": "<uuid>",
  "timestamp": 1667220873846,
  "method": "<见各协议>",
  "gateway": "STF200_SN_001",
  "data": {}
}
```

- `gateway` = STF200 SN（与 Topic 中 SN 一致）

- 字段命名：与协议文档一致

- 云侧 `services_reply.data.result`：`0`成功 `1`失败 `2`超时 `3`离线 `4`状态冲突 `5`重启中

## 公共 CloudMessage 定义

Tracer 协议作为 3 份上云协议文档（Spotter/Spotter Pro、SDH100、Tracer）之一，统一使用以下统一使用以下 `CloudMessage` 作为外层信封。各协议只需定义业务 payload message，通过 `google.protobuf.Any` 承载在 `data` 字段中，`type_url` 标识具体 payload 类型。

所有协议 `import "cloud_message.proto"`，共用同一外层信封。

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
  string method    = 5;  // "spotter_fusion_targets" / "sdh100_xxx" / "stf200_xxx" / ...
  google.protobuf.Any data = 6;  // 业务载荷，type_url 标识具体 payload 类型
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
  "gateway": "STF200_SN_001",
  "method": "stf200_get_device_info",
  "data": {
    "@type": "type.googleapis.com/cloud.Stf200GetDeviceInfoReqData",
    "sn": "STF200_SN_001",
    "timestamp": 1667220873800
  }
}
```

**Any 路线 vs Struct 路线 — 关键 Trade\-off**

- ✅ **类型安全**：`unpack(XxxData.class)` 编译期校验 payload 类型

- ✅ **code\-gen 强类型**：所有语言 SDK 一行 unpack 拿到强类型字段

- ✅ **跨语言 SDK 自动**：protobuf 工具链覆盖 C\+\+/Java/Go/Python

- ✅ **wire 编码零损耗**：payload 是原 message 编码

- ✅ **调试可读**：`.toString()` 是结构化 protobuf text format

- ⚠️ **加 method 需改外层 proto 重生成代码**（可控、低频）

- ⚠️ **type\_url 是字符串约定**，写错类型 unpack 失败靠 runtime 报错

**⚠️ Wire Format 大变更**
CloudMessage 完全替代原外层 message（如 `Tracer` 各方法原 `XxxRequest` / `XxxReply`），是 wire\-format 大变更。所有现存 device/cloud 解析代码全部失效，需同步改造。

---

### 1\.2 协议一览

## Method → Payload 字段映射表

Tracer 协议所有 method 对应的业务 payload type。请求/应答共享同一 method 值，靠 Topic 区分方向（`/services` = 请求，`/services_reply` = 应答，`/osd` = 上报）。

|method|请求 payload|应答 payload|Topic|
|---|---|---|---|
|`stf200_ai_config`|`cloud.Stf200AIConfig`|`cloud.Stf200AiConfigReplyData`|`/services & /services_reply`|
|`stf200_basic_work_para`|`cloud.Stf200BasicWorkParaConfig`|`cloud.Stf200BasicWorkParaReplyData`|`/services & /services_reply`|
|`stf200_data_transfer`|`cloud.Stf200DataTransferReqData`|`cloud.Stf200DataTransferReplyData`|`/services & /services_reply`|
|`stf200_decrypt_result`|`cloud.Stf200DecryptResultReqData`|`cloud.Stf200DecryptResultReplyData`|`/services & /services_reply`|
|`stf200_detect_collect`|`cloud.Stf200DetectTargetCollectConfig`|`cloud.Stf200DetectCollectReplyData`|`/services & /services_reply`|
|`stf200_detect_database`|`cloud.Stf200DetectDataBaseConfig`|`cloud.Stf200DetectDatabaseReplyData`|`/services & /services_reply`|
|`device_uav`|`—`|`cloud.Stf200DetectionTargetsReport`|`thing/product/{STF200设备SN}/osd`|
|`device_encrypt_uav`|`—`|`cloud.Stf200EncryptStreamData`|thing/product/\{STF200设备SN\}/osd|
|`stf200_freq_stream`待确认|`—`|`cloud.Stf200FreqStreamData`|`/osd`|
|`stf200_get_device_info`|`cloud.Stf200GetDeviceInfoReqData`|`cloud.Stf200GetDeviceInfoReplyData`|`/services & /services_reply`|
|`stf200_get_time_info`|`cloud.Stf200GetTimeInfoEventData`|`cloud.Stf200GetTimeInfoData`|`/services & /services_reply`|
|`stf200_ip_config`|`cloud.Stf200IpConfigReqData`|`cloud.Stf200IpConfigReplyData`|`/services & /services_reply`|
|`device_heart`|`—`|`cloud.Stf200LinkStatusData`|`thing/product/{STF200 子设备SN}/osd`|
|`stf200_ntp_config`|`cloud.Stf200NTPParaConfig`|`cloud.Stf200NtpConfigReplyData`|`/services & /services_reply`|
|`stf200_position_orientation`|`cloud.Stf200PositionOrientationConfig`|`cloud.Stf200PositionOrientationReplyData`|`/services & /services_reply`|
|`device_posture`||`Stf200PositionOrientationConfig `<br>|thing/product/\{STF200设备SN\}/osd|
|`stf200_rf_detect_config`|`cloud.Stf200RFDetectConfig`|`cloud.Stf200RfDetectConfigReplyData`|`/services & /services_reply`|
|`stf200_rf_filter`|`cloud.Stf200DetectFilterConfig`|`cloud.Stf200RfFilterReplyData`|`/services & /services_reply`|
|`stf200_rf_track_targets`|`cloud.Stf200RFTrackTargetsConfig`|`cloud.Stf200RfTrackTargetsReplyData`|`/services & /services_reply`|
|`stf200_spectrum_monitor`|`cloud.Stf200SpectrumMonitorSetting`|`cloud.Stf200SpectrumMonitorReplyData`|`/services & /services_reply`|
|`stf200_spectrum_monitor_result`待确认|`—`|`cloud.Stf200ReportSpectrumMonitorResultPB`|`/osd`|
|`stf200_wifi_filter`|`cloud.Stf200BeaconFilterConfig`|`cloud.Stf200WifiFilterReplyData`|`/services & /services_reply`|
|`device_heart`|`—`|`cloud.Stf200WorkStatusData`|`thing/product/{STF200设备SN}/osd`|

## 0x0010 设备信息查询

### 协议概要

### Protobuf

```protobuf
// ========== 请求 ==========
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_get_device_info
// 对应设备协议: 0x0010 / DataRequest
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200GetDeviceInfoReqData


message Stf200GetDeviceInfoReqData {  
    // 请求类型，固定 1=查询（对应 DataRequest.request_mode）  
    uint32 request_mode = 1;
}

<em>// ========== 应答 ==========</em>
<em>// Topic: thing/product/{STF200 设备SN}/services_reply</em>
<em>// method: stf200_get_device_info</em>
<em>// 对应设备协议: 0x0010 / DeviceStatusResponse</em>
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200GetDeviceInfoReplyData

message Stf200GetDeviceInfoReplyData {
  <em>// 云侧统一结果码:</em>
  <em>// 0:成功 1:失败 2:超时 3:设备不在线 4:状态冲突 5:重启中</em>
  int32 result = 1;
  Stf200DeviceInfoOutput output = 2;  <em>// result=0 时有效</em>
}
message Stf200DeviceInfoOutput {
  <em>// 设备侧 request_mode:</em>
  <em>// 1: 查询成功</em>
  <em>// >255 为错误码:</em>
  <em>// 256: 不支持的请求类型</em>
  <em>// 257: 查询失败</em>
  uint32 request_mode = 1;
  uint32 device_type = 2;      <em>// 设备类型码 0~255</em>
  string device_sn = 3;        <em>// 设备 SN，最长 32</em>
  string hw_version = 4;       <em>// 硬件版本，最长 32</em>
  string sw_version = 5;       <em>// 软件版本，最长 32</em>
  <em>// 设备侧为 Uint8*6；上云建议用字符串，如 "AA:BB:CC:DD:EE:FF"</em>
  string device_mac = 6;
  <em>// 设备侧为 Uint8*4；上云建议用字符串，如 "192.168.1.50"</em>
  string device_ip = 7;
}

```

### 请求示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_get_device_info",
  "data": {
    "request_mode": 1,
    "@type": "type.googleapis.com/cloud.Stf200GetDeviceInfoReqData"
  }
}
```

### 应答示例

```JSON
//应答示例
//应答（成功）
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "method": "stf200_get_device_info",
  "gateway": "STF200_SN_001",
  "data": {
    "result": 0,
    "output": {
      "request_mode": 1,
      "device_type": 33,
      "device_sn": "STF200_SN_001",
      "hw_version": "HW_V1.0.0",
      "sw_version": "SW_V2.1.3",
      "device_mac": "AA:BB:CC:DD:EE:FF",
      "device_ip": "192.168.1.50"
    }
  }
}
//应答（失败）
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "method": "stf200_get_device_info",
  "gateway": "STF200_SN_001",
  "data": {
    "result": 1,
    "output": {
      "request_mode": 257,
      "device_type": 0,
      "device_sn": "",
      "hw_version": "",
      "sw_version": "",
      "device_mac": "",
      "device_ip": ""
    }
  }
}
```

## 0x0012 工作状态上报

### 协议概要

### Protobuf

```protobuf
<em>// Topic: thing/product/{STF200设备SN}/osd</em>
<em>// method: device_heart
<em>// 对应设备协议: 0x0012 / DeviceWorkStatusResponse</em>
// 外层使用 CloudMessage（见文档开头公共定义）
// 上报 data payload 类型: cloud.Stf200WorkStatusData


message Stf200WorkStatusData {
  <em>// 0:主动上报 1:查询成功</em>
  <em>// >255 错误码: 256不支持的请求类型 257查询失败</em>
  uint32 request_mode = 1;
  uint64 device_time = 2;              <em>// 设备时间 ms（文档拼写 deveice_time，此处按正确拼写）</em>
  <em>// 自检状态字:</em>
  <em>// B0 频谱模组异常  B1 协议模组异常  B2 预留</em>
  <em>// B3 综控模组异常  B4 温度异常  B5 同步信号异常</em>
  <em>// B6 GPS定位异常  B7 频谱检测饱和  B8-31 预留</em>
  uint32 check_status = 3;
  <em>// 工作状态字:</em>
  <em>// B0 关闭侦测(0工作/1关闭)  B1 广域侦测  B2 旋转侦测</em>
  <em>// B3 抵近侦测  B4 外同步有效  B5 频谱图采集</em>
  <em>// B6 原始IQ采集  B7 频谱图传输  B8 测试模式</em>
  <em>// B9 数据队列满载  B10-31 预留</em>
  uint32 work_status = 4;
  <em>// 系统温度℃ *7: 面阵Module1-4、一体板1-2、主机</em>
  <em>// 文档字段名: sys_temprature_list</em>
  repeated float sys_temprature_list = 5;
  Stf200FaultMessage fault_msg = 6;
  double longitude = 7;
  double latitude = 8;
  float altitude = 9;
  float yaw = 10;
  float pitch = 11;
  float roll = 12;
  uint32 scan_period = 13;             <em>// 频率扫描周期 ms</em>
  uint32 scan_freq_num = 14;           <em>// 频率扫描个数</em>
  <em>// [0]搜星状态 0正常/1异常  [1]GPS搜星数量</em>
  repeated uint32 gps_state = 15;
  double longitude_gps = 16;
  double latitude_gps = 17;
  float altitude_gps = 18;
  float yaw_imu = 19;
  float pitch_imu = 20;
  float roll_imu = 21;
  <em>// [0]设备状态: 0开机中 1自检中(~10s) 2侦测中</em>
  <em>// [1]无线电环境(已取消)  [2]探测性能(已取消)</em>
  <em>// [3]时间来源: 0 EDGE / 1 NTP / 2 手动 / 3 chrony</em>
  repeated uint32 global_state = 22;
  string time_now = 23;                <em>// 如 "2026/02/11 00:00:00 UTC"</em>
  string last_update_time = 24;        <em>// 如 "2026/02/11 00:00:00 UTC"</em>
}

<em>// Stf200FaultMessage PB定义（文档驼峰）</em>
message Stf200FaultMessage {
  string sn = 1;                       <em>// 设备 SN，最长 25</em>
  uint32 err_num = 2;                   <em>// 错误数量</em>
  repeated Stf200FirstClass first_class = 3;  <em>// 一级错误列表，0~32</em>
}

<em>// Stf200FirstClass PB定义（文档驼峰）</em>
message Stf200FirstClass {
  uint32 first_level_code = 1;
  uint32 second_level_code = 2;
  uint32 third_level_code = 3;
  uint32 four_err_num = 4;
  repeated Stf200SecondClass second_class = 5; <em>// 0~32</em>
}

<em>// Stf200SecondClass PB定义（文档驼峰）</em>
message Stf200SecondClass {
  uint32 four_level_code = 1;            <em>// 四级业务错误码</em>
  string four_level_msg = 2;             <em>// 错误描述，最长 50</em>
}
```

### 上报示例

```JSON
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "method": "device_heart",
  "gateway": "STF200_SN_001",
  "data": {
    "request_mode": 0,
    "device_time": 1667220873800,
    "check_status": 0,
    "work_status": 2,
    "sys_temprature_list": [
      42.1,
      41.8,
      43.0,
      42.5,
      45.2,
      44.8,
      48.0
    ],
    "fault_msg": {
      "sn": "STF200_SN_001",
      "err_num": 1,
      "first_class": [
        {
          "first_level_code": 1,
          "second_level_code": 1001,
          "third_level_code": 2001,
          "four_err_num": 1,
          "second_class": [
            {
              "four_level_code": 30001,
              "four_level_msg": "spectrum module over temperature"
            }
          ]
        }
      ]
    },
    "longitude": 114.05789,
    "latitude": 22.54321,
    "altitude": 35.5,
    "yaw": 90.0,
    "pitch": 1.2,
    "roll": -0.5,
    "scan_period": 1000,
    "scan_freq_num": 16,
    "gps_state": [
      0,
      12
    ],
    "longitude_gps": 114.05788,
    "latitude_gps": 22.5432,
    "altitude_gps": 34.8,
    "yaw_imu": 90.1,
    "pitch_imu": 1.1,
    "roll_imu": -0.4,
    "global_state": [
      2,
      0,
      0,
      1
    ],
    "time_now": "2026/02/11 00:00:00 UTC",
    "last_update_time": "2026/02/10 18:30:00 UTC",
    "@type": "type.googleapis.com/cloud.Stf200WorkStatusData"
  }
}
```

## 0x0014 获取时间信息

### 协议概要

### Protobuf

```protobuf
<em>// Topic: thing/product/{STF200设备SN}/requests</em>
<em>// method: stf200_get_time_info</em>
<em>// 对应设备: 0x0014 请求，参数长度 0</em>
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200GetTimeInfoEventData


message Stf200GetTimeInfoEventData {}

<em>// ========== 应答：云下发时间 ==========
// Topic: thing/product/{STF200设备SN}/requests_reply
// method: stf200_get_time_info
// 对应设备: 0x0014 应答，time(20) + time_zone(1)
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200GetTimeInfoData

message Stf200GetTimeInfoData {
  string time = 1;         // YYYYMMDDHHMMSS.sss，固定 20 字符
  int32 time_zone = 2;     // 时区设置（文档 int8）
</em><em>}</em>
```

### 请求示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_get_time_info",
  "data": {
    "@type": "type.googleapis.com/cloud.Stf200GetTimeInfoEventData"
  }
}
```

### 应答示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995800,
  "gateway": "STF200_SN_001",
  "method": "stf200_get_time_info",
  "data": {
    "time": "20240515011746.901",
    "time_zone": 8,
    "@type": "type.googleapis.com/cloud.Stf200GetTimeInfoEventData"
  }
}
```

## 0x0015 上报4个子设备的工作状态

### 协议概要

### Protobuf

```protobuf
<em>// Topic: thing/product/{STF200 子设备SN}/osd
<em>// method: device_heart
<em>// 对应设备协议: 0x0015 / TracerAirLinkStatusReport</em>
// 外层使用 CloudMessage（见文档开头公共定义）
// 上报 data payload 类型: cloud.Stf200LinkStatusData

message Stf200LinkStatusData {
  <em>// 0:主动上报 1:查询成功</em>
  <em>// >255: 256不支持的请求类型 257查询失败</em>
  uint32 request_mode = 1;
  uint64 matrix_time_ms = 2;         <em>// TracerMatrix 本地时间 ms</em>
  string sn = 3; //设备sn
  uint32 unit_num = 4;               <em>// 有效子设备条数，固定 4（只处理频谱子设备）</em>
  repeated Stf200AirLinkStatusUnit unit_list = 5;
}

message Stf200AirLinkStatusUnit {
  uint32 slot_index = 1;             <em>// 槽位索引，从 0 递增</em>
  string sn = 2;                     <em>// 子设备 SN</em>
  <em>// 1:在线侦测中 2:在线待机中 3:离线 4:异常</em>
  uint32 link_state = 3;
  uint32 fault = 4;                  <em>// 异常状态（当前未使用）</em>
  float azimuth = 5;                 <em>// 配置方位角 °</em>
}
```

### 上报示例

```json
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "device_heart",
  "data": {
    "request_mode": 0,
    "matrix_time_ms": 1667220873800,
    "sn": "stf200 sn",
    "unit_num": 4,
    "unit_list": [
      {
        "slot_index": 0,
        "sn": "TRACER_AIR_SN_001",
        "link_state": 1,
        "fault": 0,
        "azimuth": 0.0
      },
      {
        "slot_index": 1,
        "sn": "TRACER_AIR_SN_002",
        "link_state": 2,
        "fault": 0,
        "azimuth": 90.0
      },
      {
        "slot_index": 2,
        "sn": "TRACER_AIR_SN_003",
        "link_state": 3,
        "fault": 0,
        "azimuth": 180.0
      },
      {
        "slot_index": 3,
        "sn": "TRACER_AIR_SN_004",
        "link_state": 1,
        "fault": 0,
        "azimuth": 270.0
      }
    ],
    "@type": "type.googleapis.com/cloud.Stf200LinkStatusData"
  }
}
```

## 0x0020 侦测目标上报（包含协议和频谱） \-\-单设备

### 协议概要

### Protobuf

```protobuf
<em>// Topic: thing/product/{STF200设备SN}/osd</em>
<em>// method: device_uav
<em>// 对应设备协议: 0x0020 / Stf200DetectionTargetsReport (BeaconResult)</em>
// 外层使用 CloudMessage（见文档开头公共定义）
// 上报 data payload 类型: cloud.Stf200DetectionTargetsReport

<em>// 频谱+协议同时上报 request_mode=3</em>
message Stf200DetectionTargetsReport {
  <em>// 3:频谱+协议目标</em>
  <em>// >255: 256不支持的请求类型 257查询失败</em>
  uint32 request_mode = 1;
  uint32 target_total_num = 2;       <em>// 总个数 T = N + M</em>
  uint32 sp_target_total_num = 3;    <em>// 频谱目标个数 N</em>
  repeated Stf200SPTarget sp_target_list = 4;
  uint32 pt_target_total_num = 5;    <em>// 协议目标个数 M</em>
  repeated Stf200PTTarget pt_target_list = 6;
}
<em>// ---------- Stf200SPTarget 频谱目标 ----------</em>
message Stf200SPTarget {
  uint32 target_num = 1;
  <em>// B0-B15 数值: 1数字图传 2模拟图传 3Wifi图传 4FK上行 5FK下行</em>
  <em>// 6前导 7信号 8干扰源 9遥控 10基站 11自定义干扰 12自定义遥控 13自定义通信</em>
  <em>// B16 AI增强  B17支持频率跟踪  B18处于频率跟踪  B19指定跟踪目标</em>
  <em>// B20空中  B21地面  B22扩展  B23测向有效  B24自定义目标</em>
  <em>// B25未知威胁检测  B26：未知威胁检测策略码1 B27：未知威胁检测策略码2 B28：未知威胁检测策略码3</em>
  uint32 target_type = 2;
  uint32 target_code = 3; //目标标志码 用于标识目标频谱信号在整个数据系统内的唯一索引
  string target_name = 4; //无人机名称/Beacon-WIFI名称 字符串
  <em>// B0发现 B1跟踪 B2记忆 B3消失</em>
  uint32 track_status = 5;
  uint64 track_time_create = 6; //建立时间 UTC毫秒计数（系统设置时间）
  uint64 track_time_last = 7; //最近测量时间 UTC毫秒计数（系统设置时间）
  bytes target_chara_code = 8;       <em>// Uint8*32 无人机特征码（字符串）</em>
  uint32 target_confidence = 9; //目标置信度
  uint32 track_cnt = 10; //测量次数
  float track_frequence = 11; <em>//信号频率/MHz</em>
  float track_bw = 12; //信号带宽/MHz  
  int32 track_bws = 13; //跟踪频率起始索引
  int32 track_bwe = 14; //跟踪频率终止索引
  float track_cf = 15; //信号所在接收机本振频点/MHz
  float track_ef = 16; //信号扩展描述频率/MHz
  float track_pow = 17; //信号功率/dBm 
  float track_noice = 18; <em>//噪声功率/dBm </em>
  float track_snr = 19; //信噪比/dB
  float track_distance = 20; //距离估计/m
  float track_ct = 21; //特征时间/us <b>注：仅数字图传、模拟图传、飞控上下行有效</b>
  float track_az = 22; //测量方位/°（固定系）
  float track_ei = 23; //测量俯仰/°（固定系）
  float track_az_err = 24; //测量方位误差范围/°
  float track_el_err = 25; //测量俯仰误差范围/°
  uint64 track_angle_time = 26; //角度测量时间 UTC毫秒计数 同huntermax联动时作为<b> 脉冲上升沿时间</b>
  uint32 track_pdw_type = 27; //目标PDW类型
  float track_f_start = 28; //目标信号起始频率
  float track_f_end = 29; //目标信号结束频率
  uint32 track_pri_num = 30; //目标周期个数
  repeated float track_pri_value = 31; <em>//目标周期数组</em>
  uint32 track_pw_num = 32; //目标脉冲个数
  repeated float track_pw_value = 33;  <em>//目标脉冲数组</em>
  <em>// B0白名单 B1特征测量时间有效 B2本地时间有效</em>
  <em>// B3 GPS PPS有效 B4数据融合(被协议关联) B5固定坐标系有效</em>
  uint32 target_proc_status = 34;
  uint32 ex_info_1 = 35;               <em>// 特征测量时间-秒</em>
  uint32 ex_info_2 = 36;               <em>// 特征测量时间-纳秒</em>
  float ex_info_3 = 37;                <em>// 原始测量方位 °</em>
  float ex_info_4 = 38;                <em>// 原始测量俯仰 °</em>
  uint32 SpectMatchProtocol = 39;    <em>// 文档 PascalCase：对应协议目标编号</em>
}
<em>// ---------- Stf200PTTarget 协议目标 ----------</em>
message Stf200PTTarget {
  uint32 drone_num = 1; //无人机编号
  <em>// 按位可多选: B0 DID未加密 B1 DID加密 B2 RID-WiFi B3 RID-BT B5 DID-Detected</em>
  uint32 drone_type = 2;
  string drone_name = 3; //字符串 无人机名称
  <em>// B0发现 B1跟踪 B2记忆 B3消失</em>
  uint32 track_status = 4;
  uint64 track_time_create = 5; //建立时间  UTC毫秒计数（系统设置时间）
  uint64 track_time_last = 6; //最近测量时间 UTC毫秒计数（系统设置时间）
  bytes track_sn = 7; <em>// Uint8*32 无人机SN码 前20 SN + 中6 RID MAC + 后6 保留</em>
  uint32 track_source = 8; <em>// 单选: B0 DID未加密 B1 DID加密 B2 RID-WiFi B3 RID-BT</em>
  uint32 track_cnt = 9; //测量次数
  float track_frequence = 10; //当前信号频率/MHz
  float track_pow = 11; //当前信号功率/dBm 
  float track_noice = 12; //当前噪声功率/dBm 
  float track_snr = 13; //当前信噪比/dB
  uint64 drone_gps_time = 14; //无人机广播时间戳 UTC毫秒计数：1970年1月1日至今
  double drone_longitude = 15; //无人机经度(°)
  double drone_latitude = 16; //无人机纬度(°)
  float drone_altitude = 17; //无人机海拔高度(m)
  float drone_height1 = 18; //无人机距地高度(m)
  float drone_height2 = 19; //无人机相对设备高度(m)
  double drone_sail_longitude = 20; //无人机返航点经度(°)
  double drone_sail_latitude = 21; //无人机返航点经度(°)
  float drone_sail_altitude = 22; //无人机返航点海拔高度(m)
  double pilot_longitude = 23; //飞手经度(°)
  double pilot_latitude = 24; //飞手纬度(°)
  float pilot_altitude = 25; //飞手海拔高度(m)
  float drone_yaw_angle = 26; //无人机角度(°)
  float drone_speed = 27; //无人机绝对速度(m/s)
  float drone_vertical_speed = 28; //无人机垂直速度(m/s)
  uint32 drone_rid_seq_num = 29; //RID信号序号
  uint32 drone_did_seq_num = 30; //DID信号序号
  uint32 drone_rid_classification = 31; //RID分类 无人机类型，比如固定翼或者旋翼
  uint32 drone_rid_status = 32; <em>// 高8位 RID运行状态，低8位 RID系统状态</em>
  <em>// B0白名单 B1特征测量时间有效 B2本地时间有效</em>
  <em>// B3 GPS PPS有效 B4数据融合(关联频谱)</em>
  uint32 drone_proc_status = 33;
  uint32 ex_info_1 = 34;               <em>// DID 特征时间-秒</em>
  uint32 ex_info_2 = 35;               <em>// DID 特征时间-纳秒</em>
  uint32 ex_info_3 = 36;               <em>// RID 特征时间-秒（仅WiFi）</em>
  uint32 ex_info_4 = 37;               <em>// RID 特征时间-纳秒（仅WiFi）</em>
  uint32 SpectMatchProtocol = 38;    <em>// 对应频谱目标编号</em>
}

```

### 上报示例

```JSON
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "method": "device_uav",
  "gateway": "STF200_SN_001",
  "data": {
    "request_mode": 3,
    "target_total_num": 2,
    "sp_target_total_num": 1,
    "sp_target_list": [
      {
        "target_num": 1,
        "target_type": 1,
        "target_code": 1001,
        "target_name": "DJI-Mini",
        "track_status": 3,
        "track_time_create": 1667220870000,
        "track_time_last": 1667220873800,
        "target_chara_code": "",
        "target_confidence": 90,
        "track_cnt": 12,
        "track_frequence": 2437.0,
        "track_bw": 20.0,
        "track_bws": 0,
        "track_bwe": 0,
        "track_cf": 2440.0,
        "track_ef": 0.0,
        "track_pow": -45.5,
        "track_noice": -95.0,
        "track_snr": 20.5,
        "track_distance": 500.0,
        "track_ct": 10.0,
        "track_az": 45.2,
        "track_ei": 5.1,
        "track_az_err": 1.0,
        "track_el_err": 1.0,
        "track_angle_time": 1667220873800,
        "track_pdw_type": 0,
        "track_f_start": 2427.0,
        "track_f_end": 2447.0,
        "track_pri_num": 0,
        "track_pri_value": [
          0,
          0,
          0,
          0,
          0
        ],
        "track_pw_num": 0,
        "track_pw_value": [
          0,
          0,
          0,
          0,
          0
        ],
        "target_proc_status": 0,
        "ex_info_1": 0,
        "ex_info_2": 0,
        "ex_info_3": 45.0,
        "ex_info_4": 5.0,
        "spect_match_protocol": 1
      }
    ],
    "pt_target_total_num": 1,
    "pt_target_list": [
      {
        "drone_num": 1,
        "drone_type": 1,
        "drone_name": "DJI-Mini",
        "track_status": 3,
        "track_time_create": 1667220870000,
        "track_time_last": 1667220873800,
        "track_sn": "",
        "track_source": 1,
        "track_cnt": 8,
        "track_frequence": 2437.0,
        "track_pow": -48.0,
        "track_noice": -95.0,
        "track_snr": 18.0,
        "drone_gps_time": 1667220873000,
        "drone_longitude": 114.05789,
        "drone_latitude": 22.54321,
        "drone_altitude": 120.5,
        "drone_height1": 80.0,
        "drone_height2": 75.0,
        "drone_sail_longitude": 114.05,
        "drone_sail_latitude": 22.54,
        "drone_sail_altitude": 50.0,
        "pilot_longitude": 114.056,
        "pilot_latitude": 22.542,
        "pilot_altitude": 10.0,
        "drone_yaw_angle": 90.0,
        "drone_speed": 5.2,
        "drone_vertical_speed": 0.5,
        "drone_rid_seq_num": 1,
        "drone_did_seq_num": 1,
        "drone_rid_classification": 0,
        "drone_rid_status": 0,
        "drone_proc_status": 16,
        "ex_info_1": 0,
        "ex_info_2": 0,
        "ex_info_3": 0,
        "ex_info_4": 0,
        "spect_match_protocol": 1
      }
    ],
    "@type": "type.googleapis.com/cloud.Stf200DetectionTargetsReport"
  }
}
```

## **0x0022 频谱图上报**

### 协议概要

### Protobuf

```protobuf
// Topic: thing/product/{STF200设备SN}/osd
// method: stf200_freq_stream
// 对应设备协议: 0x0022 时频图上报（非 PB）
// 外层使用 CloudMessage（见文档开头公共定义）
// 上报 data payload 类型: cloud.Stf200FreqStreamData


message Stf200FreqStreamData {
  //B0: 选择前（0°）阵面 0表示未选中 1表示选中
  //B1: 选择右（90°）阵面 0表示未选中 1表示选中
  //B2: 选择后（180°）阵面 0表示未选中 1表示选中
  //B3: 选择左（270°）阵面 0表示未选中 1表示选中
  //B4-B31预留
  //（不可多选）
  uint32 device_select = 1;
  uint32 freq = 2; //频率，kHz
  uint32 frame_num = 3; //帧数
  uint32 frame_idx = 4; //帧序号
  uint32 frame_size = 5; //帧大小N
  bytes data = 6; //时频图数据
}
```

### 上报示例

```json
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_freq_stream",
  "data": {
    "device_select": 1,
    "freq": 2437000,
    "frame_num": 10,
    "frame_idx": 0,
    "frame_size": 1024,
    "data": "",
    "@type": "type.googleapis.com/cloud.Stf200FreqStreamData"
  }
}
```

## 0x0023 上报DroneID加密码流

### 协议概要

### Protobuf

```protobuf
// Topic: thing/product/{STF200设备SN}/osd
// method: device_encrypt_uav
// 对应设备协议: 0x0023 上报加密码流（非 PB）
// 外层使用 CloudMessage（见文档开头公共定义）
// 上报 data payload 类型: cloud.Stf200EncryptStreamData


message Stf200EncryptStreamData {
  string SN_name = 1; //设备SN号，字符串
  uint64 unique_id = 2; //唯一标识（0x4A回传结果时填充该值）
  uint32 data1_len = 3; //加密码流数据长度N
  bytes data1 = 4; //加密码流数据（N最大1K字节）
  uint32 data2_len = 5; //码流数据长度M（保留
  bytes data2 = 6; //码流数据（M最大1K字节）（保留）
}
```

### 上报示例

```json
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "device_encrypt_uav",
  "data": {
    "sn_name": "STF200_SN_001",
    "unique_id": 1234567890,
    "data1_len": 1024,
    "data1": "",
    "data2_len": 0,
    "data2": "",
    "@type": "type.googleapis.com/cloud.Stf200EncryptStreamData"
  }
}
```

## 0x0024 上报电磁环境监测统计结果

### 协议概要

### Protobuf

```protobuf
// Topic: thing/product/{STF200设备SN}/osd
// method: stf200_spectrum_monitor_result
// 对应设备协议: 0x0024 / Stf200ReportSpectrumMonitorResultPB
// 外层使用 CloudMessage（见文档开头公共定义）
// 上报 data payload 类型: cloud.Stf200ReportSpectrumMonitorResultPB


message Stf200ReportSpectrumMonitorResultPB {
  repeated Stf200SpectrumMonitorResultItem result_item_subarray1 = 1; //监测结果，子阵1
  repeated Stf200SpectrumMonitorResultItem result_item_subarray2 = 2; //监测结果，子阵2
  repeated Stf200SpectrumMonitorResultItem result_item_subarray3 = 3; //监测结果，子阵3
  repeated Stf200SpectrumMonitorResultItem result_item_subarray4 = 4; //监测结果，子阵4
}

message Stf200SpectrumMonitorResultItem {
  float freq_mhz = 1; //当前频点 数值范围：400~6000 单位MHz
  float values = 2; //当前频点监测功率值 数值范围：-120~-60 单位dBm
}
```

### 上报示例

```json
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_spectrum_monitor_result",
  "data": {
    "result_item_subarray1": [
      {
        "freq_mhz": 2400.0,
        "values": -80.5
      }
    ],
    "result_item_subarray2": [],
    "result_item_subarray3": [],
    "result_item_subarray4": [],
    "@type": "type.googleapis.com/cloud.Stf200ReportSpectrumMonitorResultPB"
  }
}
```

## **0x0030 AI大模型侦测增强**

### **协议概要**

|项|值|
|---|---|
|设备协议|`0x0030`|
|请求 Topic|thing/product/\{STF200设备SN\}/services|
|应答 Topic|thing/product/\{STF200设备SN\}/services\_reply|
|method|`stf200_ai_config`|

### **Protobuf**

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_ai_config
// 对应设备协议: 0x0030 / Stf200AIConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200AIConfig


// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_ai_config
// 对应设备协议: 0x0030 / Stf200AIConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200AiConfigReplyData


message Stf200AiConfigReplyData {
  int32 result = 1; <em>//云侧统一结果码:  0:成功 1:失败 2:超时 3:设备不在线 4:状态冲突 5:重启中</em>
  Stf200AIConfig output = 2;
}

message Stf200AIConfig {
  //请求：
  // 1查询 2更新

  //应答:
  //1: 查询成功
  //2: 更新成功
  //错误码 > 255 
  //256：不支持的请求类型
  //257:  查询失败
  //258：更新失败
  uint32 update_mode = 1;
  uint32 status = 2; //1：开启 2：关闭
}
```

### **请求示例**

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_ai_config",
  "data": {
    "update_mode": 2,
    "status": 1,
    "@type": "type.googleapis.com/cloud.Stf200AIConfig"
  }
}
```

### **应答示例**

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_ai_config",
  "data": {
    "result": 0,
    "output": {
      "update_mode": 2,
      "status": 1
    },
    "@type": "type.googleapis.com/cloud.Stf200AiConfigReplyData"
  }
}
```

## **0x0032 WIFI过滤管理设置**

### **协议概要**

|项|值|
|---|---|
|设备协议|`0x0032`|
|请求 Topic|`thing/product/{STF200设备SN}/services`|
|应答 Topic|`thing/product/{STF200设备SN}/services_reply`|
|method|`stf200_wifi_filter`|

### **Protobuf**

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_wifi_filter
// 对应设备协议: 0x0032 / Stf200BeaconFilterConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200BeaconFilterConfig


// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_wifi_filter
// 对应设备协议: 0x0032 / Stf200BeaconFilterConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200WifiFilterReplyData


message Stf200WifiFilterReplyData {
  int32 result = 1; //云侧统一结果码:  0:成功 1:失败 2:超时 3:设备不在线 4:状态冲突 5:重启中
  Stf200BeaconFilterConfig output = 2;
}

message Stf200BeaconFilterConfig {
  //请求：
  //请求类型：
  //1：查询
  //2：更新
  //3：删除（按照唯一ID删除）

  //应答:
  //1: 查询成功
  //2: 更新成功
  //3: 删除成功
  //错误码 > 255 
  //256：不支持的请求类型
  //257:  查询失败
  //258：更新失败
  //259：删除失败
  uint32 update_mode = 1;
  uint32 filter_num = 2; //过滤器数量
  repeated Stf200BeaconTargetFilter filter_target_list = 3;
}

message Stf200BeaconTargetFilter {
  uint32 id = 1; //全局唯一ID
  uint32 status = 2; //B0:1 表示被启用 0 表示不启用
  string name = 3; //Beacon（wifi名称）名称
  bytes note = 4; //备注 0-20 个（中文）字符
}
```

### **请求示例**

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_wifi_filter",
  "data": {
    "update_mode": 2,
    "filter_num": 1,
    "filter_target_list": [
      {
        "id": 1,
        "status": 1,
        "name": "wifi_filter_1",
        "note": ""
      }
    ],
    "@type": "type.googleapis.com/cloud.Stf200BeaconFilterConfig"
  }
}
```

### **应答示例**

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_wifi_filter",
  "data": {
    "result": 0,
    "output": {
      "update_mode": 2,
      "filter_num": 1,
      "filter_target_list": [
        {
          "id": 1,
          "status": 1,
          "name": "wifi_filter_1",
          "note": ""
        }
      ]
    },
    "@type": "type.googleapis.com/cloud.Stf200WifiFilterReplyData"
  }
}
```

## **0x0033 RF目标过滤**

### **协议概要**

|项|值|
|---|---|
|设备协议|`0x0033`|
|请求 Topic|hing/product/\{STF200设备SN\}/services|
|应答 Topic|thing/product/\{STF200设备SN\}/services\_reply|
|method|`stf200_rf_filter`|

### **Protobuf**

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_rf_filter
// 对应设备协议: 0x0033 / Stf200DetectFilterConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200DetectFilterConfig


// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_rf_filter
// 对应设备协议: 0x0033 / Stf200DetectFilterConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200RfFilterReplyData


message Stf200RfFilterReplyData {
  int32 result = 1; //云侧统一结果码:  0:成功 1:失败 2:超时 3:设备不在线 4:状态冲突 5:重启中
  Stf200DetectFilterConfig output = 2;
}

message Stf200DetectFilterConfig {
  ////请求：
  //1：查询
  //2：更新
  //3:  删除（按照全局唯一ID删除

  //响应:
  //1: 查询成功
  //2: 更新成功
  //3：删除成功

  //错误码 > 255 
  //256：不支持的请求类型
  //257:  查询失败
  //258：更新失败
  //259:  删除失败
  uint32 update_mode = 1;
  uint32 filter_num = 2; //过滤器数量
  repeated Stf200DetectTargetFilter filter_target_list = 3; //侦测目标过滤设置数据结构体, 目标数量0-128
}

message Stf200DetectTargetFilter {
  uint32 id = 1; //全局唯一ID
  //B0: 规则启用使能 0 表示规则不启用 1表示规则启用
  //B1: 方位角过滤使能
  //B2：俯仰角过滤使能
  uint32 status = 2;
  string filter_name = 3; //过滤器规则名称
  string target_name = 4; //目标名称 
  repeated float freq_start_list = 5; //开始频点 MHZ
  repeated float freq_end_list = 6; //结束频点 MHZ
  //B0: 0号频点使能 0表示不使能 1表示使能
  //B1: 1号频点使能 0表示不使能 1表示使能
  //B2: 2号频点使能 0表示不使能 1表示使能
  //B3: 3号频点使能 0表示不使能 1表示使能
  //B4: 4号频点使能 0表示不使能 1表示使能
  uint32 freq_selected = 7;
  //目标信号类型
  //B0：空中目标
  //B1：地面目标
  //B2：无法确认
  //其它无定义，默认填0
  uint32 signal_type = 8;
  float orient_min = 9; //方位角下限
  float orient_max = 10; //方位角上限
  float yaw_min = 11; //俯仰范围下限
  float yaw_max = 12; //俯仰范围上限
}
```

### **请求示例**

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_rf_filter",
  "data": {
    "update_mode": 1,
    "filter_num": 0,
    "filter_target_list": [],
    "@type": "type.googleapis.com/cloud.Stf200DetectFilterConfig"
  }
}
```

### **应答示例**

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_rf_filter",
  "data": {
    "result": 0,
    "output": {
      "update_mode": 1,
      "filter_num": 0,
      "filter_target_list": []
    },
    "@type": "type.googleapis.com/cloud.Stf200RfFilterReplyData"
  }
}
```

---

## **0x0034 频谱检测配置**

### **协议概要**

|项|值|
|---|---|
|设备协议|`0x0034`|
|请求 Topic|`thing/product/{STF200设备SN}/services`|
|应答 Topic|`thing/product/{STF200设备SN}/services_reply`|
|method|`stf200_spectrum_monitor`|

### **Protobuf**

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_spectrum_monitor
// 对应设备协议: 0x0034 / Stf200SpectrumMonitorSetting
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200SpectrumMonitorSetting


// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_spectrum_monitor
// 对应设备协议: 0x0034 / Stf200SpectrumMonitorSetting
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200SpectrumMonitorReplyData


message Stf200SpectrumMonitorReplyData {
  int32 result = 1;
  Stf200SpectrumMonitorSetting output = 2;
}

message Stf200SpectrumMonitorSetting {
  //请求：1：查询 2：更新（不支持新增）

  //响应:
  //1: 查询成功
  //2: 更新成功

  //错误码 > 255 
  //256：不支持的请求类型
  //257:  查询失败
  //258：更新失败
  uint32 update_mode = 1;
  uint32 working_status = 2; //工作类型：0：非频谱工作模式 1：开始扫描 (应用设置开始工作）2：停止扫描 
  //B0: 选择前（0°）阵面 0表示未选中 1表示选中
  //B1: 选择右（90°）阵面 0表示未选中 1表示选中
  //B2: 选择后（180°）阵面 0表示未选中 1表示选中
  //B3: 选择左（270°）阵面 0表示未选中 1表示选中
  //B4-B31预留
  //（可多选）
  uint32 device_select = 3;
  repeated Stf200SpectrumMonitorFreqPoint freq_point_select_list = 4;
}

message Stf200SpectrumMonitorFreqPoint {
  uint32 id = 1; //全局唯一ID
  float start_freq = 2; //起始频点 默认频段 start_freq 等于 end_freq
  float end_freq = 3; //结束频点 默认频段 start_freq 等于 end_freq
  uint32 setting_list = 4; //B0 默认频段位： 0表示自定义 1表示默认：开始频点和结束频点相等，为固定值；间隔为0
  repeated uint32 available_freq_point = 5; //该频段的可选频点列表，数量 0 - 32
  repeated uint32 freq_point_select_index = 6; //选中的列表编号，数量 0-32 如：available_freq_point 中第100位和200位被选中，这里数组为 [100, 200]
}
```

### **请求示例**

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_spectrum_monitor",
  "data": {
    "update_mode": 2,
    "working_status": 1,
    "device_select": 1,
    "freq_point_select_list": [],
    "@type": "type.googleapis.com/cloud.Stf200SpectrumMonitorSetting"
  }
}
```

### **应答示例**

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_spectrum_monitor",
  "data": {
    "result": 0,
    "output": {
      "update_mode": 2,
      "working_status": 1,
      "device_select": 1,
      "freq_point_select_list": []
    },
    "@type": "type.googleapis.com/cloud.Stf200SpectrumMonitorReplyData"
  }
}
```

## 0x0035 IP配置

### 协议概要

### Protobuf

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_ip_config
// 对应设备协议: 0x0035 / IPAddressConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200IpConfigReqData


message Stf200IpConfigReqData {
  //请求：
  //1：查询
  //2：更新

  //响应：
  //1: 查询成功
  //2: 更新成功
  //错误码 > 255 
  //256：不支持的请求类型
  //257:  查询失败
  //258：更新失败
  uint32 update_mode = 1;
  uint32 static_ip = 2; //0:表示动态IP 1:表示静态IP
  string ip_address = 3;  //Uint8*4 ipv4 版本 ip 地址
  string subnet_mark = 4; //Uint8*4 子网掩码
}

// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_ip_config
// 对应设备协议: 0x0035 / IPAddressConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200IpConfigReplyData


message Stf200IpConfigReplyData {
  int32 result = 1; ////云侧统一结果码:  0:成功 1:失败 2:超时 3:设备不在线 4:状态冲突 5:重启中
  Stf200IpConfigReqData output = 2; 
}
```

### 请求示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_ip_config",
  "data": {
    "update_mode": 2,
    "static_ip": 1,
    "ip_address": "192.168.1.50",
    "subnet_mark": "255.255.255.0",
    "@type": "type.googleapis.com/cloud.Stf200IpConfigReqData"
  }
}
```

### 应答示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_ip_config",
  "data": {
    "result": 0,
    "output": {
      "update_mode": 2,
      "static_ip": 1,
      "ip_address": "192.168.1.50",
      "subnet_mark": "255.255.255.0"
    },
    "@type": "type.googleapis.com/cloud.Stf200IpConfigReplyData"
  }
}
```

---

## 0x0036 侦测上报开关

### 协议概要

### Protobuf

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_detect_collect
// 对应设备协议: 0x0036 / Stf200DetectTargetCollectConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200DetectTargetCollectConfig


message Stf200DetectTargetCollectConfig {
  //请求类型：
  //1：查询
  //2：更新

  //响应：
  //1: 查询成功
  //2: 更新成功
  //错误码 > 255 
  //256：不支持的请求类型
  //257:  查询失败
  //258：更新失败
  uint32 update_mode = 1;
  //该协议修改成如下：
  //Bit0：对应测向子阵1，1开启0关闭
  //Bit1：对应测向子阵2
  //Bit2：对应测向子阵3
  //Bit3：对应测向子阵4
  //Bit4：对应协议主板
  //Bit5：对应协议从板
  //Bit6：对应AI节点 （同0x0030， 0x0030会去掉）
  //Bit7：禁止侦测目标上报（1：禁止上报；0：上报）
  //其它预留  （注意：bit0~bit3 已经实现，bit4~bit6暂时没有实现）
  uint32 collect_enable = 2; 
}

// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_detect_collect
// 对应设备协议: 0x0036 / Stf200DetectTargetCollectConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200DetectCollectReplyData


message Stf200DetectCollectReplyData {
  int32 result = 1; //云侧统一结果码:  0:成功 1:失败 2:超时 3:设备不在线 4:状态冲突 5:重启中
  Stf200DetectTargetCollectConfig output = 2;
}
```

### 请求示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_detect_collect",
  "data": {
    "update_mode": 2,
    "collect_enable": 1,
    "@type": "type.googleapis.com/cloud.Stf200DetectTargetCollectConfig"
  }
}
```

### 应答示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_detect_collect",
  "data": {
    "result": 0,
    "output": {
      "update_mode": 2,
      "collect_enable": 1
    },
    "@type": "type.googleapis.com/cloud.Stf200DetectCollectReplyData"
  }
}
```

---

## 0x0040 位置姿态配置

### 协议概要

### Protobuf

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_position_orientation
// 对应设备协议: 0x0040 / Stf200PositionOrientationConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200PositionOrientationConfig


message Stf200PositionOrientationConfig {
  //请求类型：
  //1：查询
  //2：更新

  //响应：
  //0: 主动上报
  //1: 查询成功
  //2: 更新成功

  //错误码 > 255 
  //256：不支持的请求类型
  //257:  查询失败
  //258：更新失败
  uint32 update_mode = 1;
  double longitude = 2; //系统GPS定位经度（°）
  double latitude = 3; //系统GPS定位纬度（°）
  float altitude = 4; //系统GPS定位海拔高度（m）
  float yaw = 5; //系统姿态偏航角（°）
  float pitch = 6; //系统姿态俯仰角（°）
  float roll = 7; //系统姿态滚转角（°）
  float speed_x = 8; //系统X轴速度（m/s）
  float speed_y = 9; //系统Y轴速度（m/s）
  float speed_z = 10; //系统Z轴速度（m/s）
  float omega_x = 11; //系统X轴角速度（°/s）
  float omega_y = 12; //系统Y轴角速度（°/s）
  float omega_z = 13; //系统Z轴角速度（°/s）
  uint32 setting_mode = 14; //1: 手动-用户设置 2：自动-通过GPS（内部设备) 3：网络-通过上位机获取
  uint32 data_source = 15; //1: 手动-用户设置 2：自动-通过GPS（内部设备) 3：网络-通过上位机获取
  uint32 data_state = 16; //0：静态 1: 动态上报位置信息：10HZ
}

// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_position_orientation
// 对应设备协议: 0x0040 / Stf200PositionOrientationConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200PositionOrientationReplyData


message Stf200PositionOrientationReplyData {
  int32 result = 1; //云侧统一结果码:  0:成功 1:失败 2:超时 3:设备不在线 4:状态冲突 5:重启中
  Stf200PositionOrientationConfig output = 2;
}

```

### 请求示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_position_orientation",
  "data": {
    "update_mode": 2,
    "longitude": 114.0579,
    "latitude": 22.5431,
    "altitude": 50.0,
    "yaw": 10.0,
    "pitch": 0.0,
    "roll": 0.0,
    "speed_x": 0,
    "speed_y": 0,
    "speed_z": 0,
    "omega_x": 0,
    "omega_y": 0,
    "omega_z": 0,
    "setting_mode": 1,
    "data_source": 1,
    "data_state": 1,
    "@type": "type.googleapis.com/cloud.Stf200PositionOrientationConfig"
  }
}
```

### 应答示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_position_orientation",
  "data": {
    "result": 0,
    "output": {
      "update_mode": 2,
      "longitude": 114.0579,
      "latitude": 22.5431,
      "altitude": 50.0,
      "yaw": 10.0,
      "pitch": 0.0,
      "roll": 0.0,
      "speed_x": 0,
      "speed_y": 0,
      "speed_z": 0,
      "omega_x": 0,
      "omega_y": 0,
      "omega_z": 0,
      "setting_mode": 1,
      "data_source": 1,
      "data_state": 1
    },
    "@type": "type.googleapis.com/cloud.Stf200PositionOrientationReplyData"
  }
}
```

### 上报示例

Topic: `thing/product/{STF200设备SN}/osd`
method: `device_posture`

```ProtoBuf
// Topic: thing/product/{STF200设备SN}/osd
// method: device_posture
// 对应设备协议: 0x0040 / Stf200PositionOrientationConfig（主动上报 update_mode=0）
// 外层使用 CloudMessage（见文档开头公共定义）
// 上报 data payload 类型: cloud.Stf200PositionOrientationConfig
```

```json
{
  "tid": "65717bf1-aee7-4abb-8ea3-9b1908548d74",
  "bid": "65717bf1-aee7-4abb-8ea3-789854512232",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "device_posture",
  "data": {
    "update_mode": 0,
    "longitude": 114.0579,
    "latitude": 22.5431,
    "altitude": 50.0,
    "yaw": 10.0,
    "pitch": 0.5,
    "roll": -0.2,
    "speed_x": 0.1,
    "speed_y": 0.0,
    "speed_z": 0.0,
    "omega_x": 0.0,
    "omega_y": 0.0,
    "omega_z": 0.1,
    "setting_mode": 2,
    "data_source": 2,
    "data_state": 1,
    "@type": "type.googleapis.com/cloud.Stf200PositionOrientationConfig"
  }
}
```

## 0x0041 基本工作参数

### 协议概要

### Protobuf

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_basic_work_para
// 对应设备协议: 0x0041 / Stf200BasicWorkParaConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200BasicWorkParaConfig


message Stf200BasicWorkParaConfig {
  //请求类型：
  //1：查询
  //2：更新

  //响应:
  //1: 查询成功
  //2: 更新成功

  //错误码 > 255 
  //256：不支持的请求类型
  //257:  查询失败
  //258：更新失败
  uint32 set_mode = 1;
  //工作模式（模式总开关）
  //B0：数据融合使能 0 表示不使能 1表示使能
  //B1：车载模式使能 0 固定 1 车载
  //B2：安装类型 0 固定 1 移动
  //B3：角度输出坐标系选择 0 固定系 1 测量系
  //B4：频谱侦测模块使能 0表示不使能 1表示使能
<del>  //B5：协议侦测DID模块使能</del>
<del>  //B6：协议侦测RID模块使能</del>
  //B7：未知信号识别功能使能 0表示不使能 1表示使能
  //B8:  协议信号功能使能 0表示不使能 1表示使能
  //B9：WIFI信号功能使能 0表示不使能 1表示使能
  //B10-B31：预留
  uint32 work_mode = 2;
  //侦测模式使能
  //频谱字段
  //B0：数字图传 Digital VT 0表示不使能 1表示使能
  //B1：模拟图传 Analog VT 0表示不使能 1表示使能
  //B2：Wifi 图传 0表示不使能 1表示使能 
  //B3：FK上行 RC  0表示不使能 1表示使能
  //B4：FK下行 RC  0表示不使能 1表示使能
  //B5：前导检测 0表示不使能 1表示使能
  //B6：信号检测 0表示不使能 1表示使能
  //B7：干扰源（Tracer   Air Ⅱ涉及） 0表示不使能 1表示使能
  //B8：遥控信号（Tracer   Air Ⅱ涉及） 0表示不使能 1表示使能
  //B9：通信基站（Tracer   Air Ⅱ涉及） 0表示不使能 1表示使能
  //B10~B15：

  //协议字段
  //B16: 协议侦测DID*模块使能 0表示不使能 1表示使能
  //B17: 协议侦测DID模块使能 0表示不使能 1表示使能
  //B18: 协议侦测RID模块使能 0表示不使能 1表示使能

  //wifi 增强型检测
  //B20: WIFI信号使能 0表示不使能 1表示使能
  //B21：Wifi 图传 0表示不使能 1表示使能
  uint32 det_type = 3;
  //目标记忆时间（s）
  //数组第一位：协议记忆时间
  //数组第二位：频谱记忆时间
  repeated uint32 det_duration = 4;
  uint32 det_sensitive = 5; //检测灵敏度 1：低  2：中 3：高
}

// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_basic_work_para
// 对应设备协议: 0x0041 / Stf200BasicWorkParaConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200BasicWorkParaReplyData


message Stf200BasicWorkParaReplyData {
  int32 result = 1; //云侧统一结果码:  0:成功 1:失败 2:超时 3:设备不在线 4:状态冲突 5:重启中
  Stf200BasicWorkParaConfig output = 2;
}
```

### 请求示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_basic_work_para",
  "data": {
    "set_mode": 2,
    "work_mode": 1,
    "det_type": 1,
    "det_duration": [
      1000,
      1000,
      1000
    ],
    "det_sensitive": 2,
    "@type": "type.googleapis.com/cloud.Stf200BasicWorkParaConfig"
  }
}
```

### 应答示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_basic_work_para",
  "data": {
    "result": 0,
    "output": {
      "set_mode": 2,
      "work_mode": 1,
      "det_type": 1,
      "det_duration": [
        1000,
        1000,
        1000
      ],
      "det_sensitive": 2
    },
    "@type": "type.googleapis.com/cloud.Stf200BasicWorkParaReplyData"
  }
}
```

---

## 0x0042 RF检测配置

### 协议概要

### Protobuf

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_rf_detect_config
// 对应设备协议: 0x0042 / Stf200RFDetectConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200RFDetectConfig


message Stf200RFDetectConfig {
  //请求类型：
  //1：查询
  //2：更新
  //3:  删除（按全局唯一ID删除 ， 默认不可删除）
  //4：恢复默认（不响应参数）

  //响应：
  //1: 查询成功
  //2: 更新成功
  //3: 删除成功（根据全局唯一ID删除）
  //4: 恢复默认成功

  //错误码 > 255 
  //256：不支持的请求类型
  //257:  查询失败
  //258：更新失败
  //259：删除失败
  //260:  恢复默认失败
  uint32 update_mode = 1;
  uint32 freq_num = 2; //对象数量
  repeated Stf200TragetConfig freq_config_list = 3; //对象列表
}

// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_rf_detect_config
// 对应设备协议: 0x0042 / Stf200RFDetectConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200RfDetectConfigReplyData


message Stf200RfDetectConfigReplyData {
  int32 result = 1; //云侧统一结果码:  0:成功 1:失败 2:超时 3:设备不在线 4:状态冲突 5:重启中
  Stf200RFDetectConfig output = 2;
}

message Stf200TragetConfig {
  uint32 id = 1; //全局唯一ID
  float start_freq = 2; //起始频点 默认频段 start_freq 等于 end_freq
  float end_freq = 3; //结束频点 默认频段 start_freq 等于 end_freq
  float freq_intevel = 4; //频点间隔; 如果是默认频段，不工作
  uint32 freq_gain = 5; //频段增益控制 dBi
  //B0 默认频段位： 0表示自定义 1表示默认：开始频点和结束频点相等，为固定值；间隔为0 (1)
  //B1：AI大模型侦测使能：0 表示不使能，1 表示使能 (2)
  //B2: 未知目标检测功能使能: 0 表示不使能，1 表示使能 (4)
  //B3：频段增益配置使能：0 表示不使能，1 表示使能 (8)
  //B4：频段启用状态使能：0 表示不使能，1 表示使能 (16)
  uint32 setting_list = 6;
}
```

### 请求示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_rf_detect_config",
  "data": {
    "update_mode": 2,
    "freq_num": 1,
    "freq_config_list": [
      {
        "id": 1,
        "start_freq": 2400.0,
        "end_freq": 2500.0,
        "freq_intevel": 1.0,
        "freq_gain": 10,
        "setting_list": 1
      }
    ],
    "@type": "type.googleapis.com/cloud.Stf200RFDetectConfig"
  }
}
```

### 应答示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_rf_detect_config",
  "data": {
    "result": 0,
    "output": {
      "update_mode": 2,
      "freq_num": 1,
      "freq_config_list": [
        {
          "id": 1,
          "start_freq": 2400.0,
          "end_freq": 2500.0,
          "freq_intevel": 1.0,
          "freq_gain": 10,
          "setting_list": 1
        }
      ]
    },
    "@type": "type.googleapis.com/cloud.Stf200RfDetectConfigReplyData"
  }
}
```

---

## 0x0043 侦测数据库

### 协议概要

### Protobuf

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_detect_database
// 对应设备协议: 0x0043 / Stf200DetectDataBaseConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200DetectDataBaseConfig


message Stf200DetectDataBaseConfig {
  //请求类型:
  //1：查询
  //2：更新
  //3：删除（按照全局唯一ID删除）

  //响应：
  //1: 查询成功
    //2: 更新成功
    //3：删除成功

    //错误码 > 255 
    //256：不支持的请求类型
    //257:  查询失败
    //258：更新失败
    //259：删除失败
  uint32 set_mode = 1;
  uint32 target_defineNum = 2;
  repeated Stf200TargetDescript target_define_list = 3;
}

// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_detect_database
// 对应设备协议: 0x0043 / Stf200DetectDataBaseConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200DetectDatabaseReplyData


message Stf200DetectDatabaseReplyData {
  int32 result = 1;
  Stf200DetectDataBaseConfig output = 2;
}

message Stf200TargetDescript {
  uint32 id = 1; //全局唯一ID
  string target_name = 2; //目标名称
  uint32 target_set = 3; //目标属性设置 B0：报文使能有效 B1：是否自定义 0 表示非自定义 1表示自定义 B2~B7预留
  //协议类型
    //1: FHSS
    //2: LB FHSS
    //3: OFDM
    //4: LB OFDM
    //5: OS OFDM
    //6: EN.WiFi
    //7: CRSF
    //8: AFHDS
    //9: ACCESS
    //10: ACCESS ACCST 
    //11: FASST
    //12: GHOST
    //13: DSMX
    //14: WBFM
    //15: Others
  uint32 protocol_type = 4;
  //目标信号类型
    //B0-B15位数值：
    //1：数字图传
    //2：模拟图传
    //3：Wifi图传（Beacon WIFI）
    //4：FK上行
    //5：FK下行
    //6：前导检测（暂不使用）
    //7：信号检测（暂不使用）
    //8：干扰源（Tracer   Air Ⅱ涉及）
    //9：遥控信号（Tracer   Air Ⅱ涉及）
    //10：通信基站（Tracer   Air Ⅱ涉及）
    //11：自定义干扰（Tracer   Air Ⅱ涉及）
    //12：自定义遥控（Tracer   Air Ⅱ涉及）
    //13：自定义通信（Tracer   Air Ⅱ涉及）

    //B16-B31 按位处理
    //B16： AI增强目标 1 表示 AI目标 0 表示非AI标
    //B17：是否支持频率跟踪 1表示支持 0表示不支持（用于显示频率跟踪按钮）
    //B18：是否处于频率跟踪 1表示处于 0表示不处于（用于显示频率跟踪状态）
    //B19：是否为指定跟踪目标
    //B20：目标来源：空中（显示图标） 
    //B21：目标来源：地面（显示图标）
    //B22：目标来源：扩展（显示图标）
    //B23：目标测向是否有效
    //B24：是否为自定义目标
    //B25:  是否为未知威胁检测
    //B26：检测策略码1（1表示固定频率检测开启（映射到数字图传检测策略），0表示关闭）
    //B27：检测策略码2（1表示跳频检测开启（映射到飞控检测策略），0表示关闭）
    //B28：检测策略码3
  uint32 target_type = 5;
  repeated float pulse_w = 6; //有效脉宽（ms，0.4~50）
  repeated float pulse_t = 7; //脉冲周期（ms，0.5~50）
  repeated float pulse_bw = 8; //信号带宽（MHz，0.4~20）
  repeated float freq_start = 9; //有效频段起始（MHz，400~6000）
  repeated float freq_end = 10; //有效频段终止（MHz，400~6000）
  //B0: 0号频点使能 0表示不使能 1表示使能
    //B1: 1号频点使能 0表示不使能 1表示使能
    //B2: 2号频点使能 0表示不使能 1表示使能
    //B3: 3号频点使能 0表示不使能 1表示使能
    //B4: 4号频点使能 0表示不使能 1表示使能
  uint32 freq_selected = 11;
  float pulse_w_err = 12; //脉宽误差（ms，0.04~0.10）注：遥控、通信节点类型有效(新建默认 0.07）
  float pulse_t_err = 13; //脉冲周期误差（ms，0.04~0.10）注：遥控、通信节点类型有效(新建默认 0.07）
  float pulse_bw_err = 14; //带宽误差（MHz，0.4~1.2）注：遥控、干扰、通信节点类型有效(新建默认 0.96）
  uint32 target_code = 15; //目标标志码
  repeated float ext_float_reserved = 16;
}
```

### 请求示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_detect_database",
  "data": {
    "set_mode": 1,
    "target_define_num": 0,
    "target_define_list": [],
    "@type": "type.googleapis.com/cloud.Stf200DetectDataBaseConfig"
  }
}
```

### 应答示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_detect_database",
  "data": {
    "result": 0,
    "output": {
      "set_mode": 1,
      "target_define_num": 0,
      "target_define_list": []
    },
    "@type": "type.googleapis.com/cloud.Stf200DetectDatabaseReplyData"
  }
}
```

---

## 0x0045 NTP配置

### 协议概要

### Protobuf

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_ntp_config
// 对应设备协议: 0x0045 / Stf200NTPParaConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200NTPParaConfig


message Stf200NTPParaConfig {
  //请求类型：1：查询 2：更新

  //响应：
    //1: 查询成功
    //2: 更新成功

    //错误码 > 255 
    //256：不支持的请求类型
    //257:  查询失败
    //258：更新失败
  uint32 set_mode = 1;
  //NTP服务器设置
  //0：使用上位机授时（为0是，以下NTP设置设备端不响应，只保存）（ 使用该选项，设备端将使用  0x0014 在建立连接的时候，求情上位机授时） 
  //1：使用NTP服务
  //2：手动设置时间
  //3：chrony 授时
  uint32 ntp_enable = 2;
  uint32 ntp_default = 3; //NTP恢复默认使能，NTP服务器地址恢复默认地址 0：使用以下设置值 1：恢复默认
  int32 ntp_time_zone = 4; //NTP时区设置（0:UTC 时间 8 东八区 -8 西八区）
  string ntp_server_addr = 5; //NTP服务器地址/chrony服务器地址
  string time = 6; //字符串：年月日时分秒.毫秒（例20240515011746.901）
}

// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_ntp_config
// 对应设备协议: 0x0045 / Stf200NTPParaConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200NtpConfigReplyData


message Stf200NtpConfigReplyData {
  int32 result = 1; //云侧统一结果码:  0:成功 1:失败 2:超时 3:设备不在线 4:状态冲突 5:重启中
  Stf200NTPParaConfig output = 2;
}
```

### 请求示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_ntp_config",
  "data": {
    "set_mode": 2,
    "ntp_enable": 1,
    "ntp_default": 0,
    "ntp_time_zone": 8,
    "ntp_server_addr": "ntp.aliyun.com",
    "time": "",
    "@type": "type.googleapis.com/cloud.Stf200NTPParaConfig"
  }
}
```

### 应答示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_ntp_config",
  "data": {
    "result": 0,
    "output": {
      "set_mode": 2,
      "ntp_enable": 1,
      "ntp_default": 0,
      "ntp_time_zone": 8,
      "ntp_server_addr": "ntp.aliyun.com",
      "time": "2026/07/24 14:00:00"
    },
    "@type": "type.googleapis.com/cloud.Stf200NtpConfigReplyData"
  }
}
```

---

## 0x004A 解密结果下发

### 协议概要

### Protobuf

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_decrypt_result
// 对应设备协议: 0x004A 解密结果（非 PB）
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200DecryptResultReqData


message Stf200DecryptResultReqData {
  uint64 unique_id = 1; //唯一标识（填充0xDA上报的值
  uint32 result = 2; //C2解密结果：0:成功；其他：失败
  uint32 json_len = 3; //json字符串长度N
  string json = 4; //json字符串
}

// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_decrypt_result
// 对应设备协议: 0x004A 解密结果应答
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200DecryptResultReplyData


message Stf200DecryptResultReplyData {
  int32 result = 1; //云侧统一结果码:  0:成功 1:失败 2:超时 3:设备不在线 4:状态冲突 5:重启中
  uint32 status = 2; //设备 0失败 1成功
}
```

### 请求示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "method": "stf200_decrypt_result",
  "gateway": "STF200_SN_001",
  "data": {
    "unique_id": 1234567890,
    "result": 1,
    "json_len": 1024
    "json": "{}"
  }
}
```

### 应答示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_decrypt_result",
  "data": {
    "result": 0,
    "status": 1,
    "@type": "type.googleapis.com/cloud.Stf200DecryptResultReplyData"
  }
}
```

---

## 0x0050 数据传输请求

### 协议概要

### Protobuf

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_data_transfer
// 对应设备协议: 0x0050 / Stf200DataRequestResponse
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200DataTransferReqData


message Stf200DataTransferReqData {
  uint32 data_id = 1; //数据ID，由C2（上位机）生成
  uint32 direction = 2; //数据方向 1: 上位机 到 TracerMatrix 导入 2：TracerMatrix 到 上位机 导出
  //数据类型
  //1：RF侦测频段配置（只有导入功能）
  //2:  RF侦测机型库（只有导入功能）
  //3：RF过滤管理（只有导入功能）
  //4：WIFI过滤管理（只有导入功能）
  //5：频谱记录数据（只有导出功能）
  uint32 data_type = 3;
  uint32 data_size = 4; //文件总大小（单位字节）导入：导入文件大小 导出: 0
  string file_name = 5; //数据名称 data_type：频谱记录数据时：为频谱列表中的文件名称 其他数据类型可为空
}

// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_data_transfer
// 对应设备协议: 0x0050 / Stf200DataRequestResponse
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200DataTransferReplyData


message Stf200DataTransferReplyData {
  int32 result = 1; //云侧统一结果码:  0:成功 1:失败 2:超时 3:设备不在线 4:状态冲突 5:重启中
  Stf200DataRequestResponse output = 2;
}

message Stf200DataRequestResponse {
  uint32 data_id = 1; //数据ID，由C2（上位机）生成
  uint32 data_size = 2; //文件总大小（单位字节）导入：成功时，和求情文件大小一致，失败时为0 导出：导出文件大小
  //0：成功
  //1:  格式校验未通过
  //2：文件错误或数据不存在
  //3:  空间不足
  uint32 response_status = 3;
  string error_str = 4; //错误信息
}
```

### 请求示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_data_transfer",
  "data": {
    "data_id": 1,
    "direction": 1,
    "data_type": 1,
    "data_size": 1024,
    "name": "detect_db.bin",
    "@type": "type.googleapis.com/cloud.Stf200DataTransferReqData"
  }
}
```

### 应答示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "gateway": "STF200_SN_001",
  "method": "stf200_data_transfer",
  "data": {
    "result": 0,
    "output": {
      "data_id": 1,
      "data_size": 1024,
      "response_status": 1,
      "error_str": ""
    },
    "@type": "type.googleapis.com/cloud.Stf200DataTransferReplyData"
  }
}
```

## 0x0060 RF频率跟踪

### 协议概要

### Protobuf

```protobuf
// Topic: thing/product/{STF200设备SN}/services
// method: stf200_rf_track_targets
// 对应设备协议: 0x0060 / Stf200RFTrackTargetsConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 请求 data payload 类型: cloud.Stf200RFTrackTargetsConfig


message Stf200RFTrackTargetsConfig {
  uint32 request_mode = 1; // 1设置 2查询
  uint32 track_num = 2;
  repeated Stf200SPTarget track_target_list = 3;
}

// Topic: thing/product/{STF200设备SN}/services_reply
// method: stf200_rf_track_targets
// 对应设备协议: 0x0060 / Stf200RFTrackTargetsSetResponse|Stf200RFTrackTargetsConfig
// 外层使用 CloudMessage（见文档开头公共定义）
// 应答 data payload 类型: cloud.Stf200RfTrackTargetsReplyData


message Stf200RfTrackTargetsReplyData {
  int32 result = 1; //云侧统一结果码:  0:成功 1:失败 2:超时 3:设备不在线 4:状态冲突 5:重启中
  // 设置应答
  Stf200RFTrackTargetsSetResponse set_output = 2;
  // 查询应答
  Stf200RFTrackTargetsConfig query_output = 3;
}

// 设置应答
message Stf200RFTrackTargetsSetResponse {
  uint32 request_mode = 1; //请求类型: 1: 设置 2：查询
  uint32 track_num = 2; //跟踪目标个数
  uint32 track_status = 3; //Status值：0：成功 1：接收出错 2：校验失败 10：状态错误 其他错误
}

<em>// 复用 Stf200SPTarget 频谱目标结构</em>
```

### 请求示例

```json
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1752216995783,
  "gateway": "STF200_SN_001",
  "method": "stf200_rf_track_targets",
  "data": {
    "request_mode": 2,
    "track_num": 0,
    "track_target_list": [],
    "@type": "type.googleapis.com/cloud.Stf200RFTrackTargetsConfig"
  }
}
```

### 应答示例

```JSON
{
  "tid": "63067624-c202-4660-8934-2fc98c2220f4",
  "bid": "a90900c5-0a99-4ace-b190-ec4aae9fe0ff",
  "timestamp": 1667220873846,
  "method": "stf200_rf_track_targets",
  "gateway": "STF200_SN_001",
  "data": {
    "result": 0,
    "query_output": {
      "request_mode": 2,
      "track_num": 0,
      "track_target_list": []
    }
  }
```

## Todo 导入、导出协议暂定

