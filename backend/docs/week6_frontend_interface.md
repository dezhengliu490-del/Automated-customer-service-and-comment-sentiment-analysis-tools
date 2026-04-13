# Week 6 Frontend Interface (Customer Service Reply)

This document is for frontend integration of the new Week 6 backend capability: **simulated customer-service reply generation with merchant rules context**.

## 1) Python Interface (recommended for current Streamlit architecture)

### Sync

```python
from customer_service import generate_customer_service_reply_as_dict

result = generate_customer_service_reply_as_dict(
    review_text="收到货后发现包装破损，而且物流很慢。",
    merchant_rules="先致歉；提供补发或退款；不要承诺无法执行的时效。",
    provider="deepseek",            # optional: deepseek / gemini
    model=None,                     # optional
    sentiment="negative",           # optional
    pain_points=["包装破损", "物流慢"],  # optional
    style_hint="真诚、简洁",           # optional
    reply_language="zh",            # zh / en
)
```

### Async

```python
from customer_service import async_generate_customer_service_reply_as_dict

result = await async_generate_customer_service_reply_as_dict(
    review_text="...",
    merchant_rules="...",
    provider="deepseek",
    reply_language="zh",
)
```

## 2) Input Contract

- `review_text` (`str`, required): user review or question.
- `merchant_rules` (`str`, required but can be empty): merchant policy/script/rules text used as context.
- `provider` (`str`, optional): `deepseek` or `gemini`.
- `model` (`str`, optional): override model id.
- `sentiment` (`str`, optional): hint for tone control.
- `pain_points` (`list[str]`, optional): extracted key issues.
- `style_hint` (`str`, optional): tone preference such as "professional", "warm".
- `reply_language` (`str`, optional): `zh` / `en`, default `zh`.

## 3) Output Contract

```json
{
  "reply_text": "非常抱歉给您带来不便，我们已为您登记补发...",
  "provider": "deepseek",
  "model": "deepseek-chat",
  "reply_language": "zh",
  "used_rules": true
}
```

Field notes:
- `reply_text`: final customer-service reply text for UI display.
- `used_rules`: whether non-empty merchant rules were provided.

## 4) Error Behavior

Typical exceptions:
- `ValueError`: empty `review_text`.
- Provider/network/runtime exceptions from model SDK.

Frontend suggestion:
- Show concise toast/banner for error.
- Keep user input in place for retry.

## 5) CLI Smoke Test

```powershell
python backend/main.py "这个商品有瑕疵，客服一直没回复" --task reply --merchant-rules "先致歉，再提供换货/退款路径"
```

## 6) Logging / Observability

Customer-service reply calls are logged to:
- `backend/logs/llm_calls.jsonl`

Operation names:
- `customer_service_reply`
- `async_customer_service_reply`

