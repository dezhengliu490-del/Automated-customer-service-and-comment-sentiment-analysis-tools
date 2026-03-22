"""
第三周前端（Streamlit）：骨架 + 文件上传与表格预览 + 与后端 gemini_service 对接。

与后端连接方式：将 `backend/` 加入 sys.path，直接调用 `analyze_review_text_as_dict`，
与 `backend/main.py` 使用同一套 Gemini 逻辑与 `backend/.env` 密钥。

运行（项目根目录，已安装 requirements.txt）:
  streamlit run frontend/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# --- 接入后端：与 backend/main.py、gemini_service.py 同源 ---
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from google.genai import errors as genai_errors  # noqa: E402

from gemini_service import analyze_review_text_as_dict  # noqa: E402

from utils.loaders import load_dataframe

st.set_page_config(
    page_title="评论情感分析 · MVP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.header("第三周 · 前端")
    st.markdown(
        "- **数据上传与预览**：CSV / Excel → 表格\n"
        "- **单条分析**：调用后端 `gemini_service`（与 CLI `main.py` 一致）"
    )
    st.divider()
    st.caption(f"后端目录：`{_BACKEND}`")
    st.caption("密钥：`backend/.env` 中的 GEMINI_API_KEY")

st.title("自动化客服与评论情感分析")
st.markdown("**阶段一 · Week 3**：数据筹备与架构设计 — 前端骨架与后端单条链路对接。")

tab_upload, tab_single = st.tabs(["数据上传与预览", "单条情感分析（后端）"])

with tab_upload:
    st.subheader("文件上传")
    uploaded = st.file_uploader(
        "选择 CSV 或 Excel",
        type=["csv", "xlsx", "xls"],
        help="与计划书一致：验证 Pandas 读取本地文件；上传后预览表格。",
    )
    if uploaded is None:
        st.info("请上传文件以预览数据表。")
    else:
        try:
            df = load_dataframe(uploaded)
        except Exception as e:
            st.error(f"读取失败：{e}")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("行数", f"{len(df):,}")
            with c2:
                st.metric("列数", len(df.columns))
            with c3:
                st.metric("文件名", uploaded.name[:32] + ("…" if len(uploaded.name) > 32 else ""))
            st.dataframe(df, use_container_width=True, height=min(480, 120 + min(len(df), 15) * 28))
            with st.expander("列类型"):
                st.dataframe(
                    df.dtypes.rename("dtype").to_frame(),
                    use_container_width=True,
                )

with tab_single:
    st.subheader("单条评论 → 结构化 JSON")
    st.caption("与 `backend/main.py` 相同：内部调用 `gemini_service.analyze_review_text`。")
    text = st.text_area(
        "评论原文",
        height=160,
        placeholder="例如：这条评论质量不错，就是物流有点慢",
    )
    if st.button("调用后端分析", type="primary"):
        if not text or not text.strip():
            st.warning("请输入非空评论文本。")
        else:
            with st.spinner("正在调用 Gemini（后端 gemini_service）…"):
                try:
                    result = analyze_review_text_as_dict(text.strip())
                except genai_errors.ClientError as e:
                    st.error(f"Gemini API 错误：{e}")
                except RuntimeError as e:
                    st.error(str(e))
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.success("分析完成（后端返回与 CLI 一致的 JSON 结构）")
                    st.json(result)
                    st.markdown("**摘要**")
                    st.write(result.get("summary_zh", ""))
                    st.markdown("**情感** · **置信度**")
                    st.write(f"{result.get('sentiment')} · {result.get('confidence')}")
                    if result.get("pain_points"):
                        st.markdown("**痛点**")
                        for p in result["pain_points"]:
                            st.markdown(f"- {p}")
