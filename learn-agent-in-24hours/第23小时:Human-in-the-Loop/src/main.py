"""
第 23 小时：Human-in-the-Loop — 可观测的人工审批节点（交互 + 环境变量降级）。
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

HitlEvent = Literal[
    "draft_created",
    "pending_approval",
    "decision_recorded",
    "completed",
]


def emit_hitl_event(event: HitlEvent, payload: dict[str, Any] | None = None) -> None:
    """
    记录 HITL 事件到标准输出，便于肉眼观察或被日志系统采集。
    payload 使用 JSON 序列化，注意保持可打印、无敏感信息。
    """
    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "channel": "HITL",
        "event": event,
        "payload": payload or {},
    }
    print(f"[HITL] {json.dumps(record, ensure_ascii=False)}")


def _call_llm_optional(user_prompt: str) -> str | None:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip(), base_url=base_url)
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": "你是发布经理，用中文写一段不超过 120 字的上线说明草案。",
                },
                {"role": "user", "content": user_prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        emit_hitl_event("draft_created", {"mode": "llm_failed", "error": str(exc)})
        return None


@dataclass
class HitlState:
    """贯穿 HITL 流程的极简状态容器。"""

    feature_name: str
    draft: str = ""
    approved: bool | None = None
    audit: list[str] = field(default_factory=list)


def draft_proposal(state: HitlState) -> HitlState:
    """生成待审批草案（模型可选）。"""
    prompt = f"功能名称: {state.feature_name}\n请写上线说明草案。"
    text = _call_llm_optional(prompt)
    mode = "llm"
    if text is None:
        mode = "template"
        text = (
            f"【拟发布】{state.feature_name}\n"
            "- 变更摘要: 新增内部试用能力，默认关闭。\n"
            "- 影响范围: 仅测试租户；生产流量不受影响。\n"
            "- 回滚策略: 关闭特性开关并回退到上一稳定版本。\n"
            "- 验证: 已在预发环境完成冒烟测试。"
        )
    state.draft = text.strip()
    state.audit.append(f"draft:{mode}")
    emit_hitl_event("draft_created", {"mode": mode, "chars": len(state.draft)})
    return state


def present_for_approval(state: HitlState) -> HitlState:
    """展示给人类审批的内容，并标记进入 pending。"""
    print("\n---------- 待审批草案 ----------")
    print(state.draft)
    print("--------------------------------\n")
    emit_hitl_event(
        "pending_approval",
        {"hint": "请在交互终端输入 y/n，或设置环境变量 HITL_APPROVE=yes|no"},
    )
    return state


def prompt_human_approval(state: HitlState) -> HitlState:
    """
    人工决策入口：
    - 交互式终端：读取 y/n。
    - 非交互：读取环境变量 HITL_APPROVE（yes/no/1/0）。
    """
    decision_raw: str | None = None
    source = "stdin"

    if sys.stdin.isatty():
        try:
            decision_raw = input("是否批准发布？(y/n): ").strip().lower()
        except EOFError:
            decision_raw = None
    else:
        source = "env:HITL_APPROVE"
        decision_raw = os.getenv("HITL_APPROVE", "").strip().lower()

    if not decision_raw:
        print(
            "提示: 未检测到交互输入且 HITL_APPROVE 为空，默认视为 **驳回**（安全侧默认）。"
        )
        state.approved = False
    else:
        state.approved = decision_raw in ("y", "yes", "1", "true", "是", "通过")

    emit_hitl_event(
        "decision_recorded",
        {"approved": state.approved, "source": source, "raw": decision_raw or ""},
    )
    state.audit.append(f"approval:{state.approved}")
    return state


def finalize_release(state: HitlState) -> HitlState:
    """根据审批结果输出最终动作（教学用打印）。"""
    if state.approved:
        msg = "结果: 已批准 → 进入发布队列（演示：仅打印，不真的部署）。"
    else:
        msg = "结果: 已驳回 → 退回开发/产品修订，并保留审计记录。"

    print(msg)
    emit_hitl_event(
        "completed",
        {"approved": bool(state.approved), "audit_trail": state.audit},
    )
    return state


def run_hitl_demo(feature_name: str) -> HitlState:
    """串联 HITL 各步骤。"""
    state = HitlState(feature_name=feature_name)
    state = draft_proposal(state)
    state = present_for_approval(state)
    state = prompt_human_approval(state)
    state = finalize_release(state)
    return state


def main() -> None:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("提示: 未配置 OPENAI_API_KEY，草案将使用模板文本；HITL 流程不受影响。")

    if not sys.stdin.isatty():
        print(
            "提示: 当前为非交互环境。将读取环境变量 HITL_APPROVE（yes/no），"
            "未设置则默认驳回。若你直接在终端运行本章，可手动输入 y/n。"
        )

    run_hitl_demo("会议纪要行动项机器人（内测版）")


if __name__ == "__main__":
    main()
