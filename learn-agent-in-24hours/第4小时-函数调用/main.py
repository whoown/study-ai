"""
第 4 小时：函数调用

这份 main.py 是本章对应的最小可运行教学案例。

阅读建议：
1. 先看 main() 怎么启动案例。
2. 再看主流程函数如何驱动模型、工具、状态或路由。
3. 最后再看辅助函数，理解它们分别承担什么职责。

本章新增能力：用结构化协议描述工具调用。
如果你是初学者，建议一边运行一边对照源码，不要只静态阅读。
"""
from __future__ import annotations

import json
import os
import uuid
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path

try:
    from dotenv import load_dotenv

    _ROOT = Path(__file__).resolve().parents[1]
    load_dotenv(_ROOT / '.env')
except ImportError:
    pass


# [教学注释] `load_settings`
# 加载配置、数据或环境信息，让主流程保持简洁。

def load_settings() -> Tuple[Optional[str], str, str]:
    key = os.getenv("OPENAI_API_KEY")
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    if key in (None, "", "your_api_key_here"):
        return None, base, model
    return key, base, model


# ---------- 工具实现 ----------


# [教学注释] `tool_multiply`
# 教学工具函数，负责向 Agent 暴露一种可调用能力。

def tool_multiply(a: float, b: float) -> str:
    return str(a * b)


# [教学注释] `tool_say`
# 教学工具函数，负责向 Agent 暴露一种可调用能力。

def tool_say(template: str, value: str) -> str:
    return template.replace("{value}", value)


# [教学注释] `tool_finish`
# 教学工具函数，负责向 Agent 暴露一种可调用能力。

def tool_finish(note: str = "") -> str:
    """显式结束工具（教学用）：让模型有机会做收尾声明。"""
    return note or "done"


TOOLS: Dict[str, Callable[..., str]] = {
    "multiply": tool_multiply,
    "say": tool_say,
    "finish": tool_finish,
}


# [教学注释] `run_tool`
# 统一工具执行入口，便于集中做参数校验、错误处理和日志打印。

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


# [教学注释] `mock_choice`
# 离线教学分支，帮助你在没有外部依赖时也能理解流程。

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


# [教学注释] `call_model`
# 负责真正与模型交互，并把结果交回主流程。

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


# [教学注释] `run_session`
# 完整会话驱动器，负责串起消息、工具和结果。

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


# [教学注释] `main`
# 脚本入口，通常只负责启动案例。

def main() -> None:
    print("【第 4 小时】函数调用（tools / tool_calls）")
    goal = "计算 6 * 7，并输出：乘积是：<整数>（用 say）。"
    print("用户任务：", goal)
    run_session(goal)


if __name__ == "__main__":
    main()
