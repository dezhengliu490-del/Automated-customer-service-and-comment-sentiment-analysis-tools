# Week 9 Delivery: Stress Testing and Large Upload UX

This document summarizes the Week 9 frontend/backend delivery.

## Backend

Delivered:
- Added defensive edge-case assessment in `backend/edge_cases.py`.
- Added prompt-level conservative handling for sarcasm, emoji-only inputs, gibberish, hostile text, long rants, and prompt-injection-like content.
- Added customer-service handoff fallback for high-risk or unclear inputs.
- Enriched global JSONL logging with:
  - `request_id`
  - `input_hash`
  - `edge_flags`
  - `guardrail_action`
  - `prepared_text_length`
  - error type/message for failed API calls
- Added offline/live stress runner: `backend/stress_test.py`.
- Added Week 9 edge-case dataset: `data/week9_extreme_edge_cases.csv`.

Offline smoke test:

```powershell
python backend/stress_test.py `
  --file data/week9_extreme_edge_cases.csv `
  --repeat 20 `
  --output tmp/week9_stress_test_report.json
```

Live API stress test:

```powershell
python backend/stress_test.py `
  --file data/week9_extreme_edge_cases.csv `
  --live `
  --provider deepseek `
  --concurrency 8 `
  --output tmp/week9_live_stress_test_report.json
```

Report fields:
- `total_cases`
- `status_counts`
- `edge_flag_counts`
- latency mean/p50/p95/max
- wall time, CPU time, peak traced memory, throughput

## Frontend

Delivered:
- Added upload parsing status with progress bar, file size, elapsed time, and ETA.
- Added session-level upload signature caching to avoid re-parsing the same large file on every Streamlit rerun.
- Added batch-analysis progress with:
  - completed/total count
  - failed count
  - elapsed time
  - ETA
  - rows per second
- Added request and guardrail metadata to customer-service chat output.

## Notes

Streamlit exposes the uploaded file to Python after browser upload completes, so the progress bar tracks server-side parsing and analysis progress rather than raw browser transfer bytes. This still addresses the largest UX pain point for large CSV/Excel files: users can see that the system is parsing, validating, and analyzing instead of appearing frozen.
