# 第 10 小时：LangGraph 入门

## 本章目标

- 理解 **LangGraph 在 LangChain 之上多封了一层什么**：用 **图（节点 + 边）** 表达「先模型、再工具、再模型」的分支与循环，状态（如消息列表）由框架合并更新。
- 能对照 **`src/main.py`** 里的 `call_model`、`tool_node` 与 `build_graph`，说出每一步对应手写 Agent 的哪段逻辑。

## 核心概念

1. **MessagesState**：预置状态里带 `messages` 列表；新消息会通过 **reducer**（如追加）合并进状态，不用你手动 `state["messages"].append(...)` 到处拷贝。
2. **StateGraph + 节点**：每个节点是一个函数，输入状态、输出「要合并进状态的补丁」；框架负责调度与并发安全边界（本例为单线程顺序执行）。
3. **ToolNode / tools_condition**（`build_graph`）：**ToolNode** 封装「按 AIMessage.tool_calls 逐个执行工具并生成 ToolMessage」；**tools_condition** 封装「有 tool_calls 则去 tools 节点，否则结束」——这两块在手写代码里最冗长、最易出错。
4. **compile()**：把图编译成可 `invoke` 的可运行对象，便于之后加检查点、人工中断等（本课只用到 `invoke`）。

## 案例设计

与第 9 小时同款 **calculator** 工具，但编排改用 **LangGraph**：用户问题进入图 → 模型节点 → 若有工具调用则进工具节点 → 回到模型直到无 tool_calls。无 API Key 时由 **`simulate_without_api`** 说明图上的边在真实运行中如何被触发。

## 代码讲解

| 符号 | 说明 |
|------|------|
| `calculator` | 与第 9 小时类似，LangChain Core 的 `@tool`，供 `ToolNode` 消费。 |
| `call_model` | 节点函数：`llm.bind_tools(tools).invoke`，把模型回复（可能含 tool_calls）写入 `messages`。 |
| `build_graph` | 注册 `agent` / `tools` 节点，`tools_condition` 控制分支，`ToolNode` 执行工具。 |
| `run_demo` | 有 Key：`graph.invoke`；无 Key：模拟说明。 |

## 运行方式

```bash
cd "第10小时:LangGraph 入门"
python src/main.py
```

可选传入一句话作为用户输入：

```bash
python src/main.py 用工具算 6 乘 7
```
