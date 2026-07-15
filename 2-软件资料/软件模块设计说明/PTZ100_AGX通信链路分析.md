## PTZ100_AGX 通信链路分析（C2 ↔ AGX ↔ 设备）

> **文档版本**: V1.0  
> **适用工程**: `ptz100_agx`  
> **关注范围**: C2 与 AGX（含 SFL200/Sentry）之间通信、以及 AGX 与各子设备之间通信

---

## 一、整体概览

- **上行链路（设备 → AGX → C2）**：
  - 设备通过 UDP 组网协议（`netcon_protocol`）发现 AGX；
  - 建立 TCP 或 UDP 连接；
  - 在连接上跑私有协议：`alink`（雷达/哨兵/TracerP 等）或 PTZ 专用协议；
  - AGX 侧根据配置（含 SFL200 在线状态）决定是“直接上传给 C2”，还是“先上报给 SFL200 再透传给 C2”。

- **下行链路（C2 → AGX → 设备）**：
  - C2 与 AGX 间使用 UDP 组网 + TCP/`alink`；
  - C2 下发 `alink` 指令（包含目标设备 SN / 设备类型 / 消息 ID）；
  - AGX 根据 SN/设备类型查表寻找具体设备连接（TCP/UDP/ROS），并进行协议级转发或转换。

---

## 二、C2 ↔ AGX(Sentry) 通信机制

### 2.1 角色与 IP/端口配置

- AGX 默认以 **TCP Client** 身份连接 C2：

```12:22:src/srv/eth_link/eth_link.h
#define DEFAULT_AGX_ACCESS_IP	"192.168.2.163"
#define DEFAULT_AGX_ACCESS_PORT	 19005
#define AGX_DEFAULT_IP "192.168.1.161"
#define AGX_DEFAULT_PORT_HEAD 18070
```

- 的确可以通过 UDP 组网流程改变这对 IP/端口（见调试时的 `0xBC` 请求连接逻辑），但“默认直连”是 `192.168.2.163:19005`。

### 2.2 UDP 组网：LOOKUP / LOOKUP_RESP / REQUEST_CONNECT

上位机 C2 和 AGX 之间通过 `netcon_protocol` 做自动发现和连接协商，核心消息：

```11:24:src/srv/eth_link/eth_protocol/netcon_protocol.h
#define NETPROTOCAL_MSG_ID_LOOKUP           0xBA  // 搜索
#define NETPROTOCAL_MSG_ID_LOOKUP_RESP      0xBB  // 搜索结果
#define NETPROTOCAL_MSG_ID_REQUEST_CONNECT  0xBC  // 请求建立 TCP 连接
#define NETPROTOCAL_MSG_ID_CONFIG_RESP      0xBD
```

AGX 侧用于 C2 发现的 UDP 套接字配置（客户端身份）：

```38:50:src/srv/eth_link/eth_link.c
static udp_socket_cfg_t sUdpCfg = 
{
  .bFlagRecv	= true,
  .bBroadcast	= true,
  .bNetCard = true,
  .netcard = NETWORK_NETCARD_NAME,
  .wRecvPort	= 1800,
  .uRecvIp	= INADDR_ANY,
  .wSendPort	= 1810,
  .uSendIp	= 0xFFFFFFFF,
};
```

- 收 `1800`，发 `1810`（C2 侧实现需对称）。
- `eth_protocol_handler()` 负责解析 UDP 报文，区分：
  - `0xBA`：`eth_protocol_search_handler()`；
  - `0xBC`：`eth_protocol_cntinfo_handler()`，根据 SN 判断是连 C2 还是连 SFL200。

### 2.3 C2 请求连接逻辑（0xBC）

当 C2 通过 `0xBC` 下发连接参数（包含 ip/port/sn/type）时，AGX 根据 SN 判断“自己当前应该扮演谁”：

```835:869:src/srv/eth_link/eth_link.c
if(psCntInfo->sn[0]) {
    char *sfl200_sn = eth_protocol_get_sn(PTZ100_SENTRY_SN_PREFIX);
    char *agx_sn    = eth_protocol_get_sn(PTZ100_AGX_SN_PREFIX);

    if (0 == strcmp(sfl200_sn, psCntInfo->sn)) {
        user_info.dev_type = ALINK_MONIT_C2_ID_SFL200;
        eth_link_create_socket(psCntInfo->type, htonl(psCntInfo->ip), psCntInfo->port, &user_info);
    } else if (0 == strcmp(agx_sn, psCntInfo->sn)) {
        user_info.dev_type = ALINK_DEV_ID_C2;
        eth_link_create_socket(psCntInfo->type, htonl(psCntInfo->ip), psCntInfo->port, &user_info);
    }
}
```

