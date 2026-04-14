"""
第 9 小时：LangChain 入门

这份 main.py 是本章对应的最小可运行教学案例。

阅读建议：
1. 先看 main() 怎么启动案例。
2. 再看主流程函数如何驱动模型、工具、状态或路由。
3. 最后再看辅助函数，理解它们分别承担什么职责。

本章新增能力：第一次用框架接管手写胶水代码。
如果你是初学者，建议一边运行一边对照源码，不要只静态阅读。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

# 加载 .env（与仓库 learn-agent-in-24hours 根目录配合使用）
_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / '.env')


# [教学注释] `calculator`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

@tool
def calculator(operation: str, a: float, b: float) -> str:
    """仅支持加法与乘法。operation 取 'add' 或 'mul'；a、b 为两个数。"""
    if operation == "add":
        return str(a + b)
    if operation == "mul":
        return str(a * b)
    return "错误：operation 只能是 add 或 mul"


# [教学注释] `build_llm`
# 负责组装对象、提示词、索引、图或应用实例。

def build_llm() -> ChatOpenAI:
    """创建聊天模型；具体请求由 LangChain 封装。"""
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )


# [教学注释] `build_agent`
# 把模型、工具与提示词装配成 Agent。
# LangChain 1.x 用 create_agent 替代旧版 AgentExecutor + create_tool_calling_agent。
# create_agent 内部基于 LangGraph 构建「调用模型→执行工具→再调模型」的循环图，
# 返回一个可直接 invoke 的 CompiledStateGraph。

def build_agent(tools: list):
    """组装「会调工具的 Agent」：create_agent 封装 tool-calling 循环。"""
    llm = build_llm()
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=(
            "你是数学助手。需要计算时务必调用 calculator 工具，不要心算瞎猜。"
            " 用户问普通闲聊可以简短回答。"
        ),
        debug=True,
    )


# [教学注释] `extract_final_output`
# LangChain 1.x 的 create_agent 返回 {"messages": [...]}，
# 最后一条 AIMessage.content 就是模型的最终自然语言回答。

def extract_final_output(result: Any) -> str:
    """从 create_agent 返回的 state dict 中提取最终回答文本。"""
    messages = result.get("messages", []) if isinstance(result, dict) else []
    if not messages:
        return str(result)

    content = getattr(messages[-1], "content", messages[-1])
    if isinstance(content, str):
        return content
    # content 有时是 list[dict]（多模态场景），拼接其中 text 部分
    if isinstance(content, list):
        parts = [
            str(item.get("text", "")) if isinstance(item, dict) and item.get("type") == "text"
            else str(item)
            for item in content
        ]
        return "".join(parts).strip() or str(content)
    return str(content)


# [教学注释] `simulate_without_api`
# 无法调用真实模型时的教学降级分支。

def simulate_without_api() -> None:
    """不联网，演示「若环境正常，框架会替你跑完 tool 循环」。"""
    print("[教学模拟] 未检测到 OPENAI_API_KEY，跳过真实 LLM 与 Agent。")
    print("[教学模拟] 若环境正常，create_agent 构建的图会：")
    print("  1) 把用户消息和 system_prompt 交给 ChatOpenAI；")
    print("  2) 若返回 tool_calls，则执行 calculator 并把结果作为 ToolMessage 回传；")
    print("  3) 再次调用模型直到得到最终自然语言答案。")
    print("[教学模拟] 手工调用一次工具，展示「工具层」长什么样：")
    print(calculator.invoke({"operation": "add", "a": 2, "b": 3}))


# [教学注释] `run_demo`
# 本章最短可运行演示入口。

def run_demo(user_input: str) -> None:
    if not os.getenv("OPENAI_API_KEY"):
        simulate_without_api()
        return

    tools = [calculator]
    agent = build_agent(tools)
    result = agent.invoke({"messages": [{"role": "user", "content": user_input}]})
    print("\n=== 最终回答 ===\n", extract_final_output(result))


# [教学注释] `main`
# 脚本入口，通常只负责启动案例。

def main() -> None:
    q = "请用工具计算 47 加 15 是多少。"
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    run_demo(q)


if __name__ == "__main__":
    main()
