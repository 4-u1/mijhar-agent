"""Configuration. Secrets come only from the environment (or a git-ignored .env file).

Nothing here has a usable default for a secret: a missing secret makes the signing
and API layers refuse to work (fail closed) instead of falling back to a known value.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # backend/


class ConfigError(RuntimeError):
    pass


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader. Existing environment variables always win."""
    path = path or (ROOT / ".env")
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_dotenv()


def env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def data_dir() -> Path:
    p = Path(env("MIJHAR_DATA_DIR", str(ROOT / "runs")))
    p.mkdir(parents=True, exist_ok=True)
    return p


def signing_secret() -> bytes:
    s = env("MIJHAR_SIGNING_SECRET")
    if not s or len(s) < 32:
        raise ConfigError("MIJHAR_SIGNING_SECRET missing or shorter than 32 chars (run: uv run mijhar init-env)")
    return s.encode()


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _parse_pairs(raw: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in (raw or "").split(","):
        if ":" in item:
            k, v = item.split(":", 1)
            out[k.strip()] = v.strip().lower()
    return out


def check_secret(table_env: str, presented: str | None, who: str | None = None) -> str | None:
    """Constant-time check of a presented key against `name:sha256hex` pairs.
    Returns the matching name, or None. If `who` is given, only that name may match."""
    if not presented:
        return None
    table = _parse_pairs(env(table_env))
    digest = sha256_hex(presented)
    match = None
    for name, stored in table.items():
        ok = hmac.compare_digest(stored, digest)
        if ok and (who is None or who == name):
            match = name
    return match


@dataclass
class RunConfig:
    """Per-run switches. Config A and B in the evals differ only here."""
    guard_level: str = "hardened"      # "basic" (original regex port) | "hardened"
    retrieval_mode: str = "hybrid"     # "bm25" | "hybrid"
    live_llm: bool = False             # True -> OpenRouter for extraction + NLI
    use_mcp: bool = False              # True -> tools over stdio MCP, else in-process
    top_k: int = 3
    min_hybrid_score: float = 0.15   # calibrated on the 8 claim tasks: true evidence >= 0.21, spurious <= 0.095
    max_steps: int = 40
    max_run_tokens: int = 120_000
    max_doc_chars: int = 200_000

    def to_dict(self) -> dict:
        return self.__dict__.copy()


CONFIG_A = RunConfig(guard_level="basic", retrieval_mode="bm25")
CONFIG_B = RunConfig(guard_level="hardened", retrieval_mode="hybrid")


@dataclass
class OpenRouterSettings:
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = field(default_factory=lambda: env("MIJHAR_MODEL", "google/gemma-4-31b-it:free") or "")   # the course default free model
    api_key: str | None = field(default_factory=lambda: env("OPENROUTER_API_KEY"))
    # Optional second model (e.g. a paid or different free one) used when the first is gone or rate-limited.
    # "responses" = client.responses.create (the course's RAG uses it); "chat" = chat.completions.
    # If the provider rejects the Responses endpoint the client switches to "chat" by itself.
    api_shape: str = field(default_factory=lambda: env("MIJHAR_API_SHAPE", "responses") or "responses")
    fallback_model: str | None = field(default_factory=lambda: env("MIJHAR_FALLBACK_MODEL", "nvidia/nemotron-3.5-lightning:free"))
    # Hard cap on model requests per audit run, retries included (extract 1 + judge up to claims x top_k).
    max_calls_per_run: int = field(default_factory=lambda: int(env("MIJHAR_MAX_LLM_CALLS", "150") or 150))
