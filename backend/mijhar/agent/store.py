"""Sessions, the document vault and the officer's saved preferences (SQLite, one file).

* The vault holds raw uploads. Raw text is returned only to harness code (the audit tool),
  never to the model: the model gets an id, a name, a size and a hash.
* Memory is read-only for the model. Only the officer (through the API / UI) writes it, so a
  poisoned document cannot plant a standing instruction ("memory poisoning").
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ..config import data_dir

MAX_DOC_CHARS = 200_000
MAX_DOCS_PER_SESSION = 10
MAX_EVENTS = 500
PREF_VALUES = {"language": {"auto", "ar", "en"}, "detail": {"brief", "detailed"}}
DEFAULT_PREFS = {"language": "auto", "detail": "brief"}


class StoreError(ValueError):
    pass


@dataclass
class Session:
    id: str
    client: str
    created: float = field(default_factory=time.time)
    messages: list = field(default_factory=list)       # provider-format transcript (keys starting x_ are internal)
    events: list = field(default_factory=list)         # UI replay log
    jobs: list = field(default_factory=list)           # audit job ids created in this session
    announced_docs: list = field(default_factory=list)
    pending: dict | None = None                        # approval waiting for the human, or None
    usage: dict = field(default_factory=lambda: {"turns": 0, "model_calls": 0, "tool_calls": 0, "tokens": 0, "audits": 0})
    planner: str = "offline"                           # "llm" | "offline"
    protocol: str = "native"                           # "native" tool calling | "json" text protocol
    summary: str = ""                                  # compacted older turns

    def to_json(self) -> str:
        d = self.__dict__.copy()
        d["events"] = d["events"][-MAX_EVENTS:]
        return json.dumps(d, ensure_ascii=False)

    @staticmethod
    def from_json(raw: str) -> "Session":
        return Session(**json.loads(raw))


class Store:
    def __init__(self, path: str | Path | None = None):
        self.path = str(path or (data_dir() / "agent.sqlite"))
        with self._con() as c:
            c.execute("CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, client TEXT, created REAL, data TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS docs(id TEXT PRIMARY KEY, session_id TEXT, name TEXT, sha256 TEXT, chars INTEGER, text TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS memories(client TEXT PRIMARY KEY, data TEXT)")

    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        return con

    # ---- sessions
    def create(self, client: str) -> Session:
        s = Session(id=f"SES-{uuid.uuid4().hex[:10]}", client=client)
        self.save(s)
        return s

    def save(self, s: Session) -> None:
        with self._con() as c:
            c.execute("INSERT OR REPLACE INTO sessions(id, client, created, data) VALUES (?,?,?,?)",
                      (s.id, s.client, s.created, s.to_json()))

    def get(self, sid: str, client: str) -> Session | None:
        """A session is visible only to the client key that created it."""
        with self._con() as c:
            r = c.execute("SELECT data FROM sessions WHERE id=? AND client=?", (sid, client)).fetchone()
        return Session.from_json(r["data"]) if r else None

    def count(self, client: str) -> int:
        with self._con() as c:
            return c.execute("SELECT COUNT(*) FROM sessions WHERE client=?", (client,)).fetchone()[0]

    # ---- vault
    def add_doc(self, session_id: str, name: str, text: str) -> dict:
        if not isinstance(text, str) or not text.strip():
            raise StoreError("document is empty")
        if len(text) > MAX_DOC_CHARS:
            raise StoreError(f"document exceeds {MAX_DOC_CHARS} characters")
        with self._con() as c:
            n = c.execute("SELECT COUNT(*) FROM docs WHERE session_id=?", (session_id,)).fetchone()[0]
            if n >= MAX_DOCS_PER_SESSION:
                raise StoreError(f"at most {MAX_DOCS_PER_SESSION} documents per session")
            doc_id = f"DOC-{uuid.uuid4().hex[:8]}"
            sha = hashlib.sha256(text.encode()).hexdigest()
            name = (name or "document.txt")[:120]
            c.execute("INSERT INTO docs VALUES (?,?,?,?,?,?)", (doc_id, session_id, name, sha, len(text), text))
        return {"doc_id": doc_id, "name": name, "chars": len(text), "sha256": sha}

    def doc_meta(self, session_id: str, doc_id: str) -> dict | None:
        with self._con() as c:
            r = c.execute("SELECT id, name, sha256, chars FROM docs WHERE id=? AND session_id=?", (doc_id, session_id)).fetchone()
        return {"doc_id": r["id"], "name": r["name"], "sha256": r["sha256"], "chars": r["chars"]} if r else None

    def doc_text(self, session_id: str, doc_id: str) -> str | None:
        """Harness-only. Never put the return value in a model message or a tool result."""
        with self._con() as c:
            r = c.execute("SELECT text FROM docs WHERE id=? AND session_id=?", (doc_id, session_id)).fetchone()
        return r["text"] if r else None

    def list_docs(self, session_id: str) -> list[dict]:
        with self._con() as c:
            rows = c.execute("SELECT id, name, sha256, chars FROM docs WHERE session_id=? ORDER BY rowid", (session_id,)).fetchall()
        return [{"doc_id": r["id"], "name": r["name"], "sha256": r["sha256"], "chars": r["chars"]} for r in rows]

    # ---- memory (officer preferences)
    def prefs(self, client: str) -> dict:
        with self._con() as c:
            r = c.execute("SELECT data FROM memories WHERE client=?", (client,)).fetchone()
        return DEFAULT_PREFS | (json.loads(r["data"]) if r else {})

    def set_prefs(self, client: str, new: dict) -> dict:
        cur = self.prefs(client)
        for k, v in (new or {}).items():
            if k not in PREF_VALUES or v not in PREF_VALUES[k]:
                raise StoreError(f"invalid preference {k}={v!r}; allowed: { {a: sorted(b) for a, b in PREF_VALUES.items()} }")
            cur[k] = v
        with self._con() as c:
            c.execute("INSERT OR REPLACE INTO memories(client, data) VALUES (?,?)", (client, json.dumps(cur)))
        return cur
