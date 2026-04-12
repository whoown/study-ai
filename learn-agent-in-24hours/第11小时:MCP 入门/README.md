# 第 11 小时：MCP 入门

## 本章目标

- 理解 **MCP（Model Context Protocol）** 在解决什么问题：把「工具、资源、提示」从应用里抽离成 **独立 Server**，Client（宿主应用）用 **统一消息协议** 发现与调用，而不是每个产品各写一套适配层。
- 分清本教程 **`src/main.py` 里哪些是真实 MCP 协议路径，哪些是教学用简化**（见下文「真实 vs 简化」）。

## 核心概念

1. **Server / Client**：Server 声明能力（如 `tools/list` 里列出的工具）；Client 发 `tools/call` 带参数，Server 执行后返回结构化结果。
2. **传输层**：常见为 **stdio**（子进程管道）或 **HTTP(S)**；本示例主路径使用 **stdio 子进程**，与 Cursor、Claude Desktop 等本地集成方式一致。
3. **与 LangChain 工具对比**：LangChain 的 `@tool` 是「同进程函数指针」；MCP 是「进程外、协议化」——**多封装了进程边界、序列化、能力发现与版本协商**。

## 真实 vs 简化（必读）

| 部分 | 说明 |
|------|------|
| **真实** | `run_mcp_server` 中 `FastMCP` 注册的工具、`--mcp-server` 模式下 `mcp.run(transport="stdio")` 启动的是 **真实 MCP Server**；`run_mcp_client_demo` 里 `ClientSession` + `stdio_client` 子进程拉起同一脚本，会走 **initialize / list_tools / call_tool** 等真实握手与调用。 |
| **简化** | 未安装依赖、无 API Key、或子进程失败时，`teaching_fallback` 仅在 **当前进程内** 调用同名 Python 函数，**不经过 JSON-RPC**，用于保证单文件、离线也能跑通逻辑阅读。 |

## 案例设计

Server 暴露两个教学工具：**echo**（回显）、**word_count**（字数统计）。默认 `python src/main.py` 尝试 **客户端 + 子进程 Server**；加参数 `python src/main.py --mcp-server` 仅启动 stdio Server（供外部 MCP Client 连接）。

## 代码讲解

| 函数 | 作用 |
|------|------|
| `run_mcp_server` | 创建 `FastMCP`，`@mcp.tool()` 注册工具；`--mcp-server` 时阻塞跑 stdio。 |
| `run_mcp_client_demo` | `StdioServerParameters` 启动子进程 Server，`list_tools` / `call_tool` 演示完整协议路径。 |
| `teaching_fallback` | 协议不可用时的进程内降级说明。 |
| `main` | 根据 CLI 与环境选择 Server / Client / 降级。 |

## 运行方式

```bash
cd "第11小时:MCP 入门"
# 默认：尝试启动子进程 MCP Server 并用 Client 调 echo / word_count
python src/main.py

# 仅作为 stdio MCP Server 运行（给外部客户端连接）
python src/main.py --mcp-server
```

若子进程或 MCP 握手在你环境中失败，请阅读终端中的 **[教学降级]** 说明；真实排错需检查 Python 版本、`mcp` 包版本与防火墙/权限。
