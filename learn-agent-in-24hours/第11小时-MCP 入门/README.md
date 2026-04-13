# 第 11 小时：MCP 入门

## 本章定位

理解标准化工具接入协议。前面几章中，工具都是直接在 Agent 进程内以函数形式注册和调用的。MCP（Model Context Protocol）提供了一种标准化的协议，将工具的实现从 Agent 中解耦出来，使得工具可以作为独立服务运行，并被任意兼容 MCP 的 Agent 发现和调用。

## 核心概念

### MCP（Model Context Protocol）是什么

MCP 是由 Anthropic 提出的开放标准协议，旨在为 AI 模型与外部工具、数据源之间的交互定义统一的通信规范。它的核心理念类似于 USB 协议之于硬件设备——在 MCP 出现之前，每个 Agent 框架都有自己的工具注册方式，工具开发者需要为不同框架分别适配；MCP 定义了一套通用标准，使得一个工具实现可以被所有兼容 MCP 的客户端使用。

MCP 解决的根本问题是**工具生态的碎片化**。当前的 Agent 生态中，LangChain 有自己的 Tool 接口，AutoGen 有自己的工具规范，各家 LLM 服务商的 Function Calling 格式也不尽相同。MCP 通过定义一个与框架无关的协议层，将工具的"生产"和"消费"解耦开来——工具开发者只需实现一次 MCP 接口，Agent 开发者只需接入一次 MCP 客户端。

MCP 不仅仅是工具调用协议，它还涵盖了资源（Resources）和提示词模板（Prompts）的标准化访问。但在本章中，我们主要关注其工具调用层面。

### Client-Server 架构的设计思想

MCP 采用经典的 Client-Server 架构。**MCP Server** 是工具的提供方，它启动一个服务进程，声明自己能提供哪些工具，并负责执行工具调用请求。**MCP Client** 是工具的消费方，通常嵌入在 Agent 或 LLM 应用中，负责发现服务器的工具列表、将用户请求转化为工具调用、接收并处理返回结果。

这种架构的核心优势是**关注点分离**。工具的开发者不需要关心 Agent 的内部实现，只需按 MCP 规范暴露接口；Agent 的开发者不需要关心工具的内部逻辑，只需通过 MCP Client 发现和调用工具。这使得工具和 Agent 可以独立开发、独立部署、独立升级。

在本章的代码中，`echo_impl` 和 `word_count_impl` 是 MCP Server 侧的工具实现，`run_mcp_server` 负责启动服务。客户端可以通过 MCP 协议连接到这个服务，查询可用工具，并发起调用。

### Capability 声明与工具发现机制

MCP 的一个核心设计是**动态能力发现**。Client 连接到 Server 后，首先进行"握手"——Server 声明自己支持哪些 Capability（能力），包括可用的工具列表、每个工具的名称、描述和参数 schema。

这个发现过程是完全动态的，不需要任何硬编码。Client 只需知道 Server 的地址（或 stdio 管道），连接后就能自动获取所有可用工具的完整信息。这意味着 Agent 可以在运行时动态接入新工具，而不需要重新编码或重新部署。

工具的参数 schema 使用 JSON Schema 定义，这保证了参数验证的标准化。Client 可以在发送调用请求前就进行参数校验，避免无效请求到达 Server。描述字段则供 LLM 阅读，用于决策何时调用该工具——这与 LangChain 中 Tool 的 description 作用完全一致。

### MCP vs 直接 Function Calling 的区别

直接 Function Calling（如 OpenAI 的 function calling 或手写的工具注册）是将工具作为函数直接集成在 Agent 进程内的方式。工具的定义、注册和执行都在同一个进程中完成。

MCP 则将工具的执行放到了独立的进程（甚至独立的机器）中。这一区别带来了几个重要差异：

**隔离性**：MCP 工具运行在独立进程中，一个工具的崩溃不会拖垮 Agent 主进程。直接 Function Calling 中，工具抛出未捕获的异常可能导致整个 Agent 崩溃。

**语言无关性**：MCP Server 可以用任何语言实现，只要遵循 MCP 协议。你的 Agent 用 Python 写，工具可以用 Go、Rust 或 Node.js 实现。直接 Function Calling 通常要求工具和 Agent 使用同一种语言。

**可复用性**：一个 MCP Server 可以同时为多个 Client 提供服务，工具的实现只需维护一份。直接 Function Calling 中，工具代码需要复制到每个使用它的 Agent 项目中。

**网络开销**：MCP 引入了进程间通信的开销，对延迟敏感的场景需要权衡。对于执行时间较短的工具（如简单计算），通信开销可能显著大于执行开销。

### MCP 的生态与应用场景

MCP 自发布以来已被多个主流平台支持，包括 Claude Desktop、Cursor、Continue、Zed 等 IDE 和 AI 应用。社区也贡献了大量 MCP Server 实现，覆盖文件系统操作、数据库查询、Web 搜索、GitHub/GitLab 集成、Slack/Discord 通知等常见场景。

MCP 特别适合以下应用场景：**企业内部工具整合**——将已有的内部 API、数据库查询、监控系统等包装为 MCP Server，让任意 Agent 都能调用；**工具市场**——第三方开发者发布 MCP Server，用户一键安装即可在自己的 Agent 中使用；**多 Agent 协作**——多个 Agent 共享同一组 MCP Server 提供的工具，避免重复实现。

### MCP 的传输层选择（stdio、HTTP SSE）

MCP 协议与传输层解耦，目前主要支持两种传输方式：

**stdio（标准输入输出）**：Client 启动 Server 进程，通过 stdin/stdout 管道通信。这种方式适合本地运行的场景——Server 和 Client 在同一台机器上，不需要网络配置。启动简单、延迟低，是本地开发和调试的首选。本章的 `run_mcp_server` 就采用了这种方式。

**HTTP SSE（Server-Sent Events）**：Client 通过 HTTP 协议与 Server 通信，支持远程部署。Server 可以运行在远程服务器上，Client 通过 URL 连接。适合生产环境中工具服务的集中部署和管理。SSE 的使用使得 Server 可以主动推送消息给 Client，支持长时间运行的工具调用场景。

选择哪种传输方式取决于部署架构：本地开发用 stdio，分布式部署用 HTTP SSE。两种方式在协议层面是等价的，切换传输方式不需要修改工具的实现代码。

## 新手最容易卡住的点

- 混淆 MCP Server 和 MCP Client 的角色。Server 是工具的提供方，Client 是工具的使用方（通常嵌入在 Agent 中）。先确认你正在编写的是哪一侧的代码。
- stdio 模式下 Server 的 stdout 输出被 MCP 协议占用，普通的 print 语句会干扰协议通信。调试日志应输出到 stderr 或文件。
- 工具的参数 schema 定义与实际实现不匹配，导致 Client 发送的请求被 Server 拒绝或解析失败。
- 忘记处理工具执行的错误情况。MCP Server 应当对工具执行中的异常进行捕获并返回标准化的错误响应，而不是让异常导致 Server 进程崩溃。

## 建议动手实验

- 给 MCP Server 新增一个工具（比如"获取当前时间"），包括 schema 定义和实现函数，观察 Client 是否能自动发现并调用它。
- 故意修改 `word_count_impl` 让它抛出异常，观察 MCP 协议如何处理工具执行错误。
- 将 Server 的工具描述改得模糊或错误（比如把 word_count 描述成"计算数字"），观察 LLM 是否还能正确调用它。
- 运行 `teaching_fallback` 分支，对比有 MCP Server 和无 MCP Server 时的 Agent 行为差异。

## 运行方式

```bash
cd "第11小时-MCP 入门"
python main.py
```
