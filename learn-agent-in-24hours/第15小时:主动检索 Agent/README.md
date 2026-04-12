# 第 15 小时：主动检索 Agent

## 本章目标

- 区分 **「一次性 RAG」** 与 **「由 Agent 决定何时检索、检索什么」**。
- 理解 **主动检索（Active Retrieval）**：模型或策略根据当前信息缺口，**自主选择**是否调用向量库、以及改写查询词。
- 观察运行日志中的 **决策（decision）→ 行动（action）→ 状态（state）** ，而不是只看最终答案。

## 核心概念

| 术语 | 含义 |
|------|------|
| 被动 RAG | 每个问题都先检索再回答。 |
| 主动检索 | Agent 先判断「是否已足够回答」；不足时再检索，并可 **多轮查询**。 |
| 查询改写 | 把用户口语改写成更利于向量检索的关键词句。 |

本课示例用 **轻量规则 +（可选）LLM JSON 决策** 实现，避免引入过大框架，同时保留真实工作流心智模型。

## 案例设计

场景：用户问模糊问题，Agent：

1. 维护 `AgentState`（轮次、已检索片段、是否结束）。
2. 每一步打印 **`plan_decision`**：继续检索 / 可以作答。
3. 若检索：打印 **`rewrite_query`** 与 **`retrieval_hits`**。
4. 最后输出 **`final_answer`**（无 Key 时用模板化模拟）。

## 代码讲解

见 `src/main.py`：

- **`AgentState`**：用字典保存当前轮次、累积上下文、决策历史（打印时即「可观测状态」）。
- **`rule_based_decide`**：无 Key 或 LLM 失败时的确定性策略（教学可复现）。
- **`llm_decide`**：有 Key 时请求模型输出 JSON：`need_search`、`query`、`reason`。
- **`retrieve_from_store`**：内部复用哈希嵌入 + 余弦相似度（与前几课一致），也可视为「向量工具」。
- **`run_active_agent`**：主循环，打印每步 **decision / state snapshot**。

阅读重点：在输出中找到 `--- 第 n 轮 ---` 与 `task_state` 字段，理解 Agent 如何 **边想边查**。

## 运行方式

```bash
python "第15小时:主动检索 Agent/src/main.py"
python run_demo.py 15
```

配置 `OPENAI_API_KEY` 后，决策步骤将尝试走 `llm_decide`；否则自动使用 `rule_based_decide`。
