"""
第 21 小时：多智能体编排

这份 main.py 是本章对应的最小可运行教学案例。

阅读建议：
1. 先看 main() 怎么启动案例。
2. 再看主流程函数如何驱动模型、工具、状态或路由。
3. 最后再看辅助函数，理解它们分别承担什么职责。

本章新增能力：让 supervisor 调度多个角色节点。
如果你是初学者，建议一边运行一边对照源码，不要只静态阅读。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, TypedDict

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass


class OrchState(TypedDict, total=False):
    """编排状态：Supervisor 通过 next 字段驱动条件边。"""

    topic: str
    outline: str
    draft: str
    critique: str
    next: str


# [教学注释] `supervisor_node`
# 调度节点，决定当前轮到谁工作。

def supervisor_node(state: OrchState) -> dict[str, Any]:
    """指挥：按完成度决定下一个节点。"""
    if not state.get("outline"):
        return {"next": "analyst"}
    if not state.get("draft"):
        return {"next": "writer"}
    if not state.get("critique"):
        return {"next": "critic"}
    return {"next": "end"}


# [教学注释] `analyst_node`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

def analyst_node(state: OrchState) -> dict[str, Any]:
    """分析员：生成提纲。"""
    topic = state.get("topic", "").strip() or "未命名主题"
    outline = (
        f"1) {topic} 的目标用户\n"
        f"2) {topic} 的核心用例\n"
        f"3) {topic} 的风险与边界"
    )
    return {"outline": outline, "next": "supervisor"}


# [教学注释] `writer_node`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

def writer_node(state: OrchState) -> dict[str, Any]:
    """写作者：根据提纲写草案。"""
    outline = state.get("outline", "")
    draft = (
        "【草案】在理解以下提纲的基础上，我们给出实现建议：\n"
        f"{outline}\n"
        "建议采用迭代交付，并在关键节点引入人工确认（衔接第 23 小时）。"
    )
    return {"draft": draft, "next": "supervisor"}


# [教学注释] `critic_node`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

def critic_node(state: OrchState) -> dict[str, Any]:
    """评审：对草案提出简短意见。"""
    draft = state.get("draft", "")
    critique = (
        "【评审】整体结构清晰。需要补充：验收标准、失败回滚策略、监控指标。\n"
        f"针对草案摘录：{draft[:80]}..."
    )
    return {"critique": critique, "next": "supervisor"}


# [教学注释] `_route_supervisor`
# 根据状态选择下一条执行路径。

def _route_supervisor(state: OrchState) -> str:
    return state.get("next", "end")


# [教学注释] `_run_orchestration_mock`
# 内部辅助函数，为主流程提供局部能力。

def _run_orchestration_mock(initial: OrchState) -> OrchState:
    """无 LangGraph 时的同构模拟：重复 supervisor → worker 直到结束。"""
    state: OrchState = dict(initial)
    print("提示: 未使用 LangGraph（导入失败或未安装），以下按 supervisor 循环模拟执行。")
    workers = {
        "analyst": analyst_node,
        "writer": writer_node,
        "critic": critic_node,
    }
    while True:
        print("-- 节点: supervisor --")
        state.update(supervisor_node(state))
        nxt = state.get("next", "end")
        if nxt == "end":
            break
        worker = workers.get(nxt)
        if not worker:
            print(f"未知跳转: {nxt}，终止。")
            break
        print(f"-- 节点: {nxt} --")
        state.update(worker(state))
    return state


# [教学注释] `build_graph`
# 定义节点、边和路由关系，是图编排的关键入口。

def build_graph():  # noqa: ANN201 — 返回已编译图，类型随 LangGraph 版本略有差异
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        return None

    graph = StateGraph(OrchState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("writer", writer_node)
    graph.add_node("critic", critic_node)

    graph.set_entry_point("supervisor")
    graph.add_edge("analyst", "supervisor")
    graph.add_edge("writer", "supervisor")
    graph.add_edge("critic", "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        _route_supervisor,
        {
            "analyst": "analyst",
            "writer": "writer",
            "critic": "critic",
            "end": END,
        },
    )
    return graph.compile()


# [教学注释] `run_orchestration`
# 驱动一段完整流程，把前面准备好的零件真正串起来。

def run_orchestration(topic: str) -> OrchState:
    """编译并运行编排图。"""
    initial: OrchState = {"topic": topic}
    app = build_graph()
    if app is None:
        return _run_orchestration_mock(initial)

    final_state = app.invoke(initial)
    return final_state  # type: ignore[return-value]


# [教学注释] `main`
# 脚本入口，通常只负责启动案例。

def main() -> None:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("提示: 本章示例不强制使用模型；未配置 OPENAI_API_KEY 不影响运行。")

    topic = "为内部运营同学做一个「周报汇总」助手"
    print("=== 多智能体编排（Supervisor + Workers）===")
    result = run_orchestration(topic)
    print("=== 最终状态 ===")
    for k in ("topic", "outline", "draft", "critique"):
        print(f"[{k}]\n{result.get(k, '')}\n")


if __name__ == "__main__":
    main()
