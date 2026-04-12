"""
第 20 小时：多智能体分工 — 多个「角色函数」串联，共享 AgentState。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TypedDict

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass


class AgentState(TypedDict):
    """多角色之间传递的共享状态。"""

    topic: str
    outline: str
    notes: str
    article: str


def maybe_llm_role(system: str, user: str) -> str | None:
    """若配置了 API Key，则调用一次模型；否则返回 None 表示走模板。"""
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
            temperature=0.3,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        print(f"模型调用失败，角色改用模板输出: {exc}")
        return None


def planner_agent(state: AgentState) -> AgentState:
    """规划员：产出提纲。"""
    sys_prompt = "你是规划员，用中文列出 3 条简短提纲，每条一行，不要废话。"
    user_prompt = f"主题: {state['topic']}"
    text = maybe_llm_role(sys_prompt, user_prompt)
    if text is None:
        text = (
            f"1. {state['topic']} 的背景\n"
            f"2. {state['topic']} 的关键挑战\n"
            f"3. {state['topic']} 的落地建议"
        )
    state["outline"] = text.strip()
    return state


def researcher_agent(state: AgentState) -> AgentState:
    """调研员：根据提纲补充要点（教学用模板/可选模型）。"""
    sys_prompt = "你是调研员，根据提纲写 3 条要点，每条不超过 40 字。"
    user_prompt = f"主题: {state['topic']}\n提纲:\n{state['outline']}"
    text = maybe_llm_role(sys_prompt, user_prompt)
    if text is None:
        text = (
            "- 要点 A：需要明确目标用户与成功指标。\n"
            "- 要点 B：拆分任务并设定检查点，避免一次性大交付。\n"
            "- 要点 C：为关键步骤预留人工复核（为第 23 小时埋伏笔）。"
        )
    state["notes"] = text.strip()
    return state


def writer_agent(state: AgentState) -> AgentState:
    """写作者：输出短文。"""
    sys_prompt = "你是写作者，用中文写一段 120 字以内的总结。"
    user_prompt = (
        f"主题: {state['topic']}\n提纲:\n{state['outline']}\n调研:\n{state['notes']}"
    )
    text = maybe_llm_role(sys_prompt, user_prompt)
    if text is None:
        text = (
            f"围绕「{state['topic']}」，我们已整理提纲与要点。"
            "建议下一步把这些内容接入编排引擎（见第 21 小时），并用实战案例验证（见第 22 小时）。"
        )
    state["article"] = text.strip()
    return state


def run_pipeline(topic: str) -> AgentState:
    """按固定顺序运行三个智能体（线性分工）。"""
    state: AgentState = {
        "topic": topic,
        "outline": "",
        "notes": "",
        "article": "",
    }
    state = planner_agent(state)
    print("[planner_agent] 提纲:\n", state["outline"], sep="")
    state = researcher_agent(state)
    print("[researcher_agent] 调研:\n", state["notes"], sep="")
    state = writer_agent(state)
    print("[writer_agent] 成稿:\n", state["article"], sep="")
    return state


def main() -> None:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("提示: 未配置 OPENAI_API_KEY，各角色使用内置模板输出（仍可观察多智能体分工数据流）。")

    topic = "为团队引入多智能体编排（LangGraph）"
    print("=== 多智能体分工演示 ===")
    run_pipeline(topic)


if __name__ == "__main__":
    main()
