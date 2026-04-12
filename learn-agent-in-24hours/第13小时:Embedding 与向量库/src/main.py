# -*- coding: utf-8 -*-
"""
第 13 小时：Embedding 与向量库 — 最小可运行示例。

流程：准备语料 → 写入向量库（Chroma 或内存降级）→ 相似度检索。
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

# 加载 learn-agent-in-24hours/.env
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")

# 教学用语料：虚构产品说明
CORPUS: list[tuple[str, str]] = [
    ("doc_refund", "我们支持 7 天内无理由退款，需保持商品完好。"),
    ("doc_ship", "订单付款后 48 小时内发货，顺丰包邮。"),
    ("doc_vip", "VIP 会员每月赠送 2 张免运费券，自动到账。"),
    ("doc_api", "开放 API 的速率限制为每分钟 60 次，超限返回 429。"),
]


def l2_normalize(vec: Sequence[float]) -> list[float]:
    """L2 归一化，便于用点积近似余弦相似度。"""
    s = math.sqrt(sum(x * x for x in vec))
    if s == 0:
        return list(vec)
    return [x / s for x in vec]


def hash_embedding(text: str, dim: int = 64) -> list[float]:
    """
    用哈希构造确定性伪向量（教学用，不代表真实语义）。
    无 API Key 或离线演示时使用。
    """
    vec = [0.0] * dim
    raw = text.encode("utf-8")
    for i, b in enumerate(raw):
        vec[i % dim] += (b - 128) / 128.0
    return l2_normalize(vec)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """余弦相似度，范围约 [-1, 1]。"""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def run_memory_demo(query: str) -> None:
    """纯内存向量检索：不依赖 chromadb，保证任意环境可跑。"""
    print("\n=== 模式：内存向量库（教学伪 Embedding）===")
    store: list[tuple[str, str, list[float]]] = []
    for doc_id, text in CORPUS:
        store.append((doc_id, text, hash_embedding(text)))
    qv = hash_embedding(query)
    ranked = sorted(
        store,
        key=lambda item: cosine_similarity(qv, item[2]),
        reverse=True,
    )
    print(f"查询：{query!r}")
    for doc_id, text, vec in ranked[:2]:
        score = cosine_similarity(qv, vec)
        print(f"  [{doc_id}] score={score:.4f} | {text}")


def _try_chroma_embedding_function():
    """根据环境返回 (embedding_function, 描述字符串)。"""
    import chromadb  # noqa: F401 — 由调用方保证已导入

    from chromadb import Documents, EmbeddingFunction, Embeddings

    class HashEmbeddingFunction(EmbeddingFunction):
        """Chroma 可用的哈希伪嵌入。"""

        def __call__(self, input: Documents) -> Embeddings:
            return [hash_embedding(t) for t in input]

    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if api_key and api_key != "your_api_key_here":
        try:
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

            model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
            ef = OpenAIEmbeddingFunction(api_key=api_key, model_name=model)
            return ef, f"OpenAIEmbeddingFunction（{model}）"
        except Exception as e:  # noqa: BLE001 — 教学脚本：打印原因后降级
            print(f"[提示] OpenAI 嵌入不可用，将使用哈希伪向量。原因：{e}")
    return HashEmbeddingFunction(), "HashEmbeddingFunction（教学伪向量）"


def run_chroma_demo(query: str) -> None:
    """Chroma 持久化向量库演示。"""
    import chromadb

    chapter_dir = Path(__file__).resolve().parents[1]
    persist = chapter_dir / ".chroma_lesson13"
    ef, ef_desc = _try_chroma_embedding_function()

    print("\n=== 模式：Chroma 持久化向量库 ===")
    print(f"持久化目录：{persist}")
    print(f"嵌入函数：{ef_desc}")

    client = chromadb.PersistentClient(path=str(persist))
    collection = client.get_or_create_collection(
        name="lesson13_products",
        embedding_function=ef,
        metadata={"lesson": "13"},
    )
    # 幂等写入：按 id upsert
    ids = [x[0] for x in CORPUS]
    docs = [x[1] for x in CORPUS]
    collection.upsert(ids=ids, documents=docs)

    result = collection.query(query_texts=[query], n_results=2, include=["documents", "distances"])
    print(f"查询：{query!r}")
    for i, doc_id in enumerate(result["ids"][0]):
        dist = result["distances"][0][i] if result.get("distances") else None
        doc = result["documents"][0][i] if result.get("documents") else ""
        dist_s = f"{dist:.6f}" if dist is not None else "n/a"
        print(f"  [{doc_id}] distance={dist_s} | {doc}")


def main() -> None:
    query = "我想退货要怎么操作？"
    print("第 13 小时：Embedding 与向量库")
    print("说明：未配置有效 OPENAI_API_KEY 时，使用哈希伪向量；流程与真实嵌入一致。")

    try:
        run_chroma_demo(query)
    except ImportError:
        print(
            "[提示] 未安装 chromadb。请执行：pip install -r requirements.txt",
            file=sys.stderr,
        )
        run_memory_demo(query)
    except Exception as e:  # noqa: BLE001
        print(f"[提示] Chroma 运行失败，改用内存演示。原因：{e}")
        run_memory_demo(query)


if __name__ == "__main__":
    main()
