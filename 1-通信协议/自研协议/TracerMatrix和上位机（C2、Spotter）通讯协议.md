# TracerMatrix和上位机（C2、Spotter）通讯协议

# 变更记录

|版本|说明|修订人|日期|备注|
|---|---|---|---|---|
|V1\.0\.0|根据PRD制定初版|官天河|2026\-1\-21||
|V1\.0\.1|新增“适配对接Spotter”内容|官天河|2026\-2\-6||
|V1\.0\.2|根据P0需求 UI设置刷新协议https://mastergo\.com/file/181676442076875?fileOpenFrom=project\&page\_id=14%3A0783|官天河|2026\-2\-11<br>||
|V1\.0\.3|1. request\_mode 添加主动上传模式和响应错误码<br>2. 合并 0x03A4 和 RF检测配置 0x03D1， 只保留 0x03D1<br>3. 消息名称改成和UI中名称一致，ID不变；|官天河<br>|2026\-2\-23<br>||
|V1\.0\.4|1. 存在多条的消息，添加删除类型，使用唯一ID进行删除，删除之后返回删除之后的全量结果；<br>2. 在Spotter不具备16位id响应之前，只使用8位的ID和C2以及Spotter通讯；|官天河<br>|2026\-2\-24<br>||
|V1\.0\.5|1. 新增DroneID加密流上传协议 0x0023<br>2. 新增解密数据回传协议 0x004A|官天河|2026\-2\-26||
|V1\.06|1. 数据导出0x0052和导出0x0051协议添加文件名字段|官天河|2026\-3\-2||
|V1\.07|1. 新增 0x0034 设置频谱检测参数；<br>2. 0x0041 新增协议记忆时间和频谱记忆时间<br>3. 刷新 NTP服务配置 0x0045<br>4. 新增 0x0014 请求授时协议|官天河|2026\-3\-9<br>||
|V1\.08|1. 频谱检测配置 0x0044 作废删除，由0x0034升级替换；|官天河|2026\-3\-18||
|V1\.09|1. 0x0012 命令添加时间来源、当前时间和上次授时时间<br>2. 0x0014 命令添加时区设置|官天河|2026\-3\-19||
|V1\.10|1. 0x0034 修改，频点选中修改为List，以支持多个频点设置；<br>2. 子成员支持的最多的频点数量也做了修改|官天河|2026\-3\-20||
|V1\.11|1. 0x0045 新增 Chrony授时服务器功能<br>2. 修改部分字段错误问题|官天河|2026\-3\-26||
|V1\.12|1. DetectTargetFilter\.target\_name 最大长度从32个字节调整到50个字节<br>2. BeaconTargetFilter\.name 最大长度从32个字节调整到50个字节|官天河|2026\-4\-9||
|V1\.13|1. 0x0034 协议做修改，扩展内容和设备端对齐、扩展数量到256；<br>2. 0x0043 扩展字段 TargetDescript\.target\_code TargetDescript\.ext\_float\_reserved|官天河|2026\-4\-24<br>||
|V1\.14|1. 0x0020 协议 SPTarget  target\_type 添加AI标识， 低 B0 \- B15 位 作为类型，B16 位 1标识AI目标 0 标识非AI目标|官天河|2026\-4\-27||
|V1\.15 |1. 0x0043命令TargetDescript\.target\_type 内容修改为子板通讯协议D2一致的内容|官天河|2026\-4\-29||
|V1\.16|1. 0x0020 上报的协议消息添加 SpectMatchProtocol 字段|官天河|2026\-5\-12||
|V1\.17<br>|1. 新增0x0036, 0x0015协议<br>|鲍利华<br>|2026\-5\-21||
|V1\.18<br>|1. 修改0x0020协议， 新增request\_mode = 3，request\_mode = 1 和request\_mode = 2 失效（频谱目标和协议目标一起上报）|鲍利华<br>|2026\-5\-21<br>||
|V1\.19|1. 修改 0x0020 协议 SPTarget target\_type字段，添加B17\~B21定义和说明<br>2. 添加 0x0060 RF目标频率跟踪指令|周大卫|2026\-7\-6<br>||
|V1\.20|1. 修改”0x0043 RF侦测机型库配置”中protocol\_type、target\_type、pulse\_w\_err、pulse\_t\_err、pulse\_bw\_err字段内容<br>2. 添加“0x0024 上报电磁环境监测统计结果”|张小龙|2026\-7\-16<br>||
|V1\.21|1. 修改DetecTatgetFilter PB的signal\_type定义，确认为基于信号来源类型进行过滤|周大卫|2026\-7\-24||
|V1\.22|1. 新增OTA 命令及定义（完全同sentry）|鲍利华|2026\-7\-27||

# 简介

TracerMatrix 和 C2 之间通讯，采用自研 Alink（Slink） 协议V2版本的数据结构，参考  [Skyfend通用Slink通信协议](https://vxr5wm8r80r.feishu.cn/docx/SG23dQBH9ocSomx7Zk4coWsrnFc#share-NkgldweMNo04YcxcoIWc4BNbndh)

# 规则说明：

1. msgid 使用两个字节，第一个字节表示协议类型，第二个字节表示具体命令；

2. 新的协议数据内容使用 protobuf 序列化（注意设备端对部分字段字节长度做了限制，C2需要在发送前做校验，否则设备端会拒绝该消息）；已有的实现，保持现状；

3. 0x00xx 字段消息为映射消息字段，；

4. 需要新增添加在协议后部即可，新旧版本协议自动兼容，不允许在中间插入新字段，或者修改已有字段的类型；

5. 请求中request\_mode特殊说明：

    1. request\_mode 为查询时，请求消息中的数据应皆设置为默认值，且设备端不会响应任何其他参数；

    2. request\_mode 为更新时，列表参数支持全量更新所有条目和部分更新单个条目，其他只支持全量更新；

    3. request\_mode 为更新时，列表参数中全局唯一id为0的条目表示新增的参数条目，其他id值的条目为覆盖修改；

    4. request\_mode 为更新时，只支持一个整体参数条目修改，不支持对单个条目参数修改；如 不支持对 DetectTargetFilter 中的 “filter\_name” 字段单独做修改；

6. 响应中request\_mode特殊说明：

    1. 响应消息0: 表示设备端主动上报；

    2. 请求中和响应中request\_mode值相同，表示响应成功；

    3. 响应中 request\_mode 大于255的值为错误码，详见错误码解释；

7. 协议中使用Bit位表示的情况，未做特殊说的情况，Bit位置为1表示功能使能或有效，Bit位置为0表示功能不使能或无效；有冲突，以协议中的特殊说明为准；

# Alink协议说明

|字节索引|定义|内容|C数据格式|数值范围|说明|
|---|---|---|---|---|---|
|0\-3|magic|帧头|Uint32|0xFCFCFCFC|表示开始一个新的包|
|4\-7|seq|消息序号|Uint32|0\~42945967295|发送发设备消息序列号，单次递增|
|8|len\_l|有效数据长度低8位|Uint8|0\~255|表示有效数据长度的低8位|
|9|len\_h|有效数据长度高8位|Uint8|0\~255|表示有效数据长度的低8位|
|10|prototype|通讯协议类型<br>|Uint8|0\~255<br>|通讯协议类型<br>1：SLINK自定义协议<br>2：json协议<br>3：protobuf协议|
|11|checksum|包头校验值<br>|Uint8|0\~255|计算校验值校验从字节0至字节10\(简单校验和）|
|12|destid|宿端设备类型ID|Uint8|接收者的设备ID|接收者的设备ID|
|13|sourceid|源端设备类型ID|Uint8|发送者的设备ID|发送者的设备ID|
|14\-15|msgid|消息ID|Uint16|0\-65535|消息ID用于识别该SLINK帧的含义|
|16\-47|sn|设备唯一ID|\[32\]Uint8|字符串|设备唯一sn号|
|48至（N\+47\)|payload|有效数据|\-|0\-65535 字节|根据报文类型定义的有效传递的数据（以PB编码之后的长度为准）|
|N\+47\+1至N\+47\+2|crc|整帧数据校验（2个字节）|Uint16|计算校验值不包含帧头，校验从字节4至字节N\+47|\-<br>|

# 特别说明\(For AI）

满足以下规则的同时，根据以下规则，检查文档格式，并给出提示；

1. 本协议是TracerMatrix端的协议，C2 为上位机；

2. 表格中 ”PB 结构名称“ 名称定义PB名称，或者指定不使用PB，那么表示使用C\+\+的结构体来表示数据，注意数据需要一字节对齐；

3. 0x02D3 频谱消息没有应答；

4. 协议定义关注 Type 和 Name 字段即可，其他字段可参考约束; 如果 Type 和 Name 有歧义给出提示；

5. 字段高亮可以不关注；

6. 带"list"后缀的变量为数组，Type 定义中定义了最大长度，需要给出限制；

7. 同时存在 C2\-\>TracerMatrix 和 TracerMatrix\-\>C2 同时存在的消息注册cmd即可，消息由C2求情，TracerMatrix应答；

8. 只存在 TracerMatrix\-\>C2 的情况，注册package，消息由TracerMatrix发送给C2

9. 各个消息没有优先级的区别；

10. 消息解析失败的，不给出应答，由上位机自行做超时判断；

11. 兼容性要求，升级协议新增字段只允许添加在尾部；

12. 需要新增一套支持 `uint16_t` 消息ID的API接口；

# 风格

请严格安装风格命名

协议**名称**风格为：大驼峰（示例：AaaBbbCcc）；

协议**字段**风格为：蛇形（示例：aaa\_bbb\_ccc\);

备注：和内部ROS2协议风格保持一致，算法结构体查参数也建议保持一致。

# 与PRD需求列表的对应关系

