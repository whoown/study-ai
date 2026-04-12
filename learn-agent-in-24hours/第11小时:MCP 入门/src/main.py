"""
第 11 小时：MCP 入门 — FastMCP 注册工具；Client 通过 stdio 子进程走真实协议（失败时可教学降级）。
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.server.fastmcp import FastMCP

    MCP_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # noqa: BLE001 - 教学脚本允许降级
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None
    FastMCP = None
    MCP_IMPORT_ERROR = exc

# 与 --mcp-server 使用同一 FastMCP 实例
mcp = FastMCP("learn-agent-hour11") if FastMCP is not None else None


def echo_impl(text: str) -> str:
    """原样返回传入的文本（实现体，供教学降级直接调用）。"""
    return text


def word_count_impl(text: str) -> int:
    """统计字符数（实现体）。"""
    return len(text)


if mcp is not None:

    @mcp.tool()
    def echo(text: str) -> str:
        """原样返回传入的文本。"""
        return echo_impl(text)


    @mcp.tool()
    def word_count(text: str) -> int:
        """统计中英混合文本「字符数」（教学用，非 NLP 分词）。"""
        return word_count_impl(text)


def run_mcp_server() -> None:
    """真实 MCP Server：stdio 传输，由宿主或本脚本的 Client 子进程连接。"""
    if mcp is None:
        teaching_fallback(f"未安装 mcp 依赖：{MCP_IMPORT_ERROR!r}")
        return
    mcp.run(transport="stdio")


async def run_mcp_client_demo() -> bool:
    """
    真实 MCP Client：拉起子进程 Server，执行 initialize -> list_tools -> call_tool。
    返回 True 表示协议路径跑通。
    """
    if MCP_IMPORT_ERROR is not None or ClientSession is None or stdio_client is None:
        print("[MCP Client] 当前环境未安装 mcp，跳过真实协议链路。")
        return False
    params = StdioServerParameters(
        command=sys.executable,
        args=[__file__, "--mcp-server"],
        env=dict(os.environ),
    )
    try:
        async with stdio_client(params) as streams:
            read, write = streams
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                names = [t.name for t in listed.tools]
                print("[MCP Client] list_tools:", names)

                r1 = await session.call_tool("echo", {"text": "你好，MCP"})
                # 不同版本 SDK 的返回结构以 content 列表为主
                print("[MCP Client] call_tool echo ->", r1)

                r2 = await session.call_tool("word_count", {"text": "自动调研"})
                print("[MCP Client] call_tool word_count ->", r2)
        return True
    except Exception as e:  # noqa: BLE001 — 教学脚本：捕获后走降级
        print("[MCP Client] 子进程/握手失败:", repr(e))
        return False


def teaching_fallback(reason: Optional[str] = None) -> None:
    """教学降级：不经过 JSON-RPC，直接调用 Python 函数（与 Server 注册逻辑同源）。"""
    if reason:
        print("[教学降级] 原因:", reason)
    print("[教学降级] 以下调用不经过 MCP 消息，仅便于离线阅读：")
    print("  echo ->", echo_impl("你好，MCP"))
    print("  word_count ->", word_count_impl("自动调研"))
    print("[教学降级] 真实路径中，上述调用应由 Client 发 tools/call，Server 在子进程内执行。")


def main() -> None:
    if "--mcp-server" in sys.argv:
        run_mcp_server()
        return

    if "--fallback-only" in sys.argv:
        reason = "用户指定 --fallback-only"
        if MCP_IMPORT_ERROR is not None:
            reason += f"；同时检测到 mcp 缺失：{MCP_IMPORT_ERROR!r}"
        teaching_fallback(reason)
        return

    print("=== MCP 入门：默认尝试「子进程 stdio Server + ClientSession」===")
    ok = asyncio.run(run_mcp_client_demo())
    if not ok:
        teaching_fallback("Client 路径未成功完成")


if __name__ == "__main__":
    main()
