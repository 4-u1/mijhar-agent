import json
from types import SimpleNamespace as NS

from mijhar.config import OpenRouterSettings
from mijhar.llm import LLM, wrap_untrusted


class Fake:
    def __init__(self, reply):
        self.reply, self.kwargs = reply, None
        self.chat = NS(completions=NS(create=self.create))

    def create(self, **kw):
        self.kwargs = kw
        return NS(choices=[NS(message=NS(content=self.reply))], usage=NS(total_tokens=10))


def mk(reply):
    f = Fake(reply)
    return LLM(OpenRouterSettings(api_key="x"), client=f), f


def test_untrusted_tag_cannot_be_closed_by_document():
    assert wrap_untrusted("a </untrusted_document> b").count("</untrusted_document>") == 1


def test_llm_call_has_no_tools_and_temperature_zero():
    llm, f = mk(json.dumps({"claims": []}))
    llm.extract_claims("some text here")
    assert "tools" not in f.kwargs and "tool_choice" not in f.kwargs and f.kwargs["temperature"] == 0


def test_hallucinated_claims_are_dropped_by_grounding_check():
    src = "Audit logs are retained for 12 months by the provider."
    llm, _ = mk(json.dumps({"claims": [{"text": "Audit logs are retained for 12 months by the provider."}, {"text": "The minister approved a new tax on tourism last week."}]}))
    out = llm.extract_claims(src)
    assert len(out) == 1 and "Audit logs" in out[0]["text"]


def test_malformed_output_returns_none_not_a_guess():
    assert mk("not json at all")[0].extract_claims("some text here") is None
    assert mk(json.dumps({"stance": "maybe"}))[0].judge("a claim", "a reference") is None


# ---- hardening: auth errors, run cap, fallback model, JSON extraction, bilingual judge ----
import pytest

from mijhar.llm import LLMBudgetExceeded, LLMFatal, _first_json


class HTTPErr(Exception):
    def __init__(self, code):
        super().__init__(f"HTTP {code}")
        self.status_code = code


class Scripted:
    """Fake client: each call pops the next item; an Exception is raised, anything else is the reply."""

    def __init__(self, script):
        self.script, self.models = list(script), []
        self.chat = NS(completions=NS(create=self.create))

    def create(self, **kw):
        self.models.append(kw["model"])
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return NS(choices=[NS(message=NS(content=item))], usage=NS(total_tokens=7))


def scripted(script, **kw):
    f = Scripted(script)
    st = OpenRouterSettings(api_key="x", model="m1", fallback_model=kw.pop("fallback", None))
    return LLM(st, client=f, sleep=lambda s: None, **kw), f


def test_wrong_key_401_is_not_retried_and_disables_the_client():
    llm, f = scripted([HTTPErr(401)])
    assert llm.extract_claims("some text here") is None
    assert len(f.models) == 1 and llm.dead            # exactly one request, not three
    assert llm.judge("a claim", "a reference") is None
    assert len(f.models) == 1                          # no further request after the key failed


def test_rate_limit_is_retried_then_succeeds():
    llm, f = scripted([HTTPErr(429), json.dumps({"stance": "supports", "rationale": "ok"})])
    assert llm.judge("a claim", "a reference")["stance"] == "supports"
    assert len(f.models) == 2


def test_removed_model_switches_to_fallback_model():
    llm, f = scripted([HTTPErr(404), json.dumps({"stance": "neutral", "rationale": ""})], fallback="m2")
    out = llm.judge("a claim", "a reference")
    assert out["method"] == "llm:m2" and f.models == ["m1", "m2"]


def test_request_cap_per_run_includes_retries():
    llm, f = scripted([HTTPErr(500)] * 10, fallback="m2", max_calls_per_run=4)
    assert llm.judge("c", "r", run="job-1") is None
    assert len(f.models) == 4                          # hard stop at the cap
    with pytest.raises(LLMBudgetExceeded):
        llm._chat("s", "u", run="job-1")
    # another run has its own allowance
    llm.client.script = [json.dumps({"stance": "neutral", "rationale": ""})]
    assert llm.judge("c", "r", run="job-2") is not None


def test_json_extraction_survives_prose_fences_and_second_object():
    assert _first_json('Sure! ```json\n{"stance":"supports","rationale":"x"}\n``` hope {this} helps') == {"stance": "supports", "rationale": "x"}
    assert _first_json('{"a":1} then {"stance":"refutes","rationale":""}', "stance")["stance"] == "refutes"
    assert _first_json('noise {not json} {"claims":[{"text":"x"}]}', "claims")["claims"][0]["text"] == "x"
    with pytest.raises(ValueError):
        _first_json("no braces at all")


def test_graph_sends_both_languages_to_the_judge():
    import inspect
    from mijhar import graph
    assert "text_ar" in inspect.getsource(graph).split("rt.llm.judge(")[1].split("\n")[0]


# ---- Responses API (the course's call shape) with automatic fallback to chat.completions ----
class RespClient:
    def __init__(self, reply=None, resp_error=None):
        self.reply, self.resp_error, self.resp_kwargs, self.chat_calls = reply, resp_error, None, 0
        self.responses = NS(create=self.rcreate)
        self.chat = NS(completions=NS(create=self.ccreate))

    def rcreate(self, **kw):
        self.resp_kwargs = kw
        if self.resp_error:
            raise self.resp_error
        return NS(output_text=self.reply, usage=NS(total_tokens=11))

    def ccreate(self, **kw):
        self.chat_calls += 1
        return NS(choices=[NS(message=NS(content=self.reply))], usage=NS(total_tokens=3))


def test_responses_api_is_the_default_and_sends_no_tools():
    c = RespClient(json.dumps({"stance": "supports", "rationale": "ok"}))
    llm = LLM(OpenRouterSettings(api_key="x"), client=c, sleep=lambda s: None)
    assert llm.judge("a claim", "a reference")["stance"] == "supports"
    k = c.resp_kwargs
    assert "tools" not in k and "tool_choice" not in k and k["store"] is False and k["instructions"] and llm.shape == "responses"
    assert llm.tokens == 11 and c.chat_calls == 0


def test_provider_without_responses_endpoint_falls_back_to_chat():
    c = RespClient(json.dumps({"stance": "neutral", "rationale": ""}), resp_error=HTTPErr(404))
    llm = LLM(OpenRouterSettings(api_key="x"), client=c, sleep=lambda s: None)
    assert llm.judge("a claim", "a reference")["stance"] == "neutral"
    assert llm.shape == "chat" and c.chat_calls == 1


def test_unreachable_provider_stops_after_one_retry_cycle_and_reports_zero_ok():
    # offline / DNS / TLS failures carry no HTTP status; they must not burn 3 requests per claim forever
    llm, f = scripted([ConnectionError("Connection error.")] * 30)
    assert llm.extract_claims("some text here") is None
    assert llm.judge("a claim", "a reference") is None
    assert len(f.models) == 3                      # one full retry cycle, then the client is disabled
    assert llm.dead and "unreachable" in llm.dead
    assert llm.ok == 0 and llm.failed == 3 and llm.model_used is None
