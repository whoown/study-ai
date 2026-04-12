# -*- coding: utf-8 -*-
"""
第 18 小时：状态持久化 — 将计划与运行态保存为 checkpoint，并演示恢复续跑。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class RunState(BaseModel):
    """可序列化的运行状态（教学用最小字段集）。"""

    goal: str
    step_index: int = 0
    completed: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class Checkpoint(BaseModel):
    """检查点：计划 + 状态 + 事件历史。"""

    version: int = 1
    plan: list[dict[str, Any]] = Field(default_factory=list)
    state: RunState
    history: list[dict[str, Any]] = Field(default_factory=list)


def default_plan() -> list[dict[str, Any]]:
    return [
        {"id": "lint", "title": "静态检查"},
        {"id": "test", "title": "运行单元测试"},
        {"id": "deploy", "title": "发布到预发环境"},
    ]


def checkpoint_path() -> Path:
    chapter_dir = Path(__file__).resolve().parents[1]
    return chapter_dir / ".checkpoint_lesson18.json"


def save_checkpoint(cp: Checkpoint) -> None:
    path = checkpoint_path()
    path.write_text(json.dumps(cp.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[checkpoint] 已写入：{path}")


def load_checkpoint() -> Checkpoint | None:
    path = checkpoint_path()
    if not path.exists():
        print("[checkpoint] 未发现历史检查点。")
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"[checkpoint] 已读取：{path}")
    return Checkpoint.model_validate(data)


def print_checkpoint_summary(cp: Checkpoint) -> None:
    """打印检查点摘要，突出可观测字段。"""
    summary = {
        "version": cp.version,
        "goal": cp.state.goal,
        "step_index": cp.state.step_index,
        "completed": cp.state.completed,
        "plan_ids": [p["id"] for p in cp.plan],
        "history_tail": cp.history[-3:],
    }
    print("[checkpoint_summary]", json.dumps(summary, ensure_ascii=False, indent=2))


def simulate_step(cp: Checkpoint, *, crash_after_this: bool = False) -> None:
    """执行当前 step_index 指向的步骤，并推进索引。"""
    plan = cp.plan
    i = cp.state.step_index
    if i >= len(plan):
        print("[run] 所有步骤已完成。")
        return

    step = plan[i]
    print(f"\n[execute] step_index={i} id={step['id']} title={step['title']}")
    cp.history.append({"event": "step_start", "index": i, "id": step["id"]})

    # 模拟产出
    cp.state.artifacts[step["id"]] = {"ok": True, "report": f"{step['id']} passed"}
    cp.state.completed.append(step["id"])
    cp.history.append({"event": "step_done", "index": i, "id": step["id"]})

    print(
        "[task_state]",
        json.dumps(
            {
                "step_index": i,
                "completed": cp.state.completed,
                "artifact_keys": list(cp.state.artifacts.keys()),
            },
            ensure_ascii=False,
        ),
    )

    cp.state.step_index = i + 1

    if crash_after_this:
        save_checkpoint(cp)
        print(f"[crash] 模拟在步骤索引 {i} 完成后崩溃（已持久化 checkpoint）。")


def run_with_crash_then_resume_demo() -> None:
    print("第 18 小时：状态持久化")

    path = checkpoint_path()
    if path.exists():
        path.unlink()
        print(f"[reset] 已删除旧 checkpoint：{path}")

    cp = Checkpoint(
        plan=default_plan(),
        state=RunState(goal="StudyFlow 发布流水线（教学模拟）", step_index=0),
    )

    print("\n--- 场景 A：首次运行，完成第二步后写入 checkpoint 并中断 ---")
    print("[plan]", json.dumps(cp.plan, ensure_ascii=False, indent=2))
    simulate_step(cp)
    simulate_step(cp, crash_after_this=True)

    print("\n--- 场景 B：读取 checkpoint 并续跑 ---")
    loaded = load_checkpoint()
    if loaded is None:
        print("[error] 未能加载 checkpoint。")
        return

    print_checkpoint_summary(loaded)
    # 从崩溃点已推进的 step_index 继续：此处应为 2（准备执行 deploy）
    while loaded.state.step_index < len(loaded.plan):
        simulate_step(loaded)

    save_checkpoint(loaded)
    print("\n[done] 全流程结束，最终 checkpoint：")
    print_checkpoint_summary(loaded)


def recover_from_checkpoint() -> None:
    """独立入口：仅演示恢复（读者可单独调用）。"""
    cp = load_checkpoint()
    if cp is None:
        return
    print_checkpoint_summary(cp)
    while cp.state.step_index < len(cp.plan):
        simulate_step(cp)
    save_checkpoint(cp)


def main() -> None:
    run_with_crash_then_resume_demo()


if __name__ == "__main__":
    main()
