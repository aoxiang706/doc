# 截击机SLink协议

广播组网

参考连接：[Skyfend通用Slink通信协议](https://vxr5wm8r80r.feishu.cn/docx/SG23dQBH9ocSomx7Zk4coWsrnFc)

```mermaid
sequenceDiagram
    participant 地面站
    participant 设备

    rect rgb(240, 248, 255)
        Note left of 地面站: UDP通信
        地面站->>设备: 1.1 UDP广播(0xBA消息)<br/>广播地址(x.x.x.255:3800)
        设备->>地面站: 1.2 回复响应(0xBB消息)地址(x.x.x.x:3810)<br/>包含协议号和设备唯一号
        地面站->>设备: 1.3 回复(0xBC消息)地址(x.x.x.x:3800)<br/>包含设备可连接的IP和Port
    end

    rect rgb(245, 255, 245)
        Note left of 地面站: TCP通信
        设备->>地面站: 2.1 设备和地面站建立TCP连接、开始发送数据
        地面站->>设备: 下发控制指令
        设备->>地面站: 响应控制指令
        设备->>地面站: 3.1 设备主动上报
    end```



截击机 \-\-\> 地面站

地面站 \-\-\> 截击机

地面站 \-\-\> 机巢



截击机协议

截击机设备类型ID 0x32

地面站设备类型ID 0x04

机巢设备类型ID  0x33

地面图传设备类型ID  0x34

**SLINK V1协议格式定义**



## 一、截击机

预留8个

地面站 \-\-\> 截击机

### 1、TARGET\_INFO （目标信息）

### 2、CONTROL\_CMD （控制指令）





截击机 \-\-\> 地面站

### 3、INTERCEPTOR\_INFO（截击机信息）

新增：版本号/任务持续时间/gps卫星数



### 4、VIDEO\_LOCK （识别框信息）

新增：类别/置信度

### 5、CONFIG\_INFO （配置信息）

新增加和峰sn号字段

## 二、机巢

[机巢SLink协议](https://vxr5wm8r80r.feishu.cn/wiki/NvmhwcikiiABtfkc9aXcKE14nCb)

## 三、地面站

### 1、GroundStationHeartbeat（地面站心跳）



