# 第 21 小时：多智能体编排

## 本章目标

- 在 **第 20 小时** 的「多角色顺序调用」之上，引入 **编排器（Supervisor）**：由统一节点决定下一步交给哪个角色，形成「调度闭环」。
- 使用 **LangGraph** 的 `StateGraph` 表达 **节点、边、条件边**，把编排逻辑从 `if/else` 堆叠中解放出来。
- 理解 **与第 20 小时的差异**：第 20 小时是固定流水线；本章是「可分支、可回到调度器再决策」的控制流（教学上仍用确定性规则，避免过度依赖模型）。

## 核心概念

- **Supervisor 节点**：只负责读共享状态并给出 `next`（下一个节点名），相当于「指挥」。
- **Worker 节点**：`analyst`、`writer`、`critic` 等，只负责改写自己负责的字段。
- **条件边**：`add_conditional_edges` 根据状态里的 `next` 字段跳转，实现显式编排。
- **演进关系**：第 19 小时模块化能力 → 第 20 小时拆分角色 → **第 21 小时把角色放进图里统一调度**。

## 案例设计

输入一个「产品功能主题」，编排流程为：

`supervisor` →（按需）`analyst` → `supervisor` → `writer` → `supervisor` → `critic` → `supervisor` → 结束。

若未安装 `langgraph`，程序会打印提示并执行 **同构的纯 Python 模拟编排**，保证章节仍可运行。

## 代码讲解

文件：`src/main.py`。

- **`OrchState`**：编排图共享状态，含 `topic` 与各阶段产物字段，以及 **`next`**（由 `supervisor_node` 写入）。
- **`supervisor_node`**：根据已有字段决定下一个 worker 或结束；这是本章的**编排核心**。
- **`analyst_node` / `writer_node` / `critic_node`**：三个工作节点，分别产出提纲、草案、评审意见。
- **`build_graph`**：组装 `StateGraph`、普通边与条件边。
- **`run_orchestration`**：对外入口，`compile()` 后 `invoke` 运行。

## 运行方式

```bash
cd "第21小时:多智能体编排"
python src/main.py
```

依赖来自上一级 `requirements.txt` 中的 `langgraph`。若你希望同一套状态在真实模型中动态路由，可在掌握本章结构后再把 `supervisor_node` 的决策替换为 LLM 输出（注意成本与稳定性）。
