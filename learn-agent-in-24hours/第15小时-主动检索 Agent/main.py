"""
第 15 小时：主动检索 Agent

这份 main.py 是本章对应的最小可运行教学案例。

阅读建议：
1. 先看 main() 怎么启动案例。
2. 再看主流程函数如何驱动模型、工具、状态或路由。
3. 最后再看辅助函数，理解它们分别承担什么职责。

本章新增能力：让 Agent 自己判断何时检索。
如果你是初学者，建议一边运行一边对照源码，不要只静态阅读。
"""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")

# 小型知识库（与检索演示配套）
KB: list[tuple[str, str]] = [
    ("d1", "StudyFlow 企业版支持 SAML 单点登录与按部门授权。"),
    ("d2", "StudyFlow 移动端的离线缓存最长保留 30 天。"),
    ("d3", "API 速率限制默认每分钟 120 次，可申请提升至 600。"),
    ("d4", "工单系统 SLA：P1 30 分钟响应，P2 4 小时响应。"),
]


# [教学注释] `l2_normalize`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

def l2_normalize(vec: Sequence[float]) -> list[float]:
    s = math.sqrt(sum(x * x for x in vec))
    if s == 0:
        return list(vec)
    return [x / s for x in vec]


# [教学注释] `hash_embedding`
# 简化版向量函数，用于建立 Embedding 直觉。

def hash_embedding(text: str, dim: int = 64) -> list[float]:
    vec = [0.0] * dim
    for i, b in enumerate(text.encode("utf-8")):
        vec[i % dim] += (b - 128) / 128.0
    return l2_normalize(vec)


# [教学注释] `cosine_similarity`
# 通过数学方式比较语义接近程度。

def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# [教学注释] `retrieve_from_store`
# 承担本章流程中的一个明确职责，阅读时要关注它的输入、输出和在整条链路中的位置。

def retrieve_from_store(query: str, k: int = 2) -> list[tuple[str, str, float]]:
    """内存向量检索，作为 Agent 的「search_knowledge」工具实现。"""
    qv = hash_embedding(query)
    ranked: list[tuple[str, str, float]] = []
    for doc_id, text in KB:
        base = cosine_similarity(qv, hash_embedding(text))
        # 教学用轻量关键词加权：伪向量不具备真实语义时，避免演示结论「看起来随机」
        bonus = 0.0
        if any(kw in query for kw in ("登录", "账号", "SSO", "SAML", "单点")) and "SAML" in text:
            bonus += 0.25
        if "API" in query.upper() or "接口" in query:
            bonus += 0.15 if "API" in text else 0.0
        ranked.append((doc_id, text, min(1.0, base + bonus)))
    ranked.sort(key=lambda x: x[2], reverse=True)
    return ranked[:k]


# [教学注释] `rule_based_decide`
# 用规则决定是否需要检索。

def rule_based_decide(user_q: str, state: dict[str, Any]) -> dict[str, Any]:
    """
    无 LLM 时的确定性决策：
    - 首轮几乎总是检索；
    - 若最高分片段低于阈值，改写关键词再检；
    - 达到最大轮次则强制作答。
    """
    round_no = state["round"]
    if round_no == 0:
        return {
            "need_search": True,
            "query": user_q.strip(),
            "reason": "首轮：需要建立证据池。",
        }
    last_hits: list[tuple[str, str, float]] = state.get("last_hits") or []
    best = last_hits[0][2] if last_hits else 0.0
    if round_no >= 2 or best >= 0.55:
        return {
            "need_search": False,
            "query": "",
            "reason": f"证据足够或已达轮次上限（best_score={best:.3f}）。",
        }
    # 简单改写：抽取英文词与关键中文，拼接成检索式
    tokens = re.findall(r"[A-Za-z]{3,}", user_q)
    extra = "SAML SSO 授权" if any(x.lower() in user_q.lower() for x in ["登录", "sso", "账号"]) else "API 速率"
    new_q = " ".join(tokens + [extra])
    return {
        "need_search": True,
        "query": new_q.strip() or user_q,
        "reason": "相似度偏低，尝试改写查询以提升召回。",
    }


