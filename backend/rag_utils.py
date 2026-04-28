from __future__ import annotations

import math
import re
from dataclasses import dataclass


_SPACE_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]")


def _normalize_text(text: str) -> str:
    return _SPACE_RE.sub(" ", (text or "").strip())


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(_normalize_text(text).lower())


def split_text_chunks(text: str, *, chunk_size: int = 300, overlap: int = 60) -> list[str]:
    clean = _normalize_text(text)
    if not clean:
        return []
    if chunk_size <= 0:
        chunk_size = 300
    if overlap < 0:
        overlap = 0
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 5)

    chunks: list[str] = []
    start = 0
    n = len(clean)
    step = max(1, chunk_size - overlap)
    while start < n:
        end = min(n, start + chunk_size)
        piece = clean[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start += step
    return chunks


@dataclass
class ScoredChunk:
    text: str
    score: float


class SimpleRAGIndex:
    """
    Lightweight retrieval index:
    - chunk document text
    - compute BM25-like score for retrieval
    """

    def __init__(self, chunks: list[str]):
        self.chunks = [c for c in chunks if c.strip()]
        self.chunk_tokens = [tokenize(c) for c in self.chunks]
        self.df: dict[str, int] = {}
        for toks in self.chunk_tokens:
            for t in set(toks):
                self.df[t] = self.df.get(t, 0) + 1
        self.avg_len = (
            sum(len(toks) for toks in self.chunk_tokens) / len(self.chunk_tokens)
            if self.chunk_tokens
            else 1.0
        )

    @classmethod
    def from_text(cls, text: str, *, chunk_size: int = 300, overlap: int = 60) -> "SimpleRAGIndex":
        return cls(split_text_chunks(text, chunk_size=chunk_size, overlap=overlap))

    def retrieve(self, query: str, *, top_k: int = 3) -> list[ScoredChunk]:
        if not self.chunks:
            return []
        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        k1 = 1.5
        b = 0.75
        n_docs = len(self.chunks)
        scored: list[ScoredChunk] = []

        for chunk, toks in zip(self.chunks, self.chunk_tokens):
            if not toks:
                continue
            tf: dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            dl = len(toks)
            score = 0.0
            for q in q_tokens:
                f = tf.get(q, 0)
                if f <= 0:
                    continue
                df = self.df.get(q, 0)
                idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
                denom = f + k1 * (1 - b + b * dl / (self.avg_len or 1.0))
                score += idf * (f * (k1 + 1) / denom)
            if score > 0:
                scored.append(ScoredChunk(text=chunk, score=score))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[: max(1, top_k)]


def build_context_from_chunks(chunks: list[ScoredChunk]) -> str:
    if not chunks:
        return ""
    lines = []
    for i, ch in enumerate(chunks, start=1):
        lines.append(f"[KB#{i}] {ch.text}")
    return "\n".join(lines)
