# 第 1 小时：理解最小 Agent

## 本章目标

- 用**不调用大模型**的方式，把 Agent 抽象成可运行的 Python 程序。
- 理解「感知 → 思考 → 行动 → 观察 → 总结」这一最小闭环。
- 为后续接入真实 LLM、ReAct、函数调用等章节打好心智模型。

## 核心概念

- **Agent（智能体）**：在环境里根据输入做决策并执行动作的程序；不必一开始就依赖神经网络。
- **工具（Tool）**：Agent 可调用的外部能力，例如计算器、查表、模拟搜索。
- **闭环（Loop）**：每一轮先产出 **Thought（思考）**，再产出 **Action（动作）**，执行后得到 **Observation（观察）**，最后可给出 **Summary（总结）**。

## 案例设计

场景：用户给出一道简单的「需要两步工具」的问题——先算乘法，再把结果格式化成一句话。  
我们用**关键词与简单规则**模拟「大脑」，让你看清：即使没有 LLM，Agent 的结构依然成立。

## 代码讲解

本章代码集中在 `src/main.py`：

- **`TOOLS`**：工具注册表，把名字映射到可调用函数（教学上等同于「工具清单」）。
- **`run_tool(name, args)`**：统一执行入口，负责打印 **Action** 并返回 **Observation**。
- **`fake_brain(user_text)`**：用规则模拟「思考结果」，返回 `(thought, action_name, action_args)`。
- **`run_episode(user_text)`**：驱动完整循环，逐步打印 **Thought / Action / Observation**，最后打印 **Summary**。
- **`main()`**：入口函数，演示一个固定任务；你也可以改成 `input()` 交互（自行实验）。

## 运行方式

在章节目录下执行：

```bash
cd "第1小时:理解最小 Agent"
python src/main.py
```

本章**不需要** API Key，开箱即用。
