from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collector.taobao_collector import (
    ParsedProduct,
    _extract_item_id,
    _extract_taobao_reviews,
    _extract_tmall_reviews,
    _parse_jsonp,
)


def test_extract_item_id_from_url() -> None:
    assert _extract_item_id("https://item.taobao.com/item.htm?id=123456789") == "123456789"
    assert _extract_item_id("https://detail.tmall.com/item.htm?id=987654321&abc=1") == "987654321"


def test_parse_jsonp_payload() -> None:
    payload = _parse_jsonp('jsonp_cb({"comments":[{"content":"great"}]})')
    assert payload["comments"][0]["content"] == "great"


def test_extract_taobao_reviews() -> None:
    product = ParsedProduct(
        platform="taobao",
        item_id="123",
        seller_id=None,
        title="Sample Product",
        canonical_url="https://item.taobao.com/item.htm?id=123",
    )
    payload = {
        "comments": [
            {"id": "r1", "content": "Fast delivery", "date": "2026-05-20", "user": "Alice"},
            {"id": "r2", "content": " ", "date": "2026-05-20", "user": "Bob"},
        ]
    }
    rows = _extract_taobao_reviews(payload, product)
    assert len(rows) == 1
    assert rows[0]["review_id"] == "r1"
    assert rows[0]["review_text"] == "Fast delivery"


def test_extract_tmall_reviews() -> None:
    product = ParsedProduct(
        platform="tmall",
        item_id="123",
        seller_id="456",
        title="Sample Product",
        canonical_url="https://detail.tmall.com/item.htm?id=123",
    )
    payload = {
        "rateDetail": {
            "rateList": [
                {"rateId": "tm1", "rateContent": "Package damaged", "rateDate": "2026-05-20", "displayUserNick": "Kitty"}
            ]
        }
    }
    rows = _extract_tmall_reviews(payload, product)
    assert len(rows) == 1
    assert rows[0]["review_id"] == "tm1"
    assert rows[0]["review_text"] == "Package damaged"
