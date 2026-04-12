# 第 3 小时：手写 ReAct

## 本章目标

- 理解 **ReAct**（Reasoning + Acting）：把推理痕迹显式写出来，再触发工具执行。
- 自己用字符串解析实现 `Thought / Action / Action Input`，而不是依赖框架。
- 对比第 2 小时：从「一行 JSON」升级为更贴近论文表述的**可读轨迹**。

## 核心概念

- **Thought**：模型解释「为什么要这么做」，便于调试与审计。
- **Action**：要调用的工具名（与注册表一致）。
- **Action Input**：工具的参数，通常用 JSON 表达，便于扩展。
- **Observation**：工具返回值，再拼回提示，让模型继续下一步。

## 案例设计

任务：计算 `2.5 * 8`，再把结果格式化成模板字符串。  
模型按固定分隔标题输出；解析器负责抽取字段并执行工具。

## 代码讲解

代码文件：`src/main.py`。

- **`chat_completion()`**：与第 2 小时相同思路（urllib + 降级 mock）。
- **`parse_react_block(text)`**：从模型输出解析 `Thought/Action/Action Input` 三个字段。
- **`mock_react(messages)`**：无 Key 时返回标准 ReAct 文本，保证可跑。
- **`run_tool()`**：执行工具并生成 Observation。
- **`react_loop(user_goal)`**：把每次 Observation 追加进对话，形成 ReAct 轨迹。

## 运行方式

```bash
cd "第3小时:手写 ReAct"
python src/main.py
```