[Tracer Matrix边端\&云端上线PRD V1\.01 0127](https://vxr5wm8r80r.feishu.cn/wiki/SC2cwkaLCi8rdukH3OTcFhjsnGb)



[Tracer Matrix边端\&云端上线PRD V1\.0 0104](https://vxr5wm8r80r.feishu.cn/wiki/DH2TwkWvlin1KekHhzWchRsFn5g)

# 协议定义

## 1\.1 协议0x00xx

### 八位ID 适配对接 Spotter 和 C2 

说明: Spotter 暂时没有直接响应16位ID的能力, 这里将C2和Spotter接入的消息全部映射到一组 0x00 开头的八位ID协议中，在Spotter不具备16ID响应能力的情况下，只使用0x00开头的协议ID；

|非0x00xx协议（作废）|对应0x00xx协议|协议说明|
|---|---|---|
|0x0110|0x0010|设备信息查询|
|0x01A0|0x0012|主动上报工作状态|
|0x01A1|0x0013|频谱历史记录数据|
|0x02B0|0x0020|主动上报侦测结果|
|0x02C0|0x0021|WIFI目标主动上报|
|0x02D3|0x0022|频谱图上报|
|0x03A0|0x0030|AI大模型侦测增强|
|0x03A1|0x0031|频谱记录采数开关|
|0x03A2|0x0032|WIFI过滤管理|
|0x03A3|0x0033|RF过滤管理|
|0x03A4|0x0034|设置频谱检测参数|
|0x03A5|0x0035|设置IP地址|
|0x03C0|0x0040|位置姿态信息配置|
|0x03D0|0x0041|基本工作参数配置|
|0x03D1|0x0042|RF检测配置|
|0x03D2|0x0043|RF侦测机型库配置消息|
|0x03D3|0x0044|频谱检测配置|
|0x03E1|0x0045|NTP服务配置|
|0x0401|0x0050|数据上传和下载请求|
|0x045E|0x0051|数据导入|
|0x045F|0x0052|数据导出|
||0x0060|RF目标频率跟踪指令|

## 1\.2 状态信息 0x001x

### 1\.2\.1 0x0010 设备信息查询 

#### 设备信息查询消息

|消息ID|0x0010|||||
|---|---|---|---|---|---|
|消息描述|设备信息查询|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|DataRequest|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode|Uint32|请求类型<br>1： 查询|1|

#### 设备信息查询应答

|消息ID|0x0010|||||
|---|---|---|---|---|---|
|消息描述|设备信息查询回复|||||
|方向|TracerMatrix \> C2 |||||
|发送频率|跟随请求方回复；|||||
|PB 结构名称|DeviceStatusResponse|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode<br>|Uint32|请求类型:<br>1: 查询成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败|<br>|
|||device\_type|Uint32|设备类型码|0\-255|
|||device\_sn|Char\*32|设备SN号||
|||hw\_version|Char\*32|设备硬件版本||
|||sw\_version|Char\*32|设备软件版本||
|||device\_mac|Uint8\*6|设备MAC地址||
|||device\_ip|Uint8\*4|设备IP地址||

### 1\.2\.2 0x0012 工作状态查询

#### 工作状态查询消息

|消息ID|0x0012|||||
|---|---|---|---|---|---|
|消息描述|设备信息查询|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|DataRequest|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode|Uint32|请求类型<br>1：查询||

#### 工作状态查询应答

|消息ID|0x0012|||||
|---|---|---|---|---|---|
|消息描述|设备信息查询回复|||||
|方向|TracerMatrix \> C2 |||||
|发送频率|跟随请求方回复；或者 1s 主动上报一次；|||||
|PB 结构名称|DeviceWorkStatusResponse|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode<br>|Uint32|请求类型:<br>0: 主动上报<br>1: 查询成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败|<br>|
|||deveice\_time|Uint64|设备时间|ms|
|||check\_status<br>|Uint32<br>|自检状态字<br>B0：频谱模组异常标志，0表示正常，1表示异常<br>B1：协议模组异常标志，0表示正常，1表示异常<br>B2：预留<br>B3：综控模组异常标志，0表示正常，1表示异常<br>B4：温度异常标志，0表示正常，1表示异常<br>B5：同步信号异常标志，0表示正常，1表示异常<br>B6：GPS定位异常标志，0表示正常，1表示异常<br>B7：频谱检测饱和标志，0表示正常，1表示异常<br>B8\-31：预留|见描述<br>|
|||work\_status<br>|Uint32|工作状态字<br>B0：关闭侦测模式标志，0表示工作，1表示关闭<br>B1：广域侦测模式标志，0表示关闭，1表示工作<br>B2：旋转侦测模式标志，0表示关闭，1表示工作<br>B3：抵近侦测模式标志，0表示关闭，1表示工作<br>B4：外同步有效标志，0表示无效，1表示有效<br>B5：频谱图采集标志，0表示不采集，1表示采集<br>B6：原始IQ采集标志，0表示不采集，1表示采集<br>B7：频谱图传输标志，0表示不传输，1表示传输<br>B8：测试模式标志, 0 表示关闭，1表示工作<br>B9：数据队列满载标志 0 表示未满，1 表示未满<br>B10\-31：预留|见描述|
|||sys\_temprature\_list|Float\*7<br>|系统温度（℃）<br>按次序：面阵Module 1 \- 4 一体板 1 \-2 主机||
|||fault\_msg<br>|FaultMessage|故障上报协议[设备故障规范](https://vxr5wm8r80r.feishu.cn/sheets/HfzrsNVe9h2YEDt2hJRcLuiBnDc?sheet=5p6dP4) PB版本<br>||
|||longitude|Double|系统定位经度（°）手动设置或网络获取||
|||latitude|Double|系统定位纬度（°）手动设置或网络获取||
|||altitude|Float|系统定位海拔高度（m）手动设置或网络获取||
|||yaw|Float|系统姿态偏航角（°）手动设置或网络获取||
|||pitch|Float|系统姿态俯仰角（°）手动设置或网络获取||
|||roll|Float|系统姿态滚转角（°）手动设置或网络获取||
|||scan\_period|Uint16|频率扫描周期（ms）||
|||scan\_freq\_num|Uint32<br>|频率扫描个数<br>||
|||gps\_state<br>|Uint8\*2<br>|第一个字节：<br>搜星状态<br>0:  正常<br>1：异常<br>第二个字节：<br>gps搜星数量||
|||longitude\_gps|double|系统GPS定位经度（°） GPS传感器获取||
|||latitude\_gps|double|系统GPS定位纬度（°）GPS传感器获取||
|||altitude\_gps|Float|系统GPS定位海拔高度（m）GPS传感器获取||
|||yaw\_imu|Float|系统姿态偏航角（°）||
|||pitch\_imu|Float|系统姿态俯仰角（°）||
|||roll\_imu|Float|系统姿态滚转角（°）||
|||global\_state<br>|Uint8\*4<br>|第一字节：<br>设备状态：开机中 0 自检中 1 侦测中 2 <br>（自检预计完成时间10s\)<br>第二字节：<br>（取消）无线电环境状态：优 1 良 2 差 3   0 \-显示\-\-<br>第三字节：<br>（取消）探测性能：优 1 良 2 差 3 0 \-显示\-\-<br>第四字节：<br>时间来源：<br>0: EDGE授时<br>1：使用NTP服务<br>2：手动设置时间<br>3：chrony 授时||
|||time\_now|Char\*32|当前设备时间：<br>格式 2026/02/11 00:00:00 UTC||
|||last\_update\_time|Char\*32|上次设备更新时间<br>格式 2026/02/11 00:00:00 UTC||

#### FaultMessage PB定义

|Name|Type|Description|备注|
|---|---|---|---|
|sn|char\*25|设备SN号，字符串||
|errNum|uint32|错误数量||
|firstClass|FirstClass\*N \(0\-32\)|一级错误列表，数量 0\-32<br>||

#### FirstClass PB定义

|Name|Type|Description|备注|
|---|---|---|---|
|firstLevelCode|uint32|一级错误码<br>|一级列表|
|secondLevelCode|uint32|二级错误码<br>||
|thirdLevelCode|uint32|三级错误码<br>||
|fourErrNum|uint32|四级错误码数量||
|secondClass|SecondClass\*N\(0\-32\)|二级错误列表，数量 0\-32<br>||

#### SecondClass PB定义

|Name|Type|Description|备注|
|---|---|---|---|
|fourLevelCode|uint32|四级编码\(设备内部业务错误码定义\)<br>|二级列表<br>|
|fourLevelMsg|Char\*50|设备内部业务错误描述<br>||

### 1\.2\.3 0x0013 频谱历史记录数据 

#### 频谱历史记录数据查询消息

|消息ID|0x0013|||||
|---|---|---|---|---|---|
|消息描述|频谱历史记录数据查询消息|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|DataRequest|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode|Uint32|请求类型<br>1: 查询|1|

#### 频谱历史记录数据查询应答

|消息ID|0x0013|||||
|---|---|---|---|---|---|
|消息描述|频谱历史记录数据应答消息<br>1. 校验 request\_mode 和查询消息一致|||||
|方向|TracerMatrix \> C2|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|SpectrogramRecordResult|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode|Uint32|请求类型:<br>1: 查询成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败|1|
|||file\_num|Uint16|历史文件数量||
|||file\_name\_list<br>|\(Char\*256\) \*N \(0\-128\)|文件名 List， 数量 0\-128<br>||

### 1\.2\.4 0x0014 获取时间信息 

#### 获取时间信息请求 

|消息ID|0x0014||||
|---|---|---|---|---|
|消息描述|获取时间信息请求 ||||
|方向|TracerMatrix \> 上位机||||
|发送频率|由求情端决定, 间隔不低于100ms||||
|PB 结构名称|不是用PB，协议字段和原始保持一致||||
|<br>参数payload|字节|Name|Type|Description|
||0||||
|参数长度|0||||
|应答|有||||

#### 获取时间信息应答

|消息ID|0x0014||||
|---|---|---|---|---|
|消息描述|获取时间信息应答||||
|方向|上位机 \> TracerMatrix||||
|发送频率|由求情端决定||||
|PB 结构名称|不是用PB，协议字段和原始保持一致||||
|参数payload|字节|Name|Type|Description|
||20|time|char|字符串：年月日时分秒\.毫秒（例20240515011746\.901）|
||1|time\_zone|int8|时区设置|
|参数长度|20\+1||||
|应答|无||||

### 1\.2\.5 0x0015 上报4个子设备的工作状态

|消息ID|0x0015||||
|---|---|---|---|---|
|消息描述|TracerMatrix主动上报子设备的状态信息||||
|方向|TracerMatrix \-\> C2||||
|发送频率|1秒1次||||
|PB 结构名称|TracerAirLinkStatusReport||||
|参数payload<br>|字节|Name|Type|Description|
||4<br>|request\_mode<br>|Uint32<br>|请求类型：<br>0：主动上报<br>1：查询成功<br>错误码 \> 255<br>256：不支持的请求类型<br>257：查询失败（解码失败等）|
||16|matrix\_time\_ms|Uint64|AGX（TracerMatrix）本地时间|
||32|sn|char|tracerMatrix的sn|
||4|unit\_num|Uint32|子设备有效条数，固定为4， 只处理频谱的子设备；|
||4|slot\_index|Uint32|槽位下标，从 0 起连续编号R|
||32|sn|Char|子设备 sn|
||4|link\_state|Uint32|1 在线侦测中 / 2在线待机中 /3\. 离线 / 4 异常|
||4|fault|Uint32|异常状态（暂时无）|
||4|azimuth|Float|配置方位角（°） |
|参数长度|4\+16\+32\+4 \+ （4\+32\+4\+4\+4）\*6||||
|应答|无||||

## 1\.3 侦测结果上报 0x002x

### 1\.3\.1 0x0020 频谱协议目标 

#### 侦测结果请求

|消息ID|0x0020|||||
|---|---|---|---|---|---|
|消息描述|侦测结果查询|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|DataRequest|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode|Uint32<br>|请求类型<br>1: 频谱目标<br>2: 协议目标<br>3：频谱目标\+协议目标|1\-3|

#### 频谱结果应答

|消息ID|0x0020|||||
|---|---|---|---|---|---|
|消息描述|设备信息查询回复|||||
|方向|TracerMatrix \> C2 |||||
|发送频率|跟随请求方回复|||||
|PB 结构名称|SPTargetsResponse|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode|Uint32|请求类型:<br>1: 频谱目标<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败||
|||target\_total\_num|Uint32|侦测目标个数（最大128）<br>|0\-128<br>|
|||target\_list|SPTarget|频谱目标数据结构体, 数量0\-128||

##### SPTarget PB结构体定义

|Name|Type|Description|
|---|---|---|
|target\_num|Uint32|目标编号（频谱目标）|
|target\_type<br>|Uint32<br>|目标信号类型<br>B0\-B15位数值：<br>1：数字图传<br>2：模拟图传<br>3：Wifi图传（Beacon WIFI）<br>4：FK上行<br>5：FK下行<br>6：前导检测（暂不使用）<br>7：信号检测（暂不使用）<br>8：干扰源（Tracer   Air Ⅱ涉及）<br>9：遥控信号（Tracer   Air Ⅱ涉及）<br>10：通信基站（Tracer   Air Ⅱ涉及）<br>11：自定义干扰（Tracer   Air Ⅱ涉及）<br>12：自定义遥控（Tracer   Air Ⅱ涉及）<br>13：自定义通信（Tracer   Air Ⅱ涉及）<br><br>B16\-B31 按位处理<br>B16： AI增强目标 1 表示 AI目标 0 表示非AI标<br>B17：是否支持频率跟踪 1表示支持 0表示不支持（用于显示频率跟踪按钮）<br>B18：是否处于频率跟踪 1表示处于 0表示不处于（用于显示频率跟踪状态）<br>B19：是否为指定跟踪目标<br>B20：目标来源：空中（显示图标） <br>B21：目标来源：地面（显示图标）<br>B22：目标来源：扩展（显示图标）<br>B23：目标测向是否有效<br>B24：是否为自定义目标<br>B25:  是否为未知威胁检测<br>B26：未知威胁检测策略码1<br>B27：未知威胁检测策略码2<br>B28：未知威胁检测策略码3|
|target\_code|Uint16|目标标志码<br>用于标识目标频谱信号在整个数据系统内的唯一索引|
|target\_name<br>|Char\*50<br>|无人机名称/Beacon\-WIFI名称<br>字符串|
|track\_status|Uint32|无人机跟踪状态<br>B0：发现<br>B1：跟踪<br>B2：记忆<br>B3：消失|
|track\_time\_create|Uint64|建立时间<br>UTC毫秒计数（系统设置时间）|
|track\_time\_last|Uint64|最近测量时间<br>UTC毫秒计数（系统设置时间）|
|target\_chara\_code|Uint8\*32<br>|无人机特征码（字符串）<br>数字图传：<br>前8位有效，1\-4数据库识别码，5\-8特征周期（ms）<br>模拟图传：前4位有效，PAL/NTSC<br>WiFi图传：前24位有效，无人机Mac地址，遥控器Mac地址<br>飞控\-上行：<br>前8位有效，1\-4数据库识别码，5\-8特征周期（ms）<br>飞控\-下行：<br>前8位有效，1\-4数据库识别码，5\-8特征周期（ms）<br>前导检测：<br>前32位有效，1\-4为SSS根值，5\-8为BS根值，9\-16为空，17\-24为SSS计算相关值，25\-32为BS计算相关值|
|target\_confidence|uint32|目标置信度|
|track\_cnt|Uint32|测量次数|
|track\_frequence|Float|信号频率/MHz|
|track\_bW|Float|信号带宽/MHz <br>同huntermax联动时，由中心频点，确认结束频点、起始频点值<br>再由结束频点减去起始频点，起始频点和结束频点如下<br>831\-861MHz<br>900\-930MHz<br>1395\-1450MHz<br>2325\-2377MHz<br>2400\-2500MHz<br>2578\-2630MHz<br>5055\-5110MHz<br>5150\-5250MHz<br>5600\-5655MHz<br>5720\-5850MHz<br>5929\-5982MHz|
|track\_bws|int|跟踪频率起始索引|
|track\_bwe|int|跟踪频率终止索引|
|track\_cf|Float|信号所在接收机本振频点/MHz|
|track\_ef|Float|信号扩展描述频率/MHz|
|track\_pow|Float|信号功率/dBm |
|track\_noice|Float|噪声功率/dBm |
|track\_snr|Float|信噪比/dB|
|track\_distance|Float|距离估计/m<br>**注：参考**|
|track\_ct|Float|特征时间/us<br>**注：仅数字图传、模拟图传、飞控上下行有效**|
|track\_az|Float|测量方位/°（固定系）|
|track\_ei|Float|测量俯仰/°（固定系）|
|track\_az\_err|Float|测量方位误差范围/°|
|track\_el\_err|Float|测量俯仰误差范围/°|
|track\_angle\_time|Uint64|角度测量时间<br>UTC毫秒计数<br>同huntermax联动时作为** 脉冲上升沿时间**|
|track\_pdw\_type|uint32|目标PDW类型|
|track\_f\_start|Float|目标信号起始频率|
|track\_f\_end|Float|目标信号结束频率|
|track\_pri\_num|uint32|目标周期个数<br>|
|track\_pri\_value\[5\]|Float|目标周期数组<br>|
|track\_pw\_num|uint32|目标脉冲个数<br>|
|track\_pw\_value\[5\]|Float|目标脉冲数组<br>|
|target\_proc\_status|Uint32|属性状态<br>B0：白名单标志<br>B1：特征测量时间有效标志<br>B2：时间属性\-本地时间有效标志<br>B3：时间属性\-GPS时间PPS有效标志<br>B4：数据融合标志（被协议关联）<br>B5：固定坐标系有效标志|
|exInfo1|Uint32|扩展信息1<br>特征测量时间\-秒计数<br>表示特征时刻，不同类型定义不同，用于精准打击和数据融合<br>**注：用于分布式打击同步，仅数字图传、模拟图传飞控上下行、前导检测有效**|
|exInfo2|Uint32|扩展信息2<br>特征测量时间\-纳秒计数<br>表示特征时刻，不同类型定义不同，用于精准打击和数据融合<br>**注：用于分布式打击同步，仅数字图传、模拟图传飞控上下行、前导检测有效**|
|exInfo3|Float|原始测量方位/°|
|exInfo4|Float|原始测量俯仰/°|
|SpectMatchProtocol|Uint32|频谱和协议对应的目标编号<br>|

#### 协议结果应答

|消息ID|0x0020|||||
|---|---|---|---|---|---|
|消息描述|设备信息查询回复|||||
|方向|TracerMatrix \> C2 |||||
|发送频率|跟随请求方回复|||||
|PB 结构名称|PTTargetsResponse|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode|Uint32|请求类型:<br>2: 协议目标<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败|<br>|
|||target\_total\_num|Uint32|侦测目标个数（最大128）<br>|0\-128<br>|
|||target\_list|PTTarget\*N\(0\-128\)|频谱目标数据结构体，数量0\-128||

##### PTTarget PB结构体定义

|Name|Type|Description|
|---|---|---|
|drone\_num|Uint32|无人机编号|
|drone\_type<br>|Uint16<br>|无人机信号类型（按位处理）<br>B0：DroneID\-未加密<br>B1：DroneID\-加密<br>B2：RemoteID\-WiFi<br>B3：RemoteID\-Bluetheeth<br>B5：DroneID\-Detected<br>**注：可多选**|
|drone\_name|Char\*50|字符串<br>无人机名称|
|track\_status|Uint32<br>|无人机跟踪状态<br>B0：发现<br>B1：跟踪<br>B2：记忆<br>B3：消失|
|track\_time\_create|Uint64|建立时间 <br>UTC毫秒计数（系统设置时间）|
|track\_time\_last|Uint64|最近测量时间<br>UTC毫秒计数（系统设置时间）|
|track\_sn|Uint8\*32|无人机SN码<br>前20位为SN码，中间6位为RID飞机端的MAC地址，最后6位为保留|
|track\_source<br>|Uint32<br>|无人机测量来源<br>B0：DroneID\-未加密<br>B1：DroneID\-加密<br>B2：RemoteID\-WiFi<br>B3：RemoteID\-Bluetheeth<br>注：单选|
|track\_cnt|Uint32|测量次数|
|track\_frequence|Float<br>|当前信号频率/MHz<br>|
|track\_pow|Float|当前信号功率/dBm |
|track\_noice|Float|当前噪声功率/dBm |
|track\_snr|Float|当前信噪比/dB|
|drone\_gps\_time|Uint64|无人机广播时间戳<br>UTC毫秒计数：1970年1月1日至今|
|drone\_longitude|double|无人机经度\(°\)<br>|
|drone\_latitude|double|无人机纬度\(°\)<br>|
|drone\_altitude|Float|无人机海拔高度\(m\)<br>|
|drone\_height1|Float|无人机距地高度\(m\)<br>|
|drone\_height2|Float|无人机相对设备高度\(m\)|
|drone\_sail\_longitude|double|无人机返航点经度\(°\)|
|drone\_sail\_latitude|double|无人机返航点经度\(°\)|
|drone\_sail\_altitude|Float|无人机返航点海拔高度\(m\)|
|pilot\_longitude|double|飞手经度\(°\)|
|pilot\_latitude|double|飞手纬度\(°\)|
|pilot\_altitude|Float|飞手海拔高度\(m\)|
|drone\_yaw\_angle|Float|无人机角度\(°\)<br>|
|drone\_speed|Float|无人机绝对速度\(m/s\)|
|drone\_vertical\_speed|Float|无人机垂直速度\(m/s\)<br>|
|drone\_rid\_seq\_num|Uint16|RID信号序号|
|drone\_did\_seq\_num|Uint16|DID信号序号|
|drone\_rid\_classification|Uint16|RID分类<br>无人机类型，比如固定翼或者旋翼|
|drone\_rid\_status|Uint16|高8位：RID运行状态<br>低8位：RID系统状态|
|drone\_proc\_status|Uint32|属性状态（按位处理）<br>B0：白名单标志<br>B1：特征测量时间有效标志<br>B2：时间属性\-本地时间有效标志<br>B3：时间属性\-GPS时间PPS有效标志<br>B4：数据融合标志（关联频谱）|
|exInfo1|Uint32|扩展信息1：DroneID特征测量时间\-秒计数<br>表示Burst到达时刻，用于精准打击和数据融合|
|exInfo2|Uint32|扩展信息2：DroneID特征测量时间\-纳秒计数<br>表示Burst到达时刻，用于精准打击和数据融合|
|exInfo3|Uint32|扩展信息3：RemoteID特征测量时间\-秒计数<br>表示Burst到达时刻，用于精准打击和数据融合<br>注：仅WiFi有效|
|exInfo4|Uint32|扩展信息4：RemoteID特征测量时间\-纳秒计数<br>表示Burst到达时刻，用于精准打击和数据融合<br>注：仅WiFi有效|
|SpectMatchProtocol|Uint32|协议对应的频谱编号<br>|

#### 侦测目标（频谱\+协议）同时上报（0x0020）

|消息ID|0x0020|||||
|---|---|---|---|---|---|
|消息描述|频谱目标\+协议目标 一起上报|||||
|方向|TracerMatrix \> C2 |||||
|发送频率|上报间隔100ms|||||
|PB 结构名称|DetectionTargetsReport |||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode<br>|Uint32|请求类型:<br>3: 频谱目标\+协议目标<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败|3|
||<br>|target\_total\_num<br>|Uint32<br>|侦测目标个数总个数 T<br>|<br>|
|||sp\_target\_total\_num|Uint32<br>|频谱目标个数N<br>||
|||sp\_target\_list<br>|SPTarget <br>|SPTarget  \* N<br>||
|||pt\_target\_total\_num<br>|Uint32<br>|协议目标个数M<br>||
|||pt\_target\_list\[\]|PTTarget|PTTarget \* M||
|参数长度|4\+4\+4\+ SPTarget  \* N \+ PTTarget \* M                   （T = N\+M）|||||



### 1\.3\.2 0x0021 增强威胁目标（WIFI） 

#### 增强威胁目标请求消息

|消息ID|0x0021|||||
|---|---|---|---|---|---|
|消息描述|增强威胁目标请求消息|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|DataRequest|||||
|参数payload|字节|Name|Type|Description|数值范围|
||1|request\_mode|Uint32|请求类型<br>1 ： 查询 \(Beacon 目标）|1|

#### 增强威胁目标请求应答

|消息ID|0x0021|||||
|---|---|---|---|---|---|
|消息描述|增强威胁目标应答消息|||||
|方向|TracerMatrix \> C2 |||||
|发送频率|跟随请求方回复； 或 根据 03D0 设置主动上上报， 上报间隔 110ms|||||
|PB 结构名称|BeaconResult|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode|Uint32|请求类型:<br>1: 查询成功（Beacon目标）<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败|1|
||<br>|target\_total\_num|Uint32<br>|侦测目标个数（最大64）<br>|0\-64 ？<br>|
|||target\_list|BeaconTarget\*N\(0\-128\)|Beacon目标数据结构体,数量0\-128<br>||

#### BeaconTarget PB 定义

|Name|Type|Description|
|---|---|---|
|status|Uint32|B0:1 表示被禁用，0 表示未被禁用|
|name|Char\*32|Beacon名称|
|frequency|Float|频点|
|detect\_count|Uint32<br>|探测计数<br>|
|rssi\_power|Uint32|RSSI功率信息 0\-255|

### 1\.3\.3  0x0022 频谱图上报 

0x0044消息开启 "阵面配置"即开始上报，不需要C2给回复

|消息ID|0x0022|||||
|---|---|---|---|---|---|
|消息描述|TracerMatrix上报实时时频图数据，数据分包发送，合并起来为数据内容：<br>1. 格式为int16\_t buffer\[3002\]\[128\]，内容为转换后的功率值（单位0\.1dbm），其中第3000行为平均功率，第3001行为最大功率。|||||
|方向|TracerMatrix \> C2 |||||
|发送频率|跟随请求方回复|||||
|PB 结构名称|不是用PB，协议字段和原始保持一致|||||
|参数payload|字节|Name|Type|Description|数值范围|
||4<br>|device\_select<br>|Uint32<br>|B0: 选择前（0°）阵面 0表示未选中 1表示选中<br>B1: 选择右（90°）阵面 0表示未选中 1表示选中<br>B2: 选择后（180°）阵面 0表示未选中 1表示选中<br>B3: 选择左（270°）阵面 0表示未选中 1表示选中<br>B4\-B31预留<br>（不可多选）||
||4|freq|Uint32\_t|频率，kHz||
||4|frameNum|Uint32\_t|帧数||
||4|frameIdx|Uint32\_t|帧序号||
||4|frameSize|Uint32\_t|帧大小N||
||1\*N|data|uint8\_t\[N\]|时频图数据||
|参数长度|4\+4\+4\+4\+4\+1\*N=16\+N|||||
|应答|无|||||

### 1\.3\.4 0x0023 给C2（上位机）上报DroneID加密码流（0x0023）

|消息ID|0x0023||||
|---|---|---|---|---|
|消息描述|TracerMatrix 上报DroneID加密码流||||
|方向|TracerMatrix \> C2||||
|发送频率|侦测触发，约2\.56秒||||
|PB 结构名称|不是用PB，协议字段和原始保持一致||||
|参数payload|字节|Name|Type|Description|
||25|SN\_name|char\[25\]|设备SN号，字符串|
||8<br>|uniqueId<br>|uint64\_t<br>|唯一标识（0x4A回传结果时填充该值）|
||4|data1Len|uint32\_t|加密码流数据长度N|
||1\*N|data1|uint8\_t\[N\]<br>|加密码流数据（N最大1K字节）|
||4|data2Len|uint32\_t|码流数据长度M（保留）|
||1\*M|data2|uint8\_t\[M\]|码流数据（M最大1K字节）（保留）|
|参数长度|25\+8\+4\+4\+N\+M   = 41\+N\+M  N 最大 1024 M祖达1024||||
|应答|无||||

### 1\.3\.5 0x0024 上报电磁环境监测统计结果

|消息ID|0x0024|||||
|---|---|---|---|---|---|
|消息描述|TracerMatrix上报电磁环境监测统计结果<br>统计当前频点下隶属于整10MHz频段范围内的信号的环境特征：<br>1\.根据中心频率，确认哪些频段可由该时频图输出，约定为只要超过10行，即10MHz频段有4\.8M处于该工作频点下，则该点有效，解决交叉覆盖时，部分频段无统计问题<br>2\.计算10MHz频点需统计的频率行，其中1：7，122：128行无效<br>3\.计算对应10MHz频段的功率分布，计算源为N\*3000，N根据有效的行确认|||||
|方向|TracerMatrix \> C2|||||
|发送频率|侦测触发，扫频一轮上报一次|||||
|PB结构体名称|ReportSpectrumMonitorResultPB|||||
|参数payload|字节|Name|Type|Description|数值范围|
||8\*N|result\_item\_subarray1|SpectrumMonitorResultItem|监测结果，子阵1||
||8\*N<br>|result\_item\_subarray2|SpectrumMonitorResultItem|监测结果，子阵2||
||8\*N|result\_item\_subarray3|SpectrumMonitorResultItem|监测结果，子阵3||
||8\*N|result\_item\_subarray4|SpectrumMonitorResultItem|监测结果，子阵4<br>||
|参数长度|4\*8\*N\(N=\(6000\-400\)/10=560\)|||||

#### 统计结果输出结构体（SpectrumMonitorResultItem）

|字节|Name|Type|Description|数值范围|单位|
|---|---|---|---|---|---|
|4|freqMhz|float|当前频点|400\~6000|MHz|
|4|values|float|当前频点监测功率值|\-120\~\-60|dBm|

## 1\.4 设置配置 0x003x

### 1\.4\.1 0x0030 AI大模型侦测增强 

#### AI增强配置消息

|消息ID|0x0030|||||
|---|---|---|---|---|---|
|消息描述|AI增强配置消息|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|AIConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode|Uint32|请求类型：<br>1：查询<br>2：更新|1\-2|
|||status<br>|Uint32|1：开启<br>2：关闭||

#### AI增强配置应答

|消息ID|0x0030|||||
|---|---|---|---|---|---|
|消息描述|AI增强配置消息|||||
|方向|TracerMatrix \> C2 |||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|AIConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode|Uint32<br>|请求类型:<br>1: 查询成功<br>2: 更新成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败<br>258：更新失败|1\-2|
|||status<br>|Uint32<br>|1：开启<br>2：关闭||

### 1\.4\.2 0x0031 频谱记录采数开关 

#### 频谱记录采数开关消息

|消息ID|0x0031|||||
|---|---|---|---|---|---|
|消息描述|AI增强配置消息|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|SpectrogramStoreConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode<br>|Uint32|请求类型:<br>1：查询<br>2：更新|1\-2|
|||status<br>|Uint32|1：开启<br>2：关闭||
|||user\_config|Uint32|0: 不使用用户自定义设置<br>1：使用用户自定义设置||
|||task\_name|Char\*32|任务名称||
|||freqency|Uint32|所需检测频段||
|||cycle|Uint32\_t|扫描轮次||
|||store\_type|Uint32|数据存储类型<br>1:xxxx<br>2:xxxx||

#### 频谱记录采数开关应答

|消息ID|0x0031|||||
|---|---|---|---|---|---|
|消息描述|AI增强配置消息|||||
|方向|TracerMatrix \> C2|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|SpectrogramStoreConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode<br>|Uint32|请求类型:<br>1: 查询成功<br>2: 更新成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败<br>258：更新失败|1\-2|
|||status<br>|Uint32|1：开启<br>2：关闭||
|||user\_config|Uint32|0: 不使用用户自定义设置<br>1：使用用户自定义设置||
|||task\_name|Char\*32|任务名称||
|||freqency|Uint32|所需检测频段||
|||cycle|Uint32\_t|扫描轮次||
|||store\_type|Uint32|数据存储类型<br>1:xxxx<br>2:xxxx||

### 1\.4\.3 0x0032 WIFI过滤管理设置 

功能\&约束说明：

1. 查询消息，后更参数列表数量为0；设备端不会响应后更数据；

2. \`filter\_target\_list\` **\*\*全部为 \`id==0\`\*\*** 时整批新增并追加；**\*\*全部为非 0 id\*\*** 时仅刷新已存在项；**\*\*禁止\*\***同请求内 \`id==0\` 与 \`id≠0\` 混用；更新成功**\*\*不重排\*\***已有项 id；删除（mode=3）后仍会重排。

3. 删除 和 更新，无论成功失败， 后跟的条目数据为空；

#### WIFI过滤管理设置消息

|消息ID|0x0032|||||
|---|---|---|---|---|---|
|消息描述|AI增强配置消息|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|BeaconFilterConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode<br>|Uint32<br>|请求类型：<br>1：查询<br>2：更新<br>3：删除（按照唯一ID删除）|1\-2|
|||filter\_num|Uint32|过滤器数量 （0\-64）?||
|||filter\_target\_list<br>|BeaconTargetFilter\*N\(0\-128\)|Beacon目标过滤设置数据结构体,数量0\-128<br>||

#### WIFI过滤管理设置应答

|消息ID|0x0032|||||
|---|---|---|---|---|---|
|消息描述|AI增强配置消息|||||
|方向|TracerMatrix \> C2 |||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|BeaconFilterConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode<br>|Uint32<br>|请求类型:<br>1: 查询成功<br>2: 更新成功<br>3: 删除成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败<br>258：更新失败<br>259：删除失败|1\-2|
|||filter\_num|Uint32|过滤器数量 （0\-64）?||
|||filter\_target\_list<br>|BeaconTargetFilter\*N\(0\-128\)|Beacon目标过滤设置数据结构体,数量0\-128<br>||

#### BeaconTargetFilter PB定义

|Name|Type|Description|
|---|---|---|
|id|Uint32|全局唯一ID|
|status|Uint32|B0:1 表示被启用 0 表示不启用|
|name|Char\*50|Beacon（wifi名称）名称|
|note|Uint8\*128|备注 0\-20 个（中文）字符|

### 1\.4\.4 0x0033 RF过滤管理 

功能\&约束说明：

1. 查询消息，后更参数列表数量为0；设备端不会响应后更数据；

2. \`filter\_target\_list\` **\*\*全部为 \`id==0\`\*\*** 时整批新增并追加；**\*\*全部为非 0 id\*\*** 时仅刷新已存在项；**\*\*禁止\*\***同请求内 \`id==0\` 与 \`id≠0\` 混用；更新成功**\*\*不重排\*\***已有项 id；删除（mode=3）后仍会重排。

3. 删除 和 更新，无论成功失败， 后跟的条目数据为空；

#### RF过滤管理消息

|消息ID|0x0033|||||
|---|---|---|---|---|---|
|消息描述|RF过滤管理消息|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|DetectFilterConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode<br>|Uint32<br>|请求类型：<br>1：查询<br>2：更新<br>3:  删除（按照全局唯一ID删除）|1\-2|
|||filter\_num|Uint32|过滤器数量 （0\-64）?||
|||filter\_target\_list<br>|DetectTargetFilter\*N\(0\-128\)|侦测目标过滤设置数据结构体, 目标数量0\-128<br>||

#### RF过滤管理应答

|消息ID|0x0033|||||
|---|---|---|---|---|---|
|消息描述|RF过滤管理应答|||||
|方向|TracerMatrix \> C2|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|DetectFilterConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode<br>|Uint32<br>|请求类型:<br>1: 查询成功<br>2: 更新成功<br>3：删除成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败<br>258：更新失败<br>259:  删除失败|1\-2|
|||filter\_num|Uint32|过滤器数量 （0\-64）?||
|||filter\_target\_list<br>|DetectTargetFilter\*N\(0\-128\)|侦测目标过滤设置数据结构体, 目标数量0\-128<br>||

#### DetectTargetFilter PB 定义

|Name|Type|Description|
|---|---|---|
|id|Uint32|全局唯一ID|
|status<br>|Uint8|B0: 规则启用使能 0 表示规则不启用 1表示规则启用<br>B1: 方位角过滤使能<br>B2：俯仰角过滤使能|
|filter\_name|Char\*32|过滤器规则名称|
|target\_name|Char\*50|目标名称|
|freq\_start\_list|Float\*5|开始频点 MHZ<br>|
|freq\_end\_list|Float\*5|结束频点 MHZ<br>|
|freq\_selected|Uint32<br>|B0: 0号频点使能 0表示不使能 1表示使能<br>B1: 1号频点使能 0表示不使能 1表示使能<br>B2: 2号频点使能 0表示不使能 1表示使能<br>B3: 3号频点使能 0表示不使能 1表示使能<br>B4: 4号频点使能 0表示不使能 1表示使能|
|signal\_type|Uint32|目标信号类型<br>B0：空中目标<br>B1：地面目标<br>B2：无法确认<br>其它无定义，默认填0|
|orient\_min|Float|方位角下限|
|orent\_max|Float|方位角上限|
|yaw\_min|Float|俯仰范围下限|
|yaw\_max|Float|俯仰范围上限|

### 1\.4\.5 0x0034 设置频谱检测参数

功能说明：

1. 查询消息，后更参数列表数量为0；设备端不会响应后更数据；

2. 0x0034 可以更新，但只允许更新 SpectrumMonitorFreqPoint 子成员列表中的 freq\_point\_select\_index

3. 0x0034 不允许新增；

#### 设置频谱检测参数消息

|消息ID|0x0034|||||
|---|---|---|---|---|---|
|消息描述|设置频谱检测参数消息|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|SpectrumMonitorSetting|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode<br>|Uint32<br>|请求类型：<br>1：查询<br>2：更新（不支持新增）|1\-2|
|||working\_status<br>|Uint32|工作类型：<br>0：非频谱工作模式<br>1：开始扫描 \(应用设置开始工作）<br>2：停止扫描 ||
|||device\_select<br>|Uint32|B0: 选择前（0°）阵面 0表示未选中 1表示选中<br>B1: 选择右（90°）阵面 0表示未选中 1表示选中<br>B2: 选择后（180°）阵面 0表示未选中 1表示选中<br>B3: 选择左（270°）阵面 0表示未选中 1表示选中<br>B4\-B31预留<br>（可多选）||
|||freq\_point\_select\_list<br>|SpectrumMonitorFreqPoint\*N\(0\-64\)|现在的频点信息<br>||

#### 设置频谱检测参数应答

|消息ID|0x0034|||||
|---|---|---|---|---|---|
|消息描述|设置频谱检测参数应答|||||
|方向|TracerMatrix \> C2 |||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|SpectrumMonitorSetting|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode<br>|Uint32<br>|请求类型:<br>1: 查询成功<br>2: 更新成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败<br>258：更新失败|1\-2|
|||working\_status|Uint32|工作类型：<br>0：非频谱工作模式<br>1：开始扫描 \(应用设置开始工作）<br>2：停止扫描 ||
|||device\_select|Uint32|B0: 选择前（0°）阵面 0表示未选中 1表示选中<br>B1: 选择右（90°）阵面 0表示未选中 1表示选中<br>B2: 选择后（180°）阵面 0表示未选中 1表示选中<br>B3: 选择左（270°）阵面 0表示未选中 1表示选中<br>B4\-B31预留<br>（可多选）||
|||freq\_point\_select\_list<br>|SpectrumMonitorFreqPoint\*N\(0\-64\)|现在的频点信息<br>||

#### SpectrumMonitorFreqPoint PB定义

|Name|Type|Description|
|---|---|---|
|id|Uint32|全局唯一ID|
|start\_freq|float|起始频点 默认频段 start\_freq 等于 end\_freq|
|end\_freq|float|结束频点 默认频段 start\_freq 等于 end\_freq|
|setting\_list<br>|Uint32<br>|B0 默认频段位： 0表示自定义 1表示默认：开始频点和结束频点相等，为固定值；间隔为0<br>|
|available\_freq\_point|Uint32\*32<br>|该频段的可选频点列表，数量 0 \- 32<br>|
|freq\_point\_select\_index<br>|Uint32\*32|选中的列表编号，数量 0\-32<br>如：available\_freq\_point 中第100位和200位被选中，这里数组为 \[100, 200\]|

### 1\.4\.6 0x0035 设置IP地址

#### 设置IP地址配置消息

|消息ID|0x0035|||||
|---|---|---|---|---|---|
|消息描述|设置IP地址配置消息；回复消息后马上生效|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|IPAddressConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode<br>|Uint32<br>|请求类型：<br>1：查询<br>2：更新|1\-2<br>|
|||static\_ip|Uint32|0:表示动态IP 1:表示静态IP||
|||ip\_address|Uint8\*4|ipv4 版本 ip 地址||
|||subnet\_mark|Uint8\*4|子网掩码||

#### 设置IP地址配置应答

|消息ID|0x0035|||||
|---|---|---|---|---|---|
|消息描述|设置IP地址配置消息；回复消息后马上生效|||||
|方向|TracerMatrix \> C2 |||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|IPAddressConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode<br>|Uint32<br>|请求类型:<br>1: 查询成功<br>2: 更新成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败<br>258：更新失败|1\-2<br>|
|||static\_ip|Uint32|0:表示动态IP 1:表示静态IP||
|||ip\_address|Uint8\*4|ipv4 版本 ip 地址||
|||subnet\_mark|Uint8\*4|子网掩码||

### 1\.4\.7 0x0036 设置侦测目标上报开关使能

|消息ID|0x0036|||||
|---|---|---|---|---|---|
|消息描述|侦测目标上报开关使能|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|DetectTargetCollectConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode|Uint32|请求类型：<br>1：查询<br>2：更新|1\-2|
|||collect\_enable<br>|Uint32<br>|该协议修改成如下：<br>Bit0：对应测向子阵1，1开启0关闭<br>Bit1：对应测向子阵2<br>Bit2：对应测向子阵3<br>Bit3：对应测向子阵4<br>Bit4：对应协议主板<br>Bit5：对应协议从板<br>Bit6：对应AI节点 （同0x0030， 0x0030会去掉）<br>Bit7：禁止侦测目标上报（1：禁止上报；0：上报）<br>其它预留  （注意：bit0\~bit3 已经实现，bit4\~bit6暂时没有实现）||

|消息ID|0x0036|||||
|---|---|---|---|---|---|
|消息描述|侦测目标上报开关使能|||||
|方向|TracerMatrix \> C2 |||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|DetectTargetCollectConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode<br>|Uint32<br>|请求类型:<br>1: 查询成功<br>2: 更新成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败<br>258：更新失败|1\-2|
|||collect\_enable<br>|Uint32<br>|该协议修改成如下：<br>Bit0：对应测向子阵1，1开启0关闭<br>Bit1：对应测向子阵2<br>Bit2：对应测向子阵3<br>Bit3：对应测向子阵4<br>Bit4：对应协议主板<br>Bit5：对应协议从板<br>Bit6：对应AI节点 （同0x0030， 0x0030会去掉）<br>Bit7：禁止侦测目标上报（1：禁止上报；0：上报）<br>其它预留  （注意：bit0\~bit3 已经实现，bit4\~bit6暂时没有实现）||

## 1\.5 设置信息配置 0x004x

### 1\.5\.1 0x0040 位置姿态信息配置 

#### 位置姿态信息配置消息

|消息ID|0x0040|||||
|---|---|---|---|---|---|
|消息描述|位置姿态信息配置消息|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|PositionOrientationConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode|Uint32|请求类型：<br>1：查询<br>2：更新|1\-2|
|||longitude|double|系统GPS定位经度（°）||
|||latitude|double|系统GPS定位纬度（°）||
|||altitude|Float|系统GPS定位海拔高度（m）||
|||yaw|Float|系统姿态偏航角（°）||
|||pitch|Float|系统姿态俯仰角（°）||
|||roll|Float|系统姿态滚转角（°）||
|||speed\_x|Float|系统X轴速度（m/s）||
|||speed\_y|Float|系统Y轴速度（m/s）||
|||speed\_z|Float|系统Z轴速度（m/s）||
|||omega\_x|Float|系统X轴角速度（°/s）||
|||omega\_y|Float|系统Y轴角速度（°/s）||
|||omega\_z|Float|系统Z轴角速度（°/s）||
|||setting\_mode<br>|Uint32|1:  手动\-用户设置<br>2：自动\-通过GPS（内部设备\)<br>3：网络\-通过上位机获取||
|||data\_source<br>|Uint32|1:  手动\-用户设置<br>2：自动\-通过GPS（内部设备\)<br>3：网络\-通过上位机获取||
|||data\_state|Uint32|0：静态 1: 动态上报位置信息：10HZ||

#### 位置姿态信息配置应答

|消息ID|0x0040|||||
|---|---|---|---|---|---|
|消息描述|位置姿态信息配置应答|||||
|方向|TracerMatrix \> C2 |||||
|发送频率|由发送方控制,间隔时间不低于100ms；或主动上报，上报频率 10hz|||||
|PB 结构名称|PositionOrientationConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode|Uint32|请求类型:<br>0: 主动上报<br>1: 查询成功<br>2: 更新成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败<br>258：更新失败|1\-2|
|||longitude|double|系统GPS定位经度（°）||
|||latitude|double|系统GPS定位纬度（°）||
|||altitude|Float|系统GPS定位海拔高度（m）||
|||yaw|Float|系统姿态偏航角（°）||
|||pitch|Float|系统姿态俯仰角（°）||
|||roll|Float|系统姿态滚转角（°）||
|||speed\_x|Float|系统X轴速度（m/s）||
|||speed\_y|Float|系统Y轴速度（m/s）||
|||speed\_z|Float|系统Z轴速度（m/s）||
|||omega\_x|Float|系统X轴角速度（°/s）||
|||omega\_y|Float|系统Y轴角速度（°/s）||
|||omega\_z|Float|系统Z轴角速度（°/s）||
|||setting\_mode|Uint32|1:  手动\-用户设置<br>2：自动\-通过GPS（内部设备\)<br>3：网络\-通过上位机获取||
|||data\_source<br>|Uint32|1:  手动\-用户设置<br>2：自动\-通过GPS（内部设备\)<br>3：网络\-通过上位机获取||
|||data\_state|Uint32|0：静态 1: 动态上报位置信息：10HZ||

### 1\.5\.2 0x0041 基本工作参数配置 

#### 基本工作参数配置消息

|消息ID|0x0041|||||
|---|---|---|---|---|---|
|消息描述|基本工作参数配置消息|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|BasicWorkParaConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||set\_mode|Uint32|请求类型：<br>1：查询<br>2：更新|1\-2|
|||work\_mode<br>|Uint32<br>|工作模式（模式总开关）<br>B0：数据融合使能 0 表示不使能 1表示使能<br>B1：车载模式使能 0 固定 1 车载<br>B2：安装类型 0 固定 1 移动<br>B3：角度输出坐标系选择 0 固定系 1 测量系<br>B4：频谱侦测模块使能 0表示不使能 1表示使能<br>~~B5：协议侦测DID模块使能~~<br>~~B6：协议侦测RID模块使能~~<br>B7：未知信号识别功能使能 0表示不使能 1表示使能<br>B8:  协议信号功能使能 0表示不使能 1表示使能<br>B9：WIFI信号功能使能 0表示不使能 1表示使能<br>B10\-B31：预留||
|||det\_type<br>|Uint32<br>|侦测模式使能<br>频谱字段<br>B0：数字图传 Digital VT 0表示不使能 1表示使能<br>B1：模拟图传 Analog VT 0表示不使能 1表示使能<br>B2：Wifi 图传 0表示不使能 1表示使能 <br>B3：FK上行 RC  0表示不使能 1表示使能<br>B4：FK下行 RC  0表示不使能 1表示使能<br>B5：前导检测 0表示不使能 1表示使能<br>B6：信号检测 0表示不使能 1表示使能<br>B7：干扰源（Tracer   Air Ⅱ涉及） 0表示不使能 1表示使能<br>B8：遥控信号（Tracer   Air Ⅱ涉及） 0表示不使能 1表示使能<br>B9：通信基站（Tracer   Air Ⅱ涉及） 0表示不使能 1表示使能<br>B10\~B15：<br><br>协议字段<br>B16: 协议侦测DID\*模块使能 0表示不使能 1表示使能<br>B17: 协议侦测DID模块使能 0表示不使能 1表示使能<br>B18: 协议侦测RID模块使能 0表示不使能 1表示使能<br><br>wifi 增强型检测<br>B20: WIFI信号使能 0表示不使能 1表示使能<br>B21：Wifi 图传 0表示不使能 1表示使能<br>|频谱 16bit<br>协议 4bit<br>wifi 4bit<br>预留|
|||det\_duration<br>|Uint32\*2<br>|目标记忆时间（s）<br>数组第一位：协议记忆时间<br>数组第二位：频谱记忆时间||
|||det\_sensitive|Uint32|检测灵敏度<br>1：低 <br>2：中<br>3：高||

#### 基本工作参数配置应答

|消息ID|0x0041|||||
|---|---|---|---|---|---|
|消息描述|基本工作参数配置消息|||||
|方向|TracerMatrix \> C2|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|BasicWorkParaConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||set\_mode|Uint32|请求类型:<br>1: 查询成功<br>2: 更新成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败<br>258：更新失败|1\-2|
|||work\_mode<br>|Uint32<br>|工作模式（模式总开关）<br>B0：数据融合使能 0 表示不使能 1表示使能<br>B1：车载模式使能 0 固定 1 车载<br>B2：安装类型 0 固定 1 移动<br>B3：角度输出坐标系选择 0 固定系 1 测量系<br>B4：频谱侦测模块使能 0表示不使能 1表示使能<br>B5\-B6: 预留<br>B7：未知信号识别功能使能 0表示不使能 1表示使能<br>B8:  协议信号功能使能 0表示不使能 1表示使能<br>B9：WIFI信号功能使能 0表示不使能 1表示使能<br>B10\-B31：预留||
|||det\_type<br>|Uint32|侦测模式使能<br>频谱字段<br>B0：数字图传 Digital VT 0表示不使能 1表示使能<br>B1：模拟图传 Analog VT 0表示不使能 1表示使能<br>B2：Wifi 图传 0表示不使能 1表示使能<br>B3：FK上行 RC  0表示不使能 1表示使能<br>B4：FK下行 RC  0表示不使能 1表示使能<br>B5：前导检测 0表示不使能 1表示使能<br>B6：信号检测 0表示不使能 1表示使能<br>B7：干扰源（Tracer   Air Ⅱ涉及） 0表示不使能 1表示使能<br>B8：遥控信号（Tracer   Air Ⅱ涉及） 0表示不使能 1表示使能<br>B9：通信基站（Tracer   Air Ⅱ涉及） 0表示不使能 1表示使能<br><br>协议字段<br>B16: 协议侦测DID\*模块使能 0表示不使能 1表示使能<br>B17: 协议侦测DID模块使能 0表示不使能 1表示使能<br>B18: 协议侦测RID模块使能 0表示不使能 1表示使能<br><br>wifi 增强型检测<br>B20: WIFI信号使能 0表示不使能 1表示使能<br>|频谱 16bit<br>协议 4bit<br>wifi 4bit<br>预留|
|||det\_duration<br>|Uint32\*2<br>|目标记忆时间（s）<br>数组第一位：协议记忆时间<br>数组第二位：频谱记忆时间||
|||det\_sensitive|Uint32|检测灵敏度<br>1：低 <br>2：中<br>3：高||

### 1\.5\.3 0x0042 RF检测配置 

1. 查询消息，后更参数列表数量为0；设备端不会响应后更数据；

2. \`freq\_config\_list\` **\*\*全部为 \`id==0\`\*\*** 时整批新增并追加；**\*\*全部为非 0 id\*\*** 时仅刷新已存在项；**\*\*禁止\*\***同请求内 \`id==0\` 与 \`id≠0\` 混用；更新成功**\*\*不重排\*\***已有项 id；删除（mode=3）后仍会重排。

3. 删除 和 更新，无论成功失败， 后跟的条目数据为空；

#### RF 检测配置消息

|消息ID|0x0042|||||
|---|---|---|---|---|---|
|消息描述|RF 检测器配置消息<br>1\.查询消息，后更参数列表数量为0；|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|RFDetectConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode<br>|Uint32<br>|请求类型：<br>1：查询<br>2：更新<br>3:  删除（按全局唯一ID删除 ， 默认不可删除）<br>4：恢复默认（不响应参数）|1\-2<br>|
|||freq\_num|Uint32|对象数量||
|||freq\_config\_list<br>|TragetConfig \*N\(0\-128\)|对象列表<br>||

#### RF 检测配置应答

|消息ID|0x0042|||||
|---|---|---|---|---|---|
|消息描述|RF 检测器配置应答<br>1. 恢复默认，无论成功还是失败，后跟的条目数据为空；<br>2. 删除 和 更新，无论成功失败， 后跟的条目数据为空；|||||
|方向|TracerMatrix \> C2|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|RFDetectConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||update\_mode<br>|Uint32<br>|请求类型:<br>1: 查询成功<br>2: 更新成功<br>3: 删除成功（根据全局唯一ID删除）<br>4: 恢复默认成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败<br>258：更新失败<br>259：删除失败<br>260:  恢复默认失败|1\-2<br>|
|||freq\_num|Uint32|对象数量||
|||freq\_config\_list<br>|TragetConfig \*N\(0\-128\)|对象列表<br>||

#### TargetConfig PB 定义

|Name|Type|Description|
|---|---|---|
|id|Uint32|全局唯一ID|
|start\_freq|float|起始频点 默认频段 start\_freq 等于 end\_freq|
|end\_freq|float|结束频点 默认频段 start\_freq 等于 end\_freq|
|freq\_intevel|float|频点间隔; 如果是默认频段，不工作|
|freq\_gain|Uint32|频段增益控制 dBi|
|setting\_list<br>|Uint32<br>|B0 默认频段位： 0表示自定义 1表示默认：开始频点和结束频点相等，为固定值；间隔为0 \(1\)<br>B1：AI大模型侦测使能：0 表示不使能，1 表示使能 \(2\)<br>B2: 未知目标检测功能使能: 0 表示不使能，1 表示使能 \(4\)<br>B3：频段增益配置使能：0 表示不使能，1 表示使能 \(8\)<br>B4：频段启用状态使能：0 表示不使能，1 表示使能 \(16\)|

### 1\.5\.4 0x0043 RF侦测机型库配置 

1. 查询消息，后更参数列表数量为0；设备端不会响应后更数据；

2. \`target\_define\_list\` **\*\*全部为 \`id==0\`\*\*** 时整批新增并追加；**\*\*全部为非 0 id\*\*** 时仅刷新已存在项；**\*\*禁止\*\***同请求内 \`id==0\` 与 \`id≠0\` 混用；更新成功**\*\*不重排\*\***已有项 id；删除（mode=3）后仍会重排。

3. 删除 和 更新，无论成功失败， 后跟的条目数据为空；

#### RF侦测机型库配置消息

|消息ID|0x0043|||||
|---|---|---|---|---|---|
|消息描述|工作频段配置消息<br>1\.查询消息，后更参数列表数量为0；|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|DetectDataBaseConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||set\_mode<br>|Uint32|请求类型:<br>1：查询<br>2：更新<br>3：删除（按照全局唯一ID删除）|1\-2|
|||target\_defineNum|Uint32|0\~64（最大可支持64）||
|||target\_define\_list<br>|TargetDescript \* N（0\-128）|自定义目标配置参数,目标格式 0\-256<br>||

#### RF侦测机型库配置应答

|消息ID|0x0043|||||
|---|---|---|---|---|---|
|消息描述|工作频段配置消息<br>1. 删除 和 更新，无论成功失败， 后跟的条目数据为空；|||||
|方向|TracerMatrix \> C2|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|DetectDataBaseConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||set\_mode|Uint32|请求类型:<br>1: 查询成功<br>2: 更新成功<br>3：删除成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败<br>258：更新失败<br>259：删除失败|1\-2|
|||target\_defineNum|Uint32<br>|0\~256（最大可支持256）<br>||
|||target\_define\_list<br>|TargetDescript \* N（0\-256）|自定义目标配置参数,目标格式 0\-256<br>||

#### TargetDescript PB 定义

|Name|Type|Description|
|---|---|---|
|id|Uint32|全局唯一ID|
|target\_name|Char\*50|目标名称|
|target\_set|Uint32<br>|目标属性设置<br>B0：报文使能有效<br>B1：是否自定义 0 表示非自定义 1表示自定义<br>B2\~B7预留|
|protocol\_type|Uint32|协议类型<br>1: FHSS<br>2: LB FHSS<br>3: OFDM<br>4: LB OFDM<br>5: OS OFDM<br>6: EN\.WiFi<br>7: CRSF<br>8: AFHDS<br>9: ACCESS<br>10: ACCESS ACCST <br>11: FASST<br>12: GHOST<br>13: DSMX<br>14: WBFM<br>15: Others|
|target\_type<br>|Uint32<br>|目标信号类型<br>B0\-B15位数值：<br>1：数字图传<br>2：模拟图传<br>3：Wifi图传（Beacon WIFI）<br>4：FK上行<br>5：FK下行<br>6：前导检测（暂不使用）<br>7：信号检测（暂不使用）<br>8：干扰源（Tracer   Air Ⅱ涉及）<br>9：遥控信号（Tracer   Air Ⅱ涉及）<br>10：通信基站（Tracer   Air Ⅱ涉及）<br>11：自定义干扰（Tracer   Air Ⅱ涉及）<br>12：自定义遥控（Tracer   Air Ⅱ涉及）<br>13：自定义通信（Tracer   Air Ⅱ涉及）<br><br>B16\-B31 按位处理<br>B16： AI增强目标 1 表示 AI目标 0 表示非AI标<br>B17：是否支持频率跟踪 1表示支持 0表示不支持（用于显示频率跟踪按钮）<br>B18：是否处于频率跟踪 1表示处于 0表示不处于（用于显示频率跟踪状态）<br>B19：是否为指定跟踪目标<br>B20：目标来源：空中（显示图标） <br>B21：目标来源：地面（显示图标）<br>B22：目标来源：扩展（显示图标）<br>B23：目标测向是否有效<br>B24：是否为自定义目标<br>B25:  是否为未知威胁检测<br>B26：检测策略码1（1表示固定频率检测开启（映射到数字图传检测策略），0表示关闭）<br>B27：检测策略码2（1表示跳频检测开启（映射到飞控检测策略），0表示关闭）<br>B28：检测策略码3|
|pulse\_w|Float\*5|有效脉宽（ms，0\.4\~50）<br>注：遥控、通信节点类型有效|
|pulse\_t|float\*5|脉冲周期（ms，0\.5\~50）<br>注：遥控、通信节点类型有效|
|pulse\_bw|float\*5|信号带宽（MHz，0\.4\~20）<br>注：遥控、通信节点类型有效|
|freq\_start|float\*5|有效频段起始（MHz，400\~6000）<br>注：遥控、干扰、通信节点类型有效|
|freq\_end|float\*5|有效频段终止（MHz，400\~6000）<br>注：遥控、干扰、通信节点类型有效|
|freq\_selected|Uint32<br>|B0: 0号频点使能 0表示不使能 1表示使能<br>B1: 1号频点使能 0表示不使能 1表示使能<br>B2: 2号频点使能 0表示不使能 1表示使能<br>B3: 3号频点使能 0表示不使能 1表示使能<br>B4: 4号频点使能 0表示不使能 1表示使能|
|pulse\_w\_err|float|脉宽误差（ms，0\.04\~0\.10）<br>注：遥控、通信节点类型有效<br>\(新建默认 0\.07）|
|pulse\_t\_err|float|脉冲周期误差（ms，0\.04\~0\.10）<br>注：遥控、通信节点类型有效<br>\(新建默认 0\.07）|
|pulse\_bw\_err|float|带宽误差（MHz，0\.4\~1\.2）<br>注：遥控、干扰、通信节点类型有效<br>\(新建默认 0\.96）|
|target\_code|Uint32|目标标志码|
|ext\_float\_reserved\[16\]|**float\*16**<br>|扩展字段：<br>不会在界面显示|



### 1\.5\.5 0x0045 NTP服务配置 

#### NTP服务配置消息

|消息ID|0x0045|||||
|---|---|---|---|---|---|
|消息描述|频谱检测配置消息|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|NTPParaConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||set\_mode|Uint32|请求类型：<br>1：查询<br>2：更新|1\-2|
|||ntp\_enable<br>|Uint32|NTP服务器设置<br>0：使用上位机授时（为0是，以下NTP设置设备端不响应，只保存）（ 使用该选项，设备端将使用  0x0014 在建立连接的时候，求情上位机授时） <br>1：使用NTP服务<br>2：手动设置时间<br>3：chrony 授时||
|||ntp\_default|Uint32|NTP恢复默认使能，NTP服务器地址恢复默认地址<br>0：使用以下设置值<br>1：恢复默认||
|||ntp\_time\_zone|Int32<br>|NTP时区设置（0:UTC 时间 8 东八区 \-8 西八区）<br>||
|||ntp\_server\_addr|char\*512|NTP服务器地址/chrony服务器地址<br>||
|||time|Char\*20|字符串：年月日时分秒\.毫秒（例20240515011746\.901）||

#### NTP服务配置应答

|消息ID|0x0045|||||
|---|---|---|---|---|---|
|消息描述|频谱检测配置消息|||||
|方向|TracerMatrix \> C2|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|NTPParaConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||set\_mode|Uint32|请求类型:<br>1: 查询成功<br>2: 更新成功<br><br>错误码 \> 255 <br>256：不支持的请求类型<br>257:  查询失败<br>258：更新失败|1\-2|
|||ntp\_enable|Uint32|NTP服务器设置<br>0：使用上位机授时（为0是，以下NTP设置设备端不响应，只保存）（ 使用该选项，设备端将使用  0x0014 在建立连接的时候，求情上位机授时） <br>1：使用NTP服务<br>2：手动设置时间<br>3：chrony 授时||
|||ntp\_default|Uint32|NTP恢复默认使能，NTP服务器地址恢复默认地址<br>0：使用以下设置值<br>1：恢复默认||
|||ntp\_time\_zone|Int32<br>|NTP时区设置（0:UTC 时间 8 东八区 \-8 西八区）<br>||
|||ntp\_server\_addr|char\*512|NTP服务器地址/chrony服务器地址<br>||
|||time|Char\*20|字符串：年月日时分秒\.毫秒（例20240515011746\.901）||

### 1\.5\.6 0x004A C2\(上位机）回传DroneID解密结果\(0x004A\)

#### 回传DroneID解密结果消息

|消息ID|0x004A||||
|---|---|---|---|---|
|消息描述|C2上位机回传DroneID解密结果，使用json字符串||||
|方向|C2 \> TracerMatirx||||
|发送频率|发送者触发||||
|PB 结构名称|不是用PB，协议字段和原始保持一致||||
|参数payload|字节|Name|Type|Description|
||8<br>|uniqueId|uint64\_t|唯一标识（填充0xDA上报的值）|
||4<br>|result|uint32\_t|C2解密结果：<br>0:成功；<br>其他：失败|
||4|jsonLen<br>|uint32\_t|json字符串长度N|
||1\*N|json|char\[N\]|json字符串|
|参数长度|16\+N||||
|应答|有||||

#### 回传DroneID解密结果应答

|消息ID|0x004A||||
|---|---|---|---|---|
|消息描述|结果应答||||
|方向|Tracer  \> C2 \(上位机\)||||
|发送频率|根据请求触发||||
|PB 结构名称|不是用PB，协议字段和原始保持一致||||
|参数payload|字节|Name|Type|Description|
||1<br>|status|uint8\_t<br>|0：失败<br>1：成功|
|参数长度|1 ||||



## 1\.6 数据导入和导出0x005x

### 1\.6\.1  0x0050 数据导入和导出请求

#### 数据导入和导出请求消息

|消息ID|0x0050|||||
|---|---|---|---|---|---|
|消息描述|数据导入和导出请求消息|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|DataRequestConfig|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||data\_id|Uint32|数据ID，由C2（上位机）生成||
|||direction|Uint32|数据方向<br>1: 上位机 到 TracerMatrix 导入<br>2：TracerMatrix 到 上位机 导出||
|||data\_type|Uint32|数据类型<br>1：RF侦测频段配置（只有导入功能）<br>2:  RF侦测机型库（只有导入功能）<br>3：RF过滤管理（只有导入功能）<br>4：WIFI过滤管理（只有导入功能）<br>5：频谱记录数据（只有导出功能）||
|||data\_size|Uint32|文件总大小（单位字节）<br>导入：导入文件大小<br>导出: 0||
|||file\_name<br>|Char\*32<br>|数据名称<br>data\_type：频谱记录数据时：为频谱列表中的文件名称<br>其他数据类型可为空||

#### 数据导入和导出求情应答

|消息ID|0x0050|||||
|---|---|---|---|---|---|
|消息描述|数据导入和导出请求消息|||||
|方向|TracerMatrix \> C2|||||
|发送频率|由发送方控制,间隔时间不低于100ms|||||
|PB 结构名称|DataRequestResponse|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||data\_id|Uint32|数据ID，由C2（上位机）生成||
|||data\_size|Uint32|文件总大小（单位字节）<br>导入：成功时，和求情文件大小一致，失败时为0<br>导出：导出文件大小||
|||response\_status|Uin32<br>|0：成功<br>1:  格式校验未通过<br>2：文件错误或数据不存在<br>3:  空间不足||
|||erroe\_str|Char\*32|错误信息||

### 1\.6\.2 0x0051 数据导入 

#### 数据导入数据消息

|消息ID|0x0051|||||
|---|---|---|---|---|---|
|消息描述|数据导入数据消息<br>1. 每次发送数据不超过 4096 个字节；<br>2. 发送端接收到 ack\_offset， status 为成功之后发送下一条；其他情况重发；（重发三次）|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制|||||
|PB 结构名称|不使用PB沿用|||||
|参数payload|字节|Name|Type|Description|数值范围|
||32|fileName|char\[32\]|文件名称||
||4|fileSize|uint32\_t|文件总大小（字节数）||
||4|sendOffset|uint32\_t|当前偏移位置||
||4|sendLength|uint32\_t|数据长度N||
||N|sendData\[N\]|uint8\_t\[N\]|文件数据流，最大4096字节||

#### 数据导入数据应答

|消息ID|0x0051|||||
|---|---|---|---|---|---|
|消息描述|数据导入数据应答<br>1. 接收数据校验成功, status为0<br>2. 其他情况回复错误<br>3. 处理对端的重复的情况，正常回复，本地做数据去重|||||
|方向|TracerMatrix \> C2|||||
|发送频率|由发送方控制|||||
|PB 结构名称|历史消息，不使用PB，沿用Tracer的协议|||||
|参数payload|字节|Name|Type|Description|数值范围|
||1<br>|status<br>|uint8\_t|Status值：<br>0：成功<br>1：接收出错<br>2：校验失败<br>10：状态错误<br>其他错误||
||4|ack\_offset|uint32\_t|最新确认的文件偏移||

### 1\.6\.3 0x0052 数据导出 

#### 数据导出数据消息

|消息ID|0x0052|||||
|---|---|---|---|---|---|
|消息描述|数据导出数据消息<br>1. 每次发送数据不超过 4096 个字节；<br>2. 发送端接收到 ack\_offset， status 为成功之后发送下一条；其他情况重发；（重发三次）|||||
|方向|TracerMatrix \> C2|||||
|发送频率|由发送方控制|||||
|PB 结构名称|历史消息，不使用PB，沿用Tracer的协议|||||
|参数payload|字节|Name|Type|Description|数值范围|
||32|fileName|char\[32\]|文件名称||
||4|fileSize|uint32\_t|文件总大小（字节数）||
||4|sendOffset|uint32\_t|当前偏移位置||
||4|sendLength|uint32\_t|数据长度N||
||N|sendData\[N\]|uint8\_t\[N\]|文件数据流，最大4096字节||

#### 数据导出数据应答

|消息ID|0x0052|||||
|---|---|---|---|---|---|
|消息描述|数据导出数据应答<br>1. 接收数据校验成功, status为0<br>2. 其他情况回复错误<br>3. 处理对端的重复的情况，正常回复，本地做数据去重|||||
|方向|C2 \> TracerMatrix|||||
|发送频率|由发送方控制|||||
|PB 结构名称|历史消息，不使用PB，沿用Tracer的协议|||||
|参数payload|字节|Name|Type|Description|数值范围|
||1|status<br>|uint8\_t|Status值：<br>0：成功<br>1：接收出错<br>2：校验失败<br>10：状态错误<br>其他错误||
||4|ack\_offset|uint32\_t|最新确认的文件偏移||

## 1\.7 目标处置

### 1\.7\.1 0x0060 RF目标频率跟踪指令

|消息ID|0x0060|||||
|---|---|---|---|---|---|
|消息描述|发送RF目标频率跟踪指令|||||
|方向|C2 \> TracerMatrix  |||||
|发送频率|跟随请求方回复|||||
|PB 结构名称|SPTargetsResponse|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode|Uint32|请求类型:<br>1: 设置<br>2：查询||
|||track\_num|Uint32|跟踪目标个数（最大128）<br>|1\-4<br>（协议支持到4个）<br>|
|||track\_target\_list|SPTarget|跟踪频谱目标数据结构体, 数量0\-128|（当前要跟踪的结构体列表）|

设置的应答

|消息ID|0x0060|||||
|---|---|---|---|---|---|
|消息描述|RF目标频率跟踪指令应答|||||
|方向|TracerMatrix \>  C2 |||||
|发送频率|跟随请求方回复|||||
|PB 结构名称|SPTargetsResponse|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode|Uint32|请求类型:<br>1: 设置<br>2：查询||
|||track\_num|Uint32|跟踪目标个数（1\-4）<br>|1\-4<br>（协议支持到4个）<br>|
|||track\_status|uint32|Status值：<br>0：成功<br>1：接收出错<br>2：校验失败<br>10：状态错误<br>其他错误|（当前要跟踪的结构体列表）|

查询的应答

|消息ID|0x0060|||||
|---|---|---|---|---|---|
|消息描述|RF目标频率跟踪指令应答|||||
|方向|TracerMatrix \>  C2 |||||
|发送频率|跟随请求方回复|||||
|PB 结构名称|SPTargetsResponse|||||
|参数payload|字节|Name|Type|Description|数值范围|
|||request\_mode|Uint32|请求类型:<br>1: 设置<br>2：查询||
|||track\_num|Uint32|跟踪目标个数（最大128）<br>|1\-4<br>（协议支持到4个）<br>|
|||track\_target\_list|SPTarget|跟踪频谱目标数据结构体, 数量0\-128|（当前要跟踪的结构体列表）|

## 1\.8 OTA升级 （升级命令字同sentry）

### 1\.8\.1 固件升级请求指令 \(0xF1\)

|消息ID|0xF1||||
|---|---|---|---|---|
|消息描述|下发固件升级请求<br>下发0xF1 的升级指令（cmd=1、2）：请求一次，返回1次结果，<br>并且后续开始主动上报0xF2升级状态，升级结束后停止上报0xF2；||||
|方向|上位机  \-\> 设备||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||1<br>|cmd|uint8\_t|升级命令选项：<br>1：全量升级（升级综合软件包，主设备或多个子设备整体升级）<br>2：单设备升级（升级设备原始软件包，指定升级某个在线设备，指定device\_type、device\_sn）<br>3：版本回退：指定单设备回退到上一版本（暂时仅主设备支持）<br>4：版本回退：指定单设备恢复出厂软件版本（暂时仅主设备支持）|
||256<br>|url<br>|char\[\]|软件包 url：<br>http:// （远程服务器文件）<br>ftp:// （远程服务器文件）<br>file:// （系统本地文件）|
||1|authorization|uint8\_t|0\-无需验证，1\-需要验证用户名密码|
||32|username|char\[\]|用户名，authorization为1时必填|
||32|password|char\[\]|密码，authorization为1时必填|
||4|package\_size|uint32\_t|软件包大小（字节）可选，0无效|
||4<br>|device\_type<br>|uint32\_t|设备类型枚举，<br>参照附录A：子设备类型，<br>0为主设备，<br>其它表示子设备（子设备内也包含雷视设备，因为可能存在雷视设备级联）<br>下发指令，命令类型为2、3、4 时有效|
||32|device\_sn|char\[\]|设备SN，<br>主设备升级为空，子设备升级必填<br>下发指令，命令类型为2、3、4 时有效|
||80|reserve|uint8\_t\[\]|保留字段|
|参数长度|||||
|应答|有||||

上报应答

|消息ID|0xF1||||
|---|---|---|---|---|
|消息描述|应答||||
|方向|设备  \-\> 上位机||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||4|result<br>|uint32\_t|0：请求成功<br>1：请求失败，未知原因<br>2：请求失败，系统处于升级中|
||32|reserve|uint8\_t\[\]|保留字段|
|参数长度|||||
|应答|||||

### 1\.8\.2 固件升级状态查询指令 \(0xF2\)

下发请求

|消息ID|0xF2||||
|---|---|---|---|---|
|消息描述|下发固件升级状态查询请求||||
|方向|上位机  \-\> 设备||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||32|reserve|uint8\_t\[\]|保留字段|
|参数长度|||||
|应答|有||||

上报应答/主动上报

|消息ID|0xF2||||
|---|---|---|---|---|
|消息描述|主动查询应答：下发一次返回一次<br>主动上报：下发0xF1 开始升级后，此应答会开始主动上报0xF2，升级结束后停止上报0xF2||||
|方向|设备  \-\> 上位机||||
|发送频率|用户触发||||
|参数payload|字节|Name|Type|Description|
||4|result<br>|uint32\_t|0：请求成功<br>1：请求失败，未知原因|
||1<br>|type|uint8\_t|当前升级类型：<br>0：空闲（未升级）<br>1：全量升级中<br>2：单设备升级中|
||4<br>|status\_code<br>|uint32\_t|总升级状态结果<br>0：空闲结束<br>1：等待中 （任务准备/排队等待）<br>2：下载中<br>3：解压中<br>4：校验中<br>5：写入固件中<br>\.\.\.<br>9：升级成功<br>10：准备重启<br><br>100：升级失败，未知原因<br>101：升级失败，系统存储空间不足<br>102：升级失败，下载软件包失败<br>103：升级失败，解压失败<br>104：升级失败，校验失败<br>105：升级失败，写入固件失败<br>106：升级失败，切换分区失败<br>107：升级失败，重启失败<br>108：升级失败，整体超时|
||1|progress|uint8\_t|总升级进度：0\~100|
||32|reserve|uint8\_t\[\]|保留字段|
||1|num|uint8\_t|当前升级的所有子模块/子设备数量|
||设备列表 详细进度||||
||4|status\_code|uint32\_t|升级状态结果，同上|
||1|progress|uint8\_t|升级进度：0\~100|
||4<br>|device\_type<br>|uint32\_t|设备类型枚举<br>参照附录A：子设备类型，<br>0为主设备，其它表示子设备|
||32|device\_sn|char\[\]|设备SN<br>主设备升级为空，子设备升级必填|
||64|version|char\[\]|设备当前版本号|
||32|reserve|uint8\_t\[\]|保留字段|
|参数长度|||||
|应答|||||

# 附录

## 相关文档

[Tracer Matrix 嵌入式软件架构设计（4\+1 视图）](https://vxr5wm8r80r.feishu.cn/wiki/ONuiwaQExibvZhkQcuBcNsFunXz)

[Tracer Matrix边端\&云端上线PRD V1\.0 0104](https://vxr5wm8r80r.feishu.cn/wiki/DH2TwkWvlin1KekHhzWchRsFn5g) 

[TracerMatrix 嵌入式协议\(接口\)汇总（C2 Spotter 天盾 Sapient 算法 STA200）](https://vxr5wm8r80r.feishu.cn/wiki/J3iAws7XbiOroskDHgOcmFpCn1f)

