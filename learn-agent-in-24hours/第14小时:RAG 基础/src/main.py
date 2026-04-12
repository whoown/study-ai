# -*- coding: utf-8 -*-
"""
第 14 小时：RAG 基础 — 分块、索引、检索、拼 Prompt、生成（可模拟）。
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")


def load_wiki_text() -> str:
    """内置 Wiki 文本，避免读者额外准备文件。"""
    return """
    产品名称：StudyFlow。StudyFlow 是一款面向团队的在线学习与知识沉淀工具。
    账号与权限：管理员可创建空间并邀请成员。成员默认只读，可被赋予编辑权限。
    退款政策：企业版支持签约后 14 天内按比例退款，需提交工单并附合同编号。
    发票：支持增值税普通发票与专用发票，开票周期为付款后 7 个工作日。
    数据导出：空间管理员可在「设置-合规」中导出全部文档与评论，导出为 ZIP。
    API 限制：公开 API 默认每分钟 120 次请求，可申请提升至 600。
    安全：所有流量使用 TLS1.2+，静态数据 AES-256 加密，密钥由 KMS 托管。
    """.strip()


def chunk_text(text: str, size: int = 120, overlap: int = 30) -> list[str]:
    """按字符窗口分块（教学用简单策略）。"""
    text = " ".join(text.split())
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        chunks.append(text[start:end])
        if end == n:
            break
        start = max(0, end - overlap)
    return [c for c in chunks if c.strip()]


def l2_normalize(vec: Sequence[float]) -> list[float]:
    s = math.sqrt(sum(x * x for x in vec))
    if s == 0:
        return list(vec)
    return [x / s for x in vec]


def hash_embedding(text: str, dim: int = 64) -> list[float]:
    """与第 13 小时一致的哈希伪向量。"""
    vec = [0.0] * dim
    for i, b in enumerate(text.encode("utf-8")):
        vec[i % dim] += (b - 128) / 128.0
    return l2_normalize(vec)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def build_memory_index(chunks: list[str]) -> list[tuple[str, list[float]]]:
    indexed: list[tuple[str, list[float]]] = []
    for i, ch in enumerate(chunks):
        indexed.append((f"chunk_{i}", hash_embedding(ch)))
    return indexed


def memory_retrieve(query: str, chunks: list[str], indexed, k: int) -> list[tuple[str, str, float]]:
    qv = hash_embedding(query)
    scored: list[tuple[str, str, float]] = []
    for (cid, vec), text in zip(indexed, chunks):
        scored.append((cid, text, cosine_similarity(qv, vec)))
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:k]


def _chroma_embedding_function():
    import chromadb
    from chromadb import Documents, EmbeddingFunction, Embeddings

    class HashEmbeddingFunction(EmbeddingFunction):
        def __call__(self, input: Documents) -> Embeddings:
            return [hash_embedding(t) for t in input]

    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if api_key and api_key != "your_api_key_here":
        try:
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

            model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
            return OpenAIEmbeddingFunction(api_key=api_key, model_name=model), f"OpenAI:{model}"
        except Exception as e:  # noqa: BLE001
            print(f"[提示] OpenAI 嵌入不可用，使用哈希伪向量。原因：{e}")
    return HashEmbeddingFunction(), "hash"


def build_chroma_collection(chunks: list[str]):
    import chromadb

    chapter_dir = Path(__file__).resolve().parents[1]
    persist = chapter_dir / ".chroma_lesson14"
    ef, desc = _chroma_embedding_function()
    client = chromadb.PersistentClient(path=str(persist))
    coll = client.get_or_create_collection("lesson14_wiki", embedding_function=ef)
    ids = [f"c{i}" for i in range(len(chunks))]
    coll.upsert(ids=ids, documents=chunks)
    return coll, persist, desc


def chroma_retrieve(coll, query: str, k: int) -> list[tuple[str, str, float]]:
    res = coll.query(query_texts=[query], n_results=k, include=["documents", "distances"])
    out: list[tuple[str, str, float]] = []
    for i, doc_id in enumerate(res["ids"][0]):
        doc = res["documents"][0][i]
        dist = res["distances"][0][i]
        out.append((doc_id, doc, float(dist)))
    return out


def build_rag_prompt(question: str, hits: list[tuple[str, str, float]]) -> str:
    """把检索结果拼成可喂给模型的上下文（字符串形式）。"""
    parts = [
        "你是公司内部助手，只能依据下列片段回答，不要编造片段中不存在的信息。",
        "",
        "### 参考片段",
    ]
    for doc_id, text, score in hits:
        parts.append(f"- [{doc_id}] (相关度指标: {score:.4f}) {text}")
    parts.extend(["", "### 用户问题", question])
    return "\n".join(parts)


def mock_answer_from_context(question: str, hits: list[tuple[str, str, float]]) -> str:
    """无 API Key 时的教学输出：强调「答案应来自上下文」。"""
    return (
        "【模拟回答】未调用真实 LLM。\n"
        f"根据检索到的 {len(hits)} 条片段，应围绕「{hits[0][1][:40]}…」等原文作答。\n"
        f"用户问题：{question!r}\n"
        "配置 OPENAI_API_KEY 后可看到真实生成结果。"
    )


def generate_answer(prompt: str) -> str:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    base_url = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    if not api_key or api_key == "your_api_key_here":
        return ""

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "简洁、准确，引用事实时复述原文要点。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:  # noqa: BLE001
        return f"[LLM 调用失败] {e}"


def main() -> None:
    question = "StudyFlow 的发票多久能开出来？"
    print("第 14 小时：RAG 基础")

    wiki = load_wiki_text()
    chunks = chunk_text(wiki, size=140, overlap=40)
    print(f"\n[分块] 共 {len(chunks)} 段。")

    hits: list[tuple[str, str, float]] = []
    mode = "memory"

    try:
        coll, persist, ef_desc = build_chroma_collection(chunks)
        hits = chroma_retrieve(coll, question, k=3)
        mode = f"chroma ({ef_desc}) @ {persist}"
    except ImportError:
        print("[提示] 未安装 chromadb，使用内存索引。pip install -r requirements.txt", file=sys.stderr)
        idx = build_memory_index(chunks)
        hits = memory_retrieve(question, chunks, idx, k=3)
    except Exception as e:  # noqa: BLE001
        print(f"[提示] Chroma 失败，使用内存索引。原因：{e}")
        idx = build_memory_index(chunks)
        hits = memory_retrieve(question, chunks, idx, k=3)

    print(f"\n[检索模式] {mode}")
    print("[检索命中]")
    for doc_id, text, score in hits:
        print(f"  {doc_id} | score/dist={score:.4f} | {text[:80]}…")

    prompt = build_rag_prompt(question, hits)
    print("\n[RAG Prompt 摘要]\n" + prompt[:600] + ("…" if len(prompt) > 600 else ""))

    answer = generate_answer(prompt)
    if answer:
        print("\n[模型回答]\n" + answer)
    else:
        print("\n" + mock_answer_from_context(question, hits))


if __name__ == "__main__":
    main()
