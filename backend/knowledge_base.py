from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import get_kb_index_dir
from rag_utils import SimpleRAGIndex, build_context_from_chunks, split_text_chunks


SUPPORTED_KB_SUFFIXES = {".md", ".txt", ".csv", ".json"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_slug(text: str, default: str = "kb") -> str:
    clean = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(text or "").strip()).strip("-")
    return clean or default


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_csv_file(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    chunks: list[str] = []
    for row in rows:
        parts = [f"{k}: {v}" for k, v in row.items() if str(v or "").strip()]
        if parts:
            chunks.append(" | ".join(parts))
    return "\n".join(chunks)


def _read_json_file(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return json.dumps(data, ensure_ascii=False, indent=2)
    if isinstance(data, list):
        return "\n".join(json.dumps(item, ensure_ascii=False) for item in data)
    return str(data)


def _iter_source_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(f"knowledge source not found: {path}")
    files = [p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_KB_SUFFIXES]
    files.sort(key=lambda p: str(p).lower())
    return files


def read_knowledge_source(path: str | Path) -> str:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix in {".md", ".txt"}:
        return _read_text_file(source)
    if suffix == ".csv":
        return _read_csv_file(source)
    if suffix == ".json":
        return _read_json_file(source)
    return _read_text_file(source)


@dataclass
class KnowledgeBaseChunk:
    chunk_id: str
    text: str
    source_name: str
    source_path: str
    ordinal: int


@dataclass
class KnowledgeBaseIndexArtifact:
    index_id: str
    merchant_slug: str
    title: str
    created_at: str
    chunk_size: int
    overlap: int
    source_files: list[str]
    source_hash: str
    chunks: list[KnowledgeBaseChunk]
    retrieval_payload: dict[str, Any]


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _flatten_chunks(chunks: list[KnowledgeBaseChunk]) -> list[str]:
    return [chunk.text for chunk in chunks]


def collect_knowledge_source_files(source_paths: list[str | Path]) -> list[Path]:
    files: list[Path] = []
    for source in source_paths:
        files.extend(_iter_source_files(Path(source)))

    deduped: dict[str, Path] = {}
    for path in files:
        deduped[str(path.resolve())] = path
    resolved = list(deduped.values())
    resolved.sort(key=lambda p: str(p).lower())
    return resolved


def build_knowledge_base_index(
    *,
    merchant_slug: str,
    title: str,
    source_paths: list[str | Path],
    chunk_size: int = 300,
    overlap: int = 60,
) -> KnowledgeBaseIndexArtifact:
    files = collect_knowledge_source_files(source_paths)
    if not files:
        raise ValueError("no readable knowledge-base source files were found")

    source_texts: list[tuple[Path, str]] = []
    for path in files:
        text = read_knowledge_source(path)
        if text.strip():
            source_texts.append((path, text))

    if not source_texts:
        raise ValueError("all knowledge-base source files were empty after parsing")

    merged_text = "\n\n".join(text for _, text in source_texts)
    chunks: list[KnowledgeBaseChunk] = []
    for source_path, text in source_texts:
        parts = split_text_chunks(text, chunk_size=chunk_size, overlap=overlap)
        for idx, part in enumerate(parts, start=1):
            chunks.append(
                KnowledgeBaseChunk(
                    chunk_id=f"{_safe_slug(source_path.stem, 'doc')}-{idx}",
                    text=part,
                    source_name=source_path.name,
                    source_path=str(source_path),
                    ordinal=idx,
                )
            )

    merchant = _safe_slug(merchant_slug, "merchant")
    source_hash = _hash_text(merged_text)
    index_id = f"{merchant}-{_safe_slug(title, 'kb')}-{source_hash[:8]}"
    rag = SimpleRAGIndex(_flatten_chunks(chunks))
    return KnowledgeBaseIndexArtifact(
        index_id=index_id,
        merchant_slug=merchant,
        title=title.strip() or "Knowledge Base",
        created_at=_utc_now(),
        chunk_size=chunk_size,
        overlap=overlap,
        source_files=[str(path) for path, _ in source_texts],
        source_hash=source_hash,
        chunks=chunks,
        retrieval_payload=rag.to_payload(),
    )


def save_knowledge_base_index(artifact: KnowledgeBaseIndexArtifact, output_dir: str | Path | None = None) -> Path:
    base_dir = Path(output_dir) if output_dir else get_kb_index_dir()
    merchant_dir = base_dir / artifact.merchant_slug
    merchant_dir.mkdir(parents=True, exist_ok=True)
    target = merchant_dir / f"{artifact.index_id}.json"
    payload = asdict(artifact)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_knowledge_base_index(index_path: str | Path) -> KnowledgeBaseIndexArtifact:
    path = Path(index_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    chunks = [KnowledgeBaseChunk(**item) for item in payload.get("chunks", [])]
    payload["chunks"] = chunks
    payload.setdefault("retrieval_payload", {})
    return KnowledgeBaseIndexArtifact(**payload)


def resolve_knowledge_base_index_path(merchant_slug: str, index_id: str, base_dir: str | Path | None = None) -> Path:
    root = Path(base_dir) if base_dir else get_kb_index_dir()
    return root / _safe_slug(merchant_slug, "merchant") / f"{index_id}.json"


def list_knowledge_base_indices(
    merchant_slug: str,
    *,
    base_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    root = Path(base_dir) if base_dir else get_kb_index_dir()
    merchant_dir = root / _safe_slug(merchant_slug, "merchant")
    if not merchant_dir.is_dir():
        return []

    rows: list[dict[str, Any]] = []
    for path in sorted(merchant_dir.glob("*.json"), key=lambda p: p.name.lower()):
        try:
            artifact = load_knowledge_base_index(path)
        except Exception:
            continue
        rows.append(
            {
                "index_id": artifact.index_id,
                "merchant_slug": artifact.merchant_slug,
                "title": artifact.title,
                "created_at": artifact.created_at,
                "chunk_count": len(artifact.chunks),
                "source_file_count": len(artifact.source_files),
                "source_files": artifact.source_files,
                "index_path": str(path),
            }
        )

    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return rows


def search_knowledge_base_index(
    index: KnowledgeBaseIndexArtifact,
    query: str,
    *,
    top_k: int = 3,
) -> dict[str, Any]:
    retrieval_payload = index.retrieval_payload or {}
    if retrieval_payload:
        rag = SimpleRAGIndex.from_payload(retrieval_payload)
    else:
        rag = SimpleRAGIndex(_flatten_chunks(index.chunks))
    hits = rag.retrieve(query, top_k=max(1, int(top_k)))
    chunk_meta_by_text: dict[str, KnowledgeBaseChunk] = {}
    for chunk in index.chunks:
        chunk_meta_by_text.setdefault(chunk.text, chunk)
    return {
        "index_id": index.index_id,
        "title": index.title,
        "query": query,
        "top_k": max(1, int(top_k)),
        "context": build_context_from_chunks(hits),
        "chunks": [
            {
                "text": item.text,
                "score": item.score,
                "source_name": chunk_meta_by_text.get(item.text).source_name if chunk_meta_by_text.get(item.text) else "",
                "source_path": chunk_meta_by_text.get(item.text).source_path if chunk_meta_by_text.get(item.text) else "",
                "ordinal": chunk_meta_by_text.get(item.text).ordinal if chunk_meta_by_text.get(item.text) else 0,
            }
            for item in hits
        ],
    }


def search_knowledge_base_index_file(
    index_path: str | Path,
    query: str,
    *,
    top_k: int = 3,
) -> dict[str, Any]:
    artifact = load_knowledge_base_index(index_path)
    result = search_knowledge_base_index(artifact, query, top_k=top_k)
    result["index_path"] = str(Path(index_path))
    return result


def import_knowledge_base(
    *,
    merchant_slug: str,
    title: str,
    source_paths: list[str | Path],
    chunk_size: int = 300,
    overlap: int = 60,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    files = collect_knowledge_source_files(source_paths)
    artifact = build_knowledge_base_index(
        merchant_slug=merchant_slug,
        title=title,
        source_paths=[str(path) for path in files],
        chunk_size=chunk_size,
        overlap=overlap,
    )
    index_path = save_knowledge_base_index(artifact, output_dir=output_dir)
    return {
        "index_id": artifact.index_id,
        "merchant_slug": artifact.merchant_slug,
        "title": artifact.title,
        "chunk_count": len(artifact.chunks),
        "source_file_count": len(files),
        "source_files": artifact.source_files,
        "index_path": str(index_path),
    }
