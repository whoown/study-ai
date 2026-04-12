# 第 7 小时：短期记忆

## 本章目标

- 理解：**对话不只有 `messages` 一种记忆形态**；还可以维护「事实笔记」这类结构化短期记忆。
- 实现一个可注入提示词的 **ShortTermMemory**：把关键 Observation 压缩成条目，减少模型遗忘与重复提问。
- 观察 **Memory(update)** 与 **Thought/Action/Observation** 如何并行展示（教学日志更清晰）。

## 核心概念

- **短期记忆（Working Memory）**：当前会话内有效，程序重启即丢失（与长期记忆/向量库不同）。
- **记忆注入**：把 `memory.render()` 拼到 `system` 或单独消息里，让模型稳定「看见」已确认事实。
- **记忆裁剪**：条目过多时要遗忘最旧项（本小时用最大条数上限演示）。

## 案例设计

在「查价 → 计算 → 输出」工具链基础上，每步工具结束后由程序自动 `memory.note()` 记录一条摘要。  
下一轮模型调用前，把记忆块附加到系统提示末尾。

## 代码讲解

文件：`src/main.py`。

- **`ShortTermMemory`**：`note()` 追加条目，`render()` 生成可读块，`trim()` 控制容量。
- **`build_messages_with_memory(...)`**：把记忆动态写进 system 提示。
- **`run_session_with_memory(user_goal)`**：每次 **Observation** 后更新记忆，并打印 **Memory** 区块。

## 运行方式

```bash
cd "第7小时:短期记忆"
python src/main.py
```
