# Sentry与C2上位机通信协议

# **变更记录**

|**版本**|**说明**|**拟制人**|**日期**|
|---|---|---|---|
|V1\.0\.0<br>|整合SFL200多传感器协议、AGX\-SFL200通信协议、sentryv通信协议<br>|@罗建强<br>@周益辉|2026\-06\-10<br>|
|V1\.0\.1|修改0XE1增加geo\_precision\_level字段|@李亮|20260714|
|V1\.0\.2|1. 增加0xEA guidance\_safety字段<br>|@李亮|2026/07/21|

# 文档概述

## 文档目的

本文档用于规范Sentry设备与C2上位机平台的以太网通信规则、数据格式及交互逻辑，统一双方对接标准。有效规避对接歧义，为设备联调、项目开发、运维部署提供统一协议依据，保障设备与平台通信稳定、数据规范。

## 适用范围

本协议适用于Sentry设备和C2上位机的数据上传、平台指令下发、设备状态同步、参数配置、异常告警上报、心跳保活等全部业务交互。适用于软件开发调试、软硬件联调、项目交付部署、日常运维及版本迭代对接，为本项目网关与平台通信的唯一通用标准，所有对接主体必须严格遵循。

## 术语与缩略语

### **专业术语**

Sentry设备：搭载边缘计算能力，负责现场数据采集、预处理、协议转换、数据上传，对接上位机平台的核心网络终端设备；

C2上位机平台：云端或本地部署的管理后台，负责接收设备数据、下发控制指令、配置设备参数、统计设备状态的管理平台；

报文：设备与平台单次以太网传输的完整结构化数据包；

上行：设备主动向上位机平台上传数据、状态、告警信息；

下行：上位机平台向设备下发控制指令、配置参数、查询指令；

### **缩略语释义**

TCP：传输控制协议，本协议默认采用的以太网传输协议；

IP：互联网协议，设备网络寻址标识；

HTTP：超文本传输协议（备选传输方式）；

# 通信物理层参数

本项目设备通信采用以太网网络通信方式，实现设备与上位机平台的数据交互，所有通信参数、网络规则统一标准化，设备与平台需严格匹配通信配置，保证链路通畅、数据传输稳定。

## 通信接口与传输方式

通信接口：标准以太网RJ45网口；

传输协议：组网通信采用UDP协议，结构化报文数据通信采用TCP协议（长连接），文件传输采用HTTP协议。

## 网络核心参数

通信端口：组网分配

网络模式：支持静态IP、DHCP自动获取IP两种模式；

连接方式：UDP组网协商通信IP和端口信息，设备作为TCP客户端连接上位机分配的TCP服务器和端口。

# 报文数据帧

## 数据帧结构

16进制报文，小端对齐，数据帧结构如下：

|**起始偏移**|**字段定义**|**字节大小**|**数值范围**|**描述**|
|---|---|---|---|---|
|0|magic|1|0xFD|帧头，表示开始一个新的包|
|1|len|2|0\~65014|有效数据长度|
|3|seq|1|0\~255|帧序号，每个设备计数自己的发送序列，允许检测丢包。|
|4|destid|1|0\~255|对端接收者的设备ID|
|5|sourceid|1|0\~255|发送者的设备ID|
|6|msgid|1|0\~255|消息ID|
|7|ack<br>|1|0\~1<br>|是否需要应答<br>0：发送不需要应答；<br>1：发送并需要应答；|
|8|checksum|1|0\~255|包头校验值 \(和校验\)，magic\~ack，buf\[0\] \~ buf\[7\] |
|9|payload|N|\-\-|有效数据内容|
|9\+N|crc|2|0\~0xFFFF|整帧数据校验（CRC16校验），不包含帧头，从 buf\[1\] 至 buf\[9\+N\] 的CRC16校验，这里规定CRC16校验的初始值为0xFFFF，多项式为0x1021。|



## 设备ID定义

|**ID**|**设备名称**|
|---|---|
|0x00|保留（DEV\_NONE）|
|0x01|反制枪（DEV\_AEAG）|
|0x02|显示屏（DEV\_SCREEN）|
|0x03|雷达\(DEV\_RADAR\) |
|0x04|电脑（DEV\_PC）|
|0x06|C2（DEV\_C2）|
|0x07|DEV\_TRACER|
|0x0B|SFL（DEV\_SFL）|
|0x0C|近程雷视 SRP100|
|0x0D|SFL200|
|0x11|雷视 SRP230 \(暂时未使用\)|
|0x14|中程机扫雷视 SRP210|
|0x1B|近程雷视 SPOTTER SSF100 |
|0x1C|DPH130|
|0x1D|中程四面阵雷视 SRP200|
|0x1F|BPH110|
|0x21|SFL210 / sentry|
|0x23|中程四面阵雷视  SPOTTER PRO SSF200|
|0x34|中程机扫雷视  SPOTTER PRO SSF210|
|0x35|Spotter 电源板|
|0x36|Spotter air|
|||
|0x17|FPV\_TRACER|
|0xFF|广播（DEV\_BROADCAST）|

**说明：**

1. 当destid为0xFF时表示该帧为广播，具有中转数据功能的设备需要将该报文转发给所有与其相连的设备。

## 消息ID定义

|**消息ID分类**|**数值范围**|**说明**|
|---|---|---|
|主设备工作状态||用户消息ID是预留给用户根据各个模块实际需求自定义的消息ID，即同一个数值在不同的模块\(dev\_id\)中可以表示不同的含义。|
|主设备参数配置|||
|主设备控制|||
|子设备<br>|0xF0||

# 主设备报文消息内容

## 上报系统工作状态（0x11）

|消息ID|0x11||||
|---|---|---|---|---|
|消息描述|上报主机系统工作状态||||
|方向|设备 \-\> 上位机||||
|发送频率|1Hz||||
|参数payload<br>|字节|Name|Type|Description|
||2|Cnt|Uint16|循环计数|
||4|sysStatus  |Uint32<br>|系统自检状态（按位定义）<br>B0：雷达子系统异常标志<br>B1：视觉子系统异常标志（含转台）<br>B2：频谱子系统异常标志<br>B3：协议子系统异常标志<br>B4：干扰子系统异常标志（含转台）<br>B5：诱骗子系统异常标志<br>B6：供电子系统异常标志<br>B7：系统\-融合模块异常标志<br>B8：系统\-工作温度异常标志<br>B9\-15：预留<br>B16\-31：系统异常码，预留|
||4<br>|workStatus<br>|Uint32|系统工作状态（按位定义）<br>B0：初始化标志<br>B1：工作就绪标志<br>B2：雷达信息关闭标志<br>B3：视觉信息关闭标志<br>B4：频谱信息关闭标志<br>B5：协议信息关闭标志<br>B6：干扰禁用标志<br>B7：诱骗禁用标志<br>B8：视觉转台运动标志<br>B9：干扰转台运动标志<br>B10：网络连通标志<br>B11：时间同步正常标志<br>B12：干扰输出标志<br>B13：诱骗输出标志<br>B14\-15：预留<br>B16\-19：工作模式编号<br>~~1：自动值守 ~~<br>~~2：自动侦测 ~~<br>~~3：静态侦测 ~~<br>1：自动值守（自动）<br>2：静态侦测（手动）<br><br>B20：精确打击使能标志<br>B21: 系统控制状态：0待机，1开机<br>B22: 车载模式状态：0固定模式，1车载模式<br>B23: 驾驶模式状态：0停止，1驾驶<br>B24\-B31：预留|
||4|Temperature1|Float|系统温度（℃）|
||4|Volt|Float|系统电压（V）|
||4|Current|Float|系统电流（A）|
||4|LinkRate1|Float|系统上行通信速率（kB/s）|
||4|LinkRate2|Float|系统下行通信速率（kB/s）|
||8|Longitude|double|系统GPS定位经度（°）|
||8|Latitude|double|系统GPS定位纬度（°）|
||4|Altitude|Float|系统GPS定位海拔高度（m）|
||4|Yaw|Float|系统GPS定姿方位（°）|
||4|Pitch|Float|系统GPS定姿俯仰（°）|
||4|Roll|Float|系统GPS定姿滚转（°）|
||2|satellitesNum2|Uint16|GPS定姿卫星数量|
||1|SubNum|Uint8|子设备个数|
||array\[\] 数组||||
||**25**|**SubSN**|**Uint8**|**子设备SN号**|
||**1**|**SubOnline**<br>|**Uint8**|**0：不在线**<br>**1：在线**|
||1|subType|uint8|子设备类型，参照附录A：子设备类型枚举|
|参数长度|||||
|备注|||||



## 主/子设备基本属性设置/查询（0x10）

|消息ID|0x10||||
|---|---|---|---|---|
|消息描述|请求设置或查询主设备、子设备信息||||
|方向|上位机 \-\> 设备||||
|发送频率|用户触发||||
|参数payload<br>|字节|Name|Type|Description|
||1|cmd<br>|uint8\_t<br>|命令选项：<br>1：查询所有设备（主设备\+子设备）<br>2：查询单个设备（通过设备SN查询）<br>3：修改主设备（通过设备SN修改）\-\- 暂不支持<br>4：修改子设备（通过设备SN修改）\-\- 暂不支持<br>5：新增子设备 \-\- 暂不支持<br>6：删除子设备（通过设备SN删除） \-\- 暂不支持|
||32|reserve1|uint8\_t\[32\]|预留|
||1|num|uint8\_t|设备个数|
||array数组||||
||32|sn<br>|uint8\_t\[32\]|设备SN <br>注：如果cmd是新增子设备，不填SN，内部会自动生成唯一SN|
||1|type|uint8\_t|设备类型 参照附录A：子设备类型枚举|
||16|ip|char\[16\]|IPv4地址字符串|
||4|port|uint32\_t|基础通信端口，0无效|
||1|online|uint8\_t|设备在线状态, 0不在线，1在线|
||64|sw\_version|char\[64\]|软件版本|
||65|reserve2|uint8\_t\[65\]|预留|
||8<br>|longitude<br>|double<br>|安装位置, 无效值：INVALID\_POS = 0xFFFF<br>经度 \(WGS84\), 单位度, 无效值：INVALID\_POS|
||8|latitude|double|纬度 \(WGS84\), 单位度, 无效值：INVALID\_POS|
||4|altitude|float|海拔 \(WGS84\), 单位度, 无效值：INVALID\_POS|
||4|height|float|相对地面高度, 单位米, 无效值：INVALID\_POS|
||4|global\_heading|float|全局坐标系方位角, 单位度, 无效值：INVALID\_POS|
||4|global\_pitch|float|全局坐标系俯仰角, 单位度, 无效值：INVALID\_POS|
||4|global\_roll|float|全局坐标系横滚角, 单位度, 无效值：INVALID\_POS|
||4|local\_heading|float|局部坐标系方位角, 单位度, 无效值：INVALID\_POS|
||4|local\_pitch|float|局部坐标系俯仰角, 单位度, 无效值：INVALID\_POS|
||4|local\_roll|float|局部坐标系横滚角, 单位度, 无效值：INVALID\_POS|
||4|local\_x|float|局部坐标系x距离, 单位米, 无效值: INVALID\_POS|
||4|local\_y|float|局部坐标系y距离, 单位米, 无效值: INVALID\_POS|
||4|local\_z|float|局部坐标系z距离, 单位米, 无效值: INVALID\_POS|
||64|reserve3|uint8\_t\[64\]|预留|
|参数长度|||||
|应答|有||||



应答

|消息ID|0x10||||
|---|---|---|---|---|
|消息描述|返回请求结果||||
|方向|AGX \-\> C2||||
|发送频率|用户触发||||
|参数payload<br>|字节|Name|Type|Description|
||1|result|uint8\_t|0：响应失败<br>1：响应成功|
||1|cmd<br>|uint8\_t<br>|命令选项：<br>1：查询所有设备（主设备\+子设备）<br>2：查询单个设备（通过设备SN查询）<br>3：修改主设备（通过设备SN修改）\-\- 暂不支持<br>4：修改子设备（通过设备SN修改）\-\- 暂不支持<br>5：新增子设备 \-\- 暂不支持<br>6：删除子设备（通过设备SN删除） \-\- 暂不支持|
||32|reserve|uint8\_t\[32\]|预留|
||1|num|uint8\_t|设备个数|
||数组，如果cmd是1，返回当前主设备\+所有子设备，主设备是数组0，其他是子设备||||
||32|sn|uint8\_t\[32\]|设备SN |
||1|type|uint8\_t|设备类型 参照附录A：子设备类型枚举|
||16|ip|char\[16\]|IPv4地址字符串|
||4|port|uint32\_t|基础通信端口，0无效|
||1|online|uint8\_t|设备在线状态, 0不在线，1在线|
||64|sw\_version|char\[64\]|软件版本|
||65|reserve|uint8\_t\[65\]|预留|
||8<br>|longitude<br>|double|安装位置, 无效值：INVALID\_POS = 0xFFFF<br>经度 \(WGS84\), 无效值：INVALID\_POS|
||8|latitude|double|纬度 \(WGS84\), 无效值：INVALID\_POS|
||4|altitude|float|海拔 \(WGS84\), 无效值：INVALID\_POS|
||4|height|float|相对地面高度, 无效值：INVALID\_POS|
||4|global\_heading|float|全局坐标系方位角, 无效值：INVALID\_POS|
||4|global\_pitch|float|全局坐标系俯仰角, 无效值：INVALID\_POS|
||4|global\_roll|float|全局坐标系横滚角, 无效值：INVALID\_POS|
||4|local\_heading|float|局部坐标系方位角, 无效值：INVALID\_POS|
||4|local\_pitch|float|局部坐标系俯仰角, 无效值：INVALID\_POS|
||4|local\_roll|float|局部坐标系横滚角, 无效值：INVALID\_POS|
||4|local\_x|float|局部坐标系x距离, 单位米, 无效值: INVALID\_POS|
||4|local\_y|float|局部坐标系y距离, 单位米, 无效值: INVALID\_POS|
||4|local\_z|float|局部坐标系z距离, 单位米, 无效值: INVALID\_POS|
||64|reserve|uint8\_t\[64\]|预留|
|参数长度|||||



## 基本工作参数配置（0x30）

|消息ID|0x30||||
|---|---|---|---|---|
|消息描述|基本工作参数配置||||
|方向|上位机 \-\> 设备||||
|发送频率|用户触发||||
|<br>参数payload|字节|Name|Type|Description|
||1|cmd|Uint8|1：设置参数<br>2：查询参数|
||4|sys\_mode<br>|Uint32|系统工作模式控制（按位定义）<br>B0：雷达禁用标志（暂不实现）<br>B1：视觉禁用标志（暂不实现）<br>B2：频谱禁用标志（暂不实现）<br>B3：协议禁用标志（暂不实现）<br>B4：干扰禁用标志（暂不实现）<br>B5：诱骗禁用标志（暂不实现）<br>B6：GPS禁用标志（静态姿态有效）<br>B7\-15：预留<br>B21：精确打击使能（\+）<br>B21\-B31：预留|
||20<br>|time<br>|Char|字符串<br>年月日时分秒\.毫秒<br>（例20240515011746\.901）|
||8|Longitude|double|系统GPS定位经度（°）|
||8|Latitude|double|系统GPS定位纬度（°）|
||4|Altitude|Float|系统GPS定位海拔高度（m）|
||4|Yaw|Float|系统GPS定姿方位（°）|
||4|Pitch|Float|系统GPS定姿俯仰（°）|
||4|Roll|Float|系统GPS定姿滚转（°）|
||1|Aim\_<br>Enable<br>|Uint8|预瞄准配置<br>B0：自动值守（自动）<br>B1：静态侦测（手动）<br>B2\-7：预留<br>预瞄准半径=自动打击结束半径|
||2<br>|Jam1\_Solution<br>|Uint16<br>|干扰策略选择<br>B0\-B7:<br>1：自适应策略（Normal）<br>2：全频段策略<br>3：FPV策略<br>4：2\.4\+5\.8策略（暂不实现）<br>5：2\.4\+5\.2\+5\.8策略（DJI策略）<br>B8：GNSS干扰有效标志|
||2|Jam1Time1<br>|Uint16|单次干扰时长（s）<br>（默认30s，最大可设置180s）|
||1|work\_mode|Uint8|工作模式：<br>1：自动值守（自动）<br>2：静态侦测（手动）|
||4|Auto \_angle\_AzBegin|Float|自动值守打击范围<br>方位起始角度（°）|
||4|Auto \_angle\_AzEnd|Float|自动值守打击范围<br>方位终止角度（°）|
||4|Auto \_angle\_ElBegin|Float|自动值守打击范围<br>俯仰起始角度（°）|
||4|Auto \_angle\_ElEnd|Float|自动值守打击范围<br>俯仰终止角度（°）|
||2|Auto\_<br>HitStartR|Uint16|自动值守\-打击开始半径（m）<br>|
||2|Auto\_<br>HitEndR|Uint16|自动值守\-打击结束半径（m）<br>|
||10|Reserved|\-|保留|
|参数长度|||||
|应答|有||||



