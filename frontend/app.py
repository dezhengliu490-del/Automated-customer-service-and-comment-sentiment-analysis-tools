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
    lang_choice = st.radio(
        "Language / 语言",
        options=["中文", "English"],
        index=0,
        horizontal=False,
        help="切换页面显示语言（前端 UI）。",
    )
    lang = "zh" if lang_choice == "中文" else "en"

    I18N = {
        "zh": {
            "sidebar_header": "第三周 · 前端",
            "sidebar_bullets": "- **上传 CSV / Excel** → 预览\n- **选列 + 抽样**：对前 N 条调用后端 Gemini\n- **单条**：手动输入一条评论",
            "sidebar_backend": "后端：`{backend}`",
            "sidebar_secret": "密钥：`backend/.env` → `GEMINI_API_KEY`",
            "page_title": "自动化客服与评论情感分析",
            "page_subtitle": "**阶段一 · Week 3**：上传预览与少量数据的情感分析（与 `gemini_service` 一致）。",
            "tab_batch": "数据上传 · 预览 · 抽样分析",
            "tab_single": "单条情感分析",
            "expander_upload": "① 上传数据文件",
            "file_uploader_label": "选择 CSV 或 Excel",
            "info_wait_upload": "请先在上方的「上传数据文件」中选择 CSV 或 Excel。",
            "btn_clear": "清除已加载的数据",
            "subheader_preview": "数据预览",
            "metric_rows": "行数",
            "metric_cols": "列数",
            "metric_file": "文件",
            "subheader_sample": "抽样情感分析",
            "caption_sample": "从表格**最前面**连续取 N 行，对指定列文本逐条调用后端 `analyze_review_text_as_dict`（受 API 配额与耗时限制，N 不宜过大）。",
            "selectbox_col": "评论文本所在列",
            "slider_n": "分析条数 N（取前 N 行）",
            "btn_start": "开始抽样分析",
            "progress_preparing": "准备中…",
            "progress_done": "完成",
            "expander_coltypes": "列类型",
            "download_csv": "下载分析结果 CSV",
            "subheader_single": "单条评论 → 结构化 JSON",
            "caption_single": "与 `backend/main.py` 相同逻辑。",
            "label_text": "评论原文",
            "placeholder_text": "例如：这条评论质量不错，就是物流有点慢",
            "btn_single": "调用后端分析",
            "warn_empty_text": "请输入非空评论文本。",
            "spinner_calling": "正在调用 Gemini…",
            "error_api": "Gemini API 错误：{e}",
            "error_runtime": "{e}",
            "success_done": "分析完成",
            "section_summary": "**摘要**",
            "section_sentiment": "**情感** · **置信度**",
            "section_pain_points": "**痛点**",
            # 输出列名（UI 友好，和 backend keys 不冲突）
            "col_index": "行索引",
            "col_excerpt": "原文片段",
            "col_pain_points": "痛点",
            "summary_empty_skipped": "（空文本，已跳过）",
        },
        "en": {
            "sidebar_header": "Week 3 · Frontend",
            "sidebar_bullets": "- **Upload CSV / Excel** → Preview\n- **Pick a text column + Sample**: call Gemini for the first N rows\n- **Single review**: paste one review manually",
            "sidebar_backend": "Backend: `{backend}`",
            "sidebar_secret": "Key: `backend/.env` → `GEMINI_API_KEY`",
            "page_title": "Automated Customer Service & Review Sentiment Analysis",
            "page_subtitle": "**Phase 1 · Week 3**: upload preview + sentiment analysis for a small sample.",
            "tab_batch": "Upload · Preview · Sample Analysis",
            "tab_single": "Single Review Analysis",
            "expander_upload": "① Upload data file",
            "file_uploader_label": "Select CSV or Excel",
            "info_wait_upload": "Please upload a CSV/Excel file above first.",
            "btn_clear": "Clear loaded data",
            "subheader_preview": "Data preview",
            "metric_rows": "Rows",
            "metric_cols": "Columns",
            "metric_file": "File",
            "subheader_sample": "Sample sentiment analysis",
            "caption_sample": "Take the first N rows from the table, and call backend `analyze_review_text_as_dict` row-by-row for the selected text column. N is capped to keep latency/API quota under control.",
            "selectbox_col": "Column containing review text",
            "slider_n": "Number of rows N (take first N)",
            "btn_start": "Start sample analysis",
            "progress_preparing": "Preparing…",
            "progress_done": "Done",
            "expander_coltypes": "Column types",
            "download_csv": "Download CSV result",
            "subheader_single": "Single review → Structured JSON",
            "caption_single": "Same logic as `backend/main.py`.",
            "label_text": "Review text",
            "placeholder_text": "Example: The quality is ok, but shipping is a bit slow.",
            "btn_single": "Analyze with backend",
            "warn_empty_text": "Please enter non-empty review text.",
            "spinner_calling": "Calling Gemini…",
            "error_api": "Gemini API error: {e}",
            "error_runtime": "{e}",
            "success_done": "Analysis completed",
            "section_summary": "**Summary**",
            "section_sentiment": "**Sentiment** · **Confidence**",
            "section_pain_points": "**Pain points**",
            "col_index": "Row index",
            "col_excerpt": "Text excerpt",
            "col_pain_points": "Pain points",
            "summary_empty_skipped": "(Empty text, skipped)",
        },
    }

    d = I18N[lang]

    st.header(d["sidebar_header"])
    st.markdown(d["sidebar_bullets"])
    st.divider()
    st.caption(d["sidebar_backend"].format(backend=_BACKEND))
    st.caption(d["sidebar_secret"])

