"""Hybrid retrieval: Okapi BM25 + a dense encoder, fused with Reciprocal Rank Fusion.

BM25 is implemented here (k1=1.5, b=0.75) so results are deterministic and testable.
Dense encoder:
  - model2vec (static neural embeddings) when installed AND downloadable (needs internet
    to Hugging Face on first use); select with MIJHAR_DENSE=model2vec.
  - otherwise HashingNgramEncoder: hashed character 3-5-gram vectors. It is a
    lexical-morphological proxy, NOT a neural semantic model; it helps Arabic
    inflection and typos, not true paraphrase. The index reports which one is active.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from .config import env
from .guard import normalize

_TOK = re.compile(r"[\w\u0600-\u06ff]+", re.U)
_STOP = set("the a an of to in and or for on be is are by with at as that this it its must shall may should".split()) | \
        set("في من الى إلى على عن او أو و ان أن هذا هذه ذلك التي الذي يجب".split())


def _stem_ar(tok: str) -> str:
    for p in ("وال", "بال", "كال", "فال", "لل", "ال"):
        if tok.startswith(p) and len(tok) - len(p) >= 3:
            tok = tok[len(p):]
            break
    for s in ("ات", "ون", "ين", "ها", "ية", "ه"):
        if tok.endswith(s) and len(tok) - len(s) >= 3:
            tok = tok[: -len(s)]
            break
    return tok


def tokenize(text: str) -> list[str]:
    t = normalize(text).lower()
    out = []
    for w in _TOK.findall(t):
        if w in _STOP or len(w) < 2:
            continue
        out.append(_stem_ar(w) if re.search(r"[\u0600-\u06ff]", w) else (w[:-1] if w.endswith("s") and len(w) > 3 else w))
    return out


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.N = len(docs)
        self.avgdl = (sum(len(d) for d in docs) / self.N) if self.N else 0.0
        self.df: Counter = Counter()
        for d in docs:
            self.df.update(set(d))
        self.tf = [Counter(d) for d in docs]

    def idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def scores(self, query: list[str]) -> list[float]:
        out = []
        for i, d in enumerate(self.docs):
            s, dl = 0.0, len(d)
            for t in set(query):
                f = self.tf[i].get(t, 0)
                if f:
                    s += self.idf(t) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1)))
            out.append(s)
        return out


class HashingNgramEncoder:
    name = "hashing-ngram (lexical proxy, not neural)"
    floor = 0.0
    DIM = 1024

    def encode(self, text: str) -> list[float]:
        t = " " + " ".join(tokenize(text)) + " "
        v = [0.0] * self.DIM
        for n in (3, 4, 5):
            for i in range(len(t) - n + 1):
                h = int.from_bytes(hashlib.blake2b(t[i:i + n].encode(), digest_size=4).digest(), "big")
                v[h % self.DIM] += 1.0 if (h >> 31) & 1 else -1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]


class Model2VecEncoder:  # pragma: no cover - needs network on first use
    def __init__(self, model_id: str):
        from model2vec import StaticModel
        self.m = StaticModel.from_pretrained(model_id)
        self.name = f"model2vec:{model_id}"

    def encode(self, text: str) -> list[float]:
        v = self.m.encode([text])[0]
        n = math.sqrt(float((v * v).sum())) or 1.0
        return [float(x) / n for x in v]


class OpenRouterEncoder:
    """Real neural embeddings through OpenRouter's embeddings API (same call the course RAG uses).

    PDPL: the TEXT YOU EMBED LEAVES THE PROCESS (claim text at query time, corpus passages at build
    time). Opt in with MIJHAR_DENSE=openrouter. No retries here: any failure raises, and the index
    falls back to the offline hashing encoder instead of burning the free quota. A hard cap on
    requests per process (MIJHAR_MAX_EMBED_CALLS, default 300) and a cache keep the cost bounded.
    """

    def __init__(self, model: str | None = None, client=None, max_calls: int | None = None):
        self.model = model or env("MIJHAR_EMBED_MODEL", "nvidia/nemotron-3-embed-1b:free") or ""
        if client is None:
            key = env("OPENROUTER_API_KEY")
            if not key:
                raise RuntimeError("OPENROUTER_API_KEY not set")
            from openai import OpenAI
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key, timeout=30, max_retries=0)
        self.client = client
        self.max_calls = int(max_calls or env("MIJHAR_MAX_EMBED_CALLS", "300") or 300)
        self.calls = 0
        self._cache: dict[str, list[float]] = {}
        self.name = f"openrouter:{self.model}"
        # Neural cosines of UNRELATED texts are not ~0, so the dense part is rescaled above this floor.
        # 0.3 is an UNCALIBRATED starting point: tune with MIJHAR_DENSE_FLOOR after running the evals.
        self.floor = float(env("MIJHAR_DENSE_FLOOR", "0.3") or 0.3)

    def encode_many(self, texts: list[str]) -> list[list[float]]:
        todo = [t for t in dict.fromkeys(texts) if t not in self._cache]
        if todo:
            if self.calls >= self.max_calls:
                raise RuntimeError(f"embedding request cap reached ({self.max_calls})")
            self.calls += 1
            r = self.client.embeddings.create(model=self.model, input=[t[:8000] for t in todo], encoding_format="float")
            data = sorted(r.data, key=lambda d: getattr(d, "index", 0))
            if len(data) != len(todo):
                raise RuntimeError("embedding response size mismatch")
            for t, d in zip(todo, data):
                v = [float(x) for x in d.embedding]
                n = math.sqrt(sum(x * x for x in v)) or 1.0
                self._cache[t] = [x / n for x in v]
        return [self._cache[t] for t in texts]

    def encode(self, text: str) -> list[float]:
        return self.encode_many([text])[0]


def make_encoder():
    # Default "hash": the 0.15 evidence cut-off and every recorded eval were calibrated on it. Neural embeddings
    # (openrouter / model2vec) are opt-in: they change scores, cost free-tier requests and send text out (PDPL).
    mode = env("MIJHAR_DENSE", "hash") or "hash"
    if mode == "auto":   # real embeddings whenever a key is configured, offline proxy otherwise
        mode = "openrouter" if env("OPENROUTER_API_KEY") else "hash"
    if mode == "openrouter":
        try:
            return OpenRouterEncoder()
        except Exception:
            pass  # no key: fall back; the index reports the proxy encoder
    if mode == "model2vec":
        try:
            return Model2VecEncoder(env("MIJHAR_DENSE_MODEL", "minishlab/potion-multilingual-128M") or "")
        except Exception:
            pass  # fall back, and the index reports the proxy encoder
    return HashingNgramEncoder()


def _cos(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@lru_cache(maxsize=1)
def load_passages() -> tuple:
    p = Path(__file__).parent / "data" / "corpora.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    return tuple(data["corpora"][c]["passages"][i] | {} for c in data["corpora"] for i in range(len(data["corpora"][c]["passages"])))


class HybridIndex:
    def __init__(self, passages=None, encoder=None):
        self.passages = list(passages or load_passages())
        self.encoder = encoder or make_encoder()
        texts = [f"{p['title_en']} {p['text_en']} {p['title_ar']} {p['text_ar']}" for p in self.passages]
        self.bm25 = BM25([tokenize(t) for t in texts])
        self.fallback_reason: str | None = None
        self.degraded = False
        try:
            many = getattr(self.encoder, "encode_many", None)
            self.vecs = many(texts) if many else [self.encoder.encode(t) for t in texts]
        except Exception as e:  # neural encoder unreachable / key rejected: stay usable offline
            self.fallback_reason = f"{type(e).__name__}: {e}"[:200]
            self.encoder = HashingNgramEncoder()
            self.vecs = [self.encoder.encode(t) for t in texts]

    def search(self, query: str, top_k: int = 3, mode: str = "hybrid", corpus_id: str | None = None, rrf_k: int = 60) -> list[dict]:
        q = tokenize(query)
        bm = self.bm25.scores(q)
        try:
            qv = self.encoder.encode(query)
            de = [_cos(qv, v) for v in self.vecs]
        except Exception:   # query-time embedding failed: BM25 only for this query, and say so
            self.degraded = True
            de = [0.0] * len(self.vecs)
        idx = [i for i, p in enumerate(self.passages) if corpus_id in (None, "", "all", p["corpus"])]
        r_bm = {i: r for r, i in enumerate(sorted(idx, key=lambda i: (-bm[i], i)), 1)}
        fl = getattr(self.encoder, "floor", 0.0)
        dn = [max(0.0, (x - fl) / (1 - fl)) for x in de]          # dense score above the encoder's noise floor
        r_de = {i: r for r, i in enumerate(sorted(idx, key=lambda i: (-de[i], i)), 1)}
        # absolute normalisation: share of the ideal score for this query (every term matched once in an
        # average-length passage). Max-normalising made any single weak match score 1.0 (found in eval run 1).
        bm_max = sum(self.bm25.idf(t) for t in set(q)) or 1.0
        res = []
        for i in idx:
            rrf = 1 / (rrf_k + r_bm[i]) + 1 / (rrf_k + r_de[i])
            bm_n = min(1.0, bm[i] / bm_max)
            hybrid = 0.5 * bm_n + 0.5 * dn[i]      # score in [0,1] used for the min-score cut-off
            fused = rrf if mode == "hybrid" else 1 / (rrf_k + r_bm[i])
            score = hybrid if mode == "hybrid" else bm_n
            if bm[i] == 0 and (mode == "bm25" or dn[i] < 0.05):
                continue
            p = self.passages[i]
            res.append({"id": p["id"], "corpus": p["corpus"], "title_en": p["title_en"], "title_ar": p["title_ar"],
                        "text_en": p["text_en"], "text_ar": p["text_ar"],
                        "bm25_score": round(bm[i], 4), "dense_score": round(de[i], 4),
                        "rrf_score": round(rrf, 5), "score": round(score, 4), "_sort": fused})
        res.sort(key=lambda r: (-r["_sort"], r["id"]))
        for r in res:
            r.pop("_sort")
        return res[:top_k]


@lru_cache(maxsize=1)
def default_index() -> HybridIndex:
    return HybridIndex()