|消息ID|0x30||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|||||
|参数payload|字节|Name|Type|Description|
||1|status|Uint8|0：响应失败<br>1：设置成功<br>2：查询成功|
||4|sys\_mode|Uint32|系统工作模式控制（按位定义）<br>B0：雷达禁用标志（暂不实现）<br>B1：视觉禁用标志（暂不实现）<br>B2：频谱禁用标志（暂不实现）<br>B3：协议禁用标志（暂不实现）<br>B4：干扰禁用标志（暂不实现）<br>B5：诱骗禁用标志（暂不实现）<br>B6：GPS禁用标志（静态姿态有效）<br>B7\-15：预留<br>B21：精确打击使能（\+）<br>B21\-B31：预留|
||20<br>|time|Char|字符串<br>年月日时分秒\.毫秒<br>（例20240515011746\.901）|
||8|Longitude|double|系统GPS定位经度（°）|
||8|Latitude|double|系统GPS定位纬度（°）|
||4|Altitude|Float|系统GPS定位海拔高度（m）|
||4|Yaw|Float|系统GPS定姿方位（°）|
||4|Pitch|Float|系统GPS定姿俯仰（°）|
||4|Roll|Float|系统GPS定姿滚转（°）|
||2|Aim\_<br>Enable|Uint8|预瞄准配置<br>B0：自动值守（自动）<br>B1：静态侦测（手动）<br>B2\-7：预留<br>预瞄准半径=自动打击结束半径|
||2|Jam1\_Solution|Uint16|干扰策略选择<br>B0\-B7:<br>1：自适应策略（Normal）<br>2：全频段策略<br>3：FPV策略<br>4：2\.4\+5\.8策略（暂不实现）<br>5：2\.4\+5\.2\+5\.8策略（DJI策略）<br>B8：GNSS干扰有效标志|
||2|Jam1Time1|Uint16|单次干扰时长（s）<br>（默认30s，最大可设置180s）|
||||||
||1|work\_mode|Uint8|工作模式：<br>1：自动值守（自动）<br>2：静态侦测（手动）|
||4|Auto \_angle\_AzBegin|Float|自动值守打击范围<br>方位起始角度（°）|
||4|Auto \_angle\_AzEnd|Float|自动值守打击范围<br>方位终止角度（°）|
||4|Auto \_angle\_ElBegin|Float|自动值守打击范围<br>俯仰起始角度（°）|
||4|Auto \_angle\_ElEnd|Float|自动值守打击范围<br>俯仰终止角度（°）|
||2|Auto\_<br>HitStartR|Uint16|自动值守\-打击开始半径（m）|
||2|Auto\_<br>HitEndR|Uint16|自动值守\-打击结束半径（m）<br>|
||||||
||||||
|参数长度|||||
|应答|无||||

## 系统开关控制（0x32）\(待机/开机）

|消息ID|0x32||||
|---|---|---|---|---|
|消息描述|C2下发请求，设置AGX系统开关||||
|方向|C2 \-\> AGX||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|mode<br>|Uint8<br>|控制模式<br>0：待机<br>注：如果是sentry v，待机模式下，嵌入式执行操作参考车载D档<br><br>1：开机<br>注：如果是sentry v，切换开机模式下，嵌入式只返回状态切换为开机，不执行操作，开机之后，需要手动切换到P档，子设备才可正常工作<br>|
||64|reserve|Uint8\[\]|预留|
|参数长度|||||

|消息ID|0x32||||
|---|---|---|---|---|
|消息描述|AGX上传应答||||
|方向|AGX \-\> C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|status<br>|Uint8|0：失败<br>1：成功<br>2：需要一键校准（子设备相对姿态未配置）<br>3：位置变化，重新校准|
||64|reserve|Uint8\[\]|预留|
|参数长度|||||



## 目标干扰打击 \(0x41\)

|消息ID|0x41||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|触发||||
|参数payload|字节|Name|Type|Description|
||1|cmd|Uint8|1：设置任务<br>2：查询当前执行任务|
||||||
||1|Method|Uint8|打击开关（预留）<br>0：停止打击<br>1：打击|
||4|droneNum|Uint32|无人机编号（融合目标）|
||4|reserved|Uint8\[\]|预留|
|参数长度|||||



|消息ID|0x40||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|SFL200  C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|status|Uint8|0：响应失败<br>1：设置成功<br>2：查询成功|
||1|Method|char|打击开关（预留）<br>0：停止打击<br>1：打击|
||4|droneNum|Uint32|无人机编号（融合目标）|
||4|reserve|Int32|预留|
||||||
|参数长度|1||||
||||||



## 系统车载模式指令（sentry V）

### 0x01 协议 IMU车辆姿态查询（差分GPS数据）【优先实现】

IMU数据更新到心跳对应的字段，同时提供提供对外查询接口；

|消息ID|0x01||||
|---|---|---|---|---|
|消息描述|agx上报设备状态属性信息||||
|方向|AGX \-\> C2||||
|发送频率|查询||||
|参数payload<br>|字节|Name|Type|Description|
||2<br>|subtype<br>|uint16<br>|子设备类型<br>参照附录A：子设备类型枚举 \-\> 差分GPS惯导设备 18|
||1|submsgid|Uintu|子设备消息ID（0x01）|
||25|sn|char\[\]|子设备SN|
||2|cnt|uint16|循环计数|
||4|sysstatus  <br>|uint32|系统状态（按位定义）<br>Bit0：是否在线 （0不在线，1在线）<br>Bit1：是否异常/故障（0正常，1异常）|
||1<br>|workstatus<br>|uint8<br>|工作状态<br>0：待机<br>1：开机|
||8|timestamp\_ms|uint64|接收到gps数据时间戳ms|
||8|gps\_timestamp\_ms|uint64|gps原始时间戳ms|
||4|heading|float|航向角（0\~360）|
||4|pitch|float|俯仰角（\-90\~90）|
||4|roll|float|横滚角（\-180\~180）|
||8|lattitude|double|纬度（\-90\~90）|
||8|longitude|double|经度（\-180\~180）|
||4|altitude|float|海拔高度，单位（m）|
||4|v\_e|float|东向速度，单位（m/s）|
||4|v\_n|float|北向速度，单位（m/s）|
||4|v\_u|float|天向速度，单位（m/s）|
||4|baseline|float|基线长度，单位（m）|
||1|nsv1|uint8|天线 1 卫星数|
||1|nsv2|uint8|天线 2 卫星数|
||1<br>|gps\_status|uint8|主天线Gps定位状态:<br>0：初始化/未定位; <br>1：单点定位; <br>2：RTD; <br>3：RTK浮点解; <br>4：RTK固定解;|
||1|speed\_status|uint8|0:无车体速度信息; 1:有车体速度信息|
||4|vehicle\_speed|float|车体速度 Km/h|
||4|acc\_x|float|加速度 X 轴，m/s2|
||4|acc\_y|float|加速度 Y 轴，m/s2|
||4|acc\_z|float|加速度 Z 轴，m/s2|
||4|gyro\_x|float|陀螺仪 X 轴，单位°/s|
||4|gyro\_y|float|陀螺仪 Y 轴，单位°/s|
||4|gyro\_z|float|陀螺仪 Z 轴，单位°/s|
||32|reverse|uint8\[\]|预留|
|参数长度|||||
|应答|无||||
|备注|||||



### 0x02 下发imu数据【优先实现】

|消息ID|0x02||||
|---|---|---|---|---|
|消息描述|如果imu数据不准，需要矫正||||
|方向|c2 \-\> agx||||
|发送频率|查询||||
|参数payload<br>|字节|Name|Type|Description|
||4|heading|float|航向角（0\~360）|
||4|pitch|float|俯仰角（\-90\~90）|
||4|roll|float|横滚角（\-180\~180）|
||8|lattitude|double|纬度（\-90\~90）|
||8|longitude|double|经度（\-180\~180）|
||4|altitude|float|海拔高度，单位（m）|
|参数长度|4\+4\+4\+8\+8\+4||||
|应答|有||||
|备注|||||

|消息ID|0x02||||
|---|---|---|---|---|
|消息描述|收到下发指令返回||||
|方向|AGX  上位机||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|Status<br>|Uint8\_t|0：成功<br>其他：参考章节4 错误码|
|参数长度|1||||



### 0x03 协议（一键标定4个雷达）【暂不实现】

|消息ID|0x03||||
|---|---|---|---|---|
|消息描述|自动标定4个近程雷达，并且查询4个雷达的数据||||
|方向|上位机  AGX||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||8|timestamp|uint64\_t|时间戳|
||25|Sn|Uint8\_t\*|Sentry v sn|
|参数长度|33||||
|响应|有||||

|消息ID|0x03||||
|---|---|---|---|---|
|消息描述|保存配置||||
|方向|AGX  上位机||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|Status<br>|Uint8\_t|0：成功<br>其他：参考章节4 错误码|
|参数长度|1||||



### 0x04 协议（SRP100协议：下发命令获取四雷达数据）【暂不实现】

|消息ID|0x04||||
|---|---|---|---|---|
|消息描述|自动标定4个近程雷达，并且查询4个雷达的数据||||
|方向|上位机  AGX||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||8|timestamp|uint64\_t|时间戳|
||25|Sn|Uint8\_t\*|Sentry v sn|
|参数长度|33||||
|响应|有||||

|消息ID|0x04||||
|---|---|---|---|---|
|消息描述|agx上报雷达的经纬度、方向角等信息||||
|方向|AGX \-\> C2||||
|发送频率|查询||||
|参数payload<br>|字节|Name|Type|Description|
||1|devnum|uint8\_t|雷达个数|
||25|sn|uint8\_t \*|雷达1sn|
||4|heading|float|航向角（0\~360）|
||4|pitch|float|俯仰角（\-90\~90）|
||4|roll|float|横滚角（\-180\~180）|
||8|lattitude|double|纬度（\-90\~90）|
||8|longitude|double|经度（\-180\~180）|
||4|altitude|float|海拔高度，单位（m）|
||\.\.\.\.\.\.||||
|参数长度|1 \+ \(25\+4\+4\+4\+8\+8\+4\)\*devnum||||
|应答|无||||
|备注|||||



### 0x05（车载姿态与子设备配置查询\-\-车辆、四雷达、光学、RF）【暂不实现】

|消息ID|0x05||||
|---|---|---|---|---|
|消息描述|车载子设备配置查询：车辆，雷达，ptz， rf||||
|方向|上位机  AGX||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||8|timestamp|uint64\_t|时间戳|
||25|sn|Uint8\_t\*|Sentry v sn|
|参数长度|33||||
|响应|有||||

|消息ID|0x05||||
|---|---|---|---|---|
|消息描述|agx上报agx子设备的经纬度、方向角等信息||||
|方向|AGX \-\> C2||||
|发送频率|查询||||
|参数payload<br>|字节|Name|Type|Description|
||1|devnum|uint8\_t|设备个数|
||25|sn|uint8\_t \*|设备 （车辆sn：sentryv sn； 光学sn：ptz sn）|
||4|heading|float|航向角（0\~360）|
||4|pitch|float|俯仰角（\-90\~90）|
||4|roll|float|横滚角（\-180\~180）|
||8|lattitude|double|纬度（\-90\~90）|
||8|longitude|double|经度（\-180\~180）|
||4|altitude|float|海拔高度，单位（m）|
||\.\.\.\.\.\.||||
|参数长度|1 \+ \(25\+4\+4\+4\+8\+8\+4\)\*devnum||||
|应答|无||||
|备注|devnum = imu \+ 4雷达 \+ sfl100 \+ ptz光学||||



### 0x06（车载姿态与子设备配置下发（车辆、四雷达、光学、RF 写入数据库）【暂不实现】

|消息ID|0x06||||
|---|---|---|---|---|
|消息描述|c2下发配置信息到agx， 类似0x71||||
|方向|c2 \-\> agx||||
|发送频率|查询||||
|参数payload<br>|字节|Name|Type|Description|
||1|devnum|uint8\_t|设备个数|
||25|sn|uint8\_t \*|子设备sn|
||4|heading|float|航向角（0\~360）|
||4|pitch|float|俯仰角（\-90\~90）|
||4|roll|float|横滚角（\-180\~180）|
||8|lattitude|double|纬度（\-90\~90）|
||8|longitude|double|经度（\-180\~180）|
||4|altitude|float|海拔高度，单位（m）|
||\.\.\.\.\.\.||||
|参数长度|1 \+ \(25\+4\+4\+4\+8\+8\+4\)\*devnum||||
|应答|有||||
|备注|devnum = imu \+ 4雷达 \+ sfl100 \+ ptz光学||||

|消息ID|0x06||||
|---|---|---|---|---|
|消息描述|保存配置||||
|方向|AGX  上位机||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|Status<br>|Uint8\_t|0：成功<br>其他：参考章节4 错误码|
|参数长度|1||||



### 0x08 协议（数据采集开始\-\-通知算法开始采集无人机数据）【优先实现】

|消息ID|0x08||||
|---|---|---|---|---|
|消息描述|下发采数指令，通知算法开始采集||||
|方向|上位机  AGX||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||8|timestamp|uint64\_t|时间戳|
||25|devsn|Uint8\_t\*|sfl100 sn|
||25|dronesn|Uint8\_t\*|无人机sn|
|参数长度|58||||
|响应|有||||

|消息ID|0x08||||
|---|---|---|---|---|
|消息描述|收到下发指令返回||||
|方向|AGX  上位机||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|Status<br>|Uint8\_t|0：成功<br>其他：参考章节4 错误码|
|参数长度|1||||



### 0x92 协议（在sentryv中已经实现）【优先实现】





### 0x09 协议（下发子设备相对坐标值）【优先实现】

