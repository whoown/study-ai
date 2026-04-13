"""
第 10 小时：LangGraph 入门

这份 main.py 是本章对应的最小可运行教学案例。

阅读建议：
1. 先看 main() 怎么启动案例。
2. 再看主流程函数如何驱动模型、工具、状态或路由。
3. 最后再看辅助函数，理解它们分别承担什么职责。

本章新增能力：用图来表达节点、边和状态流转。
如果你是初学者，建议一边运行一边对照源码，不要只静态阅读。
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


# [教学注释] `calculator`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

@tool
def calculator(operation: str, a: float, b: float) -> str:
    """仅支持加法与乘法。operation 取 'add' 或 'mul'。"""
    if operation == "add":
        return str(a + b)
    if operation == "mul":
        return str(a * b)
    return "错误：operation 只能是 add 或 mul"


# [教学注释] `build_llm`
# 负责组装对象、提示词、索引、图或应用实例。

def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )


# [教学注释] `call_model`
# 负责真正与模型交互，并把结果交回主流程。

def call_model(state: MessagesState, tools: List):
    """Agent 节点：绑定工具并调用模型；返回的新消息由框架合并进 state['messages']。"""
    llm = build_llm().bind_tools(tools)
    msg = llm.invoke(state["messages"])
    return {"messages": [msg]}


# [教学注释] `build_graph`
# 定义节点、边和路由关系，是图编排的关键入口。

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


# [教学注释] `simulate_without_api`
# 无 API Key 时的教学降级分支。

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


# [教学注释] `run_demo`
# 本章最短可运行演示入口。

def run_demo(user_text: str) -> None:
    tools = [calculator]
    if not os.getenv("OPENAI_API_KEY"):
        simulate_without_api()
        return
    graph = build_graph(tools)
    result = graph.invoke({"messages": [HumanMessage(user_text)]})
    last = result["messages"][-1]
    print("\n=== 最终回答 ===\n", getattr(last, "content", last))


# [教学注释] `main`
# 脚本入口，通常只负责启动案例。

def main() -> None:
    q = "请用工具计算 8 乘以 7。"
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    run_demo(q)


if __name__ == "__main__":
    main()
