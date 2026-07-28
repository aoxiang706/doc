# 机巢SLink协议



```mermaid
sequenceDiagram
    participant 地面站
    participant 设备

    rect rgb(245, 255, 245)
        Note left of 地面站: TCP通信
        设备->>地面站: 设备和地面站建立TCP连接、开始发送数据
            设备->>地面站: 1.1 定时发送(0xBB消息)地址(x.x.x.x:3760)<br/>包含协议号和设备唯一号
            地面站->>设备: 1.2 回复地面站心跳
            地面站->>设备: 2.1下发控制指令
            设备->>地面站: 响应控制指令
            设备->>地面站: 3.1 设备主动上报
    end```



截击机设备类型ID 0x32

地面站设备类型ID 0x04

机巢设备类型ID  0x33

地面图传设备类型ID  0x34

**SLINK V1协议格式定义**



## 一、机巢

预留8个

### 1、CONTROL\_SWITCH（总控制开关）

STRIKE\_SWITCH（打击开关） 待补充

### 2、EMERGENCY\_STOP（紧急停止）

### 3、CONTROL\_DOOR （机巢门控制）

### 4、CONTROL\_AIR\_CONDITIONER （压缩机控制）

待补充



### 5、CONTROL\_CHARGE（充电控制）

### 6、RESUME\_SWITCH（唤醒开关）

待补充

### 7、NEST\_INFO（机巢状态）

机巢心跳  待补充

GPS、电量、SN、飞机状态

### 8、OTA\_UPDATE （远程升级） 待协商参数

### 9、 NEST\_LOG（日志下载）  待协商参数

### 9、 DRONE\_LOG（日志下载）  待协商参数

## 二、地面站

### 1、GroundStationHeartbeat（地面站心跳）