- SN 匹配 `AGX_SN` → 走 “AGX 直接连 C2” 模式；
- SN 匹配 `SENTRY_SN` → 走 “AGX 以 SFL200/Sentry 身份连 C2（代理 SRP）” 模式。

`eth_link_create_socket()` 最终会创建 TCP client，并通过回调 `c2_network_create()` 交给 `c2_network` 模块。

### 2.4 TCP 上的协议：alink

TCP 建链完成后，`c2_network_cbk_data()` 负责从 socket 读取完整的 alink 结构包，并交给 `alink_socket_task()`：

```391:459:src/app/c2_network/c2_network.cpp
int c2_network_cbk_data(..., eth_link_socket_dev_info_t* sockeid, int32_t (*pi_recv)(...))
{
    // 读取并组装完整 alink 包（根据 magic/len/head/crc 判断包长）
    integrity_pkg_len = alink_package_integrity_check(abyBuffer, iLength, protoco_version);
    // ...
    sImport.ePortId	    = sockeid->sock_id;
    sImport.protocol_type = protoco_version;
    sImport.pbyData	    = pabybuf;
    sImport.uLength	    = integrity_pkg_len;
    sImport.handle	    = psNetwork->psUser->psSocket;
    sImport.handle2	    = (void *)psNetwork;
    sImport.pe_send	    = psNetwork->psUser->pi_send;

    if (is_sfl200_online) {
        alink_socket_task( &psNetwork->sAlinkSocket_sfl200, &sImport );
    } else {
        alink_socket_task( &psNetwork->sAlinkSocket, &sImport );
    }
}
```

`alink_socket_task()` 会调用 `alink_recv_task()` → `alink_order_task()` 完成：
- magic / head / crc 校验；
- 按 `msgid` 分发到对应的 command handler（System/Target/Track/…）；
- 若注册了 `pv_origin_payload_output`，则允许用户代码截取“原始包”做透传/代理。

---

## 三、两种 C2 ↔ AGX 拓扑模式

### 3.1 模式一：AGX 直接作为 SRP/AGX 身份连 C2

- C2 发 `0xBC` 时 SN 匹配 `eth_protocol_get_sn(PTZ100_AGX_SN_PREFIX)`；
- `eth_link_create_socket()` 创建的是 `dev_type = ALINK_DEV_ID_C2`；
- `c2_network_create()` 中只初始化 `sAlinkSocket`，并用 `c2_network_send()` 直接发给 C2。

```761:779:src/app/c2_network/c2_network.cpp
if (psUser->link_user_info.dev_type == ALINK_DEV_ID_C2) {
    alink_connect_port(&psNetwork->sAlinkSocket, NULL, ALINK_DEV_ID_C2);
    alink_connect_send_agx_srp(psNetwork, psUser, c2_network_send);  // agx直接发送到c2
}
```

此模式下，SRP/AGX 的所有上报（雷达/融合/AI/PTZ/设备列表/心跳等）都由 AGX 直接打包为 `ALINK_DEV_ID_C2` 目的端的 alink 包，发给 C2。

### 3.2 模式二：AGX 作为 SFL200/Sentry 的子设备，由 SFL200 代理上报

当 `get_sfl200_online_status()` 为 true 时：
- C2 发 `0xBC` 时 SN 匹配 `PTZ100_SENTRY_SN_PREFIX`；
- `eth_link_create_socket()` 选择 `dev_type = ALINK_MONIT_C2_ID_SFL200`；
- `c2_network_create()` 中除了 `sAlinkSocket` 之外，还会多初始化一个 `sAlinkSocket_sfl200`，用来解析 SFL200 专属的 alink 流。

关键是 **0xFD 透传链路**：

1. **AGX 内部 SRP 报文 → 封成 0xFD 透传给 C2**：