st.title(d["page_title"])
st.markdown(d["page_subtitle"])

tab_batch, tab_single = st.tabs([d["tab_batch"], d["tab_single"]])

# --------------------------------------------------------------------------- #
# 共享：加载文件写入 session_state
# --------------------------------------------------------------------------- #
with st.expander(d["expander_upload"], expanded=True):
    uploaded = st.file_uploader(
        d["file_uploader_label"],
        type=["csv", "xlsx", "xls"],
        key="file_uploader_main",
    )
    if uploaded is not None:
        try:
            df_new = load_dataframe(uploaded)
        except Exception as e:
            if lang == "zh":
                st.error(f"读取失败：{e}")
            else:
                st.error(f"Failed to read file: {e}")
        else:
            st.session_state[SS_DF] = df_new
            st.session_state[SS_NAME] = uploaded.name
            if lang == "zh":
                st.success(f"已加载：**{uploaded.name}**（{len(df_new):,} 行）")
            else:
                st.success(f"Loaded: **{uploaded.name}** ({len(df_new):,} rows)")

    if st.session_state.get(SS_DF) is not None:
        if st.button(d["btn_clear"]):
            st.session_state.pop(SS_DF, None)
            st.session_state.pop(SS_NAME, None)
            st.rerun()

df = st.session_state.get(SS_DF)

