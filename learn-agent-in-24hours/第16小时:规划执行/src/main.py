# -*- coding: utf-8 -*-
"""
第 16 小时：规划执行 — 生成计划、按依赖逐步执行并维护 TaskState。
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TaskState:
    """运行时任务状态（可打印、可扩展为持久化）。"""

    goal: str
    current_step_id: str | None = None
    completed: set[str] = field(default_factory=set)
    artifacts: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    log: list[dict[str, Any]] = field(default_factory=list)


def build_plan(goal: str) -> list[dict[str, Any]]:
    """
    构造一个带依赖关系的线性+分支最小计划。
    字段说明：id, title, depends_on, tool
    """
    return [
        {
            "id": "s1",
            "title": "收集本版本变更摘要",
            "depends_on": [],
            "tool": "fetch_changelog",
        },
        {
            "id": "s2",
            "title": "生成对外公告草稿",
            "depends_on": ["s1"],
            "tool": "draft_release_note",
        },
        {
            "id": "s3",
            "title": "敏感词与合规检查",
            "depends_on": ["s2"],
            "tool": "compliance_scan",
        },
        {
            "id": "s4",
            "title": "汇总最终发布素材包",
            "depends_on": ["s1", "s2", "s3"],
            "tool": "bundle_assets",
        },
    ]


def can_run_step(step: dict[str, Any], completed: set[str]) -> bool:
    return all(dep in completed for dep in step.get("depends_on", []))


def fake_tool_call(step_id: str, tool: str, state: TaskState) -> dict[str, Any]:
    """
    模拟工具返回。含一次可恢复失败，用于展示执行器重试策略。
    """
    time.sleep(0.05)  # 模拟 IO

    if tool == "fetch_changelog":
        return {"ok": True, "payload": {"items": ["修复登录偶发超时", "新增导出审计日志"]}}

    if tool == "draft_release_note":
        base = state.artifacts.get("s1", {}).get("payload", {})
        return {
            "ok": True,
            "payload": {
                "markdown": f"版本亮点：{', '.join(base.get('items', []))}",
            },
        }

    if tool == "compliance_scan":
        # 第一次失败，第二次成功：展示状态机+重试
        attempts = sum(1 for e in state.log if e.get("step_id") == step_id)
        if attempts == 0:
            return {"ok": False, "error": "命中敏感词占位符（模拟）"}
        return {"ok": True, "payload": {"cleared": True}}

    if tool == "bundle_assets":
        draft = state.artifacts.get("s2", {}).get("payload", {})
        return {"ok": True, "payload": {"zip": "release_bundle.zip", "draft": draft}}

    return {"ok": False, "error": f"未知工具：{tool}"}


def run_plan_and_execute(goal: str) -> TaskState:
    plan = build_plan(goal)
    state = TaskState(goal=goal)

    print("第 16 小时：规划执行")
    print("\n[plan] 初始计划：")
    print(json.dumps(plan, ensure_ascii=False, indent=2))

    rng = random.Random(42)  # 固定种子，输出稳定（预留扩展用）

    while len(state.completed) < len(plan):
        runnable = [s for s in plan if s["id"] not in state.completed and can_run_step(s, state.completed)]
        if not runnable:
            state.errors.append("存在无法满足依赖的步骤，计划停滞。")
            break

        # 简单策略：取字典序第一个可运行步骤
        runnable.sort(key=lambda x: x["id"])
        step = runnable[0]
        state.current_step_id = step["id"]

        print(f"\n[execute] step={step['id']} tool={step['tool']} title={step['title']}")
        print(
            "[task_state]",
            json.dumps(
                {
                    "current_step_id": state.current_step_id,
                    "completed": sorted(state.completed),
                    "errors": state.errors[-2:],
                },
                ensure_ascii=False,
            ),
        )

        result = fake_tool_call(step["id"], step["tool"], state)
        state.log.append({"step_id": step["id"], "tool": step["tool"], "result": result})

        if result.get("ok"):
            state.artifacts[step["id"]] = result
            state.completed.add(step["id"])
            print(f"[observe] OK artifacts[{step['id']}] keys={list(result.get('payload', {}).keys())}")
        else:
            err = str(result.get("error", "unknown"))
            state.errors.append(f"{step['id']}: {err}")
            print(f"[observe] FAIL {err} — 将在下一轮对同一步骤重试（教学演示）")

        # 让随机源参与后续扩展（当前不影响结果）
        _ = rng.random()

    state.current_step_id = None
    print("\n[plan] 执行结束 — 完成度：", f"{len(state.completed)}/{len(plan)}")
    print("[task_state] 最终快照：")
    snapshot = asdict(state)
    snapshot["completed"] = sorted(state.completed)  # set 需转为列表便于 JSON 阅读
    print(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str))
    return state


def main() -> None:
    run_plan_and_execute(goal="准备 StudyFlow 2.3 发布说明素材")


if __name__ == "__main__":
    main()
