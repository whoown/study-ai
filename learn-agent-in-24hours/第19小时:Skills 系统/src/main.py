"""
第 19 小时：单 Agent + Skills 注册表（可选接入 OpenAI 函数调用）。
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# 将工程根目录加入路径，便于加载上一级 .env（与 run_demo.py 行为一致）
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
    """单个技能：名称、给人/模型看的说明、实际执行函数。"""

    name: str
    description: str
    run: Callable[..., str]


SKILL_REGISTRY: dict[str, Skill] = {}


def register_skill(skill: Skill) -> None:
    """注册技能到全局表。"""
    SKILL_REGISTRY[skill.name] = skill


def _skill_get_time(_: str) -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _skill_word_count(text: str) -> str:
    stripped = text.strip()
    return f"字数（含空格）: {len(stripped)}"


def _skill_echo_topic(topic: str) -> str:
    return f"已记录主题: {topic.strip()}"


def _openai_tools_schema() -> list[dict[str, Any]]:
    """构造 Chat Completions 的 tools 定义（仅用于演示）。"""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "返回当前本地时间字符串。",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "word_count",
                "description": "统计用户给出文本的字数（含空格）。",
                "parameters": {
                    "type": "object",
                    "properties": {"text": {"type": "string", "description": "要统计的文本"}},
                    "required": ["text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "echo_topic",
                "description": "复述并确认一个主题标题。",
                "parameters": {
                    "type": "object",
                    "properties": {"topic": {"type": "string", "description": "主题"}},
                    "required": ["topic"],
                },
            },
        },
    ]


def pick_skill_with_llm(user_text: str) -> tuple[str, str] | None:
    """
    使用 OpenAI 兼容 API 的 tool_calls 选择技能。
    返回 (技能名, 结果文本)；失败时返回 None。
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        print("未安装 openai 库，无法调用模型。请执行: pip install openai")
        return None

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": "你是技能调度器，只能调用提供的函数来完成用户需求，不要编造数据。",
                },
                {"role": "user", "content": user_text},
            ],
            tools=_openai_tools_schema(),
            tool_choice="auto",
        )
    except Exception as exc:  # noqa: BLE001 — 教学示例：打印友好错误
        print(f"调用模型失败（将降级到模拟调度）: {exc}")
        return None

    msg = resp.choices[0].message
    calls = getattr(msg, "tool_calls", None) or []
    if not calls:
        return None

    call = calls[0]
    fname = call.function.name
    raw_args = call.function.arguments or "{}"
    try:
        args = json.loads(raw_args)
    except json.JSONDecodeError:
        args = {}

    skill = SKILL_REGISTRY.get(fname)
    if not skill:
        return None

    if fname == "get_time":
        out = skill.run("")
    elif fname == "word_count":
        out = skill.run(args.get("text", user_text))
    elif fname == "echo_topic":
        out = skill.run(args.get("topic", user_text))
    else:
        out = skill.run(json.dumps(args, ensure_ascii=False))

    return fname, out


def pick_skill_mock(user_text: str) -> tuple[str, str]:
    """无 API Key 时的教学用路由：靠关键词选择技能。"""
    text = user_text.lower()
    if "时间" in user_text or "几点" in user_text:
        return "get_time", SKILL_REGISTRY["get_time"].run("")
    if "字数" in user_text or "多少字" in user_text:
        return "word_count", SKILL_REGISTRY["word_count"].run(user_text)
    return "echo_topic", SKILL_REGISTRY["echo_topic"].run(user_text)


def run_once(user_text: str) -> None:
    """执行一轮：优先 LLM 选技能，否则模拟调度。"""
    picked = pick_skill_with_llm(user_text)
    mode = "模型调度（tools）"
    if picked is None:
        mode = "教学模拟（关键词路由）"
        picked = pick_skill_mock(user_text)

    name, result = picked
    print(f"[模式] {mode}")
    print(f"[选中技能] {name}")
    print(f"[输出] {result}")


def main() -> None:
    register_skill(Skill("get_time", "返回当前时间", _skill_get_time))
    register_skill(Skill("word_count", "统计字数", _skill_word_count))
    register_skill(Skill("echo_topic", "复述主题", _skill_echo_topic))

    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("提示: 未检测到 OPENAI_API_KEY，将使用 pick_skill_mock 进行教学演示。")

    demos = [
        "现在几点了？",
        "请统计字数：今天学习 Skills 系统。",
        "主题为：多智能体编排实战。",
    ]
    for q in demos:
        print("-" * 48)
        print(f"用户: {q}")
        run_once(q)


if __name__ == "__main__":
    main()
