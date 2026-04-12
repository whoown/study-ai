"""
第 4 小时：函数调用（OpenAI tools / tool_calls 协议）
"""

from __future__ import annotations

import json
import os
import uuid
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


# ---------- 工具实现 ----------


def tool_multiply(a: float, b: float) -> str:
    return str(a * b)


def tool_say(template: str, value: str) -> str:
    return template.replace("{value}", value)


def tool_finish(note: str = "") -> str:
    """显式结束工具（教学用）：让模型有机会做收尾声明。"""
    return note or "done"


TOOLS: Dict[str, Callable[..., str]] = {
    "multiply": tool_multiply,
    "say": tool_say,
    "finish": tool_finish,
}


def run_tool(name: str, arguments_json: str) -> str:
    """根据函数名与参数 JSON 字符串执行工具。"""
    try:
        args = json.loads(arguments_json or "{}")
    except json.JSONDecodeError as e:
        return f"[错误] 参数不是合法 JSON：{e}"
    if name not in TOOLS:
        return f"[错误] 未知工具: {name}"
    try:
        return TOOLS[name](**args)
    except TypeError as e:
        return f"[错误] 参数不匹配 {name}({args}): {e}"


# ---------- OpenAI tools schema ----------


TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "计算两个数的乘积",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "say",
            "description": "把 value 填入 template 中的 {value} 占位符",
            "parameters": {
                "type": "object",
                "properties": {
                    "template": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["template", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "当任务完成时调用，可附带简短说明",
            "parameters": {
                "type": "object",
                "properties": {"note": {"type": "string"}},
            },
        },
    },
]


# ---------- 调用与 mock ----------


def mock_choice(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """模拟 API 返回的 choice 结构（含 tool_calls）。"""
    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    stage = len(tool_msgs)

    if stage == 0:
        return {
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock_1",
                        "type": "function",
                        "function": {
                            "name": "multiply",
                            "arguments": json.dumps({"a": 6, "b": 7}),
                        },
                    }
                ],
            }
        }
    if stage == 1:
        return {
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock_2",
                        "type": "function",
                        "function": {
                            "name": "say",
                            "arguments": json.dumps(
                                {
                                    "template": "乘积是：{value}",
                                    "value": "42",
                                }
                            ),
                        },
                    }
                ],
            }
        }
    if stage == 2:
        return {
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock_3",
                        "type": "function",
                        "function": {
                            "name": "finish",
                            "arguments": json.dumps({"note": "已完成格式化输出"}),
                        },
                    }
                ],
            }
        }
    # stage >= 3：不再发起工具调用，结束会话
    return {
        "message": {
            "role": "assistant",
            "content": "（mock）所有工具已执行完毕。",
        }
    }


def call_model(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    key, base, model = load_settings()
    if not key:
        print("\n[提示] 无有效 OPENAI_API_KEY，使用 mock_choice() 模拟 tool_calls。\n")
        return mock_choice(messages)

    url = f"{base}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "tools": TOOL_SPECS,
        "tool_choice": "auto",
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
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]
    except Exception as e:
        print(f"\n[错误] {e}\n[降级] mock_choice()\n")
        return mock_choice(messages)


def run_session(user_goal: str, max_rounds: int = 10) -> None:
    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": "你是工具型助手：优先用工具完成任务，最后调用 finish。",
        },
        {"role": "user", "content": user_goal},
    ]

    print("\n=== Memory：messages 保留完整 tool 协议轨迹 ===\n")

    for rnd in range(1, max_rounds + 1):
        choice = call_model(messages)
        msg = choice.get("message", {})
        messages.append(msg)

        content = msg.get("content")
        tcs = msg.get("tool_calls") or []

        print(f"[Round {rnd}] assistant.content = {content!r}")
        print(f"[Round {rnd}] tool_calls 数量 = {len(tcs)}")
        if content:
            print(f"[Round {rnd}] Thought(assistant 文本): {content}")

        if not tcs:
            print(f"[Round {rnd}] Observation: 无工具调用，会话结束。")
            break

        for tc in tcs:
            tid = tc.get("id", f"call_{uuid.uuid4().hex[:8]}")
            fn = tc.get("function", {})
            name = fn.get("name", "")
            arguments = fn.get("arguments", "{}")
            print(f"[Round {rnd}] Action: {name} args={arguments}")

            obs = run_tool(name, arguments)
            print(f"[Round {rnd}] Observation: {obs}")

            messages.append({"role": "tool", "tool_call_id": tid, "content": obs})

    print("\n=== Summary ===")
    print("函数调用的关键是：schema 约束参数 + tool_call_id 回填闭环。")


def main() -> None:
    print("【第 4 小时】函数调用（tools / tool_calls）")
    goal = "计算 6 * 7，并输出：乘积是：<整数>（用 say）。"
    print("用户任务：", goal)
    run_session(goal)


if __name__ == "__main__":
    main()
