# 第 9 小时：LangChain 入门

## 本章目标

- 理解 **LangChain 替你封装了什么**：消息格式、工具绑定、Agent 循环与「模型 → 工具 → 再模型」的胶水代码。
- 能读懂并运行本章示例 `src/main.py`，观察有/无 API Key 时的行为差异。

## 核心概念

1. **ChatOpenAI**（`build_llm`）：把「发 HTTP、解析响应、流式/非流式」藏在模型对象后面；你主要和「可调用模型」打交道。
2. **`@tool` 装饰器**（`calculator`）：把普通 Python 函数变成带 **JSON Schema 描述** 的工具，供模型做 **Function Calling**；你不用手写 schema 字符串（仍可自定义描述）。
3. **create_tool_calling_agent + AgentExecutor**（`build_agent` / `run_demo`）：框架把 **解析 tool_calls、执行工具、把结果塞回 agent_scratchpad、再调模型** 这一圈循环封装掉；手写时这些都要自己写 while 循环和消息拼装。

## 案例设计

用户输入自然语言问题，Agent 自主决定是否调用 **计算器工具**（仅支持 `add` / `mul`）。无 API Key 时，不发起网络请求，打印说明并走 **教学模拟**（`simulate_without_api`），仍能看清「本应发生的步骤」。

## 代码讲解

示例集中在 **`src/main.py`**：

| 函数 | 作用 |
|------|------|
| `calculator` | LangChain 工具：框架负责生成 schema 与注册名。 |
| `build_llm` | 创建 `ChatOpenAI`，统一模型名与温度等参数。 |
| `build_agent` | 用 `create_tool_calling_agent` 组装 prompt + 模型 + 工具；`AgentExecutor` 负责多轮工具循环。 |
| `run_demo` | 有 Key 时跑真实 Agent；无 Key 时调用 `simulate_without_api`。 |
| `simulate_without_api` | 无 Key 时的降级：打印「若已配置 Key 会由模型决定是否调用工具」。 |

## 运行方式

在仓库目录 `learn-agent-in-24hours` 下（已安装 `requirements.txt`、可选配置 `.env` 中的 `OPENAI_API_KEY`）：

```bash
cd "第9小时:LangChain 入门"
python src/main.py
```

有 Key 时：会调用真实模型（默认 `gpt-4o-mini`，可在代码中修改）。无 Key 时：仅打印提示与模拟流程，不报错退出。
