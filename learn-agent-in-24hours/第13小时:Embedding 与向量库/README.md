# 第 13 小时：Embedding 与向量库

## 本章目标

- 理解 **文本 → 向量（Embedding）** 在 Agent / RAG 流水线中的作用。
- 认识 **向量库（Vector Store）** 的职责：写入、索引、相似度检索。
- 跑通一条最小工作流：**建库 → 写入文档 → 用查询文本检索 Top-K**，并能在无 API Key 时仍看到完整流程（教学用伪向量）。

## 核心概念

| 概念 | 一句话 |
|------|--------|
| Embedding | 把文本变成固定维度的数值向量，语义相近的文本在空间中距离更近。 |
| 相似度检索 | 用查询向量与库内向量算相似度（如余弦相似度），取最相近的若干条。 |
| 向量库 | 持久化或内存中的「文档 + 向量」存储，对外提供 `add` / `query` 等接口。 |

真实项目里常用 OpenAI、`sentence-transformers` 等产生高质量向量；本课为降低门槛，在 **未配置 `OPENAI_API_KEY`** 时使用 **确定性哈希伪向量**（仅用于理解流程，不代表真实语义）。

## 案例设计

我们准备一小段「产品知识库」文档（几条字符串），演示：

1. 将每条文档编码为向量并写入集合（Chroma 或内存降级）。
2. 用户提问一句，检索最相关的文档 ID 与内容。
3. 控制台打印：是否使用 Chroma、是否使用真实 OpenAI Embedding、检索得分（距离）。

## 代码讲解

示例入口在 `src/main.py`。

- **`hash_embedding`**：把文本变成固定维度伪向量（无 Key 时走此路径，保证可复现）。
- **`l2_normalize` / `cosine_similarity`**：手写相似度，便于对照「向量库内部在算什么」。
- **`HashEmbeddingFunction`**：供 Chroma 使用的嵌入函数类（与 `chromadb` 的 `EmbeddingFunction` 协议对齐）。
- **`run_memory_demo`**：不依赖 Chroma 的纯 Python 向量检索，作为 **ImportError 或无向量库时的保底**。
- **`run_chroma_demo`**：`PersistentClient` + `get_or_create_collection`，演示真实 **持久化向量库** 工作流；有 Key 时优先 **`OpenAIEmbeddingFunction`**。

阅读时建议顺着 `main()` 的分支顺序看：**Chroma 可用 → 选嵌入函数 → 建库检索 → 否则内存演示**。

## 运行方式

在仓库 `learn-agent-in-24hours` 目录下（已安装 `requirements.txt`）：

```bash
python "第13小时:Embedding 与向量库/src/main.py"
```

或使用统一入口：

```bash
python run_demo.py 13
```

可选：在项目根放置 `.env` 并配置 `OPENAI_API_KEY`，将自动使用 OpenAI 官方嵌入模型（需网络与额度）。

首次使用 Chroma 持久化时，会在本章目录下生成 `.chroma_lesson13/` 数据目录（可手动删除以清空演示数据）。
