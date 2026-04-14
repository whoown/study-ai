"""
第 2 小时：接入真实 LLM

这份 main.py 是本章对应的最小可运行教学案例。

阅读建议：
1. 先看 main() 怎么启动案例。
2. 再看主流程函数如何驱动模型、工具、状态或路由。
3. 最后再看辅助函数，理解它们分别承担什么职责。

本章新增能力：把假大脑换成真实大模型。
如果你是初学者，建议一边运行一边对照源码，不要只静态阅读。
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path

# 可选加载 .env（与仓库根目录示例一致）
try:
    from dotenv import load_dotenv

    _ROOT = Path(__file__).resolve().parents[1]
    load_dotenv(_ROOT / '.env')
except ImportError:
    pass


# [教学注释] `load_settings`
# 加载配置、数据或环境信息，让主流程保持简洁。

def load_settings() -> Tuple[Optional[str], str, str]:
    """读取环境变量：api_key, base_url, model。"""
    key = os.getenv("OPENAI_API_KEY")
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    if key in (None, "", "your_api_key_here"):
        return None, base, model
    return key, base, model


# ---------- 工具层（与第 1 小时同构） ----------


# [教学注释] `tool_multiply`
# 教学工具函数，负责向 Agent 暴露一种可调用能力。

def tool_multiply(a: float, b: float) -> str:
    return str(a * b)


# [教学注释] `tool_say`
# 教学工具函数，负责向 Agent 暴露一种可调用能力。

def tool_say(template: str, value: str) -> str:
    return template.replace("{value}", value)


TOOLS: Dict[str, Callable[..., str]] = {
    "multiply": tool_multiply,
    "say": tool_say,
}


# [教学注释] `run_tool`
# 统一工具执行入口，便于集中做参数校验、错误处理和日志打印。

def run_tool(name: str, args: Dict[str, Any]) -> str:
    if name not in TOOLS:
        return f"[错误] 未知工具: {name}"
    try:
        return TOOLS[name](**args)
    except TypeError as e:
        return f"[错误] 参数不匹配 {name}({args}): {e}"


# ---------- LLM 调用：真实 / 模拟 ----------


# [教学注释] `mock_chat_completion`
# 离线教学分支，帮助你在没有外部依赖时也能理解流程。

def mock_chat_completion(messages: List[Dict[str, str]]) -> str:
    """
    教学用模拟：根据「工具反馈轮次」推进，避免 system 提示里的 tool 名干扰判断。
    """
    tool_rounds = sum(
        1
        for m in messages
        if m.get("role") == "user" and "observation=" in (m.get("content") or "")
    )
    if tool_rounds == 0:
        return json.dumps(
            {"thought": "先计算乘积。", "tool": "multiply", "args": {"a": 3.5, "b": 4}},
            ensure_ascii=False,
        )
    if tool_rounds == 1:
        return json.dumps(
            {
                "thought": "已有乘积，格式化输出。",
                "tool": "say",
                "args": {"template": "计算结果是：{value}", "value": "14"},
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {"thought": "没有更多信息了，结束。", "tool": "finish", "args": {}},
        ensure_ascii=False,
    )


# [教学注释] `chat_completion`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

def chat_completion(messages: List[Dict[str, str]]) -> str:
    """返回 assistant 文本（我们要求模型输出一行 JSON）。"""
    key, base, model = load_settings()
    if not key:
        print(
            "\n[提示] 未检测到有效 OPENAI_API_KEY，将使用本地 mock_chat_completion() 模拟模型输出。\n"
        )
        return mock_chat_completion(messages)

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
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="ignore")
        print(f"\n[HTTP 错误] {e.code}: {err}\n")
        print("[降级] 改用 mock_chat_completion() 继续演示。\n")
        return mock_chat_completion(messages)
    except Exception as e:
        print(f"\n[网络/解析错误] {e}\n[降级] 改用 mock_chat_completion() 继续演示。\n")
        return mock_chat_completion(messages)


# [教学注释] `parse_plan`
# 把模型文本计划解析成结构化步骤。

def parse_plan(text: str) -> Tuple[str, str, Dict[str, Any]]:
    """从模型输出中解析 thought/tool/args。"""
    text = text.strip()
    # 允许模型用 markdown 代码块包裹
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError(f"无法解析 JSON 计划: {text}")
    obj = json.loads(m.group(0))
    thought = str(obj.get("thought", ""))
    tool = str(obj.get("tool", ""))
    args = obj.get("args", {})
    if not isinstance(args, dict):
        args = {}
    return thought, tool, args


# [教学注释] `agent_loop`
# 本章主循环，负责驱动模型、工具和状态更新。

def agent_loop(user_goal: str, max_steps: int = 6) -> None:
    """Thought / Action / Observation 循环，由 LLM 产出计划。"""
    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "你是工具调度助手。每一步只输出一行 JSON，格式严格为：\n"
                '{"thought":"...","tool":"multiply|say|finish","args":{...}}\n'
                "规则：multiply 参数 a,b 为数字；say 参数 template,value 为字符串；"
                "finish 表示任务完成。"
            ),
        },
        {"role": "user", "content": user_goal},
    ]

    print("\n=== Memory（消息列表 messages，将作为下一轮的上下文）===")
    for step in range(1, max_steps + 1):
        raw = chat_completion(messages)
        print(f"\n[Step {step}] Thought(raw LLM): {raw}")
        try:
            thought, tool, args = parse_plan(raw)
        except Exception as e:
            print(f"[Step {step}] Observation: 解析失败：{e}")
            break

        print(f"[Step {step}] Thought(parsed): {thought}")
        print(f"[Step {step}] Action: {tool} {json.dumps(args, ensure_ascii=False)}")

        if tool == "finish":
            print(f"[Step {step}] Observation: （无工具调用）")
            break

        obs = run_tool(tool, args)
        print(f"[Step {step}] Observation: {obs}")

        # 把「模型原始输出 + 工具结果」写回对话，形成闭环
        messages.append({"role": "assistant", "content": raw})
        messages.append(
            {
                "role": "user",
                "content": f"工具输出 observation={obs}\n请继续输出下一步 JSON。",
            }
        )

    print("\n=== Summary ===")
    print("本轮对话已结束。你可以对比：有/无 API Key 时闭环是否都能跑通。")


# [教学注释] `main`
# 脚本入口，通常只负责启动案例。

def main() -> None:
    print("【第 2 小时】接入真实 LLM（urllib + OpenAI 兼容）")
    goal = "请计算 3.5 * 4，并用一句话输出：计算结果是：<数值>。"
    print("用户任务：", goal)
    agent_loop(goal)


if __name__ == "__main__":
    main()
