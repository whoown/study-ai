# 《24小时学会 Agent 开发》课程提纲

> 每小时演进一次，从最简概念到部署上线，理论 + 可运行代码。

---

## 第 1 小时：理解最小 Agent

- Agent 与普通 Chatbot 的本质区别
- 核心公式：Agent = LLM + Tools + Loop
- 用 30 行 Python 写一个最简 while 循环 Agent（硬编码逻辑，不调 LLM）
- **关键理解**：Agent 的本质是"循环决策"

## 第 2 小时：接入真实 LLM

- 调用 OpenAI / DeepSeek API 的基础用法
- 将第 1 小时的硬编码决策替换为 LLM 调用
- 理解 system prompt 对 Agent 行为的影响
- **关键理解**：LLM 是 Agent 的"大脑"

## 第 3 小时：ReAct 模式

- Thought → Action → Observation 循环的完整实现
- 手写一个 ReAct Agent（纯 Python，不用框架）
- 用 prompt 引导 LLM 输出结构化的思考过程
- **关键理解**：ReAct 是几乎所有 Agent 的底层范式

## 第 4 小时：工具定义与 Function Calling

- OpenAI Function Calling 协议详解
- 用 JSON Schema 定义工具描述
- 结构化输出：JSON mode 与 Pydantic 模型约束
- 实现一个计算器工具 + LLM 自动选择调用
- **关键理解**：工具描述的质量直接决定 Agent 的能力上限

## 第 5 小时：多工具 Agent

- 为 Agent 注册多个工具（计算器、时间查询、单位换算）
- LLM 如何在多工具中做选择
- 工具调用结果回注上下文的机制
- 处理 LLM 输出解析失败的容错策略
- **关键理解**：工具越多，prompt 设计越关键

## 第 6 小时：Rules — 规则系统与行为约束

- System prompt 工程：角色定义、行为边界、输出规范
- 静态规则 vs 动态规则（运行时注入）
- 规则冲突与优先级处理
- 安全护栏：防注入、防越权、输出审查
- **关键理解**：Rules 是让 Agent 从"能跑"到"可控"的关键

## 第 7 小时：对话记忆（短期）

- 消息列表作为最简记忆机制
- 管理 system / user / assistant / tool 消息角色
- 多轮对话中的上下文累积
- **关键理解**：记忆 = 上下文窗口中的消息管理

## 第 8 小时：上下文窗口管理

- Token 计数与上下文窗口限制
- 消息截断、摘要压缩策略
- 滑动窗口 vs 摘要记忆的取舍
- **关键理解**：真实场景中上下文爆炸是最常踩的坑

## 第 9 小时：初识框架 — LangChain 基础

- 为什么需要框架（手写胶水代码的痛点）
- LangChain 核心概念：Chain / LLM / Tool
- 用 LangChain 重写之前的手写 Agent
- **关键理解**：框架 = 帮你省掉 80% 胶水代码，但你得先懂那 80%

## 第 10 小时：LangGraph 入门

- 从 Chain 到 Graph：为什么需要图结构
- Node / Edge / State 三要素
- 用 LangGraph 构建一个带条件分支的 Agent
- **关键理解**：Graph 让复杂的 Agent 工作流变得可控可调试

## 第 11 小时：MCP — 标准化工具接入协议

- MCP 架构：Client / Server 模型
- Tool Server 与 Resource Server
- 用 MCP 协议连接外部工具（替代手动注册）
- 编写一个简单的 MCP Server
- **关键理解**：MCP 让工具接入从"每个 API 写一遍适配"变成"统一协议即插即用"

## 第 12 小时：第一个实战项目 — 自动调研 Agent

- 整合搜索工具 + 内容提取 + 摘要生成
- 完整的 Agent 工作流串联
- 应对 hallucination 和工具调用不稳定的实战策略
- **关键理解**：从这一步开始体会"工程能力"与"Demo 能力"的差距

---

## 第 13 小时：Embedding 与向量数据库

- 文本向量化原理（不深究数学，理解直觉）
- 使用 ChromaDB 存储和检索文档
- 相似度搜索的基本用法
- **关键理解**：向量数据库是 Agent 长期记忆的核心基础设施

## 第 14 小时：RAG（检索增强生成）

- RAG 的完整流程：索引 → 检索 → 生成
- 文档分块策略（chunk size / overlap）
- 用 RAG 让 Agent 基于本地文档回答问题
- **关键理解**：RAG 让 Agent 突破了训练数据的边界

