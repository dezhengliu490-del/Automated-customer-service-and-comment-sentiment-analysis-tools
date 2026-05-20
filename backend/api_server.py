from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from customer_service import generate_customer_service_reply_as_dict
from knowledge_base import (
    import_knowledge_base,
    list_knowledge_base_indices,
    load_knowledge_base_index,
    resolve_knowledge_base_index_path,
    search_knowledge_base_index,
)

try:
    from fastapi import FastAPI, HTTPException
except ModuleNotFoundError:  # pragma: no cover
    FastAPI = None
    HTTPException = RuntimeError


class KnowledgeImportRequest(BaseModel):
    merchant_slug: str
    title: str
    source_paths: list[str] = Field(default_factory=list)
    chunk_size: int = 300
    overlap: int = 60


class KnowledgeSearchRequest(BaseModel):
    merchant_slug: str
    index_id: str
    query: str
    top_k: int = 3


class CustomerServiceReplyRequest(BaseModel):
    review_text: str
    merchant_rules: str = ""
    provider: str | None = None
    model: str | None = None
    sentiment: str | None = None
    pain_points: list[str] | None = None
    style_hint: str | None = None
    reply_language: str = "zh"
    knowledge_base_text: str | None = None
    knowledge_base_index_id: str | None = None
    knowledge_base_index_path: str | None = None
    merchant_slug: str | None = None
    kb_top_k: int = 3


def create_app():
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Install fastapi and uvicorn to run the API server.")

    app = FastAPI(title="E-commerce AI Customer Service API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/knowledge-bases/import")
    def import_kb(req: KnowledgeImportRequest) -> dict[str, Any]:
        try:
            return import_knowledge_base(
                merchant_slug=req.merchant_slug,
                title=req.title,
                source_paths=req.source_paths,
                chunk_size=req.chunk_size,
                overlap=req.overlap,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/v1/knowledge-bases/{merchant_slug}")
    def list_kb(merchant_slug: str) -> dict[str, Any]:
        try:
            return {
                "merchant_slug": merchant_slug,
                "indices": list_knowledge_base_indices(merchant_slug),
            }
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/v1/knowledge-bases/search")
    def search_kb(req: KnowledgeSearchRequest) -> dict[str, Any]:
        try:
            path = resolve_knowledge_base_index_path(req.merchant_slug, req.index_id)
            index = load_knowledge_base_index(path)
            return search_knowledge_base_index(index, req.query, top_k=req.top_k)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/v1/customer-service/reply")
    def reply(req: CustomerServiceReplyRequest) -> dict[str, Any]:
        try:
            knowledge_base_index_path = req.knowledge_base_index_path
            if not knowledge_base_index_path and req.knowledge_base_index_id and req.merchant_slug:
                knowledge_base_index_path = str(
                    resolve_knowledge_base_index_path(req.merchant_slug, req.knowledge_base_index_id)
                )

            return generate_customer_service_reply_as_dict(
                review_text=req.review_text,
                merchant_rules=req.merchant_rules,
                provider=req.provider,
                model=req.model,
                sentiment=req.sentiment,
                pain_points=req.pain_points,
                style_hint=req.style_hint,
                reply_language=req.reply_language,
                knowledge_base_text=req.knowledge_base_text,
                knowledge_base_index_path=knowledge_base_index_path,
                kb_top_k=req.kb_top_k,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc))

    return app


app = create_app() if FastAPI is not None else None
