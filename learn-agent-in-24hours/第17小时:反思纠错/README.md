# 第 17 小时：反思纠错

## 本章目标

- 理解 **Reflection（反思）** 在 Agent 流水线中的位置：对草稿或工具结果进行 **批评—修订** 闭环。
- 学会阅读日志里的 **`reflection` 块**：发现了什么问题、是否通过检查、是否触发改写。
- 在缺少 LLM 时，仍能通过 **规则化反思器** 观察完整纠错流程。

## 核心概念

| 环节 | 作用 |
|------|------|
| Draft | 第一版答案或中间产物。 |
| Critique | 反思模块输出：缺陷列表、是否阻塞、建议修改方向。 |
| Revise | 根据批评修订草稿（可用 LLM 或规则）。 |

## 案例设计

场景：根据几条「内部规定」片段回答用户合规问题。

1. 先产生一版 **故意略不严谨** 的草稿（`draft_answer`）。
2. `reflect_answer` 检查 **是否引用未出现的信息**、**是否缺少关键限定词**。
3. 打印 **`[reflection]`** JSON：通过与否、`issues`、`suggestions`。
4. 不通过则 `revise_answer` 修订，最多两轮；每轮打印 **`[reflection_round]`**。

若配置 `OPENAI_API_KEY`，反思与修订可切换为 **LLM 文本批评**（失败则自动回退规则实现）。

## 代码讲解

见 `src/main.py`：

- **`draft_answer`**：构造初稿（教学上便于看到纠错前后差异）。
- **`rule_reflect` / `rule_revise`**：不依赖模型的反思与修订，输出稳定。
- **`llm_reflect` / `llm_revise`**：可选接入 OpenAI Chat Completions。
- **`run_reflection_loop`**：控制最大轮数，逐步打印 **reflection → revised draft**。

阅读时请跟踪函数 **`reflect_answer`** 与 **`revise_answer`**：它们如何被主循环组合成 **自我检查** 工作流。

## 运行方式

```bash
python "第17小时:反思纠错/src/main.py"
python run_demo.py 17
```

可选 `.env` 配置与全仓库一致；无 Key 时完全本地可跑。