# [教学注释] `llm_decide`
# 用模型决定是否需要检索。

def llm_decide(user_q: str, state: dict[str, Any]) -> dict[str, Any] | None:
    """可选：让 LLM 以 JSON 输出下一步要不要检索。"""
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    base_url = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    if not api_key or api_key == "your_api_key_here":
        return None

    summary = json.dumps(
        {
            "round": state["round"],
            "evidence_count": len(state.get("evidence", [])),
            "last_best_score": (state.get("last_hits") or [[0, 0, 0]])[0][2]
            if state.get("last_hits")
            else None,
        },
        ensure_ascii=False,
    )
    prompt = f"""你是检索调度器。根据用户问题与当前状态，决定下一步。
只输出 JSON，键为 need_search(bool), query(string), reason(string)。
若 need_search 为 false，query 置空字符串。
用户问题：{user_q}
状态：{summary}
"""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        text = (resp.choices[0].message.content or "").strip()
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        data = json.loads(m.group(0))
        return {
            "need_search": bool(data.get("need_search")),
            "query": str(data.get("query", "")),
            "reason": str(data.get("reason", "")),
        }
    except Exception:
        return None


# [教学注释] `mock_final_answer`
# 离线教学分支，帮助你在没有外部依赖时也能理解流程。

def mock_final_answer(user_q: str, evidence: list[str]) -> str:
    joined = "\n".join(f"- {e}" for e in evidence[:4])
    return (
        "【模拟最终回答】未调用 LLM 生成自然语言。\n"
        f"问题：{user_q!r}\n"
        "依据片段：\n"
        f"{joined}\n"
        "（配置 OPENAI_API_KEY 可在此步骤接入真实生成。）"
    )


# [教学注释] `llm_final_answer`
# 基于大模型的策略或生成逻辑。

def llm_final_answer(user_q: str, evidence: list[str]) -> str:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    base_url = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    if not api_key or api_key == "your_api_key_here":
        return ""

    ctx = "\n".join(evidence)
    prompt = f"仅依据下列证据作答，不要编造：\n{ctx}\n\n问题：{user_q}"
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:  # noqa: BLE001
        return f"[生成失败] {e}"


# [教学注释] `run_active_agent`
# 驱动一段完整流程，把前面准备好的零件真正串起来。

def run_active_agent(user_question: str, max_rounds: int = 3) -> None:
    state: dict[str, Any] = {
        "round": 0,
        "evidence": [],
        "last_hits": [],
        "history": [],
    }

    print("第 15 小时：主动检索 Agent")
    print(f"用户问题：{user_question!r}\n")

    while state["round"] < max_rounds:
        print(f"--- 第 {state['round'] + 1} 轮 ---")
        decision = llm_decide(user_question, state) or rule_based_decide(user_question, state)
        print("[plan_decision]", json.dumps(decision, ensure_ascii=False))

        state["history"].append({"round": state["round"], "decision": decision})
        print(
            "[task_state]",
            json.dumps(
                {
                    "round": state["round"],
                    "evidence_count": len(state["evidence"]),
                },
                ensure_ascii=False,
            ),
        )

        if not decision.get("need_search"):
            print("[action] STOP_RETRIEVAL -> 进入作答阶段")
            break

        q = decision.get("query") or user_question
        print(f"[action] RETRIEVE query={q!r}")
        hits = retrieve_from_store(q, k=2)
        state["last_hits"] = hits
        for _id, text, score in hits:
            state["evidence"].append(f"[{_id}] {text}")
        print("[retrieval_hits]")
        for _id, text, score in hits:
            print(f"  {_id} score={score:.4f} | {text}")

        state["round"] += 1

    ans = llm_final_answer(user_question, state["evidence"]) or mock_final_answer(
        user_question, state["evidence"]
    )
    print("\n[final_answer]\n" + ans)


# [教学注释] `main`
# 脚本入口，通常只负责启动案例。

def main() -> None:
    run_active_agent("我们公司想用 StudyFlow，登录这块能对接公司账号体系吗？")


if __name__ == "__main__":
    main()
