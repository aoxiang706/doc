---
name: agx-remote-dev-workflow
description: AGX 远程开发工作流，包含 gadd/gcommit/gsync/gpush/gpull 等自定义 Git 工具使用说明。用于在 AGX 与 Ubuntu 之间同步代码、提交代码时使用。
---

# AGX 远程开发工作流

## 一、架构说明

```
┌─────────────────┐     rsync      ┌─────────────────┐
│   AGX (开发机)   │ ←──────────→  │  Ubuntu (编译机) │
│   代码编辑       │               │   Git 仓库       │
│   运行调试       │               │   编译构建       │
└─────────────────┘               └─────────────────┘
         ↑                                 ↑
         │                                 │
     Cursor SSH                      Git 远程仓库
```

**核心概念**：AGX 上编辑代码，通过 rsync 同步到 Ubuntu，在 Ubuntu 上执行 Git 操作和编译。

---

## 二、常用命令速查

| 命令 | 用途 | 示例 |
|------|------|------|
| `gadd` | 添加文件到暂存区 | `gadd src/ ros_ws/` |
| `gcommit` | 提交更改 | `gcommit -m "修复bug"` |
| `gpush` | 推送到远程 | `gpush` |
| `gpull` | 从远程拉取 | `gpull` |
| `gsync` | 同步代码 | `gsync up` / `gsync down` |
| `gstatus` | 查看状态 | `gstatus` |
| `gbranch` | 分支管理 | `gbranch checkout develop` |
| `glog` | 查看日志 | `glog` |
| `gdiff` | 查看差异 | `gdiff` |

---

## 三、典型工作流程

### 日常开发流程

```bash
# 1. 在 AGX 上编辑代码（使用 Cursor）

# 2. 添加修改的文件
gadd src/srv/xxx.cpp ros_ws/src/ptz_service/

# 3. 提交
gcommit -m "功能: 添加xxx功能"

# 4. 推送
gpush
```

### 切换分支

```bash
# 切换分支（会自动同步到 AGX）
gbranch checkout feature/xxx

# 或查看所有分支
gbranch -a
```

### 同步代码

```bash
# AGX → Ubuntu (默认，排除 .git)
gsync up

# Ubuntu → AGX (包含 .git，保持 git 状态一致)
gsync down

# 指定 Ubuntu IP（如 192.168.2.x 网段）
gsync down 192.168.2.103
gsync up 192.168.2.103
```

---

## 四、命令详解

### gadd - 添加到暂存区

```bash
# 添加指定文件/目录
gadd public/gstNvDeeps/ ros_ws/src/ptz_service/

# 指定 Ubuntu IP
gadd 192.168.2.103 src/foo.cpp
gadd 192.168.2.103 -a

# 添加所有修改
gadd -a
```

### gcommit - 提交

```bash
# 方式1：使用 -m 参数
gcommit -m "功能: 添加xxx"

# 方式2：直接写消息（兼容旧用法）
gcommit "功能: 添加xxx"
```

### gsync - 代码同步

```bash
# 上传到 Ubuntu (排除 .git)
gsync up

# 下载到 AGX (包含 .git，保持状态一致)
gsync down

# 指定 Ubuntu IP（默认 192.168.3.103）
gsync down 192.168.2.103
gsync up 192.168.2.103
```

**注意**：`gsync down` 会包含 `.git` 目录，确保 AGX 的 git 状态与 Ubuntu 一致。

### AGX 本地保护路径（永久保护）

以下目录**永不同步、永不覆盖、永不被 `--delete` 删掉**：

- `ros_ws/build/`
- `ros_ws/install/`
- `.cursor/`（AGX 本地 Cursor 配置，`gsync down` 拉代码时不覆盖、不删除）

规则在 `~/bin/git_tools_common.sh` 的 `RSYNC_EXCLUDES`（含 `protect` 过滤器）。`gadd ros_ws/build`、`gadd .cursor` 会被拒绝。

需要全量重编时，用户自行：

```bash
rm -rf ros_ws/build ros_ws/install
cd ros_ws && colcon build ...
```

### 配置模板 / yamlConfig 重构后必编

修改 `public/config/**`（如 `SingleCfgBase`、`systemWorkParamCfg`）后，除 `gadd`/`gcommit` 外，必须在 AGX 上 **`colcon build` 所有链接方**（至少 `ptz100_ros` + `ptz_service`）。Python 单测不能替代 C++ 编译。详见项目 skill：`.cursor/skills/config-refactor-build-verify/SKILL.md`。

---

## 五、配置路径

| 变量 | 值 |
|------|---|
| AGX 代码路径 | `/home/skyfend/workspace/ptz100_agx` |
| Ubuntu 代码路径 | `/home/skyfend/ptz100_agx_code/cur/ptz100_agx` |
| Ubuntu IP | `192.168.3.103` |
| 脚本位置 | `/home/skyfend/bin/` |

---

## 六、常见问题

### Q: gadd 后 AGX 上 git status 还显示未跟踪？

A: 执行 `gsync down` 同步 `.git` 目录，或使用 `gpull`。

### Q: gbranch checkout 后代码没更新？

A: `gbranch checkout` 会自动同步，如果没生效，手动执行 `gsync down`。

### Q: 如何查看 Ubuntu 上的 git 状态？

A: 使用 `gstatus` 查看 Ubuntu 仓库状态。

---

## 七、脚本自动补全

已配置 bash 补全，支持：

```bash
# 子命令补全
gbranch <Tab>  # 显示 checkout, -c, -r, -a, -h

# 分支名补全
gbranch checkout <Tab>  # 显示远程分支列表
gbranch checkout user<Tab>  # 补全为 user/2.0.2.24_fix20260115
```

补全脚本位置：`/home/skyfend/bin/gbranch_completion.bash`
