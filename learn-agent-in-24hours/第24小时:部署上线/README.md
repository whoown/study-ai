# 第 24 小时：部署上线

## 本章目标

- 用 **FastAPI** 搭一个 **最小可部署** 的 HTTP 服务，把「Agent 能力」暴露为 **稳定的网络接口**。
- 理解部署时要考虑的 **健康检查、输入校验、无密钥降级、进程启动方式**。
- 知道如何把同一套业务逻辑 **扩展到 Streamlit 管理台或前后端分离**（本章在代码外说明，不在 `main.py` 里强行堆 UI）。

## 核心概念

- **服务边界**：客户端只依赖 HTTP 契约（路径、JSON 字段），不关心内部是模板还是大模型。
- **配置外置**：密钥来自环境变量（`OPENAI_API_KEY` 等），避免写进镜像或代码库。
- **可观测性起点**：至少提供 `/health`，生产环境再叠加日志、指标、追踪。

## 案例设计

`src/main.py` 提供：

| 路径 | 作用 |
|------|------|
| `GET /health` | 健康检查，负载均衡与编排常用 |
| `POST /agent/invoke` | 接收 `{"task": "..."}`，返回 `mode`（`llm` 或 `mock`）与 `answer` |

当未配置 API Key 时，`answer` 来自确定性模板，并返回 `mode=mock`，便于在 CI 或离线环境演练部署流程。

## 代码讲解

文件：`src/main.py`。

- **`create_app`**：工厂函数，集中挂载路由，便于测试或嵌入更大应用。
- **`health`**：轻量存活探测。
- **`InvokeBody`（Pydantic 模型）**：校验请求体字段，减少无效输入。
- **`invoke_agent`**：核心处理器：优先 `_answer_with_llm`，失败或无 Key 时 `_answer_mock`。
- **`main` 守护块**：用 `uvicorn.run` 启动内置服务器，方便 `python src/main.py` 一键体验。

## 运行方式

```bash
cd "第24小时:部署上线"
python src/main.py
```

默认监听 `http://127.0.0.1:8000`。另开终端探测：

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/agent/invoke \
  -H 'Content-Type: application/json' \
  -d '{"task":"帮我把这句话压缩成标题：多智能体实战与部署"}'
```

等价启动（若你已熟悉 ASGI 启动器）：

```bash
cd "第24小时:部署上线"
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 扩展到 Streamlit / 前后端

- **Streamlit**：在独立 `streamlit_app.py`（可自行添加）里用 `requests.post("http://127.0.0.1:8000/agent/invoke", json=...)` 调用本服务；UI 只负责表单与展示，模型与编排逻辑仍在后端。
- **前后端分离**：前端页面调用同一接口；通过网关统一鉴权（例如 API Key、JWT、OAuth2）；对公网暴露时务必加 **速率限制、审计日志与密钥轮换**。

生产部署还可选用 Docker + 反向代理（Nginx/Caddy）、进程管理（systemd/supervisor）或云托管（Cloud Run、ECS 等）；本章保持最小实现，避免把运维细节写进教学代码。
