"""
第 1 小时：最小 Agent（无 LLM）
演示 Thought / Action / Observation / Summary 的闭环结构。
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, Tuple


# ---------- 工具层：Agent 可调用的外部能力 ----------


def tool_multiply(a: float, b: float) -> str:
    """返回两数乘积的字符串，便于日志阅读。"""
    return str(a * b)


def tool_say(template: str, value: str) -> str:
    """把数值填入模板，模拟「格式化输出」类工具。"""
    return template.replace("{value}", value)


TOOLS: Dict[str, Callable[..., str]] = {
    "multiply": tool_multiply,
    "say": tool_say,
}


def run_tool(name: str, args: Dict[str, Any]) -> str:
    """根据工具名执行对应函数，并统一做参数校验。"""
    if name not in TOOLS:
        return f"[错误] 未知工具: {name}"
    fn = TOOLS[name]
    try:
        return fn(**args)
    except TypeError as e:
        return f"[错误] 参数不匹配 {name}({args}): {e}"


# ---------- 「假大脑」：用规则模拟决策（第 2 小时会换成 LLM） ----------


def fake_brain(user_text: str) -> Tuple[str, str, Dict[str, Any], bool]:
    """
    返回 (thought, action, args, finished)。
    finished=True 表示本 episode 结束（不再产生新的 Action）。
    """
    text = user_text.strip()

    # 教学用固定任务：识别「3.5 * 4」并分两步完成
    m = re.search(r"([\d.]+)\s*\*\s*([\d.]+)", text)
    if not m:
        thought = "我没从输入里识别到「a * b」形式的乘法题，只能演示固定流程。"
        return thought, "", {}, True

    a, b = float(m.group(1)), float(m.group(2))

    # 第一步：先算乘积
    if "第一步" not in text and "已完成 multiply" not in text:
        thought = f"用户想计算 {a}*{b}。我应先用 multiply 得到数值结果。"
        return thought, "multiply", {"a": a, "b": b}, False

    # 第二步：把结果包装成自然语言（这里用 say 工具演示「后处理」）
    if "已完成 multiply" in text and "已完成 say" not in text:
        thought = "乘积已得到。下一步用 say 把结果填入模板，生成最终回答。"
        return (
            thought,
            "say",
            {
                "template": "计算结果是：{value}",
                "value": text.split("乘积=", 1)[-1].strip(),
            },
            False,
        )

    thought = "流程已完成。"
    return thought, "", {}, True


def run_episode(user_text: str) -> None:
    """跑完一个「任务片段」：多轮 Thought→Action→Observation。"""
    scratchpad = user_text
    memory_notes: list[str] = []

    print("\n=== Memory（本轮工作记忆，教学展示）===")
    print("（本章 Memory 只是 Python 列表；第 7 小时会把它升级成对话记忆）")
    print("=== 开始 ===\n")

    for step in range(1, 6):
        thought, action, args, finished = fake_brain(scratchpad)
        print(f"[Step {step}] Thought: {thought}")

        if finished and not action:
            print("[Step {step}] Summary: 任务结束。".format(step=step))
            break

        print(f"[Step {step}] Action: {action} {json.dumps(args, ensure_ascii=False)}")
        obs = run_tool(action, args)
        print(f"[Step {step}] Observation: {obs}")

        memory_notes.append(f"step{step}: {action} -> {obs}")
        print(
            f"[Step {step}] Memory(update): 追加一条笔记（共 {len(memory_notes)} 条）"
        )

        # 把观察写回「草稿」，让假大脑能进入下一步
        if action == "multiply":
            scratchpad += f"\n[已完成 multiply] 乘积={obs}"
        elif action == "say":
            scratchpad += f"\n[已完成 say] 最终输出={obs}"
        else:
            scratchpad += f"\n[观察] {obs}"

    print("\n=== Summary（人类可读总结）===")
    if memory_notes:
        print("本轮关键步骤：")
        for line in memory_notes:
            print("-", line)
    else:
        print("没有产生工具调用。")


def main() -> None:
    demo = "请帮我算 3.5 * 4，并把结果用一句话告诉我。"
    print("【第 1 小时】最小 Agent（无 LLM）")
    print("用户任务：", demo)
    run_episode(demo)


if __name__ == "__main__":
    main()
