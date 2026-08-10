---
name: clangd-setup-guide
description: Clangd 环境配置指南，用于实现 C++ 代码跳转 (F12)、高亮、自动补全。适用于 ROS2/colcon 项目的 SSH 远程开发。
---

# Clangd 环境配置指南

## 一、核心组件

| 组件 | 作用 |
|------|------|
| `clangd` | C++ 语言服务器，提供代码跳转/补全 |
| `compile_commands.json` | 编译数据库，告诉 clangd 如何编译每个文件 |
| `.clangd` | clangd 配置文件 |

---

## 二、快速配置

### 1. 安装 clangd (远程服务器)

```bash
sudo apt-get install clangd
```

### 2. 安装 VSCode 扩展 (本地)

在 Cursor/VSCode 中安装 `llvm-vs-code-extensions.vscode-clangd`

### 3. 生成 compile_commands.json

```bash
# 使用开发构建脚本（已配置好）
./config/tools/build_dev.sh

# 或手动 colcon build
cd ros_ws
colcon build --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
```

### 4. 合并 compile_commands.json (ROS2 项目)

colcon 会为每个包生成独立的 `compile_commands.json`，需要合并：

```bash
# build_dev.sh 已自动处理合并
# 合并后的文件位于项目根目录
ls -la compile_commands.json
```

---

## 三、配置文件

### 全局配置 (SSH 远程)

位置：`~/.vscode-server/data/Machine/settings.json`

```json
{
    "clangd.path": "/usr/bin/clangd",
    "clangd.arguments": [
        "--background-index",
        "--clang-tidy",
        "--header-insertion=iwyu",
        "--completion-style=detailed"
    ],
    "C_Cpp.intelliSenseEngine": "disabled"
}
```

### 项目配置

位置：`项目根目录/.clangd`

```yaml
CompileFlags:
  Add:
    - "-I/opt/ros/humble/include/**"
    - "-std=c++17"

Index:
  Background: Build
```

---

## 四、常见问题

### Q: F12 无法跳转？

1. 确认 `compile_commands.json` 存在且在项目根目录
2. 执行 `Ctrl+Shift+P` → `clangd: Restart language server`
3. 检查 clangd 输出日志

### Q: 索引很慢？

clangd 首次会在后台建立索引（`.cache/clangd/`），耐心等待或查看进度。

### Q: 与 C/C++ 扩展冲突？

在 settings.json 中禁用：
```json
"C_Cpp.intelliSenseEngine": "disabled"
```

---

## 五、配置持久性

| 配置类型 | 路径 | 作用范围 |
|----------|------|----------|
| 全局设置 | `~/.vscode-server/data/Machine/settings.json` | 所有项目 |
| 项目 .clangd | `项目根目录/.clangd` | 当前项目 |
| compile_commands.json | `项目根目录/compile_commands.json` | 当前项目 |

**注意**：`compile_commands.json` 需要在代码结构变化后重新生成（运行 `build_dev.sh`）。

---

## 六、快捷键

| 功能 | 快捷键 |
|------|--------|
| 跳转到定义 | `F12` |
| 返回上一位置 | `Ctrl+-` 或 `Alt+←` |
| 查看引用 | `Shift+F12` |
| 重命名符号 | `F2` |
