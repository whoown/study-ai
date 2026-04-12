# 第 12 小时：自动调研 Agent

## 本章目标

- 用 **离线样本资料 + 模拟检索** 串起一条完整「调研」工作流：**发现资料 → 检索 → 汇总成报告**，避免依赖真实爬虫与外网。
- 体会 **框架封装**（`create_tool_calling_agent` + `AgentExecutor`）：模型何时调用 `mock_search` / `list_sources`、如何把工具输出接回对话；无 Key 时由 **`run_offline_pipeline`** 用同一套工具函数演示数据流。

## 核心概念

1. **工具即「可控的外部能力」**：真实场景可能是搜索 API、内部 Wiki、数据库；这里用 **`MOCK_KNOWLEDGE_BASE`** 代替，但接口形状与真工具一致。
2. **Agent 循环**：LLM 决定检索词、是否再搜、如何组织报告；**AgentExecutor** 负责多轮 tool 调用与消息拼装（与第 9 小时同一套抽象，本章强调业务编排）。
3. **反幻觉约束**：System prompt 要求 **只根据工具返回内容写报告**，无资料则明确写「样本库未覆盖」——工程上常与引用片段、校验步骤配合（本课以 prompt 约束为主）。

## 案例设计

内置三篇关于「某虚构产品 AutoRAG-1」的短文档。用户给出一个调研主题（如竞品对比、风险），Agent（或离线管道）调用 **`list_sources`** 看有哪些条目，再 **`mock_search`** 拉取相关摘要，最后输出 **Markdown 式调研小结**。**不使用真实网络**。

## 代码讲解

| 函数 | 作用 |
|------|------|
| `MOCK_KNOWLEDGE_BASE` | 内置样本「网页/报告」正文，供检索。 |
| `mock_search` | 按关键词在样本中打分排序，返回若干片段（模拟 SERP + snippet）。 |
| `list_sources` | 列出样本条目标题与标签，帮助 Agent 选检索方向。 |
| `build_agent` | 装配调研用 System prompt + `AgentExecutor`。 |
| `run_with_llm` | 有 `OPENAI_API_KEY` 时走完整 Agent。 |
| `run_offline_pipeline` | 无 Key：顺序调用 `list_sources` 与 `mock_search`，**模板化**生成报告，展示与 Agent 相同的数据来源。 |

## 运行方式

```bash
cd "第12小时:自动调研 Agent"
python src/main.py
```

自定义调研问题：

```bash
python src/main.py 请调研 AutoRAG-1 的局限与风险
```

有 Key 时由模型自主多步调工具；无 Key 时仍输出基于样本的结构化报告。
