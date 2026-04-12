"""
第 10 小时：LangGraph 入门 — 用图封装「分支 + 工具循环 + 状态归并」。
"""

from __future__ import annotations

import os
import sys
from typing import List

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()


@tool
def calculator(operation: str, a: float, b: float) -> str:
    """仅支持加法与乘法。operation 取 'add' 或 'mul'。"""
    if operation == "add":
        return str(a + b)
    if operation == "mul":
        return str(a * b)
    return "错误：operation 只能是 add 或 mul"


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )


def call_model(state: MessagesState, tools: List):
    """Agent 节点：绑定工具并调用模型；返回的新消息由框架合并进 state['messages']。"""
    llm = build_llm().bind_tools(tools)
    msg = llm.invoke(state["messages"])
    return {"messages": [msg]}


def build_graph(tools: List):
    """构图：START -> agent -> (有工具? tools -> agent 循环 : END)。"""
    graph = StateGraph(MessagesState)

    # 使用闭包把 tools 传给节点（教学上直观；生产可用 partial 或 RunnableConfig）
    def _agent(state: MessagesState):
        return call_model(state, tools)

    graph.add_node("agent", _agent)
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "agent")
    # tools_condition 返回 "tools" 或 "__end__"；需映射到节点名与 END
    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", "__end__": END},
    )
    graph.add_edge("tools", "agent")
    return graph.compile()


def simulate_without_api() -> None:
    """无 Key：用假 AIMessage 演示 tools_condition 与 ToolNode 的分工（不跑真实 LLM）。"""
    print("[教学模拟] 未检测到 OPENAI_API_KEY。")
    print("[教学模拟] tools_condition 会检查最后一条 AIMessage 是否含 tool_calls；")
    print("          若有，边指向 'tools' 节点，由 ToolNode 执行并产出 ToolMessage。")
    tools = [calculator]
    fake_ai = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "calculator",
                "args": {"operation": "mul", "a": 8, "b": 7},
                "id": "call_demo_1",
                "type": "tool_call",
            }
        ],
    )
    state = {"messages": [HumanMessage("演示"), fake_ai]}
    tool_node = ToolNode(tools)
    out = tool_node.invoke(state)
    print("[教学模拟] ToolNode 输出消息条数:", len(out.get("messages", [])))
    for m in out.get("messages", []):
        print("  ->", getattr(m, "content", m))


def run_demo(user_text: str) -> None:
    tools = [calculator]
    if not os.getenv("OPENAI_API_KEY"):
        simulate_without_api()
        return
    graph = build_graph(tools)
    result = graph.invoke({"messages": [HumanMessage(user_text)]})
    last = result["messages"][-1]
    print("\n=== 最终回答 ===\n", getattr(last, "content", last))


def main() -> None:
    q = "请用工具计算 8 乘以 7。"
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    run_demo(q)


if __name__ == "__main__":
    main()
