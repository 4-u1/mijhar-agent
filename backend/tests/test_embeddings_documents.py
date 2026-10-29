import math
from types import SimpleNamespace as NS

import pytest

from mijhar.documents import load_document, read_pdf, split_overlap
from mijhar.retrieval import HashingNgramEncoder, HybridIndex, OpenRouterEncoder


class FakeEmbeddings:
    """Deterministic fake of client.embeddings.create (bag of letters), counts requests."""

    def __init__(self, fail=None):
        self.n, self.fail = 0, fail
        self.embeddings = NS(create=self.create)

    def create(self, model, input, encoding_format):
        self.n += 1
        if self.fail:
            raise self.fail
        data = []
        for i, t in enumerate(input):
            v = [float(t.lower().count(c)) for c in "abcdefghijklmnopqrstuvwxyz"]
            data.append(NS(index=i, embedding=v))
        return NS(data=list(reversed(data)))      # out of order on purpose: index must be honoured


def test_encoder_normalises_orders_and_caches():
    f = FakeEmbeddings()
    enc = OpenRouterEncoder(model="m", client=f, max_calls=5)
    a, b = enc.encode_many(["abc", "xyz zzz"])
    assert math.isclose(sum(x * x for x in a), 1.0) and a[0] > 0 and b[0] == 0   # order preserved
    enc.encode_many(["abc", "xyz zzz"])
    assert f.n == 1                                   # second call fully served from cache


def test_encoder_request_cap():
    enc = OpenRouterEncoder(model="m", client=FakeEmbeddings(), max_calls=1)
    enc.encode("one")
    with pytest.raises(RuntimeError):
        enc.encode("two")


def test_index_falls_back_offline_when_embeddings_fail():
    enc = OpenRouterEncoder(model="m", client=FakeEmbeddings(fail=RuntimeError("401")))
    ix = HybridIndex(encoder=enc)
    assert isinstance(ix.encoder, HashingNgramEncoder) and "RuntimeError" in ix.fallback_reason
    assert ix.search("audit logs retained 12 months", 3)          # still answers


def test_index_with_neural_encoder_and_query_failure_degrades_to_bm25():
    f = FakeEmbeddings()
    ix = HybridIndex(encoder=OpenRouterEncoder(model="m", client=f))
    assert ix.encoder.name == "openrouter:m" and ix.fallback_reason is None
    f.fail = RuntimeError("down")
    res = ix.search("audit logs retained for 12 months", 3, "bm25")
    assert res and ix.degraded is True


def test_split_overlap_windows():
    t = "x" * 4500
    w = split_overlap(t, 2000, 200)
    assert w == [(0, 2000), (1800, 2000), (3600, 900)]
    assert split_overlap("", 2000, 200) == [] and split_overlap("abc", 2000, 200) == [(0, 3)]
    with pytest.raises(ValueError):
        split_overlap("abc", 100, 100)


def test_load_text_and_pdf_without_pypdf(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("نص تجريبي", encoding="utf-8")
    assert load_document(p) == "نص تجريبي"
    try:
        import pypdf  # noqa: F401
    except ImportError:
        with pytest.raises(RuntimeError, match="pypdf"):
            read_pdf(tmp_path / "x.pdf")
