"""
第 5 小时：多工具决策

这份 main.py 是本章对应的最小可运行教学案例。

阅读建议：
1. 先看 main() 怎么启动案例。
2. 再看主流程函数如何驱动模型、工具、状态或路由。
3. 最后再看辅助函数，理解它们分别承担什么职责。

本章新增能力：让模型在多个工具之间做选择。
如果你是初学者，建议一边运行一边对照源码，不要只静态阅读。
"""
from __future__ import annotations

import json
import os
import uuid
import urllib.request
from typing import Any, Callable, Dict, List, Tuple

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


# [教学注释] `load_settings`
# 加载配置、数据或环境信息，让主流程保持简洁。

def load_settings() -> Tuple[str | None, str, str]:
    key = os.getenv("OPENAI_API_KEY")
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    if key in (None, "", "your_api_key_here"):
        return None, base, model
    return key, base, model


# ---------- 工具：价目表 + 计算 + 格式化 ----------


PRICE_TABLE = {"banana": 2.5, "apple": 3.0, "orange": 2.0}


# [教学注释] `tool_get_unit_price`
# 教学工具函数，负责向 Agent 暴露一种可调用能力。

def tool_get_unit_price(item: str) -> str:
    """返回单价（字符串），查不到则提示错误。"""
    item_l = item.strip().lower()
    if item_l not in PRICE_TABLE:
        return f"[错误] 没有该商品: {item}"
    return str(PRICE_TABLE[item_l])


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
    return note or "done"


TOOLS: Dict[str, Callable[..., str]] = {
    "get_unit_price": tool_get_unit_price,
    "multiply": tool_multiply,
    "say": tool_say,
    "finish": tool_finish,
}


# [教学注释] `run_tool`
# 统一工具执行入口，便于集中做参数校验、错误处理和日志打印。

def run_tool(name: str, arguments_json: str) -> str:
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


TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "get_unit_price",
            "description": "查询商品的单价（单位：元/斤）",
            "parameters": {
                "type": "object",
                "properties": {"item": {"type": "string"}},
                "required": ["item"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "计算两数乘积",
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
            "description": "把 value 填入 template 的 {value}",
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
            "description": "任务完成时调用",
            "parameters": {
                "type": "object",
                "properties": {"note": {"type": "string"}},
            },
        },
    },
]


# [教学注释] `mock_choice`
# 离线教学分支，帮助你在没有外部依赖时也能理解流程。

def mock_choice(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """按 tool 消息数量推进：询价 -> 相乘 -> 输出 -> 收尾 -> 停止。"""
    stage = len([m for m in messages if m.get("role") == "tool"])

    if stage == 0:
        return {
            "message": {
                "role": "assistant",
                "content": "Thought(mock): 先查 banana 单价。",
                "tool_calls": [
                    {
                        "id": "call_m1",
                        "type": "function",
                        "function": {
                            "name": "get_unit_price",
                            "arguments": json.dumps({"item": "banana"}),
                        },
                    }
                ],
            }
        }
    if stage == 1:
        return {
            "message": {
                "role": "assistant",
                "content": "Thought(mock): 单价已知，计算 2.5*3。",
                "tool_calls": [
                    {
                        "id": "call_m2",
                        "type": "function",
                        "function": {
                            "name": "multiply",
                            "arguments": json.dumps({"a": 2.5, "b": 3}),
                        },
                    }
                ],
            }
        }
    if stage == 2:
        return {
            "message": {
                "role": "assistant",
                "content": "Thought(mock): 生成一句话回答。",
                "tool_calls": [
                    {
                        "id": "call_m3",
                        "type": "function",
                        "function": {
                            "name": "say",
                            "arguments": json.dumps(
                                {
                                    "template": "买 3 斤香蕉花费：{value} 元",
                                    "value": "7.5",
                                }
                            ),
                        },
                    }
                ],
            }
        }
    if stage == 3:
        return {
            "message": {
                "role": "assistant",
                "content": "Thought(mock): 调用 finish。",
                "tool_calls": [
                    {
                        "id": "call_m4",
                        "type": "function",
                        "function": {
                            "name": "finish",
                            "arguments": json.dumps({"note": "完成"}),
                        },
                    }
                ],
            }
        }
    return {"message": {"role": "assistant", "content": "（mock）结束。"}}


# [教学注释] `call_model`
# 负责真正与模型交互，并把结果交回主流程。

def call_model(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    key, base, model = load_settings()
    if not key:
        print("\n[提示] 无有效 OPENAI_API_KEY，使用 mock_choice()。\n")
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

def run_session(user_goal: str, max_rounds: int = 12) -> None:
    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "你是多工具助手。严格按任务：先查价、再计算数量乘积、再用 say 输出一句话，"
                "最后 finish。不要跳步。"
            ),
        },
        {"role": "user", "content": user_goal},
    ]

    print("\n=== Memory：观察每轮 Thought（assistant.content）与 tool_calls ===\n")

    for rnd in range(1, max_rounds + 1):
        choice = call_model(messages)
        msg = choice.get("message", {})
        messages.append(msg)

        content = msg.get("content")
        tcs = msg.get("tool_calls") or []
        print(f"[Round {rnd}] Thought(可选文本): {content}")
        print(f"[Round {rnd}] tool_calls: {len(tcs)} 个")

        if not tcs:
            print(f"[Round {rnd}] Observation: 无工具调用，停止。")
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
    print("工具越多，越要把 function description 写清楚，减少歧义。")


# [教学注释] `main`
# 脚本入口，通常只负责启动案例。

def main() -> None:
    print("【第 5 小时】多工具决策")
    goal = "查 banana 的单价，买 3 斤要多少钱？用一句话回答。"
    print("用户任务：", goal)
    run_session(goal)


if __name__ == "__main__":
    main()
