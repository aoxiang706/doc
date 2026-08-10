---
name: commit-message-demo
description: 提交消息示例与 Conventional Commits 格式参考，配合 commit-cn rule 使用。
---

# 提交消息示例

## 格式

```
<emoji> <type>(<scope>): <简短描述>

[可选：详细说明]
```

## 示例

```
✨ feat(ptz): 和普云台设备启动后手动设置识别自适应

✨ feat(video): 增加 GStreamer 硬解参数配置

🐛 fix(video): 修复多线程调用 cv::VideoCapture 导致的段错误

📝 docs: 补充 ptzDeviceHepu 视频流流程图

♻️ refactor(alink): 统一设备类型枚举命名

🔧 chore: 更新 .gitignore 忽略 .cache 目录
```

## 与 commit-cn 规则配合

在对话中说「按 commit-cn 写提交信息」即可生成符合规范的提交消息。
