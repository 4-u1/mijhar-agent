"""Document loading: .txt / .md / .pdf  ->  plain text, plus overlapping chunk offsets.

PDF text is as untrusted as any upload: it goes through the same guard before a model sees it.
`pypdf` is an optional dependency (`uv sync --extra pdf`) and is imported lazily.
"""
from __future__ import annotations

from pathlib import Path

PAGE_BREAK = "\n\n"


def split_overlap(text: str, chunk_size: int = 2000, overlap: int = 200) -> list[tuple[int, int]]:
    """(offset, length) windows of `chunk_size` chars overlapping by `overlap` (always advances)."""
    if chunk_size <= 0 or not 0 <= overlap < chunk_size:
        raise ValueError("need chunk_size > 0 and 0 <= overlap < chunk_size")
    out, i = [], 0
    while i < len(text):
        out.append((i, min(chunk_size, len(text) - i)))
        if i + chunk_size >= len(text):
            break
        i += chunk_size - overlap
    return out


def read_pdf(path: str | Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError("PDF support needs pypdf: run `uv sync --extra pdf`") from e
    pages = []
    for page in PdfReader(str(path)).pages:
        t = page.extract_text()
        if t and t.strip():
            pages.append(t.strip())
    if not pages:
        raise ValueError("no extractable text in this PDF (scanned? OCR is not supported)")
    return PAGE_BREAK.join(pages)


def load_document(path: str | Path) -> str:
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        return read_pdf(p)
    return p.read_text(encoding="utf-8")
