"""
第 24 小时：部署上线

这份 main.py 是本章对应的最小可运行教学案例。

阅读建议：
1. 先看 main() 怎么启动案例。
2. 再看主流程函数如何驱动模型、工具、状态或路由。
3. 最后再看辅助函数，理解它们分别承担什么职责。

本章新增能力：把 Agent 包装成可访问服务。
如果你是初学者，建议一边运行一边对照源码，不要只静态阅读。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

from fastapi import FastAPI
from pydantic import BaseModel, Field


class InvokeBody(BaseModel):
    """调用 Agent 的请求体。"""

    task: str = Field(..., min_length=1, description="用户任务描述")


class InvokeResponse(BaseModel):
    """统一响应结构，便于前端与监控解析。"""

    mode: str
    answer: str


# [教学注释] `_answer_with_llm`
# 内部辅助函数，为主流程提供局部能力。

def _answer_with_llm(task: str) -> str | None:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip(), base_url=base_url)
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": "你是简洁中文助手，用一两句话回答，不要markdown。",
                },
                {"role": "user", "content": task},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        return f"[LLM 错误] {exc}"


# [教学注释] `_answer_mock`
# 内部辅助函数，为主流程提供局部能力。

def _answer_mock(task: str) -> str:
    """无密钥或调用失败时的教学输出。"""
    return (
        "【模拟应答】已收到任务，将在配置 OPENAI_API_KEY 后走真实模型。\n"
        f"任务摘要（前 80 字）: {task.strip()[:80]}"
    )


# [教学注释] `create_app`
# 应用工厂函数，负责组装 API 服务。

def create_app() -> FastAPI:
    """应用工厂：挂载路由。"""
    app = FastAPI(title="Hour24 Agent Service", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        """健康检查，供负载均衡或探针使用。"""
        return {"status": "ok"}

    @app.post("/agent/invoke", response_model=InvokeResponse)
    def invoke_agent(body: InvokeBody) -> InvokeResponse:
        """将任务交给 Agent（可选 LLM，否则模板）。"""
        text = _answer_with_llm(body.task)
        if text is None:
            return InvokeResponse(mode="mock", answer=_answer_mock(body.task))
        if text.startswith("[LLM 错误]"):
            return InvokeResponse(mode="error", answer=text)
        return InvokeResponse(mode="llm", answer=text)

    return app


app = create_app()


# [教学注释] `main`
# 脚本入口，通常只负责启动案例。

def main() -> None:
    """直接运行本文件时启动 uvicorn（开发体验向）。"""
    import uvicorn

    host = os.getenv("HOUR24_HOST", "127.0.0.1")
    port = int(os.getenv("HOUR24_PORT", "8000"))
    print(f"启动服务: http://{host}:{port}  （健康检查: /health ，调用: POST /agent/invoke）")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("提示: 未配置 OPENAI_API_KEY，/agent/invoke 将返回 mode=mock。")

    # 直接传入 app 对象，避免依赖工作目录与模块名字符串解析
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
