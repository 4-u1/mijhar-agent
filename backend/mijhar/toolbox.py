"""One interface to the three tools: in-process, or over a persistent stdio MCP session."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import threading

from . import tools


class ToolError(RuntimeError):
    pass


class McpBridge:
    """Runs an MCP stdio client session on a background event loop so sync graph nodes can call it."""

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._err: Exception | None = None
        self._stop: asyncio.Event | None = None
        self._session = None
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()
        if not self._ready.wait(60) or self._err:
            raise ToolError(f"MCP server failed to start: {self._err}")

    def _run(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._main())

    async def _main(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        self._stop = asyncio.Event()
        env = {k: v for k, v in os.environ.items() if k.startswith("MIJHAR_")}
        params = StdioServerParameters(command=sys.executable, args=["-m", "mijhar.mcp_server"], env=env)
        try:
            async with stdio_client(params) as (r, w):
                async with ClientSession(r, w) as s:
                    await s.initialize()
                    self._session = s
                    self._ready.set()
                    await self._stop.wait()
        except Exception as e:  # pragma: no cover
            self._err = e
            self._ready.set()

    def call(self, name: str, args: dict) -> dict:
        async def _c():
            return await self._session.call_tool(name, args)
        res = asyncio.run_coroutine_threadsafe(_c(), self._loop).result(120)
        text = "".join(getattr(c, "text", "") for c in res.content)
        if res.is_error:
            raise ToolError(text or "tool error")
        return json.loads(text)

    def list_tools(self) -> list[str]:
        async def _l():
            return [t.name for t in (await self._session.list_tools()).tools]
        return asyncio.run_coroutine_threadsafe(_l(), self._loop).result(60)

    def close(self):
        if self._stop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)
        self._t.join(timeout=10)


class ToolBox:
    def __init__(self, use_mcp: bool = False):
        self.use_mcp = use_mcp
        self.bridge = McpBridge() if use_mcp else None
        self.calls: list[dict] = []

    def call(self, name: str, args: dict) -> dict:
        self.calls.append({"tool": name, "transport": "mcp" if self.use_mcp else "local"})
        if self.bridge:
            return self.bridge.call(name, args)
        fn = getattr(tools, name)
        try:
            return fn(**args)
        except (ValueError, PermissionError) as e:
            raise ToolError(str(e)) from e

    def close(self):
        if self.bridge:
            self.bridge.close()
