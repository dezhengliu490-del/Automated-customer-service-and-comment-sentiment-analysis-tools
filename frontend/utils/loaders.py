"""提供从上传文件（CSV/Excel）解析为 pandas DataFrame 的工具函数。"""

from __future__ import annotations

from io import BytesIO
from typing import Any


def load_dataframe(uploaded_file: Any) -> "Any":
    """
    接收 Streamlit 上传的文件对象，根据后缀名解析并返回 DataFrame。
    支持自动检测 CSV 编码（utf-8, gbk 等）。
    """
    import pandas as pd

    # 获取文件名并转为小写以检查后缀
    name = (uploaded_file.name or "").lower()
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    # 读取原始字节流
    raw = uploaded_file.read()
    bio = BytesIO(raw)

    # 处理 CSV 文件
    if name.endswith(".csv"):
        # 尝试多种常用编码，解决中文乱码问题
        for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
            try:
                bio.seek(0)
                return pd.read_csv(bio, encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError("无法识别该 CSV 的编码格式，请尝试另存为 UTF-8 编码后再上传。")

    # 处理 Excel 文件
    if name.endswith((".xlsx", ".xls")):
        bio.seek(0)
        return pd.read_excel(bio)

    # 不支持的文件类型
    raise ValueError("目前仅支持 CSV、Excel（.xlsx / .xls）格式的文件。")
