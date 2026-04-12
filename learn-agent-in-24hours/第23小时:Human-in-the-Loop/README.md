# 第 23 小时：Human-in-the-Loop

## 本章目标

- 理解 **HITL（人机协同）** 在 Agent 工作流里的典型位置：在 **高风险、高成本或强合规** 步骤前暂停，等待人类输入。
- 把 **人工审批** 做成 **可观测**：任何学习者都能从终端日志里看出「卡在哪一步、等待什么、人类决策是什么、后续怎么走」。
- 对比「完全自动发布」与「审批后再发布」在工程上的差异（审计、回滚、责任边界）。

## 核心概念

- **中断点（Interrupt）**：工作流在到达某节点时主动停下，把中间产物呈现给人类；本章用 `input()` 与环境变量模拟，避免绑定某一框架专属 API。
- **可观测性**：不仅打印结果，还要打印 **事件时间线**（函数 `emit_hitl_event`），让 HITL 像普通服务日志一样可追踪。
- **非交互环境**：`run_demo.py` 通过子进程运行本章时可能没有 TTY，因此 `src/main.py` 中的 `prompt_human_approval` 会在 **非交互** 时读取 `HITL_APPROVE`，避免脚本卡死。

## 案例设计

流程分四步：

1. `draft_proposal`：生成一份「拟发布说明」草案（可用模型或模板）。
2. `present_for_approval`：把草案结构化展示，并 **记录 HITL 事件**（待审批）。
3. `prompt_human_approval`：人类输入 `y/n`（或环境变量），并 **记录决策事件**。
4. `finalize_release`：根据审批结果走 **通过** 或 **驳回** 分支，并打印审计摘要。

## 代码讲解

文件：`src/main.py`。

- **`emit_hitl_event`**：统一的 HITL 日志出口，带 ISO 时间戳与 `event` 字段，是本章「可观测」的核心。
- **`draft_proposal`**：产出待审内容；内部可能调用 `_call_llm_optional`。
- **`present_for_approval`**：将草案写入 `HitlState`，并发出 `pending_approval` 事件。
- **`prompt_human_approval`**：阻塞等待人类（或读取 `HITL_APPROVE`），发出 `decision_recorded` 事件。
- **`finalize_release`**：根据 `approved` 布尔值输出不同结果，并发出 `completed` 事件。
- **`run_hitl_demo`**：串联以上步骤，便于 `main()` 一次跑通。

## 运行方式

交互式终端（推荐，便于体验真人审批）：

```bash
cd "第23小时:Human-in-the-Loop"
python src/main.py
```

非交互（例如被其他脚本调用）时，在运行前导出环境变量：

```bash
export HITL_APPROVE=yes   # 或 no
python src/main.py
```

可选模型：配置 `OPENAI_API_KEY` 后，`draft_proposal` 会尝试生成更自然的草案文本。