# --------------------------------------------------------------------------- #
# Tab：上传 + 预览 + 抽样分析
# --------------------------------------------------------------------------- #
with tab_batch:
    if df is None:
        st.info(d["info_wait_upload"])
    else:
        st.subheader(d["subheader_preview"])
        name = st.session_state.get(SS_NAME, "—")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(d["metric_rows"], f"{len(df):,}")
        with c2:
            st.metric(d["metric_cols"], len(df.columns))
        with c3:
            st.metric(d["metric_file"], name[:28] + ("…" if len(str(name)) > 28 else ""))

        st.dataframe(df, use_container_width=True, height=min(420, 120 + min(len(df), 12) * 28))

        st.subheader(d["subheader_sample"])
        st.caption(d["caption_sample"])

        col_text = st.selectbox(d["selectbox_col"], list(df.columns), index=0)
        max_n = min(30, len(df))
        default_n = min(5, max_n)
        n_rows = st.slider(d["slider_n"], 1, max_n, default_n)

        if st.button(d["btn_start"], type="primary"):
            sample = df.head(n_rows)
            texts = sample[col_text]

            results_rows: list[dict] = []
            progress = st.progress(0.0, text=d["progress_preparing"])

            for i, (idx, raw) in enumerate(texts.items()):
                if lang == "zh":
                    label = f"第 {i + 1}/{len(texts)} 条"
                else:
                    label = f"Item {i + 1}/{len(texts)}"
                progress.progress((i) / max(len(texts), 1), text=label)

                cell = raw
                if pd.isna(cell) or str(cell).strip() == "":
                    results_rows.append(
                        {
                            d["col_index"]: idx,
                            d["col_excerpt"]: "",
                            "sentiment": "",
                            "confidence": None,
                            "summary_zh": d["summary_empty_skipped"],
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
                            d["col_index"]: idx,
                            d["col_excerpt"]: preview,
                            "sentiment": "",
                            "confidence": None,
                            "summary_zh": d["error_api"].format(e=e),
                            "pain_points": "",
                        }
                    )
                except (RuntimeError, ValueError) as e:
                    results_rows.append(
                        {
                            d["col_index"]: idx,
                            d["col_excerpt"]: preview,
                            "sentiment": "",
                            "confidence": None,
                            "summary_zh": d["error_runtime"].format(e=e),
                            "pain_points": "",
                        }
                    )
                else:
                    pp = r.get("pain_points") or []
                    results_rows.append(
                        {
                            d["col_index"]: idx,
                            d["col_excerpt"]: preview,
                            "sentiment": r.get("sentiment", ""),
                            "confidence": r.get("confidence"),
                            "summary_zh": r.get("summary_zh", ""),
                            "pain_points": "；".join(pp) if isinstance(pp, list) else str(pp),
                        }
                    )

            progress.progress(1.0, text=d["progress_done"])

            out_df = pd.DataFrame(results_rows)
            if lang == "zh":
                st.success(f"已完成 {len(results_rows)} 条分析。")
            else:
                st.success(f"Finished {len(results_rows)} rows.")
            st.dataframe(out_df, use_container_width=True)

            csv_bytes = out_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label=d["download_csv"],
                data=csv_bytes,
                file_name="sentiment_sample_result.csv",
                mime="text/csv",
            )

        with st.expander(d["expander_coltypes"]):
            st.dataframe(df.dtypes.rename("dtype").to_frame(), use_container_width=True)

# --------------------------------------------------------------------------- #
# Tab：单条
# --------------------------------------------------------------------------- #
with tab_single:
    st.subheader(d["subheader_single"])
    st.caption(d["caption_single"])
    text = st.text_area(
        d["label_text"],
        height=160,
        placeholder=d["placeholder_text"],
    )
    if st.button(d["btn_single"], type="primary"):
        if not text or not str(text).strip():
            st.warning(d["warn_empty_text"])
        else:
            with st.spinner(d["spinner_calling"]):
                try:
                    result = analyze_review_text_as_dict(text.strip())
                except genai_errors.ClientError as e:
                    st.error(d["error_api"].format(e=e))
                except RuntimeError as e:
                    st.error(d["error_runtime"].format(e=e))
                except ValueError as e:
                    st.error(d["error_runtime"].format(e=e))
                else:
                    st.success(d["success_done"])
                    st.json(result)
                    st.markdown(d["section_summary"])
                    st.write(result.get("summary_zh", ""))
                    st.markdown(d["section_sentiment"])
                    st.write(f"{result.get('sentiment')} · {result.get('confidence')}")
                    if result.get("pain_points"):
                        st.markdown(d["section_pain_points"])
                        for p in result["pain_points"]:
                            st.markdown(f"- {p}")
