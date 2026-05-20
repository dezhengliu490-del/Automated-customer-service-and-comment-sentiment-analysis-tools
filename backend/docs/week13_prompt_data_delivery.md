# Week 11 Prompt & Data Delivery

## 1. Prompt work completed

### 1.1 Prompt asset audit
- Reviewed `backend/prompts.py` and identified four current prompt layers:
  - sentiment-analysis system prompt
  - sentiment-analysis user prompt
  - customer-service system prompt
  - customer-service user prompt
- Confirmed current prompt capabilities already include:
  - bilingual output control (`zh` / `en`)
  - defensive prompting for malicious, vague, or adversarial input
  - customer-service conservative fallback guidance
  - RAG context injection for merchant rules and retrieved knowledge chunks

### 1.2 Prompt version summary for reporting
- `V1`: basic sentiment + pain point extraction
- `V2`: bilingual summary / bilingual pain-point control
- `V3`: defensive prompt principles for sarcasm, gibberish, emoji-only input, hostile text, and injection-like input
- `V4`: customer-service prompt with merchant rules, retrieved knowledge chunks, and handoff-first behavior

### 1.3 Prompt governance artifacts
- Added prompt contract test file:
  - `backend/tests/test_prompt_contract.py`
- These tests verify:
  - English analysis prompt requires English `pain_points`
  - English analysis prompt requires `summary_zh` field content in English
  - Chinese analysis prompt requires Chinese `pain_points` and Chinese summary
  - Customer-service prompt includes merchant rules, retrieved chunks, and defensive notes
  - Defensive principles explicitly mention conservative / handoff behavior

## 2. Data work completed

### 2.1 Data card
- Added:
  - `data/week11_data_card.md`
- The data card documents:
  - current data sources
  - label fields and semantics
  - known risks and limitations
  - recommended use for evaluation vs demo vs stress testing

### 2.2 Prompt evaluation set
- Added:
  - `data/week11_prompt_eval_set.csv`
- This is a compact curated evaluation set for reporting and future regression checks.
- Coverage includes:
  - positive / neutral / negative reviews
  - logistics, packaging, quality, size, after-sales, price
  - sarcasm
  - emoji-heavy input
  - gibberish
  - prompt-injection-like content
  - high-risk customer-service handoff cases

### 2.3 Suggested usage
- Use the Week 11 eval set for:
  - prompt iteration review
  - regression checks after prompt edits
  - demo examples during team presentation
- Suggested report metrics:
  - sentiment correctness
  - pain-point hit rate
  - language compliance (`summary_zh` content language)
  - guardrail correctness

## 3. Recommended reporting language

You can report this week as:

> We completed prompt governance and evaluation preparation work. On the prompt side, we consolidated the current bilingual and defensive prompt strategy into a versioned prompt framework and added prompt contract tests to ensure language control, conservative fallback behavior, and rule-based customer-service prompting remain stable. On the data side, we created a dedicated prompt evaluation dataset and a formal data card, so future prompt iterations can be compared on a fixed benchmark instead of ad hoc examples.

## 4. Next recommended step
- Add a small offline evaluation runner that reads `data/week11_prompt_eval_set.csv` and outputs:
  - sentiment match rate
  - guardrail match rate
  - language compliance rate
  - pain-point exact / partial match counts