## 第 15 小时：RAG Agent — 让 Agent 自主决定何时检索

- 将 RAG 作为一个工具接入 Agent
- Agent 自主判断：直接回答 or 先检索再回答
- 检索结果的相关性评估
- **关键理解**：从"被动 RAG"到"主动 RAG"是质的飞跃

## 第 16 小时：规划能力 — 任务分解

- 简单 Agent：一步步走（线性执行）
- Planning Agent：先拟计划再执行
- 实现一个 Plan-and-Execute 模式的 Agent
- **关键理解**：规划能力是 Agent 处理复杂任务的关键

## 第 17 小时：自我反思与纠错

- 让 Agent 检查自己的输出
- Reflection 模式：生成 → 评估 → 改进
- 实现一个带自我修正的写作 Agent
- **关键理解**：反思循环显著提升 Agent 输出质量

## 第 18 小时：状态持久化与断点恢复

- LangGraph Checkpointer 机制
- 将 Agent 状态保存到数据库
- 中断后恢复执行的完整流程
- **关键理解**：生产级 Agent 必须支持断点续跑

---

## 第 19 小时：Skills — 技能模块化

- Skill 的结构：指令 + 工具集 + 领域知识
- Skill 的发现与动态加载
- Skill 组合：一个 Agent 按需挂载多个 Skill
- 实现一个可插拔 Skill 系统
- **关键理解**：Skills 让 Agent 从硬编码走向可组合架构

## 第 20 小时：多智能体 — 角色分工

- 为什么需要多个 Agent 协作
- 定义不同角色：Researcher / Writer / Reviewer
- 为不同角色分配不同 Skills
- 实现两个 Agent 的简单串行协作
- **关键理解**：单一 Agent 能力有限，分工是扩展能力的自然选择

## 第 21 小时：多智能体 — 编排模式

- Sequential（串行）/ Parallel（并行）/ Hierarchical（层级）
- Supervisor 模式：Manager Agent 调度 Worker Agent
- 用 LangGraph 实现一个多 Agent 工作流
- **关键理解**：编排模式的选择取决于任务的依赖关系

## 第 22 小时：多智能体 — 综合实战

- 设计一个完整的多 Agent 协作项目（如：调研+撰稿+审校团队）
- Agent 间的消息传递与状态共享
- 多 Agent 场景下的错误传播与容错
- **关键理解**：多智能体的难点不在"多"，而在"协"

## 第 23 小时：Human-in-the-Loop

- 在关键节点引入人工确认
- Agent 的中断与等待机制
- 权限控制：哪些工具调用需要人工审批
- **关键理解**：完全自动化的 Agent 在生产中几乎不存在

## 第 24 小时：部署上线

- 用 FastAPI 将 Agent 封装为 API 服务
- 用 Streamlit / Chainlit 搭建交互 UI
- Streaming 流式输出与实时状态展示
- 基本的日志、监控与错误告警
- **关键理解**：从 notebook 到生产还有一段不短的路

---

## 附：技术栈一览

| 类别 | 选择 | 说明 |
|:--|:--|:--|
| 语言 | Python 3.11+ | Agent 生态主力语言 |
| LLM API | OpenAI / DeepSeek | 教程以 OpenAI 为主，兼容 DeepSeek |
| 框架 | LangChain + LangGraph | 当前行业标准，适合教学和生产 |
| 工具协议 | MCP | 标准化工具接入，替代私有 Function Calling 适配 |
| 向量数据库 | ChromaDB | 轻量、无需额外部署 |
| 部署 | FastAPI + Streamlit | 快速搭建后端 + 前端 |
| 本地模型（可选）| Ollama | 免费在本地跑开源模型 |

## 附：学习曲线示意

```
能力
 ▲
 │                                          ┌── 24h：部署上线
 │                                     ┌────┤
 │                                ┌────┤    └── HiTL
 │                           ┌────┤    └── 多智能体 + Skills
 │                      ┌────┤    └── 规划 + 反思 + 状态
 │                 ┌────┤    └── RAG + 长期记忆
 │            ┌────┤    └── 框架 + MCP + 实战项目
 │       ┌────┤    └── Rules + 记忆 + 上下文
 │  ┌────┤    └── ReAct + Function Calling
 │──┤    └── LLM API 调用
 │  └── 最小 Agent 概念
 └──────────────────────────────────────────────► 时间(h)
   1  2  3  4  5  6  7  8  9  ...  18  ...  24
```
