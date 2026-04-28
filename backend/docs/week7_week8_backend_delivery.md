# Week 7-8 Backend Delivery

This document summarizes the backend delivery for **Week 7 + Week 8** and provides frontend integration points.

## 1) Week 7: RAG-ready backend foundation

### 1.1 Knowledge chunking + retrieval

New file:
- `backend/rag_utils.py`

Capabilities:
- Split long rule documents into overlapping chunks (`split_text_chunks`).
- Build lightweight retrieval index (`SimpleRAGIndex`) with BM25-like scoring.
- Retrieve top-k relevant chunks by user review/query.
- Build prompt-ready context text from retrieved chunks.

### 1.2 Product pain-point aggregation utility

New file:
- `backend/insights.py`

Capability:
- `top_pain_points_from_results(...)` aggregates high-frequency pain points from sentiment analysis outputs, default focusing on negative reviews.

---

## 2) Week 8: RAG integrated into customer-service reply

Updated file:
- `backend/customer_service.py`

Enhancements:
- Customer-service reply pipeline now supports RAG context injection:
  - `knowledge_base_text` (optional KB text)
  - `kb_top_k` (retrieved chunk count)
- If `knowledge_base_text` is empty, it falls back to `merchant_rules` as retrieval source.
- Retrieved context is embedded into prompt before reply generation.
- Response now includes:
  - `retrieved_chunks` (for frontend debug/visualization)

---

## 3) Frontend Interface (Week 7-8 additions)

## 3.1 Python API (sync)

```python
from customer_service import generate_customer_service_reply_as_dict

res = generate_customer_service_reply_as_dict(
    review_text="包装破损，且物流很慢",
    merchant_rules="先致歉，再给退款/补发方案。",
    knowledge_base_text="...merchant FAQ / policy long text...",
    kb_top_k=3,
    provider="deepseek",
    reply_language="zh",
)
```

## 3.2 Python API (async)

```python
from customer_service import async_generate_customer_service_reply_as_dict

res = await async_generate_customer_service_reply_as_dict(
    review_text="...",
    merchant_rules="...",
    knowledge_base_text="...",
    kb_top_k=3,
    provider="deepseek",
    reply_language="zh",
)
```

## 3.3 New response fields

```json
{
  "reply_text": "...",
  "provider": "deepseek",
  "model": "deepseek-chat",
  "reply_language": "zh",
  "used_rules": true,
  "retrieved_chunks": ["...", "...", "..."]
}
```

---

## 4) CLI Quick Test

Updated CLI:
- `backend/main.py`

New options:
- `--kb-file`
- `--kb-top-k`

Example:

```powershell
python backend/main.py "这个商品有瑕疵，想退款" `
  --task reply `
  --merchant-rules "先致歉，确认订单，提供退款或补发路径" `
  --kb-file data/week3_merchant_faq_draft_v1.json `
  --kb-top-k 3
```

---

## 5) Suggested frontend display

- Show `reply_text` as primary output.
- Add optional expandable panel for `retrieved_chunks` to explain why model replied this way (helpful for demo and trust).
- Keep `kb_top_k` configurable (2-5 recommended).