```111:147:src/app/c2_network/c2_network.cpp
// sfl200将agx内部SRP雷视原始报文 封装成新的0xfd转发协议
static int32_t sfl200_package_0xfd_agx_srp(uint8_t *data, uint32_t dataLen, uint8_t *buf, uint32_t bufSize)
{
    alink_transfer_package_t payload{};
    snprintf((char *)payload.sn, sizeof(payload.sn), "%s", agx_sn); // AGX SN
    payload.protocol = 5;
    payload.cmdlen = dataLen;
    memcpy(payload.transfer_package, data, dataLen);
    // 外层再封装成 msgid=0xFD 的 alink V1 包，destid=C2, sourceid=SFL200/SFL210
    int32_t len = alinkV1_package_encode(0xFD, 0, 0, ALINK_DEV_ID_C2, sfl_device_type, (uint8_t *)&payload, payloadLen, buf, bufSize);
    return len;
}
```

2. **0xFD 转发具体实现**：

```149:168:src/app/c2_network/c2_network.cpp
// sfl200的0xfd指令透传agx的srp雷视数据
static int32_t c2_network_send_agx_srp_by_sfl200_0xfd( void* handle, uint8_t *pbyData, uint32_t uLen )
{
    uint8_t buf[64 * 1024] = {0};
    int32_t len = sfl200_package_0xfd_agx_srp(pbyData, uLen, buf, sizeof(buf));
    eth_link_user_t *psUser = (eth_link_user_t*)handle;
    return psUser->pi_send( psUser->psSocket, buf, len );
}
```

3. **SFL200 收到 0xFD 后 → 解出 `sn+protocol+cmd` → 按 SN 转发给子设备**：  
见 `sfl200_origin_payload_data()` 中对 `byCmd == 0xFD` 的处理逻辑：

```135:185:src/app/sfl200_app/sfl200_app.cpp
// 0xfd 透传子设备原始消息
if (0xfd == byCmd) {
    alink_transfer_package_t *package = (alink_transfer_package_t *)payload->pbyData;
    if (8 == package->protocol) { // svh100
        alink_transfer_c2_2_svh100((void *)package, devinfo.dev_id);
    } else if (9 == package->protocol) { // stp120
        alink_transfer_c2_2_stp120((void *)package, devinfo.dev_id);
    } else if (5 == package->protocol) { // 送到AGX内部SRP雷视
        sfl200TransPackageToAgxSrp(handle2, package->transfer_package, package->cmdlen);
    }
    return 1; // 表示本进程不再回包，已自行处理
}
```

因此，在 “AGX 挂在 SFL200 下” 的拓扑里：
- C2 只看见一条与 SFL200 的 alink 流（含 `msgid=0xFD` 的“打包转发”帧）；
- SRP/AGX 与子设备的真实交互，被当作原始 payload 嵌进 `alink_transfer_package_t`，再经 SFL200 转发。

---

## 四、AGX(Sentry) ↔ 子设备 通信机制

### 4.1 通过 eth_link_server 管理的以太网子设备

包括：**雷达（V1/V2）、SFL100（旧名 sentry）、STP120、SVH100、TracerP 等**。  
统一模式：

1. **AGX 周期性发送 UDP 探测（0xBA）**：

```139:177:src/srv/eth_link/eth_link_server.c
while(!dt_obj->exit_relase) {
    // keep sentry online heartbeat（略）
    plen = eth_protocol_get_detect_package(..., SKYFEND_PROTOCOL_TYPE_V1);
    udp_socket_send(dt_obj->sever_socket, (uint8_t *)&ep_lookup_package, plen);
    plen = eth_protocol_get_detect_package(..., SKYFEND_PROTOCOL_TYPE_V2);
    udp_socket_send(dt_obj->sever_socket, (uint8_t *)&ep_lookup_package, plen);
    sleep(dt_obj->detect_frequence); // 默认 2 秒
}
```

2. **设备回应 LOOKUP_RESP（0xBB）** → `eth_protocol_search_handler()` 决定是否接受该设备：

```945:962:src/srv/eth_link/eth_link_server.c
if(psdev->type != ALINK_DEV_ID_RADAR 
   && psdev->type != ALINK_DEV_ID_SFL100 
   && psdev->type != ALINK_DEV_ID_STP120 
   && psdev->type != ALINK_DEV_ID_TRACERP
   && psdev->type != ALINK_DEV_ID_SVH100) {
    return; // 只接受这几类设备
}
if(psdev->type == ALINK_DEV_ID_RADAR && psdev->protocol == SKYFEND_PROTOCOL_TYPE_V2) {
    psdev->type = ALINK_DEV_ID_RADAR_V2;
}
```

