from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge_base import (
    import_knowledge_base,
    list_knowledge_base_indices,
    load_knowledge_base_index,
    search_knowledge_base_index,
    search_knowledge_base_index_file,
)


def test_knowledge_base_import_and_search(tmp_path) -> None:
    faq_path = tmp_path / "faq.md"
    faq_path.write_text(
        "退货政策：签收后7天内支持退货。\n"
        "补发政策：商品破损可优先安排补发。\n",
        encoding="utf-8",
    )
    policy_dir = tmp_path / "kb"
    policy_dir.mkdir()
    (policy_dir / "shipping.json").write_text(
        json.dumps(
            {
                "shipping": "默认48小时内发货",
                "damaged_package": "如包装破损，可联系客服补发或退款",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    imported = import_knowledge_base(
        merchant_slug="merchant-a",
        title="售后知识库",
        source_paths=[faq_path, policy_dir],
        output_dir=tmp_path / "indices",
    )

    assert imported["chunk_count"] >= 2
    assert imported["source_file_count"] == 2

    artifact = load_knowledge_base_index(imported["index_path"])
    assert artifact.merchant_slug == "merchant-a"
    assert artifact.retrieval_payload

    result = search_knowledge_base_index(artifact, "包装破损怎么处理", top_k=2)
    assert result["chunks"]
    assert any("补发" in item["text"] or "退款" in item["text"] for item in result["chunks"])
    assert result["chunks"][0]["source_name"] in {"faq.md", "shipping.json"}

    direct = search_knowledge_base_index_file(imported["index_path"], "多久发货", top_k=1)
    assert direct["chunks"]
    assert "发货" in direct["chunks"][0]["text"]


def test_list_knowledge_base_indices(tmp_path) -> None:
    source = tmp_path / "guide.txt"
    source.write_text("客服规则：先致歉，再确认订单号。", encoding="utf-8")

    imported = import_knowledge_base(
        merchant_slug="merchant-b",
        title="客服规则",
        source_paths=[source],
        output_dir=tmp_path / "indices",
    )

    rows = list_knowledge_base_indices("merchant-b", base_dir=tmp_path / "indices")
    assert rows
    assert rows[0]["index_id"] == imported["index_id"]
    assert rows[0]["chunk_count"] >= 1
