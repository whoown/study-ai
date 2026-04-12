# 《24小时学会 Agent 开发》

这是一套面向初学者的渐进式 Agent 教学工程。你会从最小的决策循环开始，逐步掌握 LLM 接入、ReAct、Function Calling、Rules、记忆、上下文管理、LangChain、LangGraph、MCP、RAG、多智能体、Human-in-the-Loop 以及部署上线。

本教程的设计原则很简单：

- 每小时只新增一个核心能力，降低心智负担。
- 每章都包含理论讲解与最小可运行代码。
- 先理解本质，再引入框架，避免只会调用黑盒。

## 目录说明

- `core/`：课程设计说明与完整 syllabus。
- `第X小时：主题/README.md`：本章讲解文档。
- `第X小时：主题/src/main.py`：本章可运行案例入口。
- `run_demo.py`：统一运行脚本。
- `.env.example`：模型配置模板。
- `requirements.txt`：共享依赖列表。

## 为什么只维护一份依赖

建议整个工程只使用一份 `requirements.txt`，并配套一份 `.venv` 虚拟环境。

这样做的好处是：

- 学习者只需要安装一次依赖。
- 前后章节可以平滑共享模型客户端、框架与部署能力。
- 不会因为 24 份依赖文件而增加维护成本。

## 环境准备

建议使用 Python 3.11 及以上版本。

```bash
cd learn-agent-in-24hours
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

然后编辑 `.env`，填入自己的模型配置：

```bash
OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
```

如果你使用 DeepSeek 一类 OpenAI 兼容服务，可以把 `OPENAI_BASE_URL` 改为对应地址，例如 `https://api.deepseek.com`，并将 `OPENAI_MODEL` 改为相应模型名。

## 如何运行

列出所有章节：

```bash
python run_demo.py --list
```

运行指定章节：

```bash
python run_demo.py 1
python run_demo.py 12
python run_demo.py 24
```

你也可以直接进入某一章目录运行：

```bash
cd "第1小时:理解最小 Agent"
python src/main.py
```

## 学习建议

推荐你按照章节顺序推进，因为后面的章节默认你已经掌握前面的概念。如果你只是想快速看某个主题，也可以单独进入对应目录阅读 `README.md` 并运行案例。

阅读顺序建议如下：

1. 先看本章目标，明确这小时只学什么。
2. 再运行 `src/main.py`，观察程序输出。
3. 然后对照 README 中的代码讲解理解关键机制。
4. 最后尝试自己改动提示词、工具、状态结构或流程逻辑。

## 课程阶段

### 第一阶段：Agent 基础心智模型

- 第 1-8 小时：最小 Agent、真实 LLM、ReAct、函数调用、规则、记忆、上下文窗口。

### 第二阶段：框架与标准协议

- 第 9-12 小时：LangChain、LangGraph、MCP、自动调研 Agent。

### 第三阶段：检索、规划、反思与状态

- 第 13-18 小时：Embedding、RAG、主动检索、规划执行、反思纠错、状态持久化。

### 第四阶段：可组合与可上线

- 第 19-24 小时：Skills、多智能体、Human-in-the-Loop、API 与 UI 部署。

## 注意事项

- 部分章节依赖真实模型服务；如果没有配置 `.env`，代码会打印提示并走教学化降级分支。
- 课程后半段会引入 LangChain、LangGraph、Chroma、FastAPI、Streamlit 等依赖，但示例都会尽量保持最小规模。
- 当前仓库目标是教学可读性，不是直接生产可用。