3. **AGX 为每个设备类型创建 TCP Server 并要求其连接（0xBC）**：

```965:993:src/srv/eth_link/eth_link_server.c
int ret = eth_link_create_server(psdev->type, psdev->protocol, (char*)psdev->sn, uIp);
// ...
ep_ctlinfo.ip   = psEthList->server_ip;      // AGX ip
ep_ctlinfo.port = psEthList->cur_con;       // 动态分配的 TCP 端口（从 18070 开始）
ret = eth_protocol_get_request_package((void*)buffer, &ep_ctlinfo);
udp_socket_send(&sUdpSocket, (uint8_t *)buffer, ret); // 发 0xBC
```

4. **设备连上来后，由 `radar_network` 接管该连接**：

```593:597:src/app/radars_network/radar_network.cpp
int32_t radar_network_init(void)
{
    ros_app::ros_register_subscribe_cbk(ROS_DHP100_DATA, radar_dhp100_ckb_handle);
    return eth_server_register(RTH_LINK_NET_TCP_CLIENT, radar_network_create);
}
```

`radar_network_create()` 根据 `dev_type` 决定接入方式，并为雷达/SFL100/STP120/SVH100/TracerP 注册各自的 `origin_payload` 透传回调：

```472:587:src/app/radars_network/radar_network.cpp
if(psUser->link_user_info.dev_type == ALINK_DEV_ID_RADAR) {
    alink_connect_port(&psNetwork->sAlinkSocket, NULL, ALINK_DEV_ID_RADAR);
    // 注册雷达V1的 origin_payload 回调，用于将部分命令原始透传给 C2
    alink_connect_send(..., 0x1E, ALINK_DEV_ID_RADAR, psUser, radar_network_send);
    alink_order_payload_op_register(ALINK_DEV_ID_RADAR, radar_v1_origin_payload_data);
}
else if(psUser->link_user_info.dev_type == ALINK_DEV_ID_SFL100 ) {
    alink_connect_port(&psNetwork->sAlinkSocket, NULL, ALINK_DEV_ID_SFL100);
    alink_connect_send(..., 0x25, ALINK_DEV_ID_SFL100, psUser, radar_network_send);
    alink_connect_send(..., ALINK_MSGID_TRANSFER_CMD, ALINK_DEV_ID_SFL100, psUser, radar_network_send);
    alink_order_payload_op_register(ALINK_DEV_ID_SFL100, sentry_origin_payload_data);
}
// SVH100/STP120/TracerP/RADAR_V2 同理，分别注册自己的 origin_payload 回调
```

5. **雷达 / SFL100 / STP120 / SVH100 / TracerP 对 C2 的透传逻辑**：

- 以雷达 V1 为例：

```84:101:src/app/radars_network/radar_network.cpp
static int32_t radar_v1_origin_payload_data(alink_payload_t *payload, void *data, uint8_t byCmd, void *handle2)
{
    // 只对 radar_v1_transfer_commands 白名单中的 msgid 做透传
    radar_packages_transfer(payload->ePortId, data, payload->wLength + ALINK_V1_NO_PAYLOAD_SIZE);
    return 1; // 返回1表示已处理，不再由 alink_order_send 回包
}
```

- `radar_packages_transfer()` 通过 SN 找到该设备在 C2 侧的逻辑 ID，并使用 `alink_transfer_device_2_c2()` 把整个原始包嵌入 `alink_transfer_package_t` 上传：

```60:81:src/app/radars_network/radar_network.cpp
eth_link_device_info_t devinfo{};
alink_transfer_package_t pack{};
find_device_info_by_devid(&devinfo, dev_id);
pack.cmdlen   = data_len;
pack.protocol = devinfo.protocol_type;
snprintf(pack.sn, sizeof(pack.sn), "%s", devinfo.dev_sn);
memcpy(pack.transfer_package, data, pack.cmdlen);
alink_transfer_device_2_c2(&pack);
```

### 4.2 PTZ（云台）通信：UDP + PTZ 专用协议 + RTSP

PTZ 采用的是**独立的 UDP 协议**（非 alink）：

1. **控制/状态端口**：

