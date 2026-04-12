# 第 14 小时：RAG 基础

## 本章目标

- 理解 **RAG（Retrieval-Augmented Generation）**：先检索相关片段，再把片段作为上下文交给模型生成答案。
- 掌握最小流水线：**分块 → 索引 → 检索 → 拼 Prompt → 生成**。
- 在未配置 API Key 时，仍能观察 **检索结果如何进入「伪回答模板」**，不中断学习。

## 核心概念

| 环节 | 作用 |
|------|------|
| Chunking | 把长文档切成适合嵌入与检索的小段。 |
| Indexing | 将每个 chunk 向量化并写入向量库。 |
| Retrieval | 用用户问题取向量库 Top-K。 |
| Augmentation | 把检索到的文本塞进 system/user 提示词。 |
| Generation | LLM 结合上下文输出最终答案（本课可模拟）。 |

## 案例设计

给定一篇较长的「公司内部 Wiki」文本，我们：

1. 按固定字符窗口做简单分块（`chunk_text`）。
2. 用与第 13 小时一致的策略：**Chroma +（OpenAI 嵌入 或 哈希伪向量）**；失败则 **内存索引**。
3. 对用户问题执行检索，打印 **进入 Prompt 的 context**。
4. 若有有效 Key，调用 OpenAI Chat Completions 生成；否则打印 **模拟回答**（仍展示 RAG 拼接结构）。

## 代码讲解

代码集中在 `src/main.py`：

- **`load_wiki_text`**：返回内置示例长文（避免依赖外部文件）。
- **`chunk_text`**：滑动窗口分块，带 `overlap` 减少边界信息丢失。
- **`build_memory_index` / `memory_retrieve`**：无 Chroma 时的向量检索实现。
- **`build_chroma_collection` / `chroma_retrieve`**：Chroma 建集合并查询。
- **`build_rag_prompt`**：把检索片段格式化为模型提示词（教学上最关键的一眼）。
- **`generate_answer`**：有 Key 走 `OpenAI` HTTP SDK；否则 `mock_answer_from_context` 打印模板化结论。

建议对照 `main()` 里打印的 **「检索命中」→「拼接后的 Prompt 摘要」→「最终回答」** 三段输出理解 RAG。

## 运行方式

```bash
python "第14小时:RAG 基础/src/main.py"
# 或
python run_demo.py 14
```

可选 `.env`：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`（与仓库 `.env.example` 一致）。

Chroma 数据默认写在 `第14小时:RAG 基础/.chroma_lesson14/`。
