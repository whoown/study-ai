"""
第 17 小时：反思纠错

这份 main.py 是本章对应的最小可运行教学案例。

阅读建议：
1. 先看 main() 怎么启动案例。
2. 再看主流程函数如何驱动模型、工具、状态或路由。
3. 最后再看辅助函数，理解它们分别承担什么职责。

本章新增能力：先生成，再审查，再修订。
如果你是初学者，建议一边运行一边对照源码，不要只静态阅读。
"""
# -*- coding: utf-8 -*-
"""
第 17 小时：反思纠错 — 草稿、批评（reflection）、修订（revise）闭环。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")

EVIDENCE = [
    "StudyFlow 企业版支持按部门授权，但不支持将编辑权限授予外部邮箱域名。",
    "外部协作者只能以只读访客身份访问被明确分享的文档。",
]


# [教学注释] `draft_answer`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

def draft_answer(question: str) -> str:
    """故意略夸张的初稿，便于反思器抓到问题。"""
    return (
        "可以，把外部用户直接设为编辑即可，他们默认就能改你们所有文档。"
        f"（问题：{question}）"
    )


# [教学注释] `rule_reflect`
# 基于规则的判断或改写逻辑。

def rule_reflect(question: str, draft: str, evidence: list[str]) -> dict[str, Any]:
    """规则化反思：检查是否出现证据未涵盖的断言。"""
    issues: list[str] = []
    if "所有文档" in draft:
        issues.append("夸大范围：证据未说明可编辑「所有文档」。")
    if "外部用户" in draft and "编辑" in draft:
        issues.append("与证据冲突：外部协作者默认只读。")
    passed = len(issues) == 0
    suggestions = (
        []
        if passed
        else [
            "明确区分内部成员与外部访客权限。",
            "引用证据中的「只读访客」表述。",
        ]
    )
    return {
        "passed": passed,
        "issues": issues,
        "suggestions": suggestions,
    }


# [教学注释] `rule_revise`
# 基于规则的判断或改写逻辑。

def rule_revise(draft: str, reflection: dict[str, Any], evidence: list[str]) -> str:
    """极简修订：根据 issues 做字符串级修复（教学用）。"""
    text = draft
    if any("外部" in i for i in reflection.get("issues", [])):
        text = text.replace("把外部用户直接设为编辑即可", "外部访客默认只读；编辑权限仅适用于内部授权成员")
    if any("所有文档" in i for i in reflection.get("issues", [])):
        text = text.replace("他们默认就能改你们所有文档", "权限需按空间与文档分享范围配置")
    text += "\n\n依据：\n- " + "\n- ".join(evidence)
    return text


# [教学注释] `_openai_chat`
# 内部辅助函数，为主流程提供局部能力。

def _openai_chat(messages: list[dict[str, str]]) -> str:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    base_url = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    if not api_key or api_key == "your_api_key_here":
        return ""

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()


# [教学注释] `llm_reflect`
# 基于大模型的策略或生成逻辑。

def llm_reflect(question: str, draft: str, evidence: list[str]) -> dict[str, Any] | None:
    ctx = "\n".join(f"- {e}" for e in evidence)
    prompt = f"""你是合规审查员。证据：
{ctx}

用户问题：{question}
草稿：{draft}

请输出 JSON：{{"passed": bool, "issues": [string], "suggestions": [string]}}
passed 为 true 当且仅当草稿严格可由证据支持且无夸大。
"""
    text = _openai_chat([{"role": "user", "content": prompt}])
    if not text:
        return None
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return {
            "passed": bool(data.get("passed")),
            "issues": list(data.get("issues") or []),
            "suggestions": list(data.get("suggestions") or []),
        }
    except json.JSONDecodeError:
        return None


# [教学注释] `llm_revise`
# 基于大模型的策略或生成逻辑。

def llm_revise(question: str, draft: str, reflection: dict[str, Any], evidence: list[str]) -> str | None:
    ctx = "\n".join(f"- {e}" for e in evidence)
    prompt = f"""根据证据与反思结果改写草稿，输出最终中文答复（不要 JSON）。

证据：
{ctx}

问题：{question}
草稿：{draft}
反思：{json.dumps(reflection, ensure_ascii=False)}
要求：简洁、可执行，不得引入证据未支持的信息。
"""
    text = _openai_chat([{"role": "user", "content": prompt}])
    return text or None


# [教学注释] `reflect_answer`
# 从“有答案”推进到“答案质量是否合格”。

def reflect_answer(question: str, draft: str, evidence: list[str]) -> dict[str, Any]:
    return llm_reflect(question, draft, evidence) or rule_reflect(question, draft, evidence)


# [教学注释] `revise_answer`
# 根据反思意见生成更好的版本。

def revise_answer(question: str, draft: str, reflection: dict[str, Any], evidence: list[str]) -> str:
    return llm_revise(question, draft, reflection, evidence) or rule_revise(draft, reflection, evidence)


# [教学注释] `run_reflection_loop`
# 驱动一段完整流程，把前面准备好的零件真正串起来。

def run_reflection_loop(question: str, max_rounds: int = 2) -> None:
    print("第 17 小时：反思纠错")
    print(f"问题：{question!r}\n")

    draft = draft_answer(question)
    print("[draft v0]\n" + draft)

    for rnd in range(max_rounds):
        reflection = reflect_answer(question, draft, EVIDENCE)
        print(f"\n[reflection_round] {rnd + 1}")
        print("[reflection]", json.dumps(reflection, ensure_ascii=False, indent=2))

        if reflection.get("passed"):
            print("\n[result] 反思通过，输出当前草稿。")
            print(draft)
            return

        draft = revise_answer(question, draft, reflection, EVIDENCE)
        print("\n[revised_draft]\n" + draft)

    print("\n[result] 达到最大反思轮次，停止（可在此接入人工审核）。")


# [教学注释] `main`
# 脚本入口，通常只负责启动案例。

def main() -> None:
    run_reflection_loop("能不能把客户公司的顾问加成编辑，方便他们改我们的文档？")


if __name__ == "__main__":
    main()
