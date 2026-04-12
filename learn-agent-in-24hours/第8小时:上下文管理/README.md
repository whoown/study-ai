# 第 8 小时：上下文管理

## 本章目标

- 理解：对话越长，**上下文窗口与成本**越可能成为瓶颈；需要显式管理。
- 实现一个 **`ContextManager`**：在调用模型前估算体量，并在超限时**安全截断**（尽量不破坏 tool 协议尾部）。
- 把「压缩发生了什么」打印成 **Summary**，方便你观察策略效果。

## 核心概念

- **上下文预算（Budget）**：用字符数做近似（教学用）；生产环境可换成 tokenizer。
- **尾部优先（Recency Bias）**：更常保留最近几轮对话与工具结果，丢弃中间细节。
- **与短期记忆协作**：第 7 小时的 `ShortTermMemory` 可承担“被截断部分”的关键事实备份（本小时会同时展示）。

## 案例设计

故意调低 `ContextManager` 的预算阈值，让多轮 `assistant/tool` 历史触发压缩。  
压缩后仍尝试完成「查价 → 计算 → 输出」链路（无 Key 时 mock 不依赖长上下文）。

## 代码讲解

文件：`src/main.py`。

- **`ContextManager.estimate_chars(messages)`**：估算请求 JSON 体量（教学近似）。
- **`ContextManager.shrink(messages)`**：超限时保留 `system` + 占位说明 + 尾部窗口。
- **`rebuild_messages(...)`**：每轮刷新 `system`（含记忆块），再交给 `shrink`。
- **`run_session(...)`**：打印每轮压缩 **Summary**；无 Key 的 `mock_choice()` 使用「已完成工具次数」推进剧情，避免压缩后消息里 tool 条数变少导致阶段误判。

## 运行方式

```bash
cd "第8小时:上下文管理"
python src/main.py
```

若你使用真实 API，建议对比：开启/调低 `max_chars` 时模型行为变化（可能更依赖短期记忆块）。
