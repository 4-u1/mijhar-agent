"""Core tool implementations. The MCP server and the in-process toolbox share this code,
so there is exactly one implementation of each tool and one validation path."""
from __future__ import annotations

from . import signing
from .reasoning import stance_rules
from .retrieval import default_index

CORPORA = {"all", "ai_ethics", "cloud_sovereignty", "govtech_procurement"}


def hybrid_search_docs(query: str, corpus_id: str = "all", top_k: int = 5, mode: str = "hybrid") -> dict:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if len(query) > 2000:
        raise ValueError("query too long (max 2000 chars)")
    if corpus_id not in CORPORA:
        raise ValueError(f"unknown corpus_id {corpus_id!r}; expected one of {sorted(CORPORA)}")
    if not 1 <= int(top_k) <= 10:
        raise ValueError("top_k must be between 1 and 10")
    if mode not in ("bm25", "hybrid"):
        raise ValueError("mode must be 'bm25' or 'hybrid'")
    ix = default_index()
    return {"results": ix.search(query, int(top_k), mode, None if corpus_id == "all" else corpus_id),
            "encoder": ix.encoder.name, "corpus_notice": "synthetic benchmark corpus, not official law"}


def verify_evidence(claim_text: str, reference_text: str) -> dict:
    for name, v in (("claim_text", claim_text), ("reference_text", reference_text)):
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"{name} must be a non-empty string")
        if len(v) > 4000:
            raise ValueError(f"{name} too long (max 4000 chars)")
    return stance_rules(claim_text, reference_text)


def execute_audit_action(decision_token: str, action: str, job_id: str, report_sha256: str,
                         target_registry: str = "national_audit_registry") -> dict:
    """The only write tool. Fails closed on anything that is not a valid, unused, matching human approval."""
    if not all(isinstance(x, str) and x for x in (decision_token, action, job_id, report_sha256)):
        raise ValueError("decision_token, action, job_id and report_sha256 are required strings")
    return signing.commit_action(decision_token, action, job_id, report_sha256, target_registry)
