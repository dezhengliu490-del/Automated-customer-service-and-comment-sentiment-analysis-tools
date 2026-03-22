"""
第三周前端（Streamlit）：数据上传与预览 + 抽样情感分析 + 单条分析。

运行（项目根目录）:
  python -m streamlit run frontend/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# --- 接入后端 ---
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from google.genai import errors as genai_errors  # noqa: E402

from gemini_service import analyze_review_text_as_dict  # noqa: E402

from utils.loaders import load_dataframe  # noqa: E402

SS_DF = "workspace_df"
SS_NAME = "workspace_filename"

st.set_page_config(
    page_title="评论情感分析 · MVP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.header("第三周 · 前端")
    st.markdown(
        "- **上传 CSV / Excel** → 预览\n"
        "- **选列 + 抽样**：对前 N 条调用后端 Gemini\n"
        "- **单条**：手动输入一条评论"
    )
    st.divider()
    st.caption(f"后端：`{_BACKEND}`")
    st.caption("密钥：`backend/.env` → `GEMINI_API_KEY`")

st.title("自动化客服与评论情感分析")
st.markdown("**阶段一 · Week 3**：上传预览与少量数据的情感分析（与 `gemini_service` 一致）。")

tab_batch, tab_single = st.tabs(["数据上传 · 预览 · 抽样分析", "单条情感分析"])

# --------------------------------------------------------------------------- #
# 共享：加载文件写入 session_state
# --------------------------------------------------------------------------- #
with st.expander("① 上传数据文件", expanded=True):
    uploaded = st.file_uploader(
        "选择 CSV 或 Excel",
        type=["csv", "xlsx", "xls"],
        key="file_uploader_main",
    )
    if uploaded is not None:
        try:
            df_new = load_dataframe(uploaded)
        except Exception as e:
            st.error(f"读取失败：{e}")
        else:
            st.session_state[SS_DF] = df_new
            st.session_state[SS_NAME] = uploaded.name
            st.success(f"已加载：**{uploaded.name}**（{len(df_new):,} 行）")

    if st.session_state.get(SS_DF) is not None:
        if st.button("清除已加载的数据"):
            st.session_state.pop(SS_DF, None)
            st.session_state.pop(SS_NAME, None)
            st.rerun()

df = st.session_state.get(SS_DF)

# --------------------------------------------------------------------------- #
# Tab：上传 + 预览 + 抽样分析
# --------------------------------------------------------------------------- #
with tab_batch:
    if df is None:
        st.info("请先在上方的「上传数据文件」中选择 CSV 或 Excel。")
    else:
        st.subheader("数据预览")
        name = st.session_state.get(SS_NAME, "—")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("行数", f"{len(df):,}")
        with c2:
            st.metric("列数", len(df.columns))
        with c3:
            st.metric("文件", name[:28] + ("…" if len(str(name)) > 28 else ""))

        st.dataframe(df, use_container_width=True, height=min(420, 120 + min(len(df), 12) * 28))

        st.subheader("抽样情感分析")
        st.caption("从表格**最前面**连续取 N 行，对指定列文本逐条调用后端 `analyze_review_text_as_dict`（受 API 配额与耗时限制，N 不宜过大）。")

        col_text = st.selectbox("评论文本所在列", list(df.columns), index=0)
        max_n = min(30, len(df))
        default_n = min(5, max_n)
        n_rows = st.slider("分析条数 N（取前 N 行）", 1, max_n, default_n)

        if st.button("开始抽样分析", type="primary"):
            sample = df.head(n_rows)
            texts = sample[col_text]

            results_rows: list[dict] = []
            progress = st.progress(0.0, text="准备中…")

            for i, (idx, raw) in enumerate(texts.items()):
                label = f"第 {i + 1}/{len(texts)} 条"
                progress.progress((i) / max(len(texts), 1), text=label)

                cell = raw
                if pd.isna(cell) or str(cell).strip() == "":
                    results_rows.append(
                        {
                            "行索引": idx,
                            "原文片段": "",
                            "sentiment": "",
                            "confidence": None,
                            "summary_zh": "（空文本，已跳过）",
                            "pain_points": "",
                        }
                    )
                    continue

                text_full = str(cell).strip()
                preview = text_full if len(text_full) <= 80 else text_full[:77] + "…"

                try:
                    r = analyze_review_text_as_dict(text_full)
                except genai_errors.ClientError as e:
                    results_rows.append(
                        {
                            "行索引": idx,
                            "原文片段": preview,
                            "sentiment": "",
                            "confidence": None,
                            "summary_zh": f"API 错误：{e}",
                            "pain_points": "",
                        }
                    )
                except (RuntimeError, ValueError) as e:
                    results_rows.append(
                        {
                            "行索引": idx,
                            "原文片段": preview,
                            "sentiment": "",
                            "confidence": None,
                            "summary_zh": str(e),
                            "pain_points": "",
                        }
                    )
                else:
                    pp = r.get("pain_points") or []
                    results_rows.append(
                        {
                            "行索引": idx,
                            "原文片段": preview,
                            "sentiment": r.get("sentiment", ""),
                            "confidence": r.get("confidence"),
                            "summary_zh": r.get("summary_zh", ""),
                            "pain_points": "；".join(pp) if isinstance(pp, list) else str(pp),
                        }
                    )

            progress.progress(1.0, text="完成")

            out_df = pd.DataFrame(results_rows)
            st.success(f"已完成 {len(results_rows)} 条分析。")
            st.dataframe(out_df, use_container_width=True)

            csv_bytes = out_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="下载分析结果 CSV",
                data=csv_bytes,
                file_name="sentiment_sample_result.csv",
                mime="text/csv",
            )

        with st.expander("列类型"):
            st.dataframe(df.dtypes.rename("dtype").to_frame(), use_container_width=True)

# --------------------------------------------------------------------------- #
# Tab：单条
# --------------------------------------------------------------------------- #
with tab_single:
    st.subheader("单条评论 → 结构化 JSON")
    st.caption("与 `backend/main.py` 相同逻辑。")
    text = st.text_area(
        "评论原文",
        height=160,
        placeholder="例如：这条评论质量不错，就是物流有点慢",
    )
    if st.button("调用后端分析", type="primary"):
        if not text or not str(text).strip():
            st.warning("请输入非空评论文本。")
        else:
            with st.spinner("正在调用 Gemini…"):
                try:
                    result = analyze_review_text_as_dict(text.strip())
                except genai_errors.ClientError as e:
                    st.error(f"Gemini API 错误：{e}")
                except RuntimeError as e:
                    st.error(str(e))
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.success("分析完成")
                    st.json(result)
                    st.markdown("**摘要**")
                    st.write(result.get("summary_zh", ""))
                    st.markdown("**情感** · **置信度**")
                    st.write(f"{result.get('sentiment')} · {result.get('confidence')}")
                    if result.get("pain_points"):
                        st.markdown("**痛点**")
                        for p in result["pain_points"]:
                            st.markdown(f"- {p}")
