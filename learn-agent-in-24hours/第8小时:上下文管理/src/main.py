"""
第 8 小时：上下文管理（预算估算 + 安全截断 + 与短期记忆配合）
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


def load_settings() -> Tuple[str | None, str, str]:
    key = os.getenv("OPENAI_API_KEY")
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    if key in (None, "", "your_api_key_here"):
        return None, base, model
    return key, base, model


class ShortTermMemory:
    """与第 7 小时同构：用于在上下文被截断时保留关键事实。"""

    def __init__(self, max_items: int = 10) -> None:
        self.max_items = max_items
        self._items: List[str] = []

    def note(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        self._items.append(text)
        if len(self._items) > self.max_items:
            self._items = self._items[len(self._items) - self.max_items :]

    def render(self) -> str:
        if not self._items:
            return "（暂无）"
        return "\n".join(f"- {x}" for x in self._items)


class ContextManager:
    """教学用上下文管理：字符预算 + 尾部保留。"""

    def __init__(self, max_chars: int = 2800) -> None:
        self.max_chars = max_chars

    def estimate_chars(self, messages: List[Dict[str, Any]]) -> int:
        # 用 json 字符串长度近似「请求体膨胀程度」
        return len(json.dumps(messages, ensure_ascii=False))

    def shrink(self, messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
        """保留 system（若有）+ 尾部窗口；中间用占位提示替代。"""
        if self.estimate_chars(messages) <= self.max_chars:
            return messages, "未触发压缩"

        system_msg = None
        rest = messages
        if messages and messages[0].get("role") == "system":
            system_msg = messages[0]
            rest = messages[1:]

        # 从较大尾部开始尝试，直到进入预算或退无可退
        for keep in range(len(rest), 0, -1):
            tail = rest[-keep:]
            filler = {
                "role": "user",
                "content": (
                    "[上下文管理] 中间多轮 assistant/tool 轨迹已被截断。"
                    "请优先依据 system 中的【短期记忆】与下列尾部继续推理。"
                ),
            }
            candidate: List[Dict[str, Any]] = []
            if system_msg:
                candidate.append(system_msg)
            candidate.append(filler)
            candidate.extend(tail)
            if self.estimate_chars(candidate) <= self.max_chars:
                dropped = max(0, len(rest) - keep)
                note = f"已压缩：丢弃中间约 {dropped} 条消息，仅保留尾部 {keep} 条"
                return candidate, note

        # 极端情况：即使只保留 system + filler 仍超限（极少见）
        if system_msg:
            return [system_msg, {"role": "user", "content": "[上下文管理] 内容过长，已最小化。"}], "极限压缩"
        return messages, "压缩失败（回退原消息）"


# ---------- 工具（与前两章一致） ----------


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
            "description": "查询单价（元/斤）",
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


def mock_choice(completed_tool_rounds: int) -> Dict[str, Any]:
    """
    用「已完成工具次数」驱动剧情。
    注意：上下文压缩后，messages 里的 tool 条数可能变少，不能再用 len(tool) 推断阶段。
    """
    stage = completed_tool_rounds
    if stage == 0:
        return {
            "message": {
                "role": "assistant",
                "content": "Thought(mock): 查价",
                "tool_calls": [
                    {
                        "id": "x1",
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
                "content": "Thought(mock): 计算",
                "tool_calls": [
                    {
                        "id": "x2",
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
                "content": "Thought(mock): 输出",
                "tool_calls": [
                    {
                        "id": "x3",
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
                "content": "Thought(mock): finish",
                "tool_calls": [
                    {
                        "id": "x4",
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


def call_model(messages: List[Dict[str, Any]], completed_tool_rounds: int) -> Dict[str, Any]:
    key, base, model = load_settings()
    if not key:
        print("\n[提示] 无有效 OPENAI_API_KEY，使用 mock_choice()。\n")
        return mock_choice(completed_tool_rounds)

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
        return mock_choice(completed_tool_rounds)


def build_system_with_memory(base: str, memory: ShortTermMemory) -> Dict[str, Any]:
    content = (
        base
        + "\n\n【短期记忆】\n"
        + memory.render()
        + "\n\n【提示】若中间对话被截断，以短期记忆为准。"
    )
    return {"role": "system", "content": content}


def run_session(user_goal: str, max_rounds: int = 12) -> None:
    # 故意偏低，便于在少量轮次内触发压缩（可按需调大）
    ctx = ContextManager(max_chars=900)
    memory = ShortTermMemory(max_items=10)

    base_system = "你是带工具的助手：查价->相乘->say->finish。"
    history_tail: List[Dict[str, Any]] = []

    print("\n=== 上下文管理 + 短期记忆 ===\n")

    for rnd in range(1, max_rounds + 1):
        system_msg = build_system_with_memory(base_system, memory)
        raw_messages: List[Dict[str, Any]] = [system_msg]
        raw_messages.append({"role": "user", "content": user_goal})
        raw_messages.extend(history_tail)

        before = ctx.estimate_chars(raw_messages)
        compact, note = ctx.shrink(raw_messages)
        after = ctx.estimate_chars(compact)

        print(f"[Round {rnd}] ContextSummary: {note}")
        print(f"[Round {rnd}] 体量：压缩前≈{before}，压缩后≈{after}（字符近似）")

        completed_tools = len(
            [m for m in history_tail if m.get("role") == "tool"]
        )
        choice = call_model(compact, completed_tools)
        msg = choice.get("message", {})
        history_tail.append(msg)

        content = msg.get("content")
        tcs = msg.get("tool_calls") or []
        print(f"[Round {rnd}] Thought: {content!r}")
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
            memory.note(f"{name} -> {obs}")
            print(f"[Round {rnd}] Memory(update):\n{memory.render()}\n")

            history_tail.append({"role": "tool", "tool_call_id": tid, "content": obs})

    print("\n=== Summary ===")
    print("生产环境建议：用 tokenizer 计 token；截断时避免破坏 tool 配对；关键事实进记忆。")


def main() -> None:
    print("【第 8 小时】上下文管理")
    goal = "买 2 斤 banana 多少钱？一句话回答。"
    print("用户任务：", goal)
    run_session(goal)


if __name__ == "__main__":
    main()
