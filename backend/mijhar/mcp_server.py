"""MIJHAR MCP server (stdio). Three tools over the official MCP Python SDK v2.

    uv run python -m mijhar.mcp_server

In SDK v2 FastMCP was renamed MCPServer (mcp.server.mcpserver). Exceptions raised in a
tool are returned to the client as an error result, never as a silent success.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from . import tools

mcp = MCPServer("mijhar-audit-tools")


@mcp.tool()
def hybrid_search_docs(query: str, corpus_id: str = "all", top_k: int = 5, mode: str = "hybrid") -> dict:
    """Hybrid BM25 + dense retrieval (RRF) over the synthetic regulatory benchmark corpora.
    corpus_id: all | ai_ethics | cloud_sovereignty | govtech_procurement. mode: hybrid | bm25."""
    return tools.hybrid_search_docs(query, corpus_id, top_k, mode)


@mcp.tool()
def verify_evidence(claim_text: str, reference_text: str) -> dict:
    """Stance of a reference passage towards a claim: supports | refutes | neutral (rules-v1)."""
    return tools.verify_evidence(claim_text, reference_text)


@mcp.tool()
def execute_audit_action(decision_token: str, action: str, job_id: str, report_sha256: str,
                         target_registry: str = "national_audit_registry") -> dict:
    """WRITE. Commit to the audit ledger. Requires a valid, unexpired, unused, HMAC-signed human
    approval bound to this job and this exact report hash. Refuses everything else."""
    return tools.execute_audit_action(decision_token, action, job_id, report_sha256, target_registry)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
