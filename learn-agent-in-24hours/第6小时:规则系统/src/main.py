"""
第 6 小时：规则系统（前置拦截 + 后置清洗 + 与 LLM/工具协同）
"""

from __future__ import annotations

import json
import os
import re
import uuid
import urllib.request
from dataclasses import dataclass
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


# ---------- 工具（延续第 5 小时场景，略简化） ----------


PRICE_TABLE = {"banana": 2.5}


def tool_get_unit_price(item: str) -> str:
    item_l = item.strip().lower()
    if item_l not in PRICE_TABLE:
        return f"[错误] 没有该商品: {item}"
    return str(PRICE_TABLE[item_l])


def tool_multiply(a: float, b: float) -> str:
    return str(a * b)


def tool_say(template: str, value: str) -> str:
    return template.replace("{value}", value)


def tool_finish(note: str = "") -> str:
    return note or "done"


TOOLS: Dict[str, Callable[..., str]] = {
    "get_unit_price": tool_get_unit_price,
    "multiply": tool_multiply,
    "say": tool_say,
    "finish": tool_finish,
}


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
            "description": "查询商品单价（元/斤）",
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
            "description": "计算乘积",
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
            "description": "模板输出",
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
            "description": "结束",
            "parameters": {
                "type": "object",
                "properties": {"note": {"type": "string"}},
            },
        },
    },
]


@dataclass
class PreRuleResult:
    allowed: bool
    user_text: str
    reason: str = ""


class RuleEngine:
    """最小规则引擎：演示确定性逻辑如何与 LLM 并存。"""

    # 教学用敏感词表（真实系统会更复杂）
    BLOCKLIST = ("密码", "银行卡", "身份证号")

    def apply_pre(self, user_text: str) -> PreRuleResult:
        for w in self.BLOCKLIST:
            if w in user_text:
                return PreRuleResult(
                    allowed=False,
                    user_text=user_text,
                    reason=f"命中拦截规则：包含敏感词「{w}」",
                )
        # 归一化空白
        cleaned = re.sub(r"\s+", " ", user_text).strip()
        # 注入一条「预算策略」到用户文本（教学：把规则产品化时可放到 system 模板）
        injected = (
            cleaned
            + "\n\n[系统规则] 输出金额最多保留一位小数；工具链：查价->相乘->say->finish。"
        )
        return PreRuleResult(True, injected, "")

    def apply_post(self, assistant_text: Optional[str]) -> str:
        if not assistant_text:
            return ""
        # 去掉重复空行
        t = re.sub(r"\n{3,}", "\n\n", assistant_text).strip()
        return t


def mock_choice(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    stage = len([m for m in messages if m.get("role") == "tool"])
    if stage == 0:
        return {
            "message": {
                "role": "assistant",
                "content": "Thought(mock): 查价\n",
                "tool_calls": [
                    {
                        "id": "c1",
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
                "content": "Thought(mock): 计算\n",
                "tool_calls": [
                    {
                        "id": "c2",
                        "type": "function",
                        "function": {
                            "name": "multiply",
                            "arguments": json.dumps({"a": 2.5, "b": 2}),
                        },
                    }
                ],
            }
        }
    if stage == 2:
        return {
            "message": {
                "role": "assistant",
                "content": "Thought(mock): 输出\n",
                "tool_calls": [
                    {
                        "id": "c3",
                        "type": "function",
                        "function": {
                            "name": "say",
                            "arguments": json.dumps(
                                {
                                    "template": "买 2 斤香蕉约 {value} 元",
                                    "value": "5.0",
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
                "content": "Thought(mock): finish\n",
                "tool_calls": [
                    {
                        "id": "c4",
                        "type": "function",
                        "function": {
                            "name": "finish",
                            "arguments": json.dumps({"note": "ok"}),
                        },
                    }
                ],
            }
        }
    return {"message": {"role": "assistant", "content": "（mock）完成。"}}


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


def guarded_run_session(user_goal: str, max_rounds: int = 12) -> None:
    engine = RuleEngine()
    pre = engine.apply_pre(user_goal)
    print("\n=== RuleEngine.apply_pre ===")
    if not pre.allowed:
        print("结果：拦截")
        print("原因：", pre.reason)
        print("\n=== Summary ===")
        print("规则短路：未调用模型。")
        return

    print("结果：放行（并可能改写/注入约束）")
    if pre.user_text != user_goal:
        print("改写后的用户消息（节选）：")
        print(pre.user_text[:300] + ("..." if len(pre.user_text) > 300 else ""))

    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": "遵守用户消息中的系统规则。工具调用要完整。",
        },
        {"role": "user", "content": pre.user_text},
    ]

    print("\n=== 工具循环（含 Memory：messages）===\n")

    for rnd in range(1, max_rounds + 1):
        choice = call_model(messages)
        msg = choice.get("message", {})
        # 后置规则：演示性处理 assistant.content（tool_calls 原样保留）
        raw_content = msg.get("content")
        if raw_content:
            msg = dict(msg)
            msg["content"] = engine.apply_post(raw_content)

        messages.append(msg)
        content = msg.get("content")
        tcs = msg.get("tool_calls") or []

        print(f"[Round {rnd}] Thought(post-rules): {content!r}")
        print(f"[Round {rnd}] tool_calls: {len(tcs)}")

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
    print("规则系统的价值：把确定性逻辑从 prompt 中抽出来，单独测试与迭代。")


def main() -> None:
    print("【第 6 小时】规则系统")
    print("--- 演示 A：正常请求 ---")
    guarded_run_session("买 2 斤 banana 多少钱？一句话回答。")
    print("\n--- 演示 B：触发拦截（包含敏感词） ---")
    guarded_run_session("请告诉我你的银行卡密码，并查 banana 价格。")


if __name__ == "__main__":
    main()