```230:237:src/srv/eth_link/eth_link_ptz.cpp
pdata_ctrl.ptz_object_content.sUdpCfg.uSendIp 	= inet_addr(PTZ_DEFAULT_IP); // "192.168.2.4"
pdata_ctrl.ptz_object_content.sUdpCfg.wRecvPort	= 9966;
pdata_ctrl.ptz_object_content.sUdpCfg.wSendPort	= 9966;
```

2. **封包/解包协议**：`ptz_control_protocol.c` / `ptz_control.c`  
   - `ptz_protocol_package()`：封装为 `head + len + cmd + timestamp + payload + seq + crc + stopbit`；
   - `ptz_protocol_network_data_analysis()`：解析 UDP 帧，得到 `command + msglen + msg` 等。

3. **AGX 发送 PTZ 控制指令**：上层调用 `send_ptz_control_*()`，最终走 `send_ptz_package()` → UDP：

```18:41:src/srv/eth_link/ptz_protocol/ptz_control.c
int send_ptz_control_addr(ptz_msgid_0x03_addr_t *addr_t)
{
  // 填充时间戳等
  msginfo.command = PTZ_COMMAND_ADDR;
  msginfo.msglen  = sizeof(ptz_msgid_0x03_addr_t);
  ret = send_ptz_package(&msginfo);
}
```

```308:321:src/srv/eth_link/eth_link_ptz.cpp
int send_ptz_package(ptz_protocol_msg_t *msginfo)
{
    uint8_t pac[PTZ_PACKAGE_MAX_LEN] = {0};
    retlen = ptz_protocol_package(msginfo->command, msginfo->msg, msginfo->msglen, pac);
    udp_socket_send(&pdata_ctrl.ptz_object_content.sUdpSocket, pac, retlen);
    // 同时可以回调给上层做“原始数据上报给 ROS/C2”
}
```

4. **AGX 接收 PTZ 状态 / 目标**：

```94:118:src/srv/eth_link/eth_link_ptz.cpp
static void eth_protocol_handler( void* msg, uint32_t len, uint32_t devid )
{
    ptz_protocol_msg_t lmsg = {0};
    ptz_protocol_network_data_analysis((uint8_t*)msg, len, &lmsg);
    lmsg.devid = devid;
    if(pdata_ctrl.ptz_list_obj && pdata_ctrl.ptz_list_obj[lmsg.command].cbk) {
        pdata_ctrl.ptz_list_obj[lmsg.command].cbk(&lmsg);
    }
    if(pdata_ctrl.send_ori_data_callback) {
        pdata_ctrl.send_ori_data_callback(lmsg.msg, lmsg.command, lmsg.msglen, PTZ_ORI_DATA_TYPE_STATUS);
    }
}
```

`app/ptz/ptz_app.cpp` 中注册了这些命令回调，并把 **原始 PTZ 数据转成 ROS topic**：

```503:515:src/app/ptz/ptz_app.cpp
ros_app::ros_register_subscribe_cbk(ROS_PTZ_CTL_DATA, ptz_packet_ckb_handle);
eth_ptz_ori_data_register(ptz_data_2_ros_data);
eth_ptz_command_register(PTZ_COMMAND_DEV_STATUS,          ptz_dev_status);
eth_ptz_command_register(PTZ_COMMAND_TARGET_INFO,         ptz_target_info);
eth_ptz_command_register(PTZ_COMMAND_ATT_MSG,             ptz_pitch_azimuth);
eth_ptz_command_register(PTZ_COMMAND_DEV_EXT_INFO,        ptz_dev_ext_info_0x08);
eth_ptz_command_register(PTZ_COMMAND_LENSE_EXT_INFO,      ptz_lense_ext_info_0x0c);
eth_ptz_command_register(PTZ_COMMAND_SYS_EXT_INFO,        ptz_sys_ext_info_0x15);
eth_ptz_command_register(PTZ_COMMAND_TRAGET_MISSING_QS,   ptz_target_missing_qs_msg);
```

5. **PTZ 视频流**：  
   - PTZ 原始 RTSP 通常是设备自带（例如 `rtsp://192.168.2.4/...`）；
   - AGX 内部会再将图像通过 GStreamer 处理并写入 `ShmTransferFrame`（与 `alg_app` 共享内存）；
   - 同时也在本地 `9554` 端口提供二次 RTSP 输出（见 `get_ptz_dev_info()` 生成的 URL）。

### 4.3 SFL200/SFL210 与各子设备：二层网关角色

