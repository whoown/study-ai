"""
第 12 小时：自动调研 Agent

这份 main.py 是本章对应的最小可运行教学案例。

阅读建议：
1. 先看 main() 怎么启动案例。
2. 再看主流程函数如何驱动模型、工具、状态或路由。
3. 最后再看辅助函数，理解它们分别承担什么职责。

本章新增能力：把搜索、筛选和总结串成小型实战流程。
如果你是初学者，建议一边运行一边对照源码，不要只静态阅读。
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / '.env')

# 虚构资料：教学用，替代真实爬虫结果
MOCK_KNOWLEDGE_BASE: List[Dict[str, str]] = [
    {
        "id": "doc-1",
        "title": "AutoRAG-1 产品白皮书（节选）",
        "tags": "功能,架构,检索",
        "body": (
            "AutoRAG-1 将文档切块后写入向量库，查询时先做相似度检索再把片段交给大模型生成答案。"
            "官方宣称在内部客服场景可将首次解决率提升约 12%。"
        ),
    },
    {
        "id": "doc-2",
        "title": "竞品对比：AutoRAG-1 vs SearchBot Pro",
        "tags": "竞品,价格,生态",
        "body": (
            "SearchBot Pro 提供更丰富的企业连接器；AutoRAG-1 开源组件更多、私有化部署成本较低。"
            "两者均依赖高质量的文档清洗，否则检索噪声会放大模型幻觉。"
        ),
    },
    {
        "id": "doc-3",
        "title": "实施风险清单（内部备忘录）",
        "tags": "风险,合规,运维",
        "body": (
            "主要风险：分块策略不当导致上下文断裂；权限模型若未与源系统同步可能造成越权检索；"
            "需记录查询与引用片段以满足审计。建议上线前做红队测试与人工抽检。"
        ),
    },
]


# [教学注释] `_score_doc`
# 内部辅助函数，为主流程提供局部能力。

def _score_doc(query: str, doc: Dict[str, str]) -> int:
    """极简关键词命中评分（教学用，非真实搜索引擎）。"""
    q = query.lower()
    blob = f"{doc['title']} {doc['tags']} {doc['body']}".lower()
    score = 0
    for tok in re.split(r"\W+", q):
        if len(tok) < 2:
            continue
        if tok in blob:
            score += 2
    # 额外：整句子串
    if q and q in blob:
        score += 5
    return score


# [教学注释] `mock_search`
# 教学化搜索函数，用可控数据模拟外部检索。

@tool
def mock_search(query: str, top_k: int = 2) -> str:
    """在离线样本库中检索与 query 相关的片段，返回标题+摘录（模拟搜索结果）。"""
    ranked: List[Tuple[int, Dict[str, str]]] = [
        (_score_doc(query, d), d) for d in MOCK_KNOWLEDGE_BASE
    ]
    ranked.sort(key=lambda x: -x[0])
    lines: List[str] = []
    for score, d in ranked[: max(1, min(top_k, 3))]:
        lines.append(f"[{d['id']}] {d['title']} (score={score})\n摘录: {d['body'][:200]}...")
    if not lines:
        return "（无匹配条目）"
    return "\n\n".join(lines)


# [教学注释] `list_sources`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

@tool
def list_sources() -> str:
    """列出当前样本库中所有文档标题与标签，便于规划检索。"""
    parts = [f"- {d['id']}: {d['title']}  [{d['tags']}]" for d in MOCK_KNOWLEDGE_BASE]
    return "\n".join(parts)


# [教学注释] `build_llm`
# 负责组装对象、提示词、索引、图或应用实例。

def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )


# [教学注释] `build_agent`
# 把模型、工具与提示词装配成 Agent。

def build_agent():
    """调研专用 Agent：框架封装多轮工具调用。"""
    tools = [mock_search, list_sources]
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是严谨的产业调研助手。必须先使用工具获取资料："
                "必要时先用 list_sources 了解有哪些文档，再用 mock_search 检索。"
                "最终输出用 Markdown：含「要点」「风险/局限」「引用依据（doc id）」。"
                "禁止编造样本库中不存在的事实；若资料不足请明确说明。",
            ),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    agent = create_tool_calling_agent(build_llm(), tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=8)


# [教学注释] `run_with_llm`
# 驱动一段完整流程，把前面准备好的零件真正串起来。

def run_with_llm(question: str) -> None:
    exe = build_agent()
    out = exe.invoke({"input": question})
    print("\n=== 调研输出 ===\n", out.get("output", out))


# [教学注释] `run_offline_pipeline`
# 驱动一段完整流程，把前面准备好的零件真正串起来。

def run_offline_pipeline(question: str) -> None:
    """无 API Key：不走 LLM，用相同工具函数 + 固定模板拼报告，展示数据流。"""
    print("[离线模式] 未配置 OPENAI_API_KEY，跳过 LLM 与 AgentExecutor。")
    overview = list_sources.invoke({})
    hits = mock_search.invoke({"query": question, "top_k": 3})
    print("\n--- list_sources ---\n", overview)
    print("\n--- mock_search ---\n", hits)
    print("\n=== 调研输出（模板合成，非模型生成）===\n")
    print(f"**用户主题**: {question}\n")
    print("**资料范围**（来自 list_sources）:\n", overview)
    print("\n**检索摘录**（来自 mock_search）:\n", hits)
    print(
        "\n**说明**: 若接入 API Key，AgentExecutor 会由模型多次调用上述工具并自主组织段落；"
        "此处仅演示「工具返回内容即报告素材上限」。"
    )


# [教学注释] `main`
# 脚本入口，通常只负责启动案例。

def main() -> None:
    q = "请基于样本库调研 AutoRAG-1 的风险与竞品差异。"
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    if os.getenv("OPENAI_API_KEY"):
        run_with_llm(q)
    else:
        run_offline_pipeline(q)


if __name__ == "__main__":
    main()
