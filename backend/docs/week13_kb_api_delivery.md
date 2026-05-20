# Week 13 Backend Delivery: Knowledge-Base Ingestion + API Reply Service

This delivery upgrades the project from “raw text RAG” to a more formal backend flow with:

- reusable knowledge-base import/index artifacts
- lightweight persisted retrieval metadata
- HTTP-style customer-service endpoints

## 1) Formal knowledge-base ingestion flow

New file:
- `backend/knowledge_base.py`

Capabilities:
- Import from one or more **files or directories**
- Supported source types:
  - `.md`
  - `.txt`
  - `.csv`
  - `.json`
- Recursively scan directories and collect supported files
- Chunk source files into reusable retrieval units
- Persist index artifacts to `backend/data/kb_indices/<merchant_slug>/`
- Save retrieval-ready metadata so later search does not need to re-chunk the original sources

### Index artifact output

Each import creates an index JSON file containing:
- `index_id`
- `merchant_slug`
- `title`
- `created_at`
- `chunk_size`
- `overlap`
- `source_files`
- `source_hash`
- `chunks`
- `retrieval_payload`

This makes the RAG layer reusable across CLI, future frontend integration, and API requests.

## 2) Customer-service reply now supports persisted KB index

Updated file:
- `backend/customer_service.py`

Enhancements:
- Reply generation now supports:
  - `knowledge_base_text`
  - `knowledge_base_index_path`
- If `knowledge_base_index_path` is provided, the service retrieves relevant chunks directly from the persisted index artifact
- Returned payload now also includes:
  - `knowledge_base_index_path`
  - `retrieved_chunks`

This means the reply API no longer has to receive the full knowledge-base text every time.

## 3) CLI workflows

Updated file:
- `backend/main.py`

### 3.1 Import a knowledge base

```powershell
python backend/main.py --task kb-import `
  --merchant-slug demo-merchant `
  --kb-title "售后知识库" `
  --kb-source data/kb `
  --kb-source data/week3_merchant_faq_draft_v1.json
```

### 3.2 List imported indices

```powershell
python backend/main.py --task kb-list --merchant-slug demo-merchant
```

### 3.3 Search an imported index

```powershell
python backend/main.py "包装破损怎么处理" `
  --task kb-search `
  --merchant-slug demo-merchant `
  --kb-index-id demo-merchant-shou-hou-zhi-shi-ku-xxxxxxxx
```

### 3.4 Generate customer-service reply from persisted index

```powershell
python backend/main.py "收到商品后发现包装破损，想申请补发" `
  --task reply `
  --merchant-rules "先致歉，再提供补发或退款路径" `
  --kb-index-path backend/data/kb_indices/demo-merchant/demo-index.json `
  --reply-language zh
```

## 4) HTTP API service

New file:
- `backend/api_server.py`

Requires:
- `fastapi`
- `uvicorn`

### 4.1 Start the API

```powershell
python backend/main.py --task serve-api --host 127.0.0.1 --port 8000
```

### 4.2 Endpoints

#### Health check

`GET /health`

#### Import knowledge base

`POST /api/v1/knowledge-bases/import`

Example body:

```json
{
  "merchant_slug": "demo-merchant",
  "title": "售后知识库",
  "source_paths": ["data/kb", "data/week3_merchant_faq_draft_v1.json"],
  "chunk_size": 300,
  "overlap": 60
}
```

#### List merchant indices

`GET /api/v1/knowledge-bases/{merchant_slug}`

#### Search imported index

`POST /api/v1/knowledge-bases/search`

Example body:

```json
{
  "merchant_slug": "demo-merchant",
  "index_id": "demo-merchant-shou-hou-zhi-shi-ku-xxxxxxxx",
  "query": "包装破损怎么处理",
  "top_k": 3
}
```

#### Generate customer-service reply

`POST /api/v1/customer-service/reply`

Example body:

```json
{
  "review_text": "收到商品后发现包装破损，客服还没回复",
  "merchant_rules": "先致歉，再确认订单号，提供补发或退款方案",
  "merchant_slug": "demo-merchant",
  "knowledge_base_index_id": "demo-merchant-shou-hou-zhi-shi-ku-xxxxxxxx",
  "reply_language": "zh",
  "provider": "deepseek",
  "kb_top_k": 3
}
```

## 5) Recommended frontend/API usage

- During knowledge-base setup:
  - call import endpoint once
  - store returned `index_id`
- During reply generation:
  - send `merchant_slug + knowledge_base_index_id`
  - do not resend full KB text every time
- For explainability:
  - show `retrieved_chunks`
  - optionally expose source file names in admin/debug mode

## 6) Why this is more formal than raw-text RAG

Compared with the previous flow of “pass one long KB text into each request”, this version adds:

- explicit ingestion step
- persisted index artifacts
- reusable KB identifiers
- file/directory import support
- search endpoint separation
- API-style reply interface closer to production service design
