"""从上传文件解析为 pandas DataFrame（第三周：CSV/Excel 预览）。"""

from __future__ import annotations

from io import BytesIO
from typing import Any


def load_dataframe(uploaded_file: Any) -> "Any":
    import pandas as pd

    name = (uploaded_file.name or "").lower()
    raw = uploaded_file.read()
    bio = BytesIO(raw)

    if name.endswith(".csv"):
        for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
            try:
                bio.seek(0)
                return pd.read_csv(bio, encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError("无法识别 CSV 编码，请另存为 UTF-8 后重试。")

    if name.endswith((".xlsx", ".xls")):
        bio.seek(0)
        return pd.read_excel(bio)

    raise ValueError("仅支持 CSV、Excel（.xlsx / .xls）。")
