"""Response cache for model calls (same idea as the course's agentkit cache).

Identical requests (same model, messages, tools, temperature 0) replay from disk, so re-running a demo or an eval
costs no free-tier quota and survives a rate limit on stage. On by default; MIJHAR_CACHE=0 turns it off.
Evals that measure pass^k must turn it off (they do), because a cached reply is not a fresh sample.

PDPL note: the cache stores model replies (which can quote claim text) in MIJHAR_DATA_DIR/cache.sqlite.
Apply the same retention as the checkpoint database.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading

from .config import data_dir, env

_lock = threading.Lock()


def enabled() -> bool:
    return (env("MIJHAR_CACHE", "1") or "1") == "1"


def key(kind: str, payload: dict) -> str:
    return hashlib.sha256((kind + json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)).encode()).hexdigest()


def _con() -> sqlite3.Connection:
    c = sqlite3.connect(str(data_dir() / "cache.sqlite"), timeout=10)
    c.execute("CREATE TABLE IF NOT EXISTS cache(k TEXT PRIMARY KEY, v TEXT)")
    return c


def get(k: str) -> dict | None:
    if not enabled():
        return None
    with _lock, _con() as c:
        r = c.execute("SELECT v FROM cache WHERE k=?", (k,)).fetchone()
    return json.loads(r[0]) if r else None


def put(k: str, value: dict) -> None:
    if not enabled():
        return
    with _lock, _con() as c:
        c.execute("INSERT OR REPLACE INTO cache(k, v) VALUES (?, ?)", (k, json.dumps(value, ensure_ascii=False)))