|消息ID|0x09||||
|---|---|---|---|---|
|消息描述|下发sfl100相对坐标相关数值||||
|方向|上位机  AGX||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||8|timestamp|uint64\_t|时间戳|
||1|num|Uint8\_t|下发设备个数|
||设备列表数组||||
||25|sn|Uint8\_t\*|设备sn|
||1|devid|Uint8\_t|设备id参考（[雷视与C2上位机通信协议](https://vxr5wm8r80r.feishu.cn/wiki/LnzwwnKafi5TDlknvTAcVvT7ngf?from=from_copylink)）附录|
||4|x|float|x相对坐标|
||4|y|float|y相对坐标|
||4|z|float|z相对坐标|
||4|heading|float|航向角（0\~360）|
||4|pitch|float|俯仰角（\-90\~90）|
||4|roll|float|横滚角（\-180\~180）|
||\.\.\.\.\.\.\.||||
|参数长度|8\+1 \+ （25 \+ 1 \+ 4 \+ 4 \+ 4 \+ 4 \+ 4 \+ 4） \* num||||
|响应|有||||

|消息ID|0x09||||
|---|---|---|---|---|
|消息描述|收到下发指令返回||||
|方向|AGX  上位机||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|Status<br>|Uint8\_t|0：成功<br>其他：参考章节4 错误码|
|参数长度|1||||



### 0x0A 协议（获取子设备相对坐标值）【优先实现】

|消息ID|0x0A||||
|---|---|---|---|---|
|消息描述|获取子设备相对坐标值||||
|方向|上位机  AGX||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||8|timestamp|uint64\_t|时间戳|
||1|num|Uint8\_t|下发sn个数|
||25|sn|Uint8\_t\*|设备sn|
||1|devid|Uint8\_t|设备id|
||\.\.\.\.\.\.\.||||
|参数长度|8\+1 \+ （25\+1）  \* num ||||
|响应|有||||

|消息ID|0x0A||||
|---|---|---|---|---|
|消息描述|上传sfl100相对坐标的值||||
|方向|上位机  AGX||||
|发送频率|用户触发||||
|参数payload<br>|字节|Name|Type|Description|
||1|num|Uint8\_t|下发sn个数|
||25|sn|Uint8\_t\*|设备sn|
||1|devid|Uint8\_t|设备id|
||4|x|float|x相对坐标|
||4|y|float|y相对坐标|
||4|z|float|z相对坐标|
||4|heading|float|航向角（0\~360）|
||4|pitch|float|俯仰角（\-90\~90）|
||4|roll|float|横滚角（\-180\~180）|
||\.\.\.\.\.\.\.||||
|参数长度|1 \+ （25 \+ 4 \+ 4 \+ 4） \* num     num固定1||||
|响应|无||||

### 运行模式控制（0x50）

|消息ID|0x50||||
|---|---|---|---|---|
|消息描述|C2下发请求||||
|方向|C2 \-\> AGX||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|cmd|Uint8|命令类型<br>1：切换车载模式 （防止误操作，暂不支持，嵌入式手动改本地配置文件）<br>2：切换驾驶模式|
||1|mode<br>|Uint8<br>|模式取值：（对应命令类型选项）<br><br>切换车载模式（防止误操作，暂不支持）<br>0：固定模式<br>1：车载模式<br><br>切换驾驶模式<br>0：停止模式<br>1：驾驶模式|
||64|reserve|Uint8\[\]|预留|
|参数长度|66||||

|消息ID|0x50||||
|---|---|---|---|---|
|消息描述|AGX上传应答||||
|方向|AGX \-\> C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1<br>|status|Uint8|0：响应失败<br>1：设置成功|
||64|reserve|Uint8\[\]|预留|
|参数长度|65||||



### 位置校准（0x51）

|消息ID|0x51||||
|---|---|---|---|---|
|消息描述|C2下发请求||||
|方向|C2 \-\> AGX||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|cmd|Uint8|1：开始位置校准 （给各个子设备进行位置标定校准）|
||64|reserve|Uint8\[\]|预留|
|参数长度|65||||

|消息ID|0x51||||
|---|---|---|---|---|
|消息描述|AGX上传应答||||
|方向|AGX \-\> C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1<br>|status|Uint8|0：失败<br>1：成功|
||64|reserve|Uint8\[\]|预留|
|参数长度|65||||



## 云端下发控制指令**（0xA0 \~）**

### 云端下发诱骗信息**\(0xA3\)**

|消息ID|0xA3||||
|---|---|---|---|---|
|消息描述|云端广播诱骗信息给AGX，告诉sentry某个区域正在进行诱骗||||
|方向|天盾 \-\> C2 \-\> sentry||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||4<br>|work\_mode<br>|uint32\_t<br>|当前诱骗功能模式：<br>1：主动防御<br>2：区域拒止<br>3：定向驱离  <br>4: 一键炸机  <br>5：定点诱骗|
||25|spoofer\_sn|char\[\]|诱骗设备sn|
||8|spoofer\_longitude|float64|诱骗设备经度|
||8|spoofer\_latitude|float64|诱骗设备纬度|
||8|spoofer\_height|float64|诱骗设备高度|
||8|spoofer\_radius|float64|诱骗设备防御半径（m）|
||8|induce\_longitude|float64|定点诱骗的经度|
||8|induce\_latitude|float64|定点诱骗的纬度|
||1<br>|enable|uint8\_t<br>|是否启用<br>1：启用<br>2：禁用|
||32|target\_obj\_sn|char\[\]|目标无人机序列号|
||1|target\_obj\_num|uint8\_t|雷达目标个数|
||8|bomber\_radius|float64|炸机范围半径，单位m|
||8|timestamp|uint64\_t|下发请求时间戳|
||256|reserve|uint8\_t|预留|
||array数组<br>注：嵌入式内部和算法操作（根据dev\_sn进行筛选，不管目标是否来自本身，前面状态字段都要发，不属于自身目标，id发无效值；反之，则把对应的目标id找出来；||||
||32|dev\_sn|uint8\_t|侦测设备序列号|
||1|dev\_type|uint8\_t|侦测设备类型|
||4|obj\_id\_in\_dev<br>|uint32\_t|目标在侦测设备中的原始目标ID |
|参数长度|||||
|应答|||||



|消息ID|0xA3|||||
|---|---|---|---|---|---|
|消息描述|诱骗功能|||||
|方向|SFL200 \-\> C2|||||
|发送频率||||||
|参数payload|字节|Name|Type|Description||
||1|Result <br>|uint8\_t<br>|0：成功<br>1：失败||
|参数长度|1|||||
|||||||



### 云端下发 Tracer Matrix 频谱侦测信息**\(0xA4\)**

参照《STF200 Tracer Matrix对外集成协议》

|消息ID|0xA4||||
|---|---|---|---|---|
|消息描述|||||
|方向|天盾 \-\> C2 \-\> sentry||||
|发送频率|由C2决定||||
|参数payload|字节|Name|Type|Description|
||1|requestMode|Uint8|1=频谱目标|
||1|targetTotalNum|Uint8|侦测目标个数（最大64）|
||array数组||||
||4|targetNum|Uint32|目标编号（频谱目标）|
||1|targetType|Uint8|目标信号类型<br>1：数字图传<br>2：模拟图传<br>3：Wifi图传<br>4：FK上行<br>5：FK下行<br>6：前导检测<br>7：信号检测<br>8：干扰源（Tracer   Air Ⅱ涉及）<br>9：遥控信号（Tracer   Air Ⅱ涉及）<br>10：通信基站（Tracer   Air Ⅱ涉及）<br>11：自定义干扰（Tracer   Air Ⅱ涉及）<br>12：自定义遥控（Tracer   Air Ⅱ涉及）<br>13：自定义通信（Tracer   Air Ⅱ涉及）|
||2|targetCode|Uint16|目标标志码<br>用于标识目标频谱信号在整个数据系统内的唯一索引|
||50|targetName|Char\[50\]|无人机名称|
||1|trackStatus|Uint8|无人机跟踪状态<br>B0：发现<br>B1：跟踪<br>B2：记忆<br>B3：消失|
||8|trackTimeCreate|Uint64|建立时间<br>UTC毫秒计数（系统设置时间）|
||8|trackTimeLast|Uint64|最近测量时间<br>UTC毫秒计数（系统设置时间）|
||32|targetCharaCode|Char\[32\]|无人机特征码（字符串）<br>数字图传：<br>前8位有效，1\-4数据库识别码，5\-8特征周期（ms）<br>模拟图传：前4位有效，PAL/NTSC<br>WiFi图传：前24位有效，无人机Mac地址，遥控器Mac地址<br>飞控\-上行：<br>前8位有效，1\-4数据库识别码，5\-8特征周期（ms）<br>飞控\-下行：<br>前8位有效，1\-4数据库识别码，5\-8特征周期（ms）<br>前导检测：<br>前32位有效，1\-4为SSS根值，5\-8为BS根值，9\-16为空，17\-24为SSS计算相关值，25\-32为BS计算相关值|
||1|targetConfidence|uint8|目标置信度|
||4|trackCnt|Uint32|测量次数|
||4|trackFrequence|Float|信号频率/MHz|
||4|trackBW|Float|信号带宽/MHz |
||4|trackBwS|int|跟踪频率起始索引|
||4|trackBwE|int|跟踪频率终止索引|
||4|trackCF|Float|信号所在接收机本振频点/MHz|
||4|trackEF|Float|信号扩展描述频率/MHz|
||4|trackPow|Float|信号功率/dBm |
||4|trackNoice|Float|噪声功率/dBm |
||4|trackSNR|Float|信噪比/dB|
||4|trackDistance|Float|距离估计/m<br>**注：参考**|
||4|trackCT|Float|特征时间/us<br>**注：仅数字图传、模拟图传、飞控上下行有效**|
||4|trackAz|Float|测量方位/°（固定系）|
||4|trackEl|Float|测量俯仰/°（固定系）|
||4|trackAzErr|Float|测量方位误差范围/°|
||4|trackElErr|Float|测量俯仰误差范围/°|
||8|trackAngleTime|Uint64|角度测量时间<br>UTC毫秒计数|
||1|trackPDWType|uint8|目标PDW类型|
||4|trackFStart|Float|目标信号起始频率|
||4|trackFEnd|Float|目标信号结束频率|
||1|trackPRINum|uint8|目标周期个数|
||20|trackPRIValue|Float\[5\]|目标周期数组|
||1|trackPWNum|uint8|目标脉冲个数|
||20|trackPWValue|Float\[5\]|目标脉冲数组|
||4|targetProcStatus|Uint32|属性状态<br>B0：白名单标志<br>B1：特征测量时间有效标志<br>B2：时间属性\-本地时间有效标志<br>B3：时间属性\-GPS时间PPS有效标志<br>B4：数据融合标志（被协议关联）<br>B5：固定坐标系有效标志|
||4|exInfo1|Uint32|扩展信息1<br>特征测量时间\-秒计数<br>表示特征时刻，不同类型定义不同，用于精准打击和数据融合<br>**注：用于分布式打击同步，仅数字图传、模拟图传飞控上下行、前导检测有效**|
||4|exInfo2|Uint32|扩展信息2<br>特征测量时间\-纳秒计数<br>表示特征时刻，不同类型定义不同，用于精准打击和数据融合<br>**注：用于分布式打击同步，仅数字图传、模拟图传飞控上下行、前导检测有效**|
||4|exInfo3|Float|原始测量方位/°|
||4|exInfo4|Float|原始测量俯仰/°|
||6|reserved|Uint8\[6\]|备用|
|参数长度|||||
|应答|无||||



### 云端下发 Tracer Matrix 协议侦测信息**\(0xA5\)**

参照《STF200 Tracer Matrix对外集成协议》

|消息ID|0xA5||||
|---|---|---|---|---|
|消息描述|||||
|方向|天盾 \-\> C2 \-\> sentry||||
|发送频率|由C2决定||||
|参数payload|字节|Name|Type|Description|
||1|requestMode|Uint8|2=协议目标|
||1|targetTotalNum|Uint8|侦测目标个数（最大64）|
||array数组||||
||4|droneNum|Uint32|无人机编号|
||1|droneType|Uint16|无人机信号类型（按位处理）<br>B0：DroneID\-未加密<br>B1：DroneID\-加密<br>B2：RemoteID\-WiFi<br>B3：RemoteID\-Bluetheeth<br>B5：DroneID\-Detected<br>**注：可多选**|
||50|droneName|Char\[50\]|字符串<br>无人机名称|
||1|trackStatus|Uint8|无人机跟踪状态<br>B0：发现<br>B1：跟踪<br>B2：记忆<br>B3：消失|
||8|trackTimeCreate|Uint64|建立时间 <br>UTC毫秒计数（系统设置时间）|
||8|trackTimeLast|Uint64|最近测量时间<br>UTC毫秒计数（系统设置时间）|
||32|trackSN|Char\[32\]<br>|无人机SN码<br>前20位为SN码，中间6位为RID飞机端的MAC地址，最后6位为保留|
||1|trackSource|Uint8|无人机测量来源<br>B0：DroneID\-未加密<br>B1：DroneID\-加密<br>B2：RemoteID\-WiFi<br>B3：RemoteID\-Bluetheeth<br>注：单选|
||4|trackCnt|Uint32|测量次数|
||4|trackFrequence|Float|当前信号频率/MHz|
||4|trackPow|Float|当前信号功率/dBm |
||4|trackNoice|Float|当前噪声功率/dBm |
||4|trackSNR|Float|当前信噪比/dB|
||8|droneGPSTime|Uint64|无人机广播时间戳<br>UTC毫秒计数：1970年1月1日至今|
||8|droneLongitude|double|无人机经度\(°\)|
||8|droneLatitude|double|无人机纬度\(°\)|
||4|droneAltitude|Float|无人机海拔高度\(m\)|
||4|droneHeight1|Float|无人机距地高度\(m\)|
||4|droneHeight2|Float|无人机相对设备高度\(m\)|
||8|droneSailLongitude|double|无人机返航点经度\(°\)|
||8|droneSailLatitude|double|无人机返航点经度\(°\)|
||4|droneSailAltitude|Float|无人机返航点海拔高度\(m\)|
||8|pilotLongitude|double|飞手经度\(°\)|
||8|pilotLatitude|double|飞手纬度\(°\)|
||4|pilotAltitude|Float|飞手海拔高度\(m\)|
||4|droneYawAngle|Float|无人机角度\(°\)|
||4|droneSpeed|Float|无人机绝对速度\(m/s\)|
||4|droneVerticalSpeed|Float|无人机垂直速度\(m/s\)|
||2|droneRidSeqNum|Uint16|RID信号序号|
||2|droneDidSeqNum|Uint16|DID信号序号|
||2|droneRidClassification|Uint16|RID分类<br>无人机类型，比如固定翼或者旋翼|
||2|droneRidStatus|Uint16|高8位：RID运行状态<br>低8位：RID系统状态|
||4|droneProcStatus|Uint32|属性状态（按位处理）<br>B0：白名单标志<br>B1：特征测量时间有效标志<br>B2：时间属性\-本地时间有效标志<br>B3：时间属性\-GPS时间PPS有效标志<br>B4：数据融合标志（关联频谱）|
||4|exInfo1|Uint32|扩展信息1：DroneID特征测量时间\-秒计数<br>表示Burst到达时刻，用于精准打击和数据融合|
||4|exInfo2|Uint32|扩展信息2：DroneID特征测量时间\-纳秒计数<br>表示Burst到达时刻，用于精准打击和数据融合|
||4<br>|exInfo3<br>|Uint32|扩展信息3：RemoteID特征测量时间\-秒计数<br>表示Burst到达时刻，用于精准打击和数据融合<br>注：仅WiFi有效|
||4|exInfo4<br>|Uint32|扩展信息4：RemoteID特征测量时间\-纳秒计数<br>表示Burst到达时刻，用于精准打击和数据融合<br>注：仅WiFi有效|
||4|spect\_match\_protocol<br>|uint32|关联的频谱目标编号（对应 SPTarget\.target\_num），0 表示未关联|
||11|reserved|Uint8\[11\]|备用|
|参数长度|||||
|应答|||||



## **监听模式指令（0xC0 \~）**

### **目标跟踪（0xc1）（雷达\+协议）**

|消息ID|0xC1||||
|---|---|---|---|---|
|消息描述|目标跟踪||||
|方向|C2 SFL200||||
|发送频率|触发||||
|参数payload|字节|Name|Type|Description|
||1|Type<br>|Uint8\_t|~~0：雷达~~<br>~~1：tracer~~<br>0：选择PTZ设备跟踪<br>1：选择激光PTZ设备跟踪<br>2: 敌军标定<br>3: 友军标定<br>4：取消PTZ跟踪目标<br>5：取消激光PTZ设备跟踪<br>6：选择雷达TAS跟踪（20260203 by zgd）<br>7：取消雷达TAS跟踪（20260203 by zgd）|
||4|ObjId|int32\_t|雷达目标ID|
||32|sn|char|无人机序列号|
||4<br>|classification|Uint32\_t|目标类别，<br>enum AIClassification \{<br>auto, //自动<br>uav, //无人机<br>bird, //鸟类<br>cloud, //云<br>tree, //树木<br>mountain, //山<br>…<br>\}|
||4|reserve|uint8\_t\[4\]|预留|
|参数长度|47||||



|消息ID|0xC1||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|SFL200  C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|Status|uint8\_t|1：成功<br>0：失败|
|参数长度|1||||
||||||



### **目标打击处置（0xc2）（雷达\+协议）**

|消息ID|0xC2||||
|---|---|---|---|---|
|消息描述|目标打击处置||||
|方向|C2 SFL200||||
|发送频率|触发||||
|参数payload<br>|字节|Name|Type|Description|
||1<br>|Type|Uint8\_t|0：雷达<br>1：tracer|
||4|ObjId|int32\_t|雷达目标ID|
||32|sn|char|无人机序列号|
||4<br>|classification|Uint32\_t<br>|目标类别，<br>enum AIClassification \{<br>auto, //自动<br>uav, //无人机<br>bird, //鸟类<br>cloud, //云<br>tree, //树木<br>mountain, //山<br>…<br>\}|
||4|reserve|uint8\_t\[4\]|预留|
|参数长度|47||||



|消息ID|0xC2||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|SFL200  C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|Status|uint8\_t|1：成功<br>0：失败|
|参数长度|1||||
||||||



### **频谱目标定向（0xc3）（频谱）**



|消息ID|0xC3||||
|---|---|---|---|---|
|消息描述|频谱目标定向||||
|方向|C2 SFL200||||
|发送频率|触发||||
||1|productType|uint8\_t|无人机类型|
||25|droneName|char|字符串 无人机名称 |
||32|serialNum|char|字符串 无人机SN|
||4|droneLongitude|int32\_t|无人机经度\(/1e7\)|
||4|droneLatitude|int32\_t|无人机纬度\(/1e7\)|
||2|droneHeight|int16\_t|无人机相对地面高度\(0\.1m\)|
||2|droneYawAngle|int16\_t|无人机角度\(0\.01deg\)|
||2|droneSpeed|int16\_t|无人机绝对速度\(0\.01m/s\)|
||2|droneVerticalSpeed|int16\_t|无人机垂直速度\(0\.01m/s\)|
||1|Speedderection|uint8\_t|0：无人机水平向前  lite<br>1：无人机水平向后  lite<br>2：无人机水平向左  lite<br>3：无人机水平向右  lite<br>4：无人机垂直<br>无效值为0xFF|
||4|droneSailLongitude|int32\_t|无人机航点经度\(/1e7\)|
||4|droneSailLatitude|int32\_t|无人机航点经度\(/1e7\)|
||4|pilotLongitude|int32\_t|飞手经度\(/1e7\)|
||4|pilotLatitude|int32\_t|飞手纬度\(/1e7\)|
||4|droneHorizon|int32\_t|目标水平角\(0\.01°\)|
||4|dronePitch|int32\_t|目标俯仰角\(0\.01°\) |
||4|uFreq|uint32\_t|无人机信号频率\(MHz\)|
||2|uDistance|uint16\_t|无人机与本设备的距离\(m\)|
||2|uDangerLevels|uint16\_t|危险等级|
||2|uZC|uint16\_t|ZC序列值|
||1|uDirStatus|uint8\_t|定向状态<br>0：非定向状态<br>1：定向中<br>2：定向成功<br>其它：保留|
||2|uNumber|uint16\_t|编号 |
||6|Wifi\_mac|uint8\_t|WIFI mac, 仅对于wifi机型有效|
||8|gps\_clocks|uint64\_t|无人机GPS时间戳：1970年1月1日至今毫秒数 \(ms\)<br>当无人机类型为DroneID时有效|
||4|TimestampRid|uint32\_t|以当前小时为起始时刻，已经过去的1/10秒数<br>当无人机类型为RemoteID时有效|
||1|ID\_type<br>|uint8\_t|无人机的类型：<br>0：频谱类无人机<br>1: DroneID<br>2: RemoteID<br>3: DroneID \& RemoteID|
||4|flagTime|uint32\_t|图传周期结束的点数，用于精准打击和数据融合。0xFFFFFFFF均表示无效值|
||2|droneAltitude|int16\_t|无人机海拔高度\(0\.1m\)|
||2<br>|droneElevation|int16\_t|无人机相对于设备的高度\(0\.1m\)|
||1<br>|jammingAccurateType|uint8\_t|精准打击类型值<br>0：无效值，<br>1：DJI Ocusync2<br>2: DJI Ocusync3<br>3: DJI Ocusync4<br>4: DJI\_Phantom4\_RTK频谱无人机<br>5: DJI 带加密协议，并且侦测到它的图传为DJI Ocusync4<br>6：DJI 带加密协议，但是没有侦测到它对应的图传信息<br>7：其它DJI带协议的无人机（除DJI\_Phantom4\_RTK带协议外）<br>8：DJI\_Phantom4\_RTK带协议无人机<br>9：Autel无人机<br>0xFF: 无法支持精准打击<br><br>其它：保留|
||2|droneSingalPower|int16\_t|int16\_t|
||2|droneNoisePower|int16\_t|噪声信号的功率\(0\.1dBm\)|
||2|droneSNR|int16\_t|当前的信噪比（dB）|
||4|droneDetectionCnt|uint32\_t|该无人机的侦测次数|
||1|droneSingalType<br>|uint8\_t|该无人机的信号类型：<br>0：无效值<br>1：数字图传<br>2：模拟图传<br>3：WIFI<br>4：飞控下行信号<br>5：飞控上行信号<br>6：RemoteID<br>7：DroneID<br>8: DroneID\&RemoteID|
||2|droneFlag|int16\_t|无人机属性状态：按Bit位读取信息<br>B0：白名单标志（协议目标有效）<br>B1：预测数据标志（协议目标有效）<br>B2：瞄准标志（协议目标有效）<br><br>B3：精确打击有效标志  <br>B4：跟踪打击有效标志（协议目标有效）<br>B5：无附件打击标志<br><br>B6：数据融合标志（协议目标有效）<br>B7：可定向标志（频谱目标有效）<br>B8：可打击标志（频谱目标有效）<br>B9：正被打击标志<br>B10：是否支持FPV视频流截获|
||7|reserve|uint8\_t|保留值|
|参数长度|||||
|应答|有||||





|消息ID|0xC3||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|SFL200  C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|Status|uint8\_t|1：成功<br>0：失败|
|参数长度|1||||
|备注|||||





### **频谱目标定向打击（0xc4）（频谱）**

|消息ID|0xC4||||
|---|---|---|---|---|
|消息描述|频谱目标定向\+打击||||
|方向|C2 SFL200||||
|发送频率|触发||||
||1|productType|uint8\_t|无人机类型|
||25<br>|droneName<br>|char|字符串 无人机名称 |
||32|serialNum|char|字符串 无人机SN|
||4|droneLongitude|int32\_t|无人机经度\(/1e7\)|
||4|droneLatitude|int32\_t|无人机纬度\(/1e7\)|
||2<br>|droneHeight|int16\_t|无人机相对地面高度\(0\.1m\)|
||2<br>|droneYawAngle|int16\_t|无人机角度\(0\.01deg\)|
||2<br>|droneSpeed|int16\_t|无人机绝对速度\(0\.01m/s\)|
||2<br>|droneVerticalSpeed|int16\_t|无人机垂直速度\(0\.01m/s\)|
||1<br>|Speedderection|uint8\_t|0：无人机水平向前  lite<br>1：无人机水平向后  lite<br>2：无人机水平向左  lite<br>3：无人机水平向右  lite<br>4：无人机垂直<br>无效值为0xFF|
||4<br>|droneSailLongitude|int32\_t|无人机航点经度\(/1e7\)|
||4|droneSailLatitude|int32\_t|无人机航点经度\(/1e7\)|
||4|pilotLongitude|int32\_t|飞手经度\(/1e7\)|
||4|pilotLatitude|int32\_t|飞手纬度\(/1e7\)|
||4|droneHorizon|int32\_t|目标水平角\(0\.01°\)|
||4|dronePitch|int32\_t|目标俯仰角\(0\.01°\) |
||4<br>|uFreq|uint32\_t|无人机信号频率\(MHz\)|
||2|uDistance|uint16\_t|无人机与本设备的距离\(m\)|
||2|uDangerLevels|uint16\_t|危险等级|
||2|uZC|uint16\_t|ZC序列值|
||1|uDirStatus|uint8\_t|定向状态<br>0：非定向状态<br>1：定向中<br>2：定向成功<br>其它：保留|
||2|uNumber|uint16\_t|编号 |
||6|Wifi\_mac|uint8\_t|WIFI mac, 仅对于wifi机型有效|
||8|gps\_clocks|uint64\_t|无人机GPS时间戳：1970年1月1日至今毫秒数 \(ms\)<br>当无人机类型为DroneID时有效|
||4|TimestampRid<br>|uint32\_t|以当前小时为起始时刻，已经过去的1/10秒数<br>当无人机类型为RemoteID时有效|
||1|ID\_type<br>|uint8\_t|无人机的类型：<br>0：频谱类无人机<br>1: DroneID<br>2: RemoteID<br>3: DroneID \& RemoteID|
||4|flagTime|uint32\_t|图传周期结束的点数，用于精准打击和数据融合。0xFFFFFFFF均表示无效值|
||2|droneAltitude|int16\_t|无人机海拔高度\(0\.1m\)|
||2<br>|droneElevation|int16\_t|无人机相对于设备的高度\(0\.1m\)|
||1<br>|jammingAccurateType|uint8\_t|精准打击类型值<br>0：无效值，<br>1：DJI Ocusync2<br>2: DJI Ocusync3<br>3: DJI Ocusync4<br>4: DJI\_Phantom4\_RTK频谱无人机<br>5: DJI 带加密协议，并且侦测到它的图传为DJI Ocusync4<br>6：DJI 带加密协议，但是没有侦测到它对应的图传信息<br>7：其它DJI带协议的无人机（除DJI\_Phantom4\_RTK带协议外）<br>8：DJI\_Phantom4\_RTK带协议无人机<br>9：Autel无人机<br>0xFF: 无法支持精准打击<br><br>其它：保留|
||2|droneSingalPower|int16\_t|int16\_t|
||2|droneNoisePower|int16\_t|噪声信号的功率\(0\.1dBm\)|
||2|droneSNR|int16\_t|当前的信噪比（dB）|
||4|droneDetectionCnt|uint32\_t|该无人机的侦测次数|
||1|droneSingalType<br>|uint8\_t|该无人机的信号类型：<br>0：无效值<br>1：数字图传<br>2：模拟图传<br>3：WIFI<br>4：飞控下行信号<br>5：飞控上行信号<br>6：RemoteID<br>7：DroneID<br>8: DroneID\&RemoteID|
||2|droneFlag|int16\_t|无人机属性状态：按Bit位读取信息<br>B0：白名单标志（协议目标有效）<br>B1：预测数据标志（协议目标有效）<br>B2：瞄准标志（协议目标有效）<br><br>B3：精确打击有效标志  <br>B4：跟踪打击有效标志（协议目标有效）<br>B5：无附件打击标志<br><br>B6：数据融合标志（协议目标有效）<br>B7：可定向标志（频谱目标有效）<br>B8：可打击标志（频谱目标有效）<br>B9：正被打击标志<br>B10：是否支持FPV视频流截获|
||7|reserve|uint8\_t|保留值|
|参数长度|160||||
|应答|有||||





|消息ID|0xC4||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|SFL200  C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|Status|uint8\_t|2：定向成功<br>1：成功<br>0：失败|
|参数长度|1||||
|备注|||||



### **开关打击（0xc5）（纯手动）**

|# **消息ID**|0xC5||||
|---|---|---|---|---|
|消息描述|启动/停止打击  ||||
|方向|C2  SFL200||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|StartStop|uint8\_t|0：停止打击<br>1：开启打击|
|参数长度|1||||
|应答|有||||



|消息ID|0xC5||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|SFL200  C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|Status|uint8\_t|1：成功<br>0：失败|
|参数长度|1||||
||||||



### **转台手动控制（0xc6）（纯手动）**

|消息ID|0xC6||||
|---|---|---|---|---|
|消息描述|转台手动控制  ||||
|方向|C2  SFL200||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|StartStop|uint8\_t|启动/停止转动<br>0：停止转动，如下的参数全部无效<br>1：启动转动<br>2：转台复位|
||1|H\_Direction|uint8\_t|水平转动方向<br>1:顺时钟转动<br>2:逆时钟转动<br>0xFF:表示按指定角度转动<br>其它值无效|
||2|H\_Angle|int32\_t|水平转动的目标角度<br>单位为0\.01度。<br>当Direction=0xFF时，该值有效<br>有效值的范围为\-36000\~36000，其它值无效|
||2|H\_Speed|uint16\_t|水平转动速度，单位为度/秒<br>0：表示使用最大速度转动<br>当指定的最大转速大于设备的转速时，设备将以最大的转速进行转动|
||1|V\_Direction|uint8\_t|垂直转动方向<br>1:顺时钟转动<br>2:逆时钟转动<br>0xFF:表示按指定角度转动<br>其它值无效|
||2|V\_Angle|int32\_t|垂直转动的目标角度<br>单位为0\.01度。<br>当Direction=0xFF时，该值有效<br>有效值的范围为\-36000\~36000，其它值无效|
||2|V\_Speed|uint16\_t|垂直转动速度，单位为度/秒<br>0：表示使用最大速度转动<br>当指定的最大转速大于设备的转速时，设备将以最大的转速进行转动|
|参数长度|6||||
|应答|有||||
|备注|1. 当以指定转动方向转动时，会一直转动，直到收到停止命令||||



|消息ID|0xC6||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|SFL200  C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|Status|uint8\_t|1：成功<br>0：失败|
|参数长度|1||||
||1\.失败的原因可能是参数错误，或者转台故障<br>2\.不管转台是否有水平转动，收到的停止命令，返回成功。||||



## **系统工作参数（0xD0 \~）**

### **参数读取 \(0xD2\)**

|消息ID|0xD2||||
|---|---|---|---|---|
|消息描述|读取||||
|方向|C2 SFL200||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||||||
|参数长度|0||||
||||||



|消息ID|0xD2|||||
|---|---|---|---|---|---|
|消息描述|SFL200自动察打参数读取 应答|||||
|方向|SFL200  C2|||||
|发送频率|用户触发|||||
|参数payload|字节|Name|Scale|Type|Description|
||1|Sys\_GB\_lMode|1|uint8\_t|使能手动位置标定<br>1：有效<br>2：无效（默认）<br>其他：无效|
||8|Sys\_GB\_jd|1|Double|经度，单位°|
||8|Sys\_GB\_wd|1|Double|纬度，单位°|
||8|Sys\_GB\_gd|1|Double|高度，单位m|
||2|Sys\_GB\_jTime1|1|Uint16|单次干扰最大时长，单位s<br>默认180s|
||2|Sys\_GB\_jTime2|1|Uint16|单次干扰时长，<br>单位s<br>默认30s|
||2|Sys\_GB\_jTime3|1|Uint16|监听模式单次干扰时长，单位s<br>默认30s|
||1|Sys\_GB\_jMode|1|uint8\_t|干扰模式选择<br>1：频谱自动匹配模式<br>2：全频段模式<br>3：FPV模式<br>4：手动选择模式<br>其他：无效，暂不定义|
||1|Sys\_GB\_jF0|1|uint8\_t|433干扰频段有效<br>1：是，2：否，其他无效|
||1|Sys\_GB\_jF1|1|uint8\_t|800干扰频段有效<br>1：是，2：否，其他无效|
||1|Sys\_GB\_jF2<br>|1|uint8\_t|900干扰频段有效<br>1：是，2：否，其他无效|
||1|Sys\_GB\_jF3|1|uint8\_t|GNSS干扰频段有效<br>1：是，2：否，其他无效|
||1|Sys\_GB\_jF4|1|uint8\_t|2\.4G干扰频段有效<br>1：是，2：否，其他无效|
||1|Sys\_GB\_jF5|1|uint8\_t|5\.2G干扰频段有效<br>1：是，2：否，其他无效|
||1|Sys\_GB\_jF6|1|uint8\_t|5\.8G干扰频段有效<br>1：是，2：否，其他无效|
||1|Sys\_GB\_jF7|1|uint8\_t|预留|
||1|Sys\_GB\_jF8|1|uint8\_t|预留|
||1|Sys\_GB\_jF9|1|uint8\_t|预留|
||2|Sys\_GB\_jFPV1||Uint16\_t|FPV模式起始频段|
||2|Sys\_GB\_jFPV2||Uint16\_t|FPV模式终止频段|
|||||||
|参数长度|34|||||
|应答|有|||||



### 获取白名单列表（新）** \(0xD5\)**

|消息ID|0xD5||||
|---|---|---|---|---|
|消息描述|获取白名单列表||||
|方向|C2\-\>SFL200||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||64|reserve|Uint8\_t\[\]|预留|
||||||
|参数长度|64||||
|备注|||||



|消息ID|0xD5||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|SFL200 \-\> C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|status|Uint8\_t|0：失败<br>1：成功|
||32|reserve|Uint8\_t\[\]|预留|
||2|num|Uint16\_t|无人机总数|
||array 数组||||
||32<br>|sn<br>|char\[\]|字符串 （无人机SN码）|
||32|reserve|Uint8\_t\[\]|预留|
|参数长度|35 \+ num \* 64||||
|备注|||||



### 新增/删除白名单（新）** \(0xD6\)**

|消息ID|0xD6||||
|---|---|---|---|---|
|消息描述|||||
|方向|C2\-\>SFL200||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|cmdType|Uint8\_t<br>|0：增加白名单（友军）<br>1：删除白名单（敌军）|
||32|reserve|Uint8\_t\[\]|预留|
||2|num|Uint16\_t|无人机总数|
||Array 数组 单次1个或多个无人机||||
||32<br>|sn<br>|char\[\]|无人机SN码<br>\(无则填空，有SN则永久保存，没有SN的目标会根据无人机id进行临时标记\)|
||4|id|Uint32\_t|无人机id<br>（会变，无则填0）|
||28|reserve|Uint8\_t\[\]|预留|
|参数长度|35 \+ num \* 64||||
|应答|有||||
|备注|||||



|消息ID|0xD6||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|SFL200 \-\> C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1|status|Uint8\_t|0：失败<br>1：成功|
|参数长度|1 ||||
|备注|||||



## **版本列表获取 \(0xD4\)**

|消息ID|0xD4|||||
|---|---|---|---|---|---|
|消息描述|SFL200版本列表获取|||||
|方向|C2SFL200|||||
|发送频率|触发|||||
|参数payload|字节|Name|Scale|Type|Description|
|||||||
|参数长度|0|||||
|应答|有|||||



|消息ID|0xD4||||
|---|---|---|---|---|
|消息描述|SFL200版本列表获取应答||||
|方向|SFL200 C2||||
|发送频率|触发||||
|参数payload|字节|Name|Type|Description|
||64|sfl200\_version|char\*|Sfl200版本号|
||64|agx\_version|char\*|Agx版本号|
||64|sfl100\_version|char\*|Sfl100版本号|
||64|fusion\_version|char\*|Fusion版本号|
||64|tracer\_p\_version|char\*|Tracer\-p版本号|
||64|radar\_version|char\*|Radar版本号|
||64|spoffer\_version|char\*|Spoffer版本号|
|参数长度|7\*64||||
||||||



## **系统侦测信息（0xE0 \~）（周期上报）**

### **雷视融合（0xE1）**

|消息ID|E1||||
|---|---|---|---|---|
|消息描述|上报融合目标数据||||
|方向|设备 \-\> 上位机||||
|发送频率|10HZ||||
|参数payload<br>|字节|Name|Type|Description|
||8<br>|timestamp<br>|uint64|融合算法本轮执行基准时间戳（ms），UTC时间自1970年1月1日0时整至侦测数据包本轮执行基准时刻所经过的毫秒数|
||2|fusion\_tracker\_num|uint16|融合目标个数，取值为0到200|
||8|reserve|uint8\_t\[8\]|预留字段|
||array\[\] 数组||||
||4|id<br>|uint32<br>|融合目标ID，取值为1到49999，大于49999时从1重新开始循环计数<br>|
||25|dronename<br>|char|融合目标名称，优先使用无人机品牌名与机型名，否则使用“Type\-Id”形式，如Drone\-42、Unidentified\-101等|
||32|serialnum<br>|char|无人机SN序列号，无效值或未知时置为空字符串，此时协议扩展字段（加粗字段）的数值均无效|
||4<br>|source<br>|uint32|融合目标数据源 \[按位赋值b31…b0\] <br>b0：PTZ数据源（10秒内被PTZ侦测到时置1）<br>b1：协议数据源（10秒内被协议侦测到时置1）<br>b2：雷达数据源（10秒内被雷达侦测到时置1）<br>b3：频谱数据源（10秒内被频谱侦测到时置1）<br>b4\~b7：预留字段<br>b8：打击处置（融合结果受打击影响时置1）<br>b9：诱骗干扰（融合结果受诱骗影响时置1）<br>b10\~b31：预留字段<br>\[如source = 523 = 0x0010 0000 1011，表示该融合目标在近10秒内被PTZ、协议、频谱共同观测过，但融合结果正在受到导航诱骗的干扰\]|
||1|state\_type|uint8|融合目标状态，0：无效目标，1：稳态目标，2：暂态目标，3：丢失目标，9：被融合目标，其他无效|
||1|existing\_prob|uint8|融合目标存在概率百分比（%），取值为0到100|
||4|lifetime<br>|float32|融合目标生命周期（s），任意数据源第一次侦测至当前时刻的时间，取值为0到86400，当时间大于等于86400s时置为86400s|
||4|forcast\_time|float32|融合目标预测时长（s），任意数据源最近一次侦测至当前时刻的时间，取值为0到3600，当时间大于等于3600s时置为3600s|
||1|classification|uint8|融合目标类别，0：未识别，1：无人机，2：单兵，3：车辆，4：鸟类，5：轻型飞行物，其他无效|
||1|classification\_prob|uint8|融合目标类别概率百分比（%），取值为0到100|
||1|geo\_valid<br>|uint8|融合目标的地理信息是否有效，0：无效，1：有效，其他无效；<br>当本字段为0时，longitude、latitude、altitude、height字段内的数值均无效<br>\[如仅由频谱侦测的目标\]<br>\[如仅由协议侦测的室内或卫星信号差、未起飞或其他无有效地理报文情形，与受诱骗影响的目标\]|
||8|longitude|float64|融合目标经度（deg），取值为\-180（不含）到180（含），最小分辨率为小数点后第7位（约11mm），无效值或未知时置为0°|
||8|latitude|float64|融合目标纬度（deg），取值为\-90到90，最小分辨率为小数点后第7位（约11mm），无效值或未知时置为0°|
||8|altitude|float64|融合目标高度（m），几何高度（基于WGS\-84坐标系椭球面的高度）或气压高度（基于1013\.25毫巴为基准的高度），取值为\-999到10000，无效值或未知时置为\-1000m，当高度大于等于10000m时置为10000m，当高度小于等于\-999m时置为\-999m|
||8|height<br>|float64|融合目标距地高度（m），基于起飞地的高度或AGL高度，取值为\-999到10000，无效值或未知时置为\-1000m，当高度大于等于10000m时置为10000m，当高度小于等于\-999m时置为\-999m|
||4|orientation\_angle|float32|融合目标航迹角（deg），当前时刻所在位置真北方向顺时针量至地速方向的夹角，取值为0（不含）到360（含），无效值或未知时置为361°|
||4|absolute\_speed|float32|融合目标地速（m/s），相对于WGS\-84基准面的水平运动速度，取值为0到254\.25，无效值或未知时置为255m/s，当速度大于等于254\.25m/s时置为254\.25m/s|
||4|vertical\_speed|float32|融合目标垂直速度（m/s），相对于WGS\-84基准面向上的垂直速度，取值为\-62到62，无效值或未知时置为63m/s，当速度大于等于62m/s时置为62m/s，当速度小于等于\-62m/s时置为\-62m/s|
||1|motion\_type<br>|uint8|融合目标运动类型：<br>0：未识别，1：静止，2：悬停，3：靠近，4：远离，<br>5：向左，6：向右，7：向上，8：向下，9: 炸机，其他无效|
||**8**|**home\_longitude**|**float64**|**无人机返航点经度（deg），取值为\-180（不含）到180（含），无效值或未知时置为0°**|
||**8**|**home\_latitude**|**float64**|**无人机返航点纬度（deg），取值为\-90到90，无效值或未知时置为0°**|
||**8**|**pilot\_longitude**|**float64**|**无人机操作员经度（deg），取值为\-180（不含）到180（含），无效值或未知时置为0°**|
||**8**|**pilot\_latitude**|**float64**|**无人机操作员纬度（deg），取值为\-90到90，无效值或未知时置为0°**|
||**8**|**pilot\_altitude**<br>|**float64**|**无人机操作员高度（m），基于WGS\-84坐标系椭球面的几何高度，取值为\-999到10000，无效值或未知时置为\-1000m，当高度大于等于10000m时置为10000m，当高度小于等于\-999m时置为\-999m**|
||**4**|**frequency**|**float32**|**无人机信号频率（mHz），取值为1到10000，无效值或未知时置为0mHz**|
||1|load\_level|uint8|融合目标挂载等级，0：未识别，1：多，2：少，3：无，其他无效|
||1|danger\_level|uint8|融合目标危险等级，0：未识别，1：非常危险，2：危险较轻，3：无危险，其他无效|
||1|priority|uint8|融合目标处置优先级，取值为0到256，数值越大优先级越高|
||4|target\_range|float32|融合目标相对基准点的空间距离（m），取值为0到20000，当距离大于等于20000m时置为20000m|
||4|target\_azimuth|float32|融合目标相对于基准点的方位角（deg），以地理真北为0°，顺时针方向为正，取值为0（不含）到360（含），无效值或未知时置为361°|
||4|target\_elevation|float32<br>|融合目标相对于基准点的俯仰角（deg），以地面为0°，上仰方向为正，取值为\-90到90，无效值或未知时置为361°|
||4<br>|target\_arrival\_time<br>|float32<br>|融合目标相对基准点的到达时间（s），取值为0到3600，当时间大于等于3600s或目标远离关注点时置为3600s|
||4<br>|proc\_status<br>|uint32<br>|B0：白名单标志<br>B1：正被视觉引导标志<br>B2：正被视觉锁定标志<br>B3：正被干扰锁定标志<br>B4：正被干扰处置标志 （目标处于干扰中）<br>B5：精确打击有效标志（目标是否支持精确打击）<br>B6：GNSS干扰有效标志<br>B7：正被GNSS诱骗处置标志<br>B8：数据预测标志<br>B9：数据融合标志<br>B10：目标坠毁标志<br>B11：干扰有效标志（目标是否支持干扰）<br>B12：诱骗有效标志（目标是否支持诱骗）<br>B13:  正被雷达TAS跟踪标志（20260203 by zgd）|
||4|flag\_time|uint32|图传周期结束的点数，用于精准打击和数据融合。0xFFFFFFFF均表示无效值|
||1|jamming\-\_accruate\_type|uint8<br>|精准打击类型值<br>0：无效值，<br>1：DJI Ocusync2<br>2: DJI Ocusync3<br>3: DJI Ocusync4<br>4:DJI\_Phantom4\_RTK频谱无人机<br>5: DJI 带加密协议，并且侦测到它的图传为DJI Ocusync4<br>6：DJI 带加密协议，但是没有侦测到它对应的图传信息<br>7：其它DJI带协议的无人机（除DJI\_Phantom4\_RTK带协议外）<br>8:DJI\_Phantom4\_RTK带协议无人机<br>9：Autel无人机<br>0xFF: 无法支持精准打击<br>其它：保留|
||4|rf\_singal\_power|float32|噪声信号的功率\(dBm\)|
||4|rf\_noise\_power|float32|当前的信噪比（dB）<br>|
||2|rf\_snr<br>|uint16<br>|当前的信噪比（dB）<br>|
||4|rf\_detection\_cnt|uint32|无人机的侦测次数|
||1|rf\_singal\_type|uint8|无人机的信号类型<br>0：无效；1：数字图传；2：模拟图传；3：wifi图传；4：上行控制；5：下行控制；6：前导检测；7：信号检测；8：干扰源；9：遥控信号；10：通信基站；11：自定义干扰；12：自定义遥控；13：自定义通信|
||4|target\_local\_range|float32|融合目标相对基准点空间距离 \(局部坐标系\) 单位m，默认0|
||4|target\_local\_azimuth|float32|融合目标相对基准点方位角 \(局部坐标系\) 单位°，默认0|
||4|target\_local\_elevation|float32|融合目标相对基准点俯仰角 \(局部坐标系\) 单位°，默认0|
||1<br>|debug\_status<br>|uint8<br>|目标调试状态<br>0：正式目标<br>10：调试目标\-\-视觉<br>20：调试目标\-\-协议<br>30：调试目标\-\-雷达<br>40：调试目标\-\-频谱<br>41：调试目标\-\-TRACER\_AIR<br>90：调试目标\-\-GNSS|
||1<br>|antenna\_type<br>|uint8|目标天线类型:<br>0：未知<br>1：四阵元抗干扰天线|
||4|ground\_distance\_error|float32|地面距离误差（米）|
||4|range\_error|float32|三维距离误差（米）|
||4|azimuth\_error|foat32|方位角误差（米）|
||4|elevation\_error|float32|俯仰角误差（米）|
||8|falling\_longitude|float64|目标坠落经度 单位°，默认0|
||8|falling\_latitude|float64|目标坠落纬度 单位°，默认0|
||1|protocol\_msg\_type|uint8|无人机的协议类型，bit<br>bit0：DID\-解密；<br>bit1：DID\-加密；<br>bit2：RID\-wifi；<br>bit3：RID\-蓝牙。|
||4<br>|track\_bw<br>|float|信号带宽/MHz <br>同huntermax联动时，由中心频点，确认结束频点、起始频点值<br>再由结束频点减去起始频点，起始频点和结束频点如下<br>831\-861MHz<br>900\-930MHz<br>1395\-1450MHz<br>2325\-2377MHz<br>2400\-2500MHz<br>2578\-2630MHz<br>5055\-5110MHz<br>5150\-5250MHz<br>5600\-5655MHz<br>5720\-5850MHz<br>5929\-5982MHz|
||4<br>|track\_ct<br>|float<br>|特征时间/us<br>**注：仅数字图传、模拟图传、飞控上下行有效**|
||1<br>|geo\_precision\_level<br>|uint8<br>|0x00:无效值<br>0x01:多源融合高精度；一般有视觉锁定与距离信息，测距测角均可靠；可作制导主要依据<br>0x02:协议辅助高精度；须协议稳定且刷新率满足制导<br>0x03:雷达跟踪波束<br>0x04:雷达搜索波束<br>0x05:光电角度跟踪；锁定可靠，距离或三维不可靠<br>0x06:定位不可靠；无稳定视觉且协议久未更新，不宜制导|
||1|guidance\_safety|uint8|0：无效值<br>1：SAFE 安全<br>2：WARNING 警告 高度异常（注：天盾需要长时展示）<br>3：WARNING 警告 类别异常（注：天盾需要长时展示）<br>4：DANGER 危险，高度过低，停止引导（注：天盾需要短时展示）|
||19|reserved|uint8\[\]|融合目标预留字段|
|备注|||||



### **视觉计算（0xE2）**

|消息ID|0xE2||||
|---|---|---|---|---|
|消息描述|上传视觉感知数据包||||
|方向|SFL200\-\>C2||||
|发送频率|根据设置和帧处理周期触发||||
|<br>参数payload|字节|Name|Type|Description|
||8|timeStamp|uint64\_t|时间戳（ms）|
||1|objNum|uint8\_t|目标数|
||4|targetId|uint32\_t|ptz跟踪的融合目标ID编号|
||4|zoom|float|Ptz zoom大小|
||4|HFov|float|Ptz 水平视场角\(°\)|
||4|VFov|float|Ptz 垂直视场角\(°\)|
||8|reserve\[4\]|uint16\_t|备用，默认为0|
||4|azimuth|float|ptz方位指向，单位°|
||4|elevation|float|ptz俯仰指向，单位°|
||4|omega\_az|float|ptz方位转动角速度，单位°/s|
||4|omega\_el|float|ptz俯仰转动角速度，单位°/s|
||4|zoom|float|ptz镜头倍率|
||1|AI\_status|uint8\_t|AI系统状态<br>0：正常工作<br>1：待机<br>2：探测状态|
||1|AI\_Type|Uint8\_t|0：雷达<br>1：tracer|
||4|AI\_ObjId|int32\_t|雷达目标ID|
||25|AI\_sn|char|无人机序列号|
||4|AI\_workstatus|Uint32\_t|AI算法跟踪状态<br>0接收到C2下发跟踪请求<br>1 objId匹配成功<br>2 objId匹配失败<br>3请求ptz视场搜索<br>4 PTZ工作模式空闲<br>5 PTZ工作模式搜索<br>6 PTZ工作模式跟踪|
||以下为目标数据，检测到多少个目标则有多少组目标数据||||
||4|id|uint32\_t|PTZ跟踪目标ID编号|
||1|classification|uint8\_t|目标类别<br>0x00：未识别<br>0x01：无人机<br>0x02：单兵<br>0x03：车辆<br>0x04：鸟类<br>0x05：直升机<br>其他无效|
||2|rectX|uint16\_t|目标框在图像上的起始X位置|
||2|rectY|uint16\_t|目标框在图像上的起始Y位置|
||2|rectW|Uint16\_t|目标框在图像上的width|
||2|rectH<br>|Uint16\_t|目标框在图像上的height|
||2|rectXV|int16\_t|目标框在图像上所呈现的水平运行像素速度，方向左为负右为正|
||2|rectYV|int16\_t|目标框在图像上所呈现的垂直运行像素速度，方向上为负下为正|
||4|classfyProb|float|目标类别概率|
||1|type|Uint8\_t|目前针对classification为1（无人机），区分无人机类型<br>0x00：未识别<br>0x01：精灵4<br>0x02：yu3<br>0x03：yu2<br>…<br>后续根据classification扩展|
||4|typeProb|float|目标类型概率，关联type|
||1|loadLever|Uint8\_t|挂载等级：<br>0x00：未识别<br>0x01：多<br>0x02：少<br>0x03：无|
||1|dangerLever|Uint8\_t|危险等级：<br>0x00：未识别<br>0x01：非常危险<br>0x02：危险较轻<br>0x03：无危险|
||4|azimuth|float|目标方位角（°）|
||4|elevation|float|目标俯仰角（°）|
||4|range|float|目标距离\(m\)|
||1|motionType|Uint8\_t|运动方向：<br>0: 静止;  1: 左;   2: 右;<br>3: 上;    4: 下;   5：左上;<br>6：右上;  7: 左下; 8: 右下;|
||1|bTracked|Uint8\_t|是否为跟踪目标<br>1为是<br>0为否|
||8|reserve\[4\]|Uint16\_t|备用，默认为0|
||||||
|参数长度|53\+35\+50\*n||||
|应答|无||||



### **电子侦察（0xE3）**

|消息ID|0xE3||||
|---|---|---|---|---|
|消息描述|上||||
|方向|SFL200C2||||
|发送频率|根据设置和帧处理周期触发||||
|<br>参数payload<br>|字节|Name|Type|Description|
||8|timeStamp|uint64\_t|时间戳（ms）|
||1|objNum|uint8\_t|目标数|
||以下为目标数据，检测到多少个目标则有多少组目标数据||||
||1|Source<br>|char|侦测源<br>0\.融合类型<br>1\.反制枪<br>2\.tracer DroneID<br>3\.tracer RemoteID<br>n\.保留|
||1|productType|uint8\_t|无人机类型|
||25|droneName|char|字符串 无人机名称 |
||32|serialNum|char|字符串 无人机SN|
||4|droneLongitude|int32\_t|无人机经度\(/1e7\)|
||4|droneLatitude|int32\_t|无人机纬度\(/1e7\)|
||2|droneHeight|int16\_t|无人机相对地面高度\(0\.1m\)|
||2|droneYawAngle|int16\_t|无人机角度\(0\.01deg\)|
||2|droneSpeed<br>|int16\_t|无人机绝对速度\(0\.01m/s\)|
||2|droneVerticalSpeed|int16\_t|无人机垂直速度\(0\.01m/s\)|
||1|Speedderection|uint8\_t|0：无人机水平向前  lite<br>1：无人机水平向后  lite<br>2：无人机水平向左  lite<br>3：无人机水平向右  lite<br>4：无人机垂直<br>无效值为0xFF|
||4|droneSailLongitude|int32\_t|无人机航点经度\(/1e7\)|
||4|droneSailLatitude|int32\_t|无人机航点经度\(/1e7\)|
||4|pilotLongitude|int32\_t|飞手经度\(/1e7\)|
||4|pilotLatitude|int32\_t|飞手纬度\(/1e7\)|
||4|droneHorizon|int32\_t|目标水平角\(0\.01°\)|
||4|dronePitch|int32\_t|目标俯仰角\(0\.01°\) |
||4|uFreq|uint32\_t|无人机信号频率\(MHz\)|
||2|uDistance|uint16\_t|无人机与本设备的距离\(m\)|
||2|uDangerLevels|uint16\_t|危险等级|
||2|uZC|uint16\_t|ZC序列值|
||1|uDirStatus|uint8\_t|定向状态<br>0：非定向状态<br>1：定向中<br>2：定向成功<br>其它：保留|
||2|uNumber|uint16\_t|编号 |
||6|Wifi\_mac|uint8\_t|WIFI mac, 仅对于wifi机型有效|
||8|gps\_clocks|uint64\_t|无人机GPS时间戳：1970年1月1日至今毫秒数 \(ms\)<br>当无人机类型为DroneID时有效|
||4|TimestampRid|uint32\_t|以当前小时为起始时刻，已经过去的1/10秒数<br>当无人机类型为RemoteID时有效|
||1<br>|ID\_type|uint8\_t<br>|无人机的类型：<br>0：保留<br>1: DroneID<br>2: RemoteID<br>3: DroneID \& RemoteID<br>4: 频谱类无人机|
||4|flag\_time|uint32\_t|图传周期结束的点数|
||2|drone\_altitude<br>|int16\_t|无人机海拔高度\(0\.1m\)|
||2|drone\_elevation|int16\_t|无人机相对于设备的高度\(0\.1m\)|
||1|jammingAccurateType<br>|uint8\_t|精准打击类型值<br>0：无效值，<br>1：DJI Ocusync2<br>2: DJI Ocusync3<br>3: DJI Ocusync4<br>4: DJI\_Phantom4\_RTK频谱无人机<br>5: DJI 带加密协议，并且侦测到它的图传为DJI Ocusync4<br>6：DJI 带加密协议，但是没有侦测到它对应的图传信息<br>7：其它DJI带协议的无人机（除DJI\_Phantom4\_RTK带协议外）<br>8：DJI\_Phantom4\_RTK带协议无人机<br>9：Autel无人机<br>0xFF: 无法支持精准打击<br>其它：保留|
||2|singal\_power|int16\_t|无人机信号的功率\(0\.1dBm\)|
||2|noise\_power<br>|int16\_t|噪声信号的功率\(0\.1dBm\)|
||2|SNR|int16\_t|当前的信噪比（dB）|
||4|detection\_cnt|uint32\_t<br>|该无人机的侦测次数|
||1|singal\_type|uint8\_t|该无人机的信号类型：<br>0：无效值<br>1：数字图传<br>2：模拟图传<br>3：WIFI<br>4：飞控下行信号<br>5：飞控上行信号<br>6：RemoteID<br>7：DroneID<br>8: DroneID\&RemoteID|
||2|drone\_flag<br>|int16\_t<br>|无人机属性状态：按Bit位读取信息<br>B0：白名单标志（协议目标有效）<br>B1：预测数据标志（协议目标有效）<br>B2：瞄准标志（协议目标有效）<br>B3：精确打击有效标志  <br>B4：跟踪打击有效标志（协议目标有效）<br>B5：无附件打击标志<br>B6：数据融合标志（协议目标有效）<br>B7：可定向标志（频谱目标有效）<br>B8：可打击标志（频谱目标有效）<br>B9：正被打击标志<br>B10：是否支持FPV视频流截获|
||7|reserve|uint8\_t|保留值|
||||||
|参数长度|9\+161\*n||||
|应答|无||||



# 子设备报文消息内容（0xF0）

子设备报文均采用0xF0消息ID做系统封装

## 导航诱骗

固定式导航诱骗产品，在协议中的子设备类型代码为：0x31\.

### 侦测消息

无。

### 工作状态消息

#### 控制（暂不实现）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|本设备上位机||||
|发送频率|1Hz||||
|<br>参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-固定诱骗（0x31）|
||1|SubMsgID|Uint8|子设备消息ID（0xA0）|
||25|SN|Char|子设备SN|
||1|cmd|Uint8|1：设置<br>2：查询（单次）|
||2|Period|Uint16|信息上传周期（ms）<br>典型取值：<br>0：代表关闭上传<br>100、1000、2000|
||||||
|参数长度|3||||
|应答|有||||
||||||



#### 上传（需要实现）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|给上位机上传运行状态信息心跳包||||
|方向|本设备上位机||||
|发送频率|1Hz||||
|参数payload<br>|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-固定诱骗（0x31）|
||1|SubMsgID|Uint8|子设备消息ID（0xA0）|
||25|SN|Char|子设备SN|
||2|Cnt|Uint16|循环计数|
||4|sysStatus  |Uint32|自检状态（按位定义）<br>B9\-15：预留<br>B16\-31：系统异常码，预留|
||4|workStatus|Uint32|系统工作状态（按位定义）<br>B0：位置就绪标志<br>B1：星历就绪标志<br>B2：时间就绪标志<br>B3：混合星历使能标志<br>B4：L1通道输出标志<br>B5：B1通道输出标志<br>B6：G1通道输出标志<br>B7：E1通道输出标志<br>B8：噪声调制使能标志<br>B9：B15：预留<br><br>B16\-19：诱骗输出状态（诱骗工作模式）<br>0: 无输出<br>1：区域拒止输出<br>2：主动防御输出<br>3：定向驱离输出<br>4：一键炸机<br>5：定点诱骗<br>B20\-31：预留|
||4|Temperature1|Float|系统温度（℃）|
||4|Volt|Float|系统电压|
||4|Current|Float|系统电流|
||8|Longitude|double|系统GPS定位经度（°）|
||8|Latitude|double|系统GPS定位纬度（°）|
||4|Altitude|Float|系统GPS定位海拔高度（m）|
||4|Yaw|Float|系统GPS定姿方位（°）\-置空|
||4|Pitch|Float|系统GPS定姿俯仰（°）\-置空|
||4|Roll|Float|系统GPS定姿滚转（°）\-置空|
||8|Longitude1|double|禁飞点经度|
||8|Latitude1|double|禁飞点纬度|
||4|Direction|Int32|定向驱离方向<br>1：东<br>2：南<br>3：西<br>4：北<br>5：上<br>6：下|
||4|Radius |int32|主动防御半径（m）|
||8|Longitude2|double|主动防御坐标点经度|
||8|Latitude2|double|主动防御坐标点纬度|
||4|fixed\_id|Uint32|定点诱骗目标ID|
||8|fixed\_Longitude|double|定点诱骗坐标点经度（°）|
||8|fixed\_Latitude|double|定点诱骗坐标点经度（°）|
||2|fixed\_precision|Uint16|定点诱骗精度|
||1|fixed\_and\_hit|Uint8|定点诱骗是否需要同时开启打击<br>0：不需要开启打击<br>1：需要开启打击<br>|
||1|fixed\_end\_strategy<br>|Uint8|到达诱骗点位后策略<br>0：悬停<br>1：迫降|
||10|Reserved|\-|保留|
|参数长度|||||
|应答|无||||
|备注|||||



### 组成信息管理消息

#### 控制（暂不实现）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-固定诱骗（0x31）|
||1|SubMsgID|Uint8|子设备消息ID（0xA0）|
||25|SN|Char|子设备SN|
||1|cmd|Uint8|1：设置参数（暂不实现）<br>2：查询参数|
||25|系统SN号|Uint8|设备SN号<br>十六进制的SN号<br>注：查询时字段无效|
||25|系统软件版本号|Uint8|十六进制的软件版本号<br>注：查询时字段无效|
||2|子设备组合类型|Uint16|填无效值<br>注：查询时字段无效|
||2|子设备个数|Uint16|填0<br>注：查询时字段无效|
||2|子设备ID|Uint16|设备ID|
||25|子设备SN号|Uint8|十六进制的SN号|
||25|子设备软件版本号|Uint8|十六进制的软件版本号|
|参数长度|||||
|应答|有||||

#### 应答（暂不实现）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-固定诱骗（0x31）|
||1|SubMsgID|Uint8|子设备消息ID（0xA0）|
||25|SN|Char|子设备SN|
||1|status|Uint8|0：响应失败<br>1：设置成功<br>2：查询成功|
||25|系统SN号|Uint8|设备SN号<br>十六进制的SN号|
||25|系统软件版本号|Uint8|十六进制的软件版本号|
||2|子设备组合类型|Uint16|返回无效值|
||2|子设备个数|Uint16|返回0|
||2|子设备ID|Uint16|设备ID|
||25|子设备SN号|Uint8|十六进制的SN号|
||25|子设备软件版本号|Uint8|十六进制的软件版本号|
|参数长度|||||
||||||



### 工作参数配置消息

#### 控制（需要实现）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|用户触发||||
|参数payload<br>|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-固定诱骗（0x31）|
||1|SubMsgID|Uint8|子设备消息ID（0xD0）|
||25|SN|Char|子设备SN|
||1|cmd<br>|Uint8|1：设置参数<br>2：查询参数|
||4|sys\_mode<br>|Uint32|B0\-7：诱骗工作模式<br>1：区域拒止<br>2：主动防御<br>3：定向驱离<br>4：一键炸机<br>5：定点诱骗<br>B8：混合星历使能<br>B9\-B31：预留|
||20<br>|time|Char|字符串<br>年月日时分秒\.毫秒<br>（例20240515011746\.901）|
||8|Longitude|double|系统GPS定位经度（°）|
||8|Latitude|double|系统GPS定位纬度（°）|
||4|Altitude|Float|系统GPS定位海拔高度（m）|
||4|Yaw|Float|系统GPS定姿方位（°）|
||4|Pitch|Float|系统GPS定姿俯仰（°）|
||4|Roll|Float|系统GPS定姿滚转（°）|
||1|StartStop<br>|uint8|0：停止发射<br>1：开启发射|
||4|Radius |int32|防御半径（m）|
||8|Longitude2|double|主动防御坐标点经度（°）|
||8|Latitude2|double|主动防御坐标点纬度（°）|
||8|Longitude1|double|禁飞点经度（°）|
||8|Latitude1|double|禁飞点纬度（°）|
||4<br>|Direction<br>|Int32|定向驱离方向<br>1：东<br>2：南<br>3：西<br>4：北<br>5：上<br>6：下|
||4|fixed\_id|Uint32|定点诱骗目标ID|
||8|fixed\_longitude|double|定点诱骗坐标点经度（°）|
||8|fixed\_latitude|double|定点诱骗坐标点纬度（°）|
||2|fixed\_precision|Uint16|定点诱骗精度，单位m|
||1<br>|fixed\_add\_hit<br>|Uint8|定点诱骗是否需要同时开启打击<br>0：不需要开启打击<br>1：需要开启打击<br>|
||1|fixed\_end\_strategy<br>|Uint8|到达诱骗点位后策略<br>0：悬停<br>1：迫降|
|参数长度|||||
|应答|有||||



#### 应答（需要实现）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-固定诱骗（0x31）|
||1|SubMsgID|Uint8|子设备消息ID（0xD0）|
||25|SN|Char|子设备SN|
||1|status|Uint8|0：响应失败<br>1：设置成功<br>2：查询成功|
||4|sys\_mode|Uint32|B0\-7：诱骗工作模式<br>1：区域拒止<br>2：主动防御<br>3：定向驱离<br>4：一键炸机<br>5：定点诱骗<br>B8：混合星历使能<br>B9\-B31：预留|
||20|time|Char|字符串<br>年月日时分秒\.毫秒<br>（例20240515011746\.901）|
||8|Longitude|double|系统GPS定位经度（°）|
||8|Latitude|double|系统GPS定位纬度（°）|
||4|Altitude|Float|系统GPS定位海拔高度（m）|
||4|Yaw|Float|系统GPS定姿方位（°）|
||4|Pitch|Float|系统GPS定姿俯仰（°）|
||4|Roll|Float|系统GPS定姿滚转（°）|
||1|StartStop|uint8|0：停止打击<br>1：开启打击|
||4|Radius |int32|主动防御半径（m）|
||8|Longitude2|double|主动防御坐标点经度（°）|
||8|Latitude2|double|主动防御坐标点纬度（°）|
||8|Longitude1|double|禁飞点经度（°）|
||8|Latitude1|double|禁飞点纬度（°）|
||4|Direction|Int32|定向驱离方向<br>1：东<br>2：南<br>3：西<br>4：北<br>5：上<br>6：下|
||4|fixed\_id|Uint32|定点诱骗目标ID|
||8|fixed\_longitude|double|定点诱骗坐标点经度（°）|
||8|fixed\_latitude|double|定点诱骗坐标点纬度（°）|
||2|fixed\_precision|Uint16|定点诱骗精度|
||1|fixed\_add\_hit|Uint8|定点诱骗是否需要同时开启打击<br>0：不需要开启打击<br>1：需要开启打击<br>|
||1<br>|fixed\_end\_strategy|Uint8|到达诱骗点位后策略<br>0：悬停<br>1：迫降|
||||||
|参数长度|||||

### 工作任务管理消息

无



## 察打一体设备

### 侦测消息（1\.11号不要求实现）

无。

#### 原始频谱侦测消息（先不开发，结合几个需求，我先修改）

##### 控制

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|本设备上位机||||
|发送频率|1Hz||||
|<br>参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xB0）|
||25|SN|Char|子设备SN|
||1|cmd|Uint8|1：设置<br>2：查询（单次）|
||2|Period|Uint16|信息上传周期（ms）<br>典型取值：<br>0：代表关闭上传<br>100、1000、2000|
||4|Freq|Float|频率（MHz）|
||||||
|参数长度|||||
|应答|有||||
||||||



##### 上传

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|本设备上位机||||
|发送频率|1Hz||||
|<br>参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xB0）|
||25|SN|Char|子设备SN|
||2|Cnt|Uint16|循环计数|
||2|Period|Uint16|信息上传周期（ms）<br>典型取值：<br>0：代表关闭上传<br>100、1000、2000|
||4|freq|Uint32|频率（MHz\)|
||4|frameNum|Uint32|帧数|
||4|frameIdx|Uint32|帧序号|
||4|frameSize|Uint32|帧大小N<br>N = 128\*3002\*2|
||N|data|Uint8\[N\]|时频图数据<br>|
|参数长度|||||
|应答|有||||
||每帧数据长度为128\*3002\*2字节<br>每帧分多次发送。||||

### 工作状态消息（1\.11需实现）

#### 基本工作状态消息

##### 控制

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|本设备上位机||||
|发送频率|1Hz||||
|<br>参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xC0）|
||25|SN|Char|子设备SN|
||1|cmd|Uint8|1：设置<br>2：查询（单次）|
||2|Period|Uint16|信息上传周期（ms）<br>典型取值：<br>0：代表关闭上传<br>100、1000、2000|
||||||
|参数长度|3||||
|应答|有||||
||||||

##### 上传（需实现）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|10Hz||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xC0）|
||25|SN|Char|子设备SN|
||2|Cnt|Uint16|循环计数|
||4|sysStatus  |Uint32|自检状态（按位定义）<br>B0：频谱模组异常标志<br>B1：协议模组异常标志<br>B2：反制模组异常标志<br>B3：云台模组异常标志<br>B4：温度异常标志<br>B5：同步信号异常标志<br>B6：GPS定位异常标志<br>B7：GPS定姿异常标志<br>B8\-31：预留|
||4|workStatus|Uint32|系统工作状态（按位定义）<br>0：待机<br>1: 全向侦测（对应B0：频谱侦测执行标志）（置1）<br>2：定向侦测（200里不启用定向功能\-对应）<br>3：定向成功（200里不启用定向功能）<br>4：定向失败（200里不启用定向功能）<br>5：打击飞控图传（状态保留）<br>6：打击GNSS（状态保留）<br>7：打击飞控图传 \+ 打击GNSS（状态保留）<br>8：打击FPV（状态保留）<br>9：低电量不进行打击（状态弃用）<br>10：高温不进行打击（状态保留，新协议B4：sysStatus温度异常标志）  <br>11：上电开机中（移植新增）<br>12：关机（移植新增）<br>13: OTA（移植新增）<br>14: 云台自检（移植新增）<br>15\~19：保留<br>20：允许进入定向（状态弃用）<br>21：频率不在范围不允许进入定向（状态弃用）<br>22：机型不支持进入定向（状态弃用）<br>---<br>---<br>---<br>以下设计暂不启用<br>B0：频谱侦测执行标志<br>B1：协议侦测执行标志<br>B2：定向侦测执行标志<br>B3：打击执行标志（关注）<br>B4：数据融合标志<br>B5：信息网络解密有效标志<br>B6：集成工作模式（独占）<br>B7：预留<br>B8：上电开机中<br>B9：关机<br>B10: OTA<br>B11: 云台自检<br>B16\-B31：扩展状态信息<br>B16：功放1输出标志<br>B17：功放2输出标志<br>B18：功放3输出标志<br>B19：打击飞控图传标志<br>B20：打击FPV标志<br>B21：打击GNSS标志|
||4|Temperature1|Float|系统温度（℃）|
||4|Volt|Float|系统电压|
||4|Current|Float|系统电流|
||4|Power|Float|系统功率|
||8|Longitude|double|系统GPS定位经度（°）|
||8|Latitude|double|系统GPS定位纬度（°）|
||4|Altitude|Float|系统GPS定位海拔高度（m）|
||4|Yaw|Float|系统GPS定姿方位（°）（设备标定的角度）|
||4|Pitch|Float|系统GPS定姿俯仰（°）（设备标定的角度）|
||4|Roll|Float|系统GPS定姿滚转（°）（设备标定的角度）|
||4|FanSpeed|Float|风扇转速|
||4|GimAz|Float|云台偏航角指向（°） （实时转动的角度）<br>注：绝对系下|
||4|GimEl|Float|云台俯仰角指向（°）（实时转动的角度）<br>注：绝对系下|
||10|Reserved|\-|保留|
|参数长度|||||
|应答|无||||
|备注|||||

#### 高速工作状态消息（暂不实现，由基本工作状态消息闭环）

##### 控制

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|1Hz||||
|<br>参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xC1）|
||25|SN|Char|子设备SN|
||1|cmd|Uint8|1：设置<br>2：查询（单次）|
||2|Period|Uint16|信息上传周期（ms）<br>典型取值：<br>0：代表关闭上传<br>100、1000、2000|
||||||
|参数长度|||||
|应答|有||||
||||||

##### 上传

|消息ID|||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|10Hz||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xC1）|
||25|SN|Char|子设备SN|
||2|Cnt|Uint16|循环计数|
||4|GimAz|Float|云台偏航角指向（°）<br>注：绝对系下|
||4|GimEl|Float|云台俯仰角指向（°）<br>注：绝对系下|
|参数长度|||||
|应答|||||
|备注|||||

### 组成信息管理消息（暂不实现）

#### 控制

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xA0）|
||25|SN|Char|子设备SN|
||1|cmd|Uint8|1：设置参数（暂不实现）<br>2：查询参数|
||25|系统SN号|Uint8|设备SN号<br>十六进制的SN号<br>注：查询时字段无效|
||25|系统软件版本号|Uint8|十六进制的软件版本号<br>注：查询时字段无效|
||2|子设备组合类型|Uint16|填无效值<br>注：查询时字段无效|
||2|子设备个数|Uint16|填0<br>注：查询时字段无效|
||2|子设备ID|Uint16|设备ID|
||25|子设备SN号|Uint8|十六进制的SN号|
||25|子设备软件版本号|Uint8|十六进制的软件版本号|
|参数长度|||||
|应答|有||||



#### 应答

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xA0）|
||25|SN|Char|子设备SN|
||1|status|Uint8|0：响应失败<br>1：设置成功<br>2：查询成功|
||25|系统SN号|Uint8|设备SN号<br>十六进制的SN号|
||25|系统软件版本号|Uint8|十六进制的软件版本号|
||2|子设备组合类型|Uint16|返回无效值|
||2|子设备个数|Uint16|返回0|
||2|子设备ID|Uint16|设备ID|
||25|子设备SN号|Uint8|十六进制的SN号|
||25|子设备软件版本号|Uint8|十六进制的软件版本号|
|参数长度|||||
||||||

### 工作参数配置消息（0x10 需实现）

#### 控制

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0x10）|
||25|SN|Char|子设备SN|
||1|cmd|Uint8|1：设置参数<br>2：查询参数|
||4|sys\_mode<br>|Uint32|工作模式<br>B0：数据融合使能<br>B1：车载模式使能（预留）<br>B2：预留<br>B3：预留<br>B4：Normal打击模式（智能）<br>B5：FPV打击模式<br>B6：全频段打击模式<br>B7：自定义打击模式（预留）<br>B8：2\.4\\5\.8 ISM模式（预留）<br>B9：2\.4\\5\.2\\5\.8 ISM模式（预留）<br>B10：GNSS打击使能<br>B12\-B31：预留|
||20|time|Char|字符串<br>年月日时分秒\.毫秒<br>（例20240515011746\.901）|
||8|Longitude|double|系统GPS定位经度（°）|
||8|Latitude|double|系统GPS定位纬度（°）|
||4|Altitude|Float|系统GPS定位海拔高度（m）|
||4|Yaw|Float|系统GPS定姿方位（°）|
||4|Pitch|Float|系统GPS定姿俯仰（°）|
||4|Roll|Float|系统GPS定姿滚转（°）|
||1|StartStop|uint8|0：停止打击<br>1：开启打击|
||1|AimSolution<br>|uint8|精准打击\-策略（预留）<br>0：不采用（默认）<br>1：DJI策略<br>2：Autel策略<br>注：设备直接控制的时候默认填0，协议保留该字段|
||4|AimTime|Uint32|精准打击\-特征时间（预留）<br>注：设备直接控制的时候默认填0，协议保留该字段|
|参数长度|||||
|应答|有||||

#### 应答

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID~~（0xD0）~~ （0x10）|
||25|SN|Char|子设备SN|
||1|status|Uint8|0：响应失败<br>1：设置成功<br>2：查询成功|
||4<br>|sys\_mode|Uint32|工作模式<br>B0：数据融合使能<br>B1：车载模式使能<br>B2：预留<br>B3：预留<br>B4：Normal打击模式（智能）<br>B5：FPV打击模式<br>B6：全频段打击模式<br>B7：自定义打击模式（预留）<br>B8：2\.4\\5\.8 ISM模式<br>B9：2\.4\\5\.2\\5\.8 ISM模式<br>B10：GNSS打击使能<br><br>B12\-B31：预留|
||20|time|Char|字符串<br>年月日时分秒\.毫秒<br>（例20240515011746\.901）|
||8|Longitude|double|系统GPS定位经度（°）|
||8|Latitude|double|系统GPS定位纬度（°）|
||4|Altitude|Float|系统GPS定位海拔高度（m）|
||4|Yaw|Float|系统GPS定姿方位（°）|
||4|Pitch|Float|系统GPS定姿俯仰（°）|
||4|Roll|Float|系统GPS定姿滚转（°）|
||1|StartStop|uint8|0：停止打击<br>1：开启打击|
||1|AimSolution|uint8|精准打击\-策略<br>0：不采用<br>1：DJI策略<br>2：Autel策略|
||4|AimTime|Uint32|精准打击\-特征时间|
||||||
||||||
|参数长度|||||
|应答|有||||

### 工作任务分配

#### 云台指向任务\(0x11\) （未实现）

##### 控制 （设备控制不是参数设置，以后整改）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0x11）|
||25|SN|Char|子设备SN|
||1|cmd|Uint8|1：设置参数|
||4<br>|mode|Uint32|转动模式<br>1: 转动：表示按指定方向旋转<br>2:走位：表示按指定角度转动<br>3: 云台复位<br>其它值无效|
||4|AngleAz|Float|方位转动的目标角度（°）<br>有效值的范围为0\~360，其它值无效，不执行<br>（走位模式有效）|
||4|AngleEl|Float|俯仰转动的目标角度（°）<br>有效值的范围为\-30\~60，其它值无效，不执行<br>（走位模式有效）|
||4|SpeedAz|Float|方位转动速度（°/s）<br>正值为顺时针，负值为逆时针<br>当指定的最大转速大于设备的转速时，设备将以最大的转速进行转动|
||4|SpeedEl|Float|俯仰转动速度（°/s）<br>正值为朝上，负值为朝下<br>当指定的最大转速大于设备的转速时，设备将以最大的转速进行转动|
||4|NowAz|Float|当前转台方位值（°）<br>设置时无效|
||4|NowEl|Float|当前转台俯仰值（°）<br>设置时无效|
||1|StartStop|Uint8|启动/停止转动<br>0：停止转动<br>1：启动转动|
|参数长度|||||
|应答|有||||

##### 应答

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID （0x11）|
||25|SN|Char|子设备SN|
||1|status|Uint8|0：响应失败<br>1：设置成功<br>2：查询成功|
||4|mode|Uint32|转动模式<br>1:转动：表示按指定方向旋转<br>2:走位：表示按指定角度转动<br>3:云台复位<br>其它值无效|
||4|AngleAz|Float|方位转动的目标角度（°）<br>有效值的范围为0\~360，其它值无效，不执行<br>（走位模式有效）|
||4|AngleEl|Float|俯仰转动的目标角度（°）<br>有效值的范围为\-30\~60，其它值无效，不执行<br>（走位模式有效）|
||4|SpeedAz|Float|方位转动速度（°/s）<br>正值为顺时针，负值为逆时针<br>当指定的最大转速大于设备的转速时，设备将以最大的转速进行转动|
||4|SpeedEl|Float|俯仰转动速度（°/s）<br>正值为朝上，负值为朝下<br>当指定的最大转速大于设备的转速时，设备将以最大的转速进行转动|
||4|NowAz|Float|当前转台方位值（°）<br>设置时无效|
||4|NowEl|Float|当前转台俯仰值（°）<br>设置时无效|
||1|StartStop|Uint8|启动/停止转动<br>0：停止转动<br>1：启动转动|
|参数长度|||||
|应答|||||

#### 环境底噪任务

##### 设置环境底噪采集任务（0xDB）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|控制环境底噪采集、停止任务||||
|方向|C2\-\-\>SFL00||||
|发送频率|用户触发||||
|参数payload<br>|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xDB）|
||25|SN|Char|子设备SN|
||1|cmd<br>|Uint8<br>|1：设置参数<br>2：查询参数|
||1<br>|flag<br>|uint8\_t|1: 开始采集<br>2: 停止采集|
||4|freqNum|uint32\_t|频点数量N; N为0时全频段上报。|
||4\*N|freqList|uint32\_t\[N\]|频点列表|
||4|reserve|uint32\_t|保留字段|
|参数长度|||||
|应答|有||||
|应答消息|||||
|参数payload<br>|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xDB）|
||25|SN|Char|子设备SN|
||1|status|uint8\_t|0：失败<br>1：成功|

##### 环境底噪信息上报（0xDC）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|环境底噪信息上报||||
|方向|SFL200\-\-\>C2||||
|发送频率|同扫频周期：约（120ms\*34）/轮，34为扫描频点个数||||
|参数payload<br>|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xDC）|
||25|SN|Char|子设备SN|
||4|freq|uint32\_t|中心频点，单位kHz|
||4|freqStart|uint32\_t|起始频率，单位kHz|
||4|freqEnd|uint32\_t|结束频率，单位kHz|
||4|freqStep|uint32\_t|步进频率，单位kHz|
||4|arrSize|uint32\_t|数组大小|
||Noise   power info||||
||2\*arrSize|meanVal|int16\_t\[arrSize\]|对应频谱平均功率，单位0\.1dbm|
||2\*arrSize|maxVal|int16\_t\[arrSize\]|对应频谱最大功率，单位0\.1dbm|
|参数长度|2\+1\+25\+4\+4\+4\+4\+4\+2\*2\*arrSize   =48\+4\*arrSize||||
|应答|无||||
|备注|受命令0xDB控制||||

#### 侦测性能评估任务

##### 获取侦测频点列表（0xD0）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|获取侦测频点列表||||
|方向|C2\-\-\-\>SFL200||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD0）|
||25|SN|Char|子设备SN|
||1|cmd|Uint8|1：设置参数<br>**2：查询参数**|
||1|status|uint8\_t|0：获取；<br>其他：保留|
|参数长度|||||
|应答|有||||
|应答消息|||||
|参数payload<br>|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD0）|
||25|SN|Char|子设备SN|
||2|N|uint16\_t|频点个数|
||4\*N|FreqList\[N\]|uint32\_t\[N\]|频点列表，频点单位为MHz|

##### 设置时频图采集\(0xD1\)

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|设置时频图采集||||
|方向|C2\-\-\-\>SFL200||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD1）|
||25|SN|Char|子设备SN|
||1|cmd<br>|Uint8|1：设置参数<br>**2：查询参数**|
||1|mode|uint8\_t|1：开始采集，采集完成自动上报；<br>0：停止采集。|
||4|reserve|uint32\_t|保留字段|
|参数长度|||||
|应答|有||||
|应答消息|||||
|参数payload<br>|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD1）|
||25|SN|Char|子设备SN|
||1|status|uint8\_t|0：失败，采集中收到命令返回失败。<br>1：成功|

##### 上报时频图采集状态\(0xD2\)

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|时频图采集状态上报||||
|方向|SFL200\-\-\-\>C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD2）|
||25|SN|Char|子设备SN|
||1|status|uint8\_t|采集状态：<br>1：采集；<br>2：压缩；<br>3：开始上传；<br>4：上传中；<br>5：上传完成；<br>0xFF：出现错误。|
||4|param1<br>|uint32\_t|参数，不同status含义不同：<br>status=1时：保留；<br>status=2时：保留；<br>status=3时：文件大小；<br>status=4时：最大分包数；<br>status=5时：保留；<br>status=0xFF时：错误原因：<br>err 1：采集出错；<br>err 2：压缩失败；<br>err 3：传输失败；<br>（以下字段仅在status为4时有效）|
||4|packIndex|Uint32\_t|分包序号|
||4|dataLen|Uint32\_t|本次发送的数据长度|
||N|data|uint8\_t|数据内容；N∈\[0,10240\]|
|参数长度|||||
|应答|无||||
|备注|1. 本命令体现了对时频图数据的采集到发送到上位机的整个过程<br>2. 数据压缩格式为gz<br>3. 受命令0xD1命令控制||||

##### 设置实时时频图采集参数（0xD3）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|设置实时时频图采集参数||||
|方向|C2\-\-\-\>SFL200||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD3）|
||25|SN|Char|子设备SN|
||1|cmd|Uint8|1：设置参数<br>**2：查询参数**|
||1|mode|uint8\_t|0：保留<br>1：指定频点上报；<br>2：固定频点上报瀑布图数据；|
||4|freq|uint32\_t|mode为1或2时指定的频点； <br>频点不在支持范围内返回错误并不做处理。<br>为0时表示“停止采样”|
||4|reserve|uint32\_t|保留字段|
|参数长度|||||
|应答|有||||
|应答消息|||||
|参数payload<br>|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD3）|
||25|SN|Char|子设备SN|
||1|status|uint8\_t|0：失败<br>1：成功|

##### 上报时频瀑布图数据\(0xD4\)

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|时频瀑布图数据上报||||
|方向|SFL200\-\-\-\>C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD4）|
||25|SN|Char|子设备SN|
||4|freq|uint32\_t|频率，MHz|
||4|frameNum|uint32\_t|帧数|
||4|frameIdx|uint32\_t|帧序号|
||4|frameSize|uint32\_t|帧大小N|
||1\*N|data|uint8\_t\[N\]|时频瀑布图数据|
|参数长度|||||
|应答|无||||
|备注|1\.为实时时频图的抽样数据，10抽1<br>2\.数据分包发送，合并起来为数据内容，数据总大小为128\*300\*2字节<br>3\.受命令0xD3控制||||

##### 上报时频图数据（0xD5）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|时频图数据上报||||
|方向|SFL200\-\-\-\>C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD5）|
||25|SN|Char|子设备SN|
||4|freq|uint32\_t|频率，MHz|
||4|frameNum|uint32\_t|帧数|
||4|frameIdx|uint32\_t|帧序号|
||4|frameSize|uint32\_t|帧大小N|
||N|data|uint8\_t\[N\]|时频图数据|
|参数长度|||||
|应答|无||||
|备注|1\.每帧数据长度为128\*3002\*2字节<br>2\.每帧分多次发送。<br>3\.受命令0xD3控制||||

##### 上报定向实时时频图数据（0xD6）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|定向实时时频图数据上报||||
|方向|SFL200\-\-\-\>C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD6）|
||25|SN|Char|子设备SN|
||4|freq|uint32\_t|频率，MHz|
||4|trackBwS|uint32\_t|跟踪频率起始索引|
||4|trackBwE|uint32\_t|跟踪频率终止索引|
||4|frameNum|uint32\_t|帧数|
||4|frameIdx|uint32\_t|帧序号|
||4|frameSize|uint32\_t|帧大小N|
||1\*N|data|uint8\_t\[N\]|时频瀑布图数据|
|参数长度|||||
|应答|无||||
|备注|1\.为定向实时时频图的抽样数据，10抽1<br>2\.数据分包发送，合并起来为数据内容，数据总大小为128\*300\*2字节||||

##### 设置侦测性能评估（0xD7）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|侦测性能评估设置||||
|方向|C2\-\-\-\>SFL200||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD7）|
||25|SN|Char|子设备SN|
||1|cmd|Uint8|1：设置参数<br>2：查询参数|
||1|ProtocolType|uint8\_t|1. SRRC<br>2. CE<br>3. FC|
||1|Start|uint8\_t|1：开始上送<br>2：停止上送|
||16|reserve|uint8\_t|保留字段|
||||||
|参数长度|||||
|应答|有||||
|应答消息|||||
|参数payload<br>|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD7）|
||25|SN|Char|子设备SN|
||1|status|uint8\_t|0：失败<br>1：成功|

##### 上报侦测性能评估数据（0xD8）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|侦测性能评估数据上报||||
|方向|SFL200\-\-\-\>C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD8）|
||25|SN|Char|子设备SN|
||1|ItemNum|uint8\_t|侦测个数|
||4|Freq|uint32\_t|侦测频率，单位MHz|
||1|DetectionType<br>|uint8\_t|侦测类型，<br>0：频谱<br>1：DroneID<br>2: RemoteID<br>其它：保留|
||4|MinDisatance|float|距离最小值，单位Km|
||4|MaxDisatance|float|距离最大值，单位Km|
|参数长度|||||
|应答|无||||
|备注|每侦测完一轮后，上报一次数据 <br>1. 本命令受命令0xD7控制<br>2. 只有当设备处于侦测状态时才会上送||||

##### 设置性能评估参考值（0xD9）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|侦测性能评估上报开关||||
|方向|C2\-\-\-\>SFL200||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD9）|
||25|SN|Char|子设备SN|
||1|cmd|Uint8|1：设置参数<br>2：查询参数|
||1|start|uint8\_t|1：open； 2：close|
||4|freq|float32|频点值|
||4|reserve|Uint32\_t|保留字段|
|参数长度|||||
|应答|有||||
|应答消息|||||
|参数payload<br>|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xD9）|
||25|SN|Char|子设备SN|
||1|status|uint8\_t|0：失败<br>1：成功|

##### 上报性能评估参考值（0xDA）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|侦测性能评估数据上报||||
|方向|SFL200\-\-\-\>C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|SubType|Uint16|子设备类型\-SFL100|
||1|SubMsgID|Uint8|子设备消息ID（0xDA）|
||25|SN|Char|子设备SN|
||1|ItemNums|uint8\_t|侦测个数|
||4|freq|float32|侦测频率（MHZ）|
||1|DetectionType|uint8\_t|侦测设备类型：<br>0：频谱<br>1：droneId<br>2：RemoteID|
||4|MinDistance|float32|距离最小值，单位Km|
||4|MaxDistance|float32|距离最大值，单位Km|
||4|RefMinDistance|float32|参考距离最小值，单位Km|
||4|RefMaxDistance|float32|参考距离最大值，单位Km|
|参数长度|||||
|应答|无||||



## 激光设备控制（DEC200/DEC100/DEC150）

参照AGX雷视协议：[雷视与C2上位机通信协议](https://vxr5wm8r80r.feishu.cn/wiki/LnzwwnKafi5TDlknvTAcVvT7ngf)

### 上报转台和相机状态数据 （0xEC）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|Sentry \-\> C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|subType<br>|uint16<br>|参照附录A：子设备类型 \(激光设备\)<br>17：HE\-F100 激光设备 （对应C2内部型号DEC200）<br>20：HE\-P10 激光设备（对应C2内部型号DEC100）<br>21：HE\-P21 激光设备（对应C2内部型号DEC150）|
||1|subMsgId|uint8\_t|子设备消息ID <br>0xEC：上报转台相机状态数据|
||25|sn|char\[25\]|子设备SN|
||8|timestamp|uint64\_t|时间戳，单位ms|
||4|longitude|float|ptz经度，单位°|
||4|latitude|float|ptz纬度，单位°|
||4|height|float|ptz海拔高，单位m|
||4|azimuth|float|方位指向，单位°|
||4|elevation|float|俯仰指向，单位°|
||4|omega\_az|float|方位转动角速度，单位°/s|
||4|omega\_el|float|俯仰转动角速度，单位°/s|
||4|zoom|float|镜头变焦值 zoom|
||4|visible1\_h\_fov|float|可见光相机1 垂直视场角，无效值0|
||4|visible1\_v\_fov|float|可见光相机1 水平视场角，无效值0|
||4|ir1\_h\_fov|float|红外相机1 垂直视场角，无效值0|
||4|ir1\_v\_fov|float|红外相机1 水平视场角，无效值0|
||4|visible2\_h\_fov|float|可见光变焦相机2 垂直视场角，无效值0|
||4|visible2\_v\_fov|float|可见光变焦相机2 水平视场角，无效值0|
||2|ir1\_focus|uint16\_t|红外相机1 聚焦值|
||2|visible1\_focus|uint16\_t|可见光变焦相机1 聚焦值|
||2|visible2\_focus|uint16\_t|可见光变焦相机2 聚焦值|
||10|reserve|uint8\_t\[10\]|预留|
|参数长度|||||
|应答|无||||

### 获取视频流信息 （0x86）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|请求||||
|方向|C2 \-\> Sentry  ||||
|发送频率|用户触发||||
|参数payload<br>|字节|Name|Type|Description|
||2|subType<br>|uint16<br>|参照附录A：子设备类型 \(激光设备\)<br>17：HE\-F100 激光设备 （对应C2内部型号DEC200）<br>20：HE\-P10 激光设备（对应C2内部型号DEC100）<br>21：HE\-P21 激光设备（对应C2内部型号DEC150）|
||1|subMsgId<br>|uint8\_t<br>|子设备消息ID<br>0x86: 获取PTZ/激光设备 视频流信息|
||25|sn|char\[25\]|子设备SN|
|参数长度|||||
|应答|有||||



|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|Sentry  \-\> C2||||
|发送频率|用户触发||||
|参数payload<br>|字节|Name|Type|Description|
||2|subType<br>|uint16<br>|参照附录A：子设备类型 \(激光设备\)<br>17：HE\-F100 激光设备 （对应C2内部型号DEC200）<br>20：HE\-P10 激光设备（对应C2内部型号DEC100）<br>21：HE\-P21 激光设备（对应C2内部型号DEC150）|
||1|subMsgId<br>|uint8\_t<br>|子设备消息ID<br>0x86: 获取视频流信息|
||25|sn|char\[25\]|子设备SN|
||4|result|uint32\_t<br>|响应结果<br>0表示成功<br>其他表示失败|
||4|ip|uint8\_t\[\]|ip地址（16进制）|
||4|Port|uint32\_t|通信端口号|
||8|reserve|uint8\_t\[\]|预留|
||1|streamNum|Uint8\_t|当前流数量|
||array\[\] 数组||||
||1|cameraId|Uint8\_t|摄像头ID|
||128|url|char\[128\]|视频流地址|
||1|type|uint8\_t|类型 （和摄像头ID一致）<br>参照附录A：相机编号|
||2|width|uint16\_t|视频分辨率宽，无效值0|
||2|height|uint16\_t|视频分辨率高，无效值0|
||4|reserve|uint8\_t\[\]|预留|
|参数长度|||||
|应答|||||

### 转台控制（0x8a）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|请求||||
|方向|C2 \-\> Sentry  ||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|subType<br>|uint16<br>|参照附录A：子设备类型 \(激光设备\)<br>17：HE\-F100 激光设备 （对应C2内部型号DEC200）<br>20：HE\-P10 激光设备（对应C2内部型号DEC100）<br>21：HE\-P21 激光设备（对应C2内部型号DEC150）|
||1|subMsgId<br>|uint8\_t<br>|子设备消息ID<br>0x8a: 转台控制|
||25|sn|char\[25\]|子设备SN|
||1<br>|cmd<br>|uint8\_t<br>|1: 绝对位置控制（转到执行pitch和yaw角度）<br>2：按照配置的角速度持续运动控制（yaw为yaw角速度，pitch为pitch角速度，为0时表示该方向不动，此时direction表示运动方向）<br>3：只控俯仰，方位由ai控制<br>4：只控方位，俯仰由ai控制|
||4|yaw<br>|int32\_t<br>|cmd为1时，表示方位角<br>cmd为2/3/4时，表示方位角速度（度/s）|
||4|pitch<br>|int32\_t|cmd为1时，表示俯仰角<br>cmd为2/3/4时，表示俯仰角速度（度/s）|
||4|direction<br>|int32\_t<br>|当cmd是2时，direction有意义：<br>0：停止<br>1：向左<br>2：向右<br>3：向上<br>4：向下<br>5：左上<br>6：左下<br>7：右上<br>8：右下|
|参数长度|||||
|应答|||||

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|Sentry  \-\> C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|subType<br>|uint16<br>|参照附录A：子设备类型 \(激光设备\)<br>17：HE\-F100 激光设备 （对应C2内部型号DEC200）<br>20：HE\-P10 激光设备（对应C2内部型号DEC100）<br>21：HE\-P21 激光设备（对应C2内部型号DEC150）|
||1|subMsgId<br>|uint8\_t<br>|子设备消息ID<br>0x8a: 转台控制|
||25|sn|char\[25\]|子设备SN|
||4|result|uint32\_t<br>|响应结果<br>0表示成功<br>其他表示失败|
|参数长度|||||
|应答|||||

### 相机控制（0x8b）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|请求||||
|方向|C2 \-\> Sentry  ||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|subType<br>|uint16<br>|参照附录A：子设备类型 \(激光设备\)<br>17：HE\-F100 激光设备 （对应C2内部型号DEC200）<br>20：HE\-P10 激光设备（对应C2内部型号DEC100）<br>21：HE\-P21 激光设备（对应C2内部型号DEC150）|
||1|subMsgId<br>|uint8\_t<br>|子设备消息ID<br>0x8b: 相机控制|
||25|sn|char\[25\]|子设备SN|
||1|cmd<br>|uint8\_t<br>|命令类型：<br>0：变焦、聚焦停止<br><br>变焦/变倍：<br>1：变焦加，持续拉近，放大倍数（变焦/变倍）\(zoom in\)<br>2:  变焦减，持续推远，缩小倍数（变焦/变倍）\(zoom out\)<br>3：跳转到指定倍数（变焦/变倍）<br><br>聚焦：调整镜头对焦位置<br>4: 聚焦减/远，对焦远处，背景物体更清晰（focus out）<br>5: 聚焦加/近，对焦近处，前景物体变清晰（focus in）<br>6: 设置聚焦值<br><br>7：相机闭环零点控制 \(激光设备相机有\)<br>8：设置切换跟踪识别相机模式<br>9：切换一级跟踪识别相机<br><br>15: 相机校正|
||4|zoom<br>|int32\_t<br>|命令类型为 变焦/变倍有效：<br>cmd为1/2时，表示速度（0\-10）<br>cmd为3时，表示倍数（0\-100）|
||1|camera\_id|uint8\_t|单一枚举参照附录A：相机编号|
||2|focus<br>|uint16\_t|命令类型为 聚焦有效：<br>cmd为4/5时，表示速度（0\-10）<br>cmd为6时，表示数值（0\-100）|
||2<br>|zero\_x|uint16\_t|命令类型为：相机闭环零点控制时有效<br>调整闭环零点<br>取值范围：0\~图像大小<br>单位:Pixel<br>注：显示图像大小与实际图像大小不一致时，若使用鼠标双击进行闭环零点配置，需将显示图像像素点位置映射到原始图像像素位置，精跟踪、红外同理|
||2<br>|zero\_y<br>|uint16\_t||
||1|detect\_camera\_mode<br>|uint8\_t|命令类型为8时有效<br>设置切换跟踪相机模式：0自动，1手动|
||1|detect\_camera<br>|uint8\_t|命令类型为9时有效<br>切换一级跟踪识别相机，bit位表示 <br>bit0：可见光粗相机<br>bit1：红外相机|
||1<br>|ICR|uint8\_t|命令类型为14时有效<br>切换ICR模式：0\-自动，1\-开（手动），2\-关（手动）|
||1|correction|uint8\_t|命令类型为15时有效<br>相机校正: <br>0：背景矫正<br>1：快门矫正<br>2：虚焦矫正|
||6|reserve|uint8\_t\[\]|预留|
|参数长度|||||
|应答|||||



|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|Sentry  \-\> C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|subType<br>|uint16<br>|参照附录A：子设备类型 \(激光设备\)<br>17：HE\-F100 激光设备 （对应C2内部型号DEC200）<br>20：HE\-P10 激光设备（对应C2内部型号DEC100）<br>21：HE\-P21 激光设备（对应C2内部型号DEC150）|
||1|subMsgId<br>|uint8\_t<br>|子设备消息ID<br>0x8b: 相机控制|
||25|sn|char\[25\]|子设备SN|
||4|result|uint32\_t<br>|响应结果<br>0表示成功<br>其他表示失败|
|参数长度|||||
|应答|||||

### 用户下发手点像素目标值（0x95）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|C2 \-\> Sentry  ||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|subType<br>|uint16<br>|参照附录A：子设备类型 \(激光设备\)<br>17：HE\-F100 激光设备 （对应C2内部型号DEC200）<br>20：HE\-P10 激光设备（对应C2内部型号DEC100）<br>21：HE\-P21 激光设备（对应C2内部型号DEC150）|
||1|subMsgId<br>|uint8\_t<br>|子设备消息ID<br>0x95: 用户下发手点像素目标值|
||25|sn|char\[25\]|子设备SN|
||1|video\_source\_enum|uint8\_t|参照附录A：相机编号|
||2|pixel\_max\_u|uint16\_t|目标矩形框左上角坐标点<br>|
||2|pixel\_max\_v|uint16\_t||
||2|pixel\_min\_u|uint16\_t|目标矩形框右下角坐标点<br>|
||2|pixel\_min\_v|uint16\_t||
||2|pixel\_aim\_x|uint16\_t|目标相对于整个图像的坐标点 \(激光相机有\)<br>|
||2|pixel\_aim\_y|uint16\_t||
|参数长度|||||
|应答|||||

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|Sentry  \-\> C2||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|subType<br>|uint16<br>|参照附录A：子设备类型 \(激光设备\)<br>17：HE\-F100 激光设备 （对应C2内部型号DEC200）<br>20：HE\-P10 激光设备（对应C2内部型号DEC100）<br>21：HE\-P21 激光设备（对应C2内部型号DEC150）|
||1|subMsgId<br>|uint8\_t<br>|子设备消息ID<br>0x95: 用户下发手点像素目标值|
||25|sn|char\[25\]|子设备SN|
||4|result|uint32\_t<br>|响应结果<br>0表示成功<br>其他表示失败|
|参数长度|||||
|应答|||||



### 状态/设置/控制（0xC0\~0xC5）

|消息ID|0xF0||||
|---|---|---|---|---|
|消息描述|||||
|方向|C2 \-\> Sentry  ||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||2|subType<br>|uint16<br>|参照附录A：子设备类型 \(激光设备\)<br>17：HE\-F100 激光设备 （对应C2内部型号DEC200）<br>20：HE\-P10 激光设备（对应C2内部型号DEC100）<br>21：HE\-P21 激光设备（对应C2内部型号DEC150）|
||1|subMsgId<br>|uint8\_t<br>|子设备消息ID<br>0xC0: 激光状态信息上报<br>0xC1: 激光相机跟瞄结果上报<br>0xC2: 激光参数配置<br>0xC3: 激光参数获取<br>0xC4: 激光设备控制<br>0xC5: 设置/查询/上报禁打区|
||25|sn|char\[25\]|子设备SN|
||基于当前报文结构，将《[雷视与C2上位机通信协议](https://vxr5wm8r80r.feishu.cn/wiki/LnzwwnKafi5TDlknvTAcVvT7ngf)》0xC0\~0xC5 原协议的payload加进来。<br>注：请求和返回，采用原协议的payload，sn可能会多出来一个。||||
|参数长度|||||
|应答|||||



# 子设备原始协议转发（0xFD）

|消息ID|0xFD||||
|---|---|---|---|---|
|消息描述|**转发 子设备的原始协议帧包 到上位机C2**||||
|方向|子设备 \<\-\> SFL200 \<\-\> C2||||
|发送频率|子设备频率||||
|参数payload|字节|Name|Type|Description|
||25|sn|char|转发的设备SN|
||1<br>|Protocol<br>|uint8\_t<br>|设备类型对应的协议<br>参照雷视协议 消息转发（0xFD）：[雷视与C2上位机通信协议](https://vxr5wm8r80r.feishu.cn/wiki/LnzwwnKafi5TDlknvTAcVvT7ngf)|
||4|cmdLen|uint32\_t|转发的包长度|
||n|content|char|转发的包内容（原始完整帧内容结构）|
|参数长度|30\+n||||
||||||



# 附录A：通用数据编码

## **子设备类型枚举：**

**和AGX协议同步，附录A：**

[雷视与C2上位机通信协议](https://vxr5wm8r80r.feishu.cn/wiki/LnzwwnKafi5TDlknvTAcVvT7ngf)

## **相机编号：**

**和AGX协议同步，附录A：**

[雷视与C2上位机通信协议](https://vxr5wm8r80r.feishu.cn/wiki/LnzwwnKafi5TDlknvTAcVvT7ngf)

