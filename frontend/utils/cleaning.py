"""Pandas 数据清洗：去重、空值、异常字符（供前端上传表使用）。"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd

# 控制字符（保留换行制表，评论里常合并为单行）
_CTRL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# 连续空白
_MULTI_SPACE = re.compile(r"\s+")


def normalize_review_text(text: Any) -> str:
    """单条文本：规范化空白、去掉不可见控制符，NFKC 兼容全角符号。"""
    if text is None:
        return ""
    if isinstance(text, float) and pd.isna(text):
        return ""
    s = str(text)
    s = unicodedata.normalize("NFKC", s)
    s = _CTRL_CHARS.sub("", s)
    s = _MULTI_SPACE.sub(" ", s).strip()
    return s


def clean_review_dataframe(
    df: pd.DataFrame,
    text_column: str,
    *,
    drop_duplicate_text: bool = True,
    drop_empty_text: bool = True,
    drop_full_row_duplicates: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    对指定「评论文本」列做清洗，并可按文本列去重、删空行。

    返回：(清洗后的 DataFrame, 统计信息 dict)
    """
    if text_column not in df.columns:
        raise ValueError(f"列不存在: {text_column}")

    stats: dict[str, Any] = {
        "rows_in": int(len(df)),
        "dup_text_dropped": 0,
        "dup_row_dropped": 0,
        "empty_dropped": 0,
        "rows_out": 0,
    }

    out = df.copy()
    out[text_column] = out[text_column].map(normalize_review_text)

    if drop_empty_text:
        nonempty = out[text_column].str.len() > 0
        stats["empty_dropped"] = int((~nonempty).sum())
        out = out.loc[nonempty].reset_index(drop=True)

    if drop_full_row_duplicates:
        before = len(out)
        out = out.drop_duplicates(keep="first").reset_index(drop=True)
        stats["dup_row_dropped"] = before - len(out)

    if drop_duplicate_text:
        before = len(out)
        out = out.drop_duplicates(subset=[text_column], keep="first").reset_index(drop=True)
        stats["dup_text_dropped"] = before - len(out)

    stats["rows_out"] = int(len(out))
    return out, stats
