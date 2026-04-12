"""
第 3 小时：手写 ReAct（Thought / Action / Action Input / Observation）
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def load_settings() -> Tuple[Optional[str], str, str]:
    key = os.getenv("OPENAI_API_KEY")
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    if key in (None, "", "your_api_key_here"):
        return None, base, model
    return key, base, model


# ---------- 工具 ----------


def tool_multiply(a: float, b: float) -> str:
    return str(a * b)


def tool_say(template: str, value: str) -> str:
    return template.replace("{value}", value)


TOOLS: Dict[str, Callable[..., str]] = {
    "multiply": tool_multiply,
    "say": tool_say,
}


def run_tool(name: str, args: Dict[str, Any]) -> str:
    if name not in TOOLS:
        return f"[错误] 未知工具: {name}"
    try:
        return TOOLS[name](**args)
    except TypeError as e:
        return f"[错误] 参数不匹配 {name}({args}): {e}"


# ---------- LLM ----------


def mock_react(messages: List[Dict[str, str]]) -> str:
    """无网络时，按「Observation 反馈次数」推进，避免重复匹配 say。"""
    obs_rounds = sum(
        1
        for m in messages
        if m.get("role") == "user" and "Observation:" in (m.get("content") or "")
    )
    if obs_rounds == 0:
        return (
            "Thought: 我需要先计算 2.5*8 的乘积。\n"
            "Action: multiply\n"
            'Action Input: {"a":2.5,"b":8}\n'
        )
    if obs_rounds == 1:
        return (
            "Thought: 乘积已得到，接下来用模板输出一句话。\n"
            "Action: say\n"
            'Action Input: {"template":"结果是：{value}","value":"20"}\n'
        )
    return (
        "Thought: 任务完成，无需再调用工具。\n"
        "Action: finish\n"
        "Action Input: {}\n"
    )


def chat_completion(messages: List[Dict[str, str]]) -> str:
    key, base, model = load_settings()
    if not key:
        print("\n[提示] 无有效 OPENAI_API_KEY，使用 mock_react()。\n")
        return mock_react(messages)

    url = f"{base}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"\n[错误] {e}\n[降级] mock_react()\n")
        return mock_react(messages)


_re_thought = re.compile(r"Thought:\s*(.+)", re.I)
_re_action = re.compile(r"Action:\s*(\S+)", re.I)
_re_input = re.compile(r"Action Input:\s*(\{[\s\S]*\})", re.I)


def parse_react_block(text: str) -> Tuple[str, str, Dict[str, Any]]:
    """解析 ReAct 三段式字段。"""
    t = _re_thought.search(text)
    a = _re_action.search(text)
    inp = _re_input.search(text)
    if not (t and a and inp):
        raise ValueError(f"ReAct 解析失败：{text}")
    thought = t.group(1).strip()
    action = a.group(1).strip()
    args = json.loads(inp.group(1))
    if not isinstance(args, dict):
        raise ValueError("Action Input 必须是 JSON 对象")
    return thought, action, args


def react_loop(user_goal: str, max_steps: int = 8) -> None:
    system = (
        "你是一个 ReAct 智能体。每一步必须严格输出以下三行（不要输出多余文本）：\n"
        "Thought: ...\n"
        "Action: multiply|say|finish\n"
        "Action Input: {...}\n"
        "其中 Action Input 必须是 JSON 对象。"
    )
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_goal},
    ]

    print("\n=== Memory：完整对话将被保留为上下文（为第 7/8 小时埋伏笔）===\n")

    for step in range(1, max_steps + 1):
        raw = chat_completion(messages)
        print(f"[Step {step}] --- LLM 原始输出 ---\n{raw}\n")

        try:
            thought, action, args = parse_react_block(raw)
        except Exception as e:
            print(f"[Step {step}] Observation: {e}")
            break

        print(f"[Step {step}] Thought: {thought}")
        print(f"[Step {step}] Action: {action}")
        print(f"[Step {step}] Action Input: {json.dumps(args, ensure_ascii=False)}")

        if action.lower() == "finish":
            print(f"[Step {step}] Observation: （结束）")
            break

        obs = run_tool(action, args)
        print(f"[Step {step}] Observation: {obs}")

        messages.append({"role": "assistant", "content": raw})
        messages.append(
            {"role": "user", "content": f"Observation: {obs}\n请继续下一步。"}
        )

    print("\n=== Summary ===")
    print("ReAct 的关键是：推理痕迹可打印、可回放、可单测解析器。")


def main() -> None:
    print("【第 3 小时】手写 ReAct")
    goal = "计算 2.5 * 8，并输出：结果是：<数值>（用 say 工具生成字符串）。"
    print("用户任务：", goal)
    react_loop(goal)


if __name__ == "__main__":
    main()
