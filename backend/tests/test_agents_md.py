from pathlib import Path

from mijhar.llm import SYSTEM_EXTRACT, SYSTEM_JUDGE

SPEC = (Path(__file__).resolve().parents[2] / "AGENTS.md").read_text(encoding="utf-8")


def test_prompts_in_agents_md_match_code():
    assert SYSTEM_EXTRACT in SPEC and SYSTEM_JUDGE in SPEC


def test_budget_table_matches_code():
    from mijhar.budget import ALLOCATION
    for k, v in ALLOCATION.items():
        assert f"{v:,}" in SPEC, k
