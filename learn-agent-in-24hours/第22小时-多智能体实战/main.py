"""
第 22 小时：多智能体实战

这份 main.py 是本章对应的最小可运行教学案例。

阅读建议：
1. 先看 main() 怎么启动案例。
2. 再看主流程函数如何驱动模型、工具、状态或路由。
3. 最后再看辅助函数，理解它们分别承担什么职责。

本章新增能力：把角色、技能和状态合成完整系统。
如果你是初学者，建议一边运行一边对照源码，不要只静态阅读。
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypedDict

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass


@dataclass
class Skill:
    name: str
    description: str
    run: Callable[..., str]


# [教学注释] `run_skill`
# 统一技能执行入口。

def run_skill(registry: dict[str, Skill], name: str, *args: Any, **kwargs: Any) -> str:
    """按名称执行已注册技能。"""
    sk = registry.get(name)
    if not sk:
        return f"未知技能: {name}"
    return sk.run(*args, **kwargs)


# [教学注释] `skill_estimate_effort`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

def skill_estimate_effort(text: str) -> str:
    """根据需求文本粗估人天（教学用启发式，非真实项目管理）。"""
    n = len(re.findall(r"[\u4e00-\u9fff]", text)) + len(text.split())
    low = max(1, n // 40)
    high = max(low + 1, n // 20)
    return f"粗估交付: {low}-{high} 人日（仅演示算法，勿用于正式排期）"


# [教学注释] `skill_test_checklist`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

def skill_test_checklist(feature: str) -> str:
    """生成最小测试清单。"""
    return (
        f"针对「{feature[:40]}...」的测试清单：\n"
        "- 主流程 happy path\n"
        "- 边界输入/空输入\n"
        "- 权限与鉴权（若适用）\n"
        "- 失败重试与超时\n"
    )


class BattleState(TypedDict, total=False):
    idea: str
    prd: str
    estimate: str
    qa_plan: str
    delivery: str
    next: str


# [教学注释] `_maybe_llm`
# 内部辅助函数，为主流程提供局部能力。

def _maybe_llm(system: str, user: str) -> str | None:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip(), base_url=base_url)
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        print(f"模型调用失败，使用模板: {exc}")
        return None


# [教学注释] `build_skill_registry`
# 负责组装对象、提示词、索引、图或应用实例。

def build_skill_registry() -> dict[str, Skill]:
    reg: dict[str, Skill] = {}
    reg["estimate_effort"] = Skill(
        "estimate_effort",
        "粗估人日",
        skill_estimate_effort,
    )
    reg["build_test_checklist"] = Skill(
        "build_test_checklist",
        "测试清单",
        skill_test_checklist,
    )
    return reg


REGISTRY = build_skill_registry()


# [教学注释] `supervisor_node`
# 调度节点，决定当前轮到谁工作。

def supervisor_node(state: BattleState) -> dict[str, Any]:
    if not state.get("prd"):
        return {"next": "pm"}
    if not state.get("estimate"):
        return {"next": "dev"}
    if not state.get("qa_plan"):
        return {"next": "qa"}
    if not state.get("delivery"):
        return {"next": "publisher"}
    return {"next": "end"}


# [教学注释] `pm_node`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

def pm_node(state: BattleState) -> dict[str, Any]:
    idea = state.get("idea", "").strip()
    sys_prompt = "你是产品经理，用中文输出简短 PRD 摘要，含：背景/目标/范围/里程碑。"
    text = _maybe_llm(sys_prompt, idea)
    if text is None:
        text = (
            f"【PRD 摘要】\n"
            f"背景: 用户提出想法「{idea}」。\n"
            f"目标: 验证价值并形成可交付增量。\n"
            f"范围: MVP 仅覆盖主流程；非目标：复杂个性化。\n"
            f"里程碑: M1 原型 → M2 内测 → M3 上线复盘。"
        )
    return {"prd": text.strip(), "next": "supervisor"}


# [教学注释] `dev_node`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

def dev_node(state: BattleState) -> dict[str, Any]:
    blob = f"{state.get('idea','')}\n{state.get('prd','')}"
    est = run_skill(REGISTRY, "estimate_effort", blob)
    return {"estimate": est, "next": "supervisor"}


# [教学注释] `qa_node`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

def qa_node(state: BattleState) -> dict[str, Any]:
    feature = state.get("prd") or state.get("idea") or "未命名需求"
    qa = run_skill(REGISTRY, "build_test_checklist", feature)
    return {"qa_plan": qa, "next": "supervisor"}


# [教学注释] `publisher_node`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

def publisher_node(state: BattleState) -> dict[str, Any]:
    pack = (
        "====== 交付包（教学示例）======\n"
        f"{state.get('prd','')}\n\n"
        f"{state.get('estimate','')}\n\n"
        f"{state.get('qa_plan','')}\n"
        "================================\n"
        "提示: 生产环境应接入审批、审计与监控（见第 23–24 小时）。"
    )
    return {"delivery": pack.strip(), "next": "supervisor"}


# [教学注释] `_route_supervisor`
# 根据状态选择下一条执行路径。

def _route_supervisor(state: BattleState) -> str:
    return state.get("next", "end")


# [教学注释] `_run_battle_mock`
# 内部辅助函数，为主流程提供局部能力。

def _run_battle_mock(initial: BattleState) -> BattleState:
    state: BattleState = dict(initial)
    print("提示: LangGraph 不可用，使用与 supervisor 循环等价的模拟执行。")
    workers = {
        "pm": pm_node,
        "dev": dev_node,
        "qa": qa_node,
        "publisher": publisher_node,
    }
    while True:
        print("-- supervisor --")
        state.update(supervisor_node(state))
        if state.get("next") == "end":
            break
        w = workers.get(state.get("next", ""))
        if not w:
            break
        print(f"-- {state.get('next')} --")
        state.update(w(state))
    return state


# [教学注释] `build_graph`
# 定义节点、边和路由关系，是图编排的关键入口。

def build_graph():  # noqa: ANN201
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        return None

    g = StateGraph(BattleState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("pm", pm_node)
    g.add_node("dev", dev_node)
    g.add_node("qa", qa_node)
    g.add_node("publisher", publisher_node)
    g.set_entry_point("supervisor")
    for n in ("pm", "dev", "qa", "publisher"):
        g.add_edge(n, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        _route_supervisor,
        {"pm": "pm", "dev": "dev", "qa": "qa", "publisher": "publisher", "end": END},
    )
    return g.compile()


# [教学注释] `run_battle`
# 驱动一段完整流程，把前面准备好的零件真正串起来。

def run_battle(idea: str) -> BattleState:
    initial: BattleState = {"idea": idea}
    app = build_graph()
    if app is None:
        return _run_battle_mock(initial)
    return app.invoke(initial)  # type: ignore[return-value]


# [教学注释] `main`
# 脚本入口，通常只负责启动案例。

def main() -> None:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("提示: 未配置 OPENAI_API_KEY 时，PM 节点使用模板 PRD；技能与编排仍可用。")

    idea = "做一个能把会议纪要转成行动项并@负责人的内部机器人"
    print("=== 多智能体 + Skills 综合实战 ===")
    result = run_battle(idea)
    print(result.get("delivery", ""))


if __name__ == "__main__":
    main()
