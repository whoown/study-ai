"""
第 7 小时：短期记忆

这份 main.py 是本章对应的最小可运行教学案例。

阅读建议：
1. 先看 main() 怎么启动案例。
2. 再看主流程函数如何驱动模型、工具、状态或路由。
3. 最后再看辅助函数，理解它们分别承担什么职责。

本章新增能力：让 Agent 记住当前会话里的上下文。
如果你是初学者，建议一边运行一边对照源码，不要只静态阅读。
"""
from __future__ import annotations

import json
import os
import uuid
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


class ShortTermMemory:
    """短期记忆：会话级笔记，供注入提示词。"""

    def __init__(self, max_items: int = 12) -> None:
        self.max_items = max_items
        self._items: List[str] = []

    def note(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        self._items.append(text)
        self.trim()

    def trim(self) -> None:
        if len(self._items) > self.max_items:
            # 丢弃最旧条目（教学版策略；也可改成「摘要压缩」）
            overflow = len(self._items) - self.max_items
            self._items = self._items[overflow:]

    def render(self) -> str:
        if not self._items:
            return "（暂无）"
        lines = [f"- {x}" for x in self._items]
        return "\n".join(lines)


# ---------- 工具 ----------


PRICE_TABLE = {"banana": 2.5}


# [教学注释] `tool_get_unit_price`
# 教学工具函数，负责向 Agent 暴露一种可调用能力。

def tool_get_unit_price(item: str) -> str:
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


# [教学注释] `mock_choice`
# 离线教学分支，帮助你在没有外部依赖时也能理解流程。

def mock_choice(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    stage = len([m for m in messages if m.get("role") == "tool"])
    if stage == 0:
        return {
            "message": {
                "role": "assistant",
                "content": "Thought(mock): 查价",
                "tool_calls": [
                    {
                        "id": "m1",
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
                        "id": "m2",
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
                        "id": "m3",
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
                        "id": "m4",
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


# [教学注释] `build_base_system`
# 负责组装对象、提示词、索引、图或应用实例。

def build_base_system() -> str:
    return "你是带工具的助手：查价->相乘->say->finish。优先使用工具。"


# [教学注释] `rebuild_messages`
# 按需要重建下一次模型调用所需消息。

def rebuild_messages(
    base_system: str, user_text: str, history_tail: List[Dict[str, Any]], memory: ShortTermMemory
) -> List[Dict[str, Any]]:
    """每一轮重建消息：system 注入最新记忆，避免历史里 system 过期。"""
    mem_block = memory.render()
    system = (
        base_system
        + "\n\n【短期记忆（已由程序维护，请当作事实参考）】\n"
        + mem_block
    )
    out: List[Dict[str, Any]] = [{"role": "system", "content": system}]
    out.append({"role": "user", "content": user_text})
    out.extend(history_tail)
    return out


# [教学注释] `run_session_with_memory`
# 驱动一段完整流程，把前面准备好的零件真正串起来。

def run_session_with_memory(user_goal: str, max_rounds: int = 12) -> None:
    memory = ShortTermMemory(max_items=8)
    base_system = build_base_system()

    # history_tail：从第 2 轮开始累积 assistant/tool（不含首条 user）
    history_tail: List[Dict[str, Any]] = []

    print("\n=== Memory 区块：ShortTermMemory.render() 会注入 system ===\n")

    for rnd in range(1, max_rounds + 1):
        messages = rebuild_messages(base_system, user_goal, history_tail, memory)
        approx_chars = sum(len(json.dumps(m, ensure_ascii=False)) for m in messages)
        print(f"[Round {rnd}] Context 近似规模: {approx_chars} 字符（json 串长度估算）")

        choice = call_model(messages)
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

            memory.note(f"工具 {name} 输出：{obs}")
            print(f"[Round {rnd}] Memory(update):\n{memory.render()}\n")

            history_tail.append({"role": "tool", "tool_call_id": tid, "content": obs})

    print("\n=== Summary ===")
    print("短期记忆的价值：把长对话里‘已验证事实’单独挂到提示词上，降低遗忘。")


# [教学注释] `main`
# 脚本入口，通常只负责启动案例。

def main() -> None:
    print("【第 7 小时】短期记忆")
    goal = "买 2 斤 banana 多少钱？一句话回答。"
    print("用户任务：", goal)
    run_session_with_memory(goal)


if __name__ == "__main__":
    main()
