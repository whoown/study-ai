# 《24小时学会 Agent 开发》

这是一套面向初学者的渐进式 Agent 教材。核心设计思想很简单：每一小时只比上一小时多学一点，这样你既不会一上来就被框架和术语压垮，也不会只会调用黑盒而不知道 Agent 的本质。

## 你会如何学习

- 前 1 到 8 小时：先用手写 Python 建立 Agent 骨架，理解模型、工具、循环、记忆和上下文。
- 第 9 到 12 小时：开始引入 LangChain、LangGraph、MCP 和一个小型实战项目。
- 第 13 到 18 小时：进入 Embedding、RAG、主动检索、规划、反思和状态持久化。
- 第 19 到 24 小时：继续学习 Skills、多智能体、Human-in-the-Loop 和部署上线。

## 为什么建议整仓只维护一份 requirements

建议整套课共享一份 `requirements.txt` 和一个 `.venv` 虚拟环境。这样做对初学者最友好：只安装一次依赖，就能顺着 24 节课一路往后学，不会把大量精力耗在重复配环境上。

## 环境准备

```bash
python -m venv .venv
pip install -r requirements.txt
```

把 `.env.example` 复制为 `.env` 后，填入兼容 OpenAI 风格的模型配置：

```bash
OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
```

如果你使用 DeepSeek 一类兼容 OpenAI 协议的服务，只需要把 `OPENAI_BASE_URL` 和 `OPENAI_MODEL` 换成对应值即可。

## 如何运行

```bash
python run_demo.py --list
python run_demo.py 1
python run_demo.py 12
python run_demo.py 24
```

也可以直接进入某一章目录：

```bash
cd "第1小时-理解最小 Agent"
python main.py
```

## 推荐阅读方式

1. 先看本章 README，弄清楚这一小时新增了什么能力。
2. 再运行 `main.py`，观察中间过程打印。
3. 对照源码里的文件头注释、函数注释和关键逻辑注释理解实现。
4. 最后自己改几个参数、提示词、工具或状态结构。

学习 Agent，真正重要的不是背术语，而是逐步建立完整心智模型：`模型 + 工具 + 循环 + 记忆/状态 + 检索/协议 + 编排 + 部署`。
