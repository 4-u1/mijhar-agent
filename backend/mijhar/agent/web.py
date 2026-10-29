"""HTTP layer for the agent (Starlette, which FastAPI is built on). Mounted by api.py at /agent.

  GET  /                                 the agent web app (static, same origin, strict CSP)
  GET  /api/capabilities                 planner, model, MCP, limits (no secrets)
  GET  /api/samples                      bundled sample documents
  GET  /api/memory  · POST /api/memory   the officer's saved preferences            X-API-Key
  POST /api/sessions                     new session                                X-API-Key
  GET  /api/sessions/{id}                transcript, docs, pending approval         X-API-Key
  POST /api/sessions/{id}/documents      {filename, text} or {sample}               X-API-Key
  POST /api/sessions/{id}/messages       {text}; Accept: text/event-stream streams   X-API-Key
  POST /api/sessions/{id}/decision       {reviewer, decision, report_sha256}        X-API-Key + X-Reviewer-Key
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from ..config import check_secret
from .service import AgentService, ServiceError
from .store import StoreError

WEB = Path(__file__).resolve().parent.parent / "data" / "agent" / "web"
MAX_BODY = 450_000
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
       "font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
SEC = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Content-Security-Policy": CSP,
       "Permissions-Policy": "camera=(), microphone=(), geolocation=()"}


def _err(status: int, msg: str) -> JSONResponse:
    return JSONResponse({"detail": msg}, status_code=status)


def build_agent_app(get_service: Callable[[], AgentService]) -> Starlette:
    def client(req: Request) -> str:
        who = check_secret("MIJHAR_CLIENT_KEYS", req.headers.get("x-api-key"))
        if not who:
            raise ServiceError(401, "invalid or missing X-API-Key")
        return who

    async def body(req: Request) -> dict:
        if int(req.headers.get("content-length") or 0) > MAX_BODY:
            raise ServiceError(413, "request body too large")
        raw = await req.body()
        if len(raw) > MAX_BODY:
            raise ServiceError(413, "request body too large")
        try:
            data = json.loads(raw or b"{}")
        except ValueError:
            raise ServiceError(400, "body must be JSON")
        if not isinstance(data, dict):
            raise ServiceError(400, "body must be a JSON object")
        return data

    def guarded(fn):
        async def ep(req: Request):
            try:
                return await fn(req)
            except ServiceError as e:
                return _err(e.status, e.message)
            except StoreError as e:
                return _err(422, str(e))
        return ep

    # ---------------------------------------------------------------- static
    async def index(req: Request):
        return FileResponse(WEB / "index.html", headers=SEC | {"Cache-Control": "no-cache"})

    async def static(req: Request):
        name = req.path_params["name"]
        if name not in ("app.js", "app.css", "icon.svg"):
            return _err(404, "not found")
        media = {"js": "text/javascript", "css": "text/css", "svg": "image/svg+xml"}[name.rsplit(".", 1)[1]]
        return FileResponse(WEB / name, media_type=media, headers=SEC | {"Cache-Control": "no-cache"})

    # ---------------------------------------------------------------- api
    async def caps(req: Request):
        return JSONResponse(get_service().capabilities())

    async def samples(req: Request):
        return JSONResponse({"samples": get_service().samples()})

    async def memory(req: Request):
        who, svc = client(req), get_service()
        if req.method == "POST":
            return JSONResponse(svc.store.set_prefs(who, await body(req)))
        return JSONResponse(svc.store.prefs(who))

    async def new_session(req: Request):
        who = client(req)
        s = await run_in_threadpool(get_service().new_session, who)
        return JSONResponse({"session_id": s.id, "planner": s.planner}, status_code=201)

    async def get_session(req: Request):
        who = client(req)
        return JSONResponse(await run_in_threadpool(get_service().view, req.path_params["sid"], who))

    async def add_doc(req: Request):
        who, data = client(req), await body(req)
        meta = await run_in_threadpool(get_service().add_document, req.path_params["sid"], who,
                                       str(data.get("filename") or "")[:120], data.get("text"), data.get("sample"))
        return JSONResponse(meta, status_code=201)

    async def message(req: Request):
        who, data = client(req), await body(req)
        text = data.get("text")
        if not isinstance(text, str):
            raise ServiceError(422, "text must be a string")
        svc = get_service()
        events = await run_in_threadpool(svc.turn, req.path_params["sid"], who, text)   # validates, may raise
        if "text/event-stream" not in req.headers.get("accept", ""):
            return JSONResponse({"events": await run_in_threadpool(list, events)})

        def sse():
            try:
                for ev in events:
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n".encode()
            except Exception as e:  # never leave the client hanging without a reason
                yield f"data: {json.dumps({'type': 'error', 'message': f'{type(e).__name__}: {e}'[:200]})}\n\n".encode()
        return StreamingResponse(sse(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    async def decision(req: Request):
        who, data = client(req), await body(req)
        ev = await run_in_threadpool(get_service().decide, req.path_params["sid"], who, str(data.get("reviewer", ""))[:64],
                                     req.headers.get("x-reviewer-key", ""), str(data.get("decision", "")),
                                     str(data.get("report_sha256", "")))
        return JSONResponse({"events": ev})

    routes = [
        Route("/", index), Route("/static/{name}", static),
        Route("/api/capabilities", guarded(caps)), Route("/api/samples", guarded(samples)),
        Route("/api/memory", guarded(memory), methods=["GET", "POST"]),
        Route("/api/sessions", guarded(new_session), methods=["POST"]),
        Route("/api/sessions/{sid}", guarded(get_session)),
        Route("/api/sessions/{sid}/documents", guarded(add_doc), methods=["POST"]),
        Route("/api/sessions/{sid}/messages", guarded(message), methods=["POST"]),
        Route("/api/sessions/{sid}/decision", guarded(decision), methods=["POST"]),
    ]
    return Starlette(routes=routes)


def response_headers() -> dict:   # exported for tests
    return dict(SEC)


__all__ = ["build_agent_app", "Response"]
