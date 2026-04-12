# 第 4 小时：函数调用（Tool / Function Calling）

## 本章目标

- 理解「**结构化工具选择**」：模型输出不再是自由文本里的 JSON，而是 API 层的 `tool_calls`。
- 学会把工具声明成 **JSON Schema**（`parameters`），让模型按字段填参。
- 掌握对话里 `role=tool` 的回填格式，这是多轮工具链路的工业界常见形态。

## 核心概念

- **Tool schema**：描述函数名、用途、参数类型与必填项。
- **tool_calls**：模型返回的调用列表（含 `id`，用于回填结果）。
- **tool 消息**：把执行结果回传给模型，形成严格的多消息协议。

## 案例设计

任务：计算 `6 * 7`，再用 `say` 输出固定模板。  
有 API Key 时走真实 `tools` 参数；无 Key 时用本地逻辑模拟一轮 `tool_calls`。

## 代码讲解

文件：`src/main.py`。

- **`TOOL_SPECS`**：OpenAI 兼容的 tools 定义列表。
- **`call_model(messages)`**：返回 `choice` 对象；失败或无 Key 时走 `mock_choice()`。
- **`mock_choice(messages)`**：模拟 `tool_calls` 结构，保证离线可运行。
- **`execute_tool_calls(choice, messages)`**：执行工具并把 `tool` 消息追加进 `messages`。
- **`run_session(user_goal)`**：直到模型不再发起 `tool_calls` 为止。

## 运行方式

```bash
cd "第4小时:函数调用"
python src/main.py
```
