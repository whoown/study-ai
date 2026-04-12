# 第 18 小时：状态持久化

## 本章目标

- 理解 Agent **Checkpoint（检查点）** 的意义：把运行态序列化到磁盘，支持 **中断—恢复—回放**。
- 观察 **`save_checkpoint` / `load_checkpoint`** 写入的 JSON 结构：含 `step_index`、`plan`、`state`、`history`。
- 将本章与第 16 小时对照：**TaskState** 类结构越清晰，持久化越简单。

## 核心概念

| 概念 | 说明 |
|------|------|
| Checkpoint | 某一时刻的全量或增量快照，用于恢复执行。 |
| Serializable State | 可被 JSON/Pickle 等编码的运行数据（避免保存不可序列化的客户端对象）。 |
| Idempotency | 恢复后从 `step_index` 继续，避免重复副作用（本课用打印提示模拟）。 |

## 案例设计

模拟一个三步「发布检查」流水线：

1. `lint` → 2. `test` → 3. `deploy`

脚本在 **场景 A** 中顺序执行前两步，于第二步完成后 **写入 checkpoint** 并打印崩溃提示（不退出进程）；随后在 **场景 B** 从磁盘 **加载同一 checkpoint**，从第三步继续执行，并打印 **`checkpoint_summary`**。

> 若你希望体验「真实二次启动」，可第一次运行后在进程外复制/保留 `.checkpoint_lesson18.json`，第二次只调用 `recover_from_checkpoint()`（可自行改 `main`）；默认 `main()` 在同一次执行内串起 A+B，便于课堂演示。

## 代码讲解

代码文件：`src/main.py`。

- **`RunState`（pydantic BaseModel）**：强类型、可 `.model_dump()` 序列化，适合教学展示「持久化友好结构」。
- **`simulate_step`**：逐步打印 `step_index` 与 `label`，并在指定步骤触发「崩溃」。
- **`save_checkpoint` / `load_checkpoint`**：读写 `第18小时:状态持久化/.checkpoint_lesson18.json`。
- **`run_with_crash_then_resume_demo`**：串联演示 **写入 checkpoint → 读取 → 续跑**。
- **`print_checkpoint_summary`**：专门把 checkpoint 核心字段缩略打印，满足「可观测」要求。

请重点阅读 **`save_checkpoint`** 与 **`load_checkpoint`**：它们如何把 **plan + state + history** 打成一份可迁移文件。

## 运行方式

```bash
python "第18小时:状态持久化/src/main.py"
python run_demo.py 18
```

运行后若需重放「首次崩溃」流程，删除本章目录下的 `.checkpoint_lesson18.json` 即可。