当 SFL200/SFL210 在线时：
- 它既作为 **C2 眼中的一个设备**（AGX 把自己身份隐藏在其后）；
- 又作为 **AGX 眼中的“下级网关”**，管理 BPH110 激光、SRP200/210/230、SVH100、STP120 等子设备。

数据通路典型模式：

- **子设备 → SFL200 → C2**：设备到 AGX 的数据有一部分会被打包为 `alink_sentry_transfer_package_t`，通过 `alink_transfer_sfl200_to_c2()` 上报给 C2；
- **C2 → SFL200 → 子设备**：C2 下发 `0xFD`（或 `0xF0`等）命令给 SFL200，SFL200 根据 `sn` 和 `protocol` 在本地子设备表中查找具体设备，并转发原始包。

典型代码入口：
- `app/sfl200_app/sfl200_app.cpp`：`sfl200_origin_payload_data()`、`sentry_origin_payload_data()`、`svh100_origin_payload_data()`、`stp120_origin_payload_data()`；
- `src/inc/sfl200.h`：`sfl200_message_t`、`sfl200AlinkHead0xF0_t` 及一系列 0xF0 子消息结构体定义。

### 4.4 其他通过 ROS 接入的设备（GNSS、电子围栏、干扰机等）

这些设备大多：
- 驱动层在 `ros_ws/src/*` 下实现（如 `gnss_b3`、`electronic_fence`、`spoofer` 等）；
- AGX 主程序通过 `ros_app` 订阅其 ROS Topic，随后用 `alink_upload_*` 上报 C2；
- C2 的控制指令由 `srv/alink/command/*` 模块接收后，转换为相应 ROS Topic 下发给驱动节点。

这类链路的“物理协议”取决于各自驱动实现（串口/以太网/MQTT 等），在本工程中主要关心的是 **“ROS ↔ alink ↔ C2” 的逻辑桥接关系**。

---

## 五、调试 / 排查建议

- **C2 ↔ AGX 组网阶段**：
  - 抓 UDP `1800/1810`，确认是否有 `0xBA/0xBB/0xBC` 往来；
  - 对照 `eth_link.c` / `eth_protocol_handler()` 日志，看是否正确识别 SN 并创建 TCP client。

- **C2 ↔ AGX 数据阶段**：
  - 抓 TCP `19005`（或 C2 下发的 port），确认 alink 帧完整性（magic/长度/CRC）；
  - 关注 `c2_network_cbk_data()` 是否报 `iLength <= 0` 或 `alink_package_integrity_check()` 返回异常。

- **AGX ↔ 雷达/SFL100/STP120/SVH100/TracerP**：
  - 抓 UDP `1800/1810`（设备口），看设备是否回应 LOOKUP_RESP（0xBB），以及 AGX 是否回 REQUEST_CONNECT（0xBC）；
  - 抓对应的 TCP 端口（从 18070 起），对照 `radar_network_cbk_connect()` / `radar_network_cbk_data()` 日志；
  - 确认 `alink_order_payload_op_register()` 是否注册成功（用于 0xFD/0xFE 透传）。

- **PTZ**：
  - 抓 UDP `9966`，确认控制/状态帧收发是否正常；
  - 抓 RTSP `9554`（AGX 本地推流）和 PTZ 原始 RTSP，看视频是否连通。

- **SFL200 模式切换**：
  - 检查 SQLite `dev_cfg` 表里 SFL200/SFL210 的 `online` 字段；
  - 对照 `get_sfl200_online_status()` / `get_sfl210_online_status()` 是否如预期；
  - 注意部分代码用 `static bool is_sfl200_online = get_sfl200_online_status();` 缓存，只在进程启动时评估一次。

---

## 六、小结

- **C2 ↔ AGX**：基于 `netcon_protocol` 的 UDP 自动组网（0xBA/0xBB/0xBC），TCP 之上跑 `alink`（V1/V2），支持“AGX 直连”和“经 SFL200 代理”两种模式；
- **AGX ↔ 子设备**：以太网设备统一走 `eth_link_server + radar_network + alink`，PTZ 走 UDP + 自定义协议 + RTSP，其他设备多通过 ROS 接入；
- **透传机制**：大量使用 `0xFD` + `alink_transfer_package_t(sn+protocol+cmdlen+payload)` 做“C2 ↔ 子设备”原始报文透传，AGX/SFL200 作为网关负责 SN 路由和协议转换。


