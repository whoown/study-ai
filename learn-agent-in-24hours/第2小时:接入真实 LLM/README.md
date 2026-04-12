# 第 2 小时：接入真实 LLM

## 本章目标

- 把第 1 小时的「假大脑」替换为**真实大模型 API**（OpenAI 兼容接口）。
- 学会用环境变量管理 Key，并在缺失时**优雅降级**到教学模拟输出。
- 理解：LLM 在这里首先扮演「生成下一步该做什么」的组件，而不是神秘黑盒。

## 核心概念

- **Chat Completions**：把多轮对话打包成 `messages`（system/user/assistant）发给模型。
- **OpenAI 兼容 Base URL**：许多服务商提供与 OpenAI 相同的 REST 形态，可用 `OPENAI_BASE_URL` 切换。
- **降级策略（Graceful Degradation）**：没有 Key 时仍运行 demo，打印清晰提示，避免 traceback 吓到初学者。

## 案例设计

沿用「计算器 + 格式化」类问题：模型在每一轮只需要输出**下一步**要调用的工具（JSON 一行），程序负责执行并回注观察结果。  
这样你可以清楚看到：**模型负责语言与决策，Python 负责执行与约束**。

## 代码讲解

本章代码在 `src/main.py`：

- **`load_settings()`**：读取 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`。
- **`chat_completion(messages)`**：有 Key 则调用真实 API；无 Key 则走 `mock_chat_completion()`。
- **`mock_chat_completion(messages)`**：根据对话内容返回固定的教学响应，保证可运行。
- **`run_tool` / `TOOLS`**：与第 1 小时同款执行层，强调「执行不在模型内部完成」。
- **`agent_loop(user_goal)`**：多轮循环，打印 **Thought（模型文本）**、解析 **Action**、打印 **Observation**。

## 运行方式

```bash
cd "第2小时:接入真实 LLM"
# 可选：复制仓库 learn-agent-in-24hours/.env.example 为 .env 并填写 Key
python src/main.py
```

未配置 Key 时会看到提示，并自动使用模拟输出。
