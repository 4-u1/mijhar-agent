"""Agent run limits and switches. Everything here is enforced in code (loop.py), not asked of the model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentConfig:
    max_iterations: int = 10            # model calls per turn
    max_tool_calls_per_turn: int = 16
    max_audits_per_session: int = 3
    max_turns_per_session: int = 60
    session_token_budget: int = 200_000  # estimated tokens across the whole session (model + tools)
    context_limit_tokens: int = 24_000   # above this the oldest turns are compacted (scratchpad share of the 128k plan)
    trim_keep_last: int = 4              # full tool results kept; older ones become one-line stubs
    turn_seconds: float = 150.0
    tool_seconds: float = 90.0
    max_tool_result_chars: int = 6_000
    paste_to_vault: bool = True          # long chat text is vaulted, never put in the model context
    paste_threshold_chars: int = 600   # longer chat text, or any text the guard flags, is vaulted as a document
    scrub_output: bool = True            # strip links, images, tags and token-shaped strings from replies
    wrap_untrusted: bool = True          # document-derived text in tool results is tagged <untrusted_claim>
    max_sessions_per_client: int = 20
    skills: bool = True                  # skill index in the prompt + load_skill tool (live-eval config A turns it off)
