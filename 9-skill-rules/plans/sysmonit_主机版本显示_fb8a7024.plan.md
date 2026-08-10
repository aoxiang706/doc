---
name: sysmonit 主机版本显示
overview: 在 sysmonit 订阅 ros_app 发布的 `/host_sw_version`（`std_msgs/String`），缓存版本字符串，并通过 `/api/overview` 在 Home 默认 System 面板顶部显示。
todos: []
isProject: false
---

# sysmonit 订阅并显示 /host_sw_version

## 背景

[`ros_app.cpp`](src/app/ros_app/ros_app.cpp) 在 `rosWorkTaskLoop` 中每秒发布：

- Topic: `/host_sw_version`
- Type: `std_msgs/msg/String`（`data` = 主机软件版本字符串）
- QoS: `best_effort`（与 `qos_s` 一致）

```378:392:src/app/ros_app/ros_app.cpp
void publishHostSwVersionToRos(void) {
    ...
    std_msgs::msg::String msg{};
    msg.data = std::move(version);
    ros_app::host_sw_version_pub_->publish(msg);
}
```

## 显示位置（默认）

Home 页默认 **System** 面板顶部，新增一行醒目展示：`Host SW Version: <version>`。无有效数据时显示 `-`。

（System Diagnostics 页不单独再放一份，避免重复。）

## 数据流

```mermaid
flowchart LR
  rosApp[ros_app] -->|publish 1Hz| Topic["/host_sw_version"]
  Topic -->|subscribe best_effort| Sysmonit[sysmonit]
  Sysmonit -->|cache version| Overview["GET /api/overview"]
  Overview -->|loadOverview 1s| UI[Home System panel]
```

## 实现步骤

### 1. 后端订阅与缓存

文件：[`main.cpp`](ros_ws/src/sysmonit/src/main.cpp)、[`http_api.hpp`](ros_ws/src/sysmonit/include/sysmonit/http_api.hpp)、[`http_api.cpp`](ros_ws/src/sysmonit/src/http_api.cpp)

- 增加 `on_host_sw_version(std_msgs::msg::String::ConstSharedPtr)` 回调
- `main.cpp` 订阅 `/host_sw_version`，QoS 使用 `best_effort`（与发布端一致，避免收不到）
- 匿名命名空间内缓存：`version` 字符串 + `recv_ms`；新鲜度阈值建议 5s（发布 1Hz）

### 2. 注入 overview API

文件：[`http_api.cpp`](ros_ws/src/sysmonit/src/http_api.cpp) 的 `handle_overview`

在现有 `get_overview_json()` 返回的 JSON 末尾 `}` 前追加字段，避免改动 [`sys_stats.cpp`](ros_ws/src/sysmonit/src/sys_stats.cpp)：

```json
"host_sw_version": "x.y.z",
"host_sw_version_present": true
```

无有效缓存时：`host_sw_version` 为空字符串，`present=false`。

### 3. 前端显示

文件：[`index.html`](ros_ws/src/sysmonit/web/index.html)

- 在 `#overview-panel-system` 的 System 卡片标题下方（表格上方）增加展示区域，例如：
  - `Host SW Version` / `主机软件版本`（i18n）
  - 值用绿色高亮；无数据时显示 `-`
- 在已有 `loadOverview()`（1s 轮询 `/api/overview`）中读取并刷新该字段

### 4. 验证

- `colcon build --packages-select sysmonit`
- 重启 sysmonit 后打开 Home：
  1. `ros2 topic echo /host_sw_version` 有数据时，页面显示相同版本号
  2. 停止 `ptz100_ros` / 无发布超过约 5s 后，显示回退为 `-`

## 不在本次范围

- 不改 `ros_app` 发布逻辑
- 不新增独立 REST 路径（复用 `/api/overview`）
