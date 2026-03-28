"""
第三周前端（Streamlit）：提供数据上传、预览、抽样情感分析及单条分析功能。

运行方式（在项目根目录执行）:
  python -m streamlit run frontend/app.py
"""

from __future__ import annotations

import sys
import asyncio
from pathlib import Path

import pandas as pd
import streamlit as st

# --- 接入后端服务 ---
# 定位项目根目录和后端目录，确保可以导入 backend 中的模块
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from google.genai import errors as genai_errors  # noqa: E402

# 导入后端核心分析函数
from gemini_service import (
    analyze_review_text_as_dict,
    async_analyze_review_text_as_dict
)  # noqa: E402

# 导入前端工具函数：加载数据表
from utils.loaders import load_dataframe  # noqa: E402

# 定义 Session State 中的键名常量
SS_DF = "workspace_df"          # 存储加载的 DataFrame
SS_NAME = "workspace_filename"    # 存储上传的文件名

# 配置 Streamlit 页面属性
st.set_page_config(
    page_title="评论情感分析 · MVP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 侧边栏配置 ---
with st.sidebar:
    # 语言切换单选框
    lang_choice = st.radio(
        "Language / 语言",
        options=["中文", "English"],
        index=0,
        horizontal=False,
        help="切换页面显示语言（前端 UI）。",
    )
    lang = "zh" if lang_choice == "中文" else "en"

    # 多语言文案字典
    I18N = {
        "zh": {
            "sidebar_header": "第三周 · 前端",
            "sidebar_bullets": "- **上传 CSV / Excel** → 预览\n- **选列 + 抽样**：对前 N 条调用后端 Gemini\n- **单条**：手动输入一条评论数据",
            "sidebar_backend": "后端目录：`{backend}`",
            "sidebar_secret": "密钥检查：`backend/.env` → `GEMINI_API_KEY`",
            "page_title": "自动化客服与评论情感分析系统",
            "page_subtitle": "**阶段一 · Week 3**：实现数据上传预览与抽样情感分析（基于 `gemini_service`）。",
            "tab_batch": "批量上传 · 预览 · 抽样分析",
            "tab_single": "单条评论分析",
            "expander_upload": "① 第一步：上传数据文件",
            "file_uploader_label": "请选择 CSV 或 Excel 文件",
            "info_wait_upload": "请先通过上方的“上传数据文件”按钮加载 CSV 或 Excel 数据。",
            "btn_clear": "清空已加载数据",
            "subheader_preview": "数据预览区",
            "metric_rows": "总行数",
            "metric_cols": "总列数",
            "metric_file": "当前文件",
            "subheader_sample": "抽样分析测试",
            "caption_sample": "从表格**最前面**连续提取 N 条数据，对指定列进行情感分析（并发执行提高效率）。",
            "selectbox_col": "请选择包含评论文本的列",
            "slider_n": "抽样条数 N（取前 N 条进行分析）",
            "btn_start": "开始执行抽样分析",
            "progress_preparing": "正在准备数据…",
            "progress_done": "分析完成",
            "expander_coltypes": "查看数据列类型",
            "download_csv": "导出分析结果为 CSV",
            "subheader_single": "单条评论交互分析",
            "caption_single": "执行与 `backend/main.py` 相同的分析逻辑。",
            "label_text": "请输入评论内容",
            "placeholder_text": "例：该商品质量非常好，完全符合描述！",
            "btn_single": "立即调用后端分析",
            "warn_empty_text": "输入的评论文本不能为空，请重新输入。",
            "spinner_calling": "Gemini 正在冥思苦想中…",
            "error_api": "Gemini API 调用异常：{e}",
            "error_runtime": "运行时错误：{e}",
            "success_done": "分析已圆满完成",
            "section_summary": "**总结摘要**",
            "section_sentiment": "**情感倾向** · **置信得分**",
            "section_pain_points": "**核心痛点**",
            "col_index": "原行号",
            "col_excerpt": "评论摘录",
            "col_pain_points": "识别痛点",
            "summary_empty_skipped": "（文本为空，已自动跳过）",
            "tag_positive": "好评",
            "tag_negative": "差评",
            "tag_neutral": "中评"
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
            "caption_sample": "Take the first N rows from the table, and call backend for the selected text column concurrently using asyncio.",
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

# --- 页面标题 ---
st.title(d["page_title"])
st.markdown(d["page_subtitle"])

# 创建顶部标签页
tab_batch, tab_single = st.tabs([d["tab_batch"], d["tab_single"]])

# --------------------------------------------------------------------------- #
# 文件处理区域：上传并写入 session_state
# --------------------------------------------------------------------------- #
with st.expander(d["expander_upload"], expanded=True):
    # 文件上传器
    uploaded = st.file_uploader(
        d["file_uploader_label"],
        type=["csv", "xlsx", "xls"],
        key="file_uploader_main",
    )
    if uploaded is not None:
        try:
            # 调用 utils/loaders.py 中的函数读取数据
            df_new = load_dataframe(uploaded)
        except Exception as e:
            if lang == "zh":
                st.error(f"数据读取失败：{e}")
            else:
                st.error(f"Failed to read file: {e}")
        else:
            # 将读取的 DataFrame 存入 session_state 实现页面刷新不丢失数据
            st.session_state[SS_DF] = df_new
            st.session_state[SS_NAME] = uploaded.name
            if lang == "zh":
                st.success(f"成功加载文件：**{uploaded.name}**（共 {len(df_new):,} 行）")
            else:
                st.success(f"Loaded: **{uploaded.name}** ({len(df_new):,} rows)")

    # 提供清空数据的按钮
    if st.session_state.get(SS_DF) is not None:
        if st.button(d["btn_clear"]):
            st.session_state.pop(SS_DF, None)
            st.session_state.pop(SS_NAME, None)
            st.rerun()

# 尝试获取当前已加载的数据框
df = st.session_state.get(SS_DF)

# --------------------------------------------------------------------------- #
# 标签页一：批量上传 + 预览 + 抽样分析逻辑
# --------------------------------------------------------------------------- #
with tab_batch:
    if df is None:
        st.info(d["info_wait_upload"])
    else:
        # 1. 数据统计指标展示
        st.subheader(d["subheader_preview"])
        name = st.session_state.get(SS_NAME, "—")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(d["metric_rows"], f"{len(df):,}")
        with c2:
            st.metric(d["metric_cols"], len(df.columns))
        with c3:
            st.metric(d["metric_file"], name[:28] + ("…" if len(str(name)) > 28 else ""))

        # 2. 数据预览表格
        st.dataframe(df, use_container_width=True, height=min(420, 120 + min(len(df), 12) * 28))

        # 3. 抽样分析配置区
        st.subheader(d["subheader_sample"])
        st.caption(d["caption_sample"])

        col_text = st.selectbox(d["selectbox_col"], list(df.columns), index=0)
        max_n = min(30, len(df))
        default_n = min(5, max_n)
        n_rows = st.slider(d["slider_n"], 1, max_n, default_n)

        # 4. 执行抽样分析
        if st.button(d["btn_start"], type="primary"):
            sample = df.head(n_rows)
            texts = sample[col_text]

            results_rows: list[dict] = []
            progress = st.progress(0.0, text=d["progress_preparing"])

            async def process_item(i, idx, raw, sem):
                async with sem:
                    # 更新进度条文字
                    if lang == "zh":
                        label = f"正在分析第 {i + 1}/{len(texts)} 条评论"
                    else:
                        label = f"Analyzing Item {i + 1}/{len(texts)}"
                    progress.progress((i) / max(len(texts), 1), text=label)

                    cell = raw
                    if pd.isna(cell) or str(cell).strip() == "":
                        return {
                            d["col_index"]: idx,
                            d["col_excerpt"]: "",
                            "sentiment": "",
                            "confidence": None,
                            "summary_zh": d["summary_empty_skipped"],
                            "pain_points": "",
                        }

                    text_full = str(cell).strip()
                    preview = text_full if len(text_full) <= 80 else text_full[:77] + "…"

                    try:
                        # **核心：调用异步后端接口**
                        r = await async_analyze_review_text_as_dict(text_full)
                    except genai_errors.ClientError as e:
                        return {
                            d["col_index"]: idx,
                            d["col_excerpt"]: preview,
                            "sentiment": "",
                            "confidence": None,
                            "summary_zh": d["error_api"].format(e=e),
                            "pain_points": "",
                        }
                    except (RuntimeError, ValueError) as e:
                        return {
                            d["col_index"]: idx,
                            d["col_excerpt"]: preview,
                            "sentiment": "",
                            "confidence": None,
                            "summary_zh": d["error_runtime"].format(e=e),
                            "pain_points": "",
                        }
                    else:
                        pp = r.get("pain_points") or []
                        return {
                            d["col_index"]: idx,
                            d["col_excerpt"]: preview,
                            "sentiment": r.get("sentiment", ""),
                            "confidence": r.get("confidence"),
                            "summary_zh": r.get("summary_zh", ""),
                            "pain_points": "；".join(pp) if isinstance(pp, list) else str(pp),
                        }

            async def run_batch():
                sem = asyncio.Semaphore(5)  # 限制并发数为 5
                tasks = [process_item(i, idx, raw, sem) for i, (idx, raw) in enumerate(texts.items())]
                return await asyncio.gather(*tasks)

            # 执行异步批量分析
            results_rows = asyncio.run(run_batch())

            # 更新进度条完成状态
            progress.progress(1.0, text=d["progress_done"])

            # 展示分析结果表格
            out_df = pd.DataFrame(results_rows)
            if lang == "zh":
                st.success(f"已圆满完成 {len(results_rows)} 条数据的深度分析。")
            else:
                st.success(f"Finished {len(results_rows)} rows.")
            st.dataframe(out_df, use_container_width=True)

            # 提供结果下载按钮
            csv_bytes = out_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label=d["download_csv"],
                data=csv_bytes,
                file_name="sentiment_sample_result.csv",
                mime="text/csv",
            )

        # 辅助功能：展示每列的数据类型
        with st.expander(d["expander_coltypes"]):
            st.dataframe(df.dtypes.rename("dtype").to_frame(), use_container_width=True)

# --------------------------------------------------------------------------- #
# 标签页二：单条评论实时交互分析
# --------------------------------------------------------------------------- #
with tab_single:
    st.subheader(d["subheader_single"])
    st.caption(d["caption_single"])
    
    # 评论文本输入框
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
                    # 直接调用后端函数
                    result = analyze_review_text_as_dict(text.strip())
                except genai_errors.ClientError as e:
                    st.error(d["error_api"].format(e=e))
                except (RuntimeError, ValueError) as e:
                    st.error(d["error_runtime"].format(e=e))
                else:
                    # 格式化展示结果
                    st.success(d["success_done"])
                    # 展示原始 JSON 结构
                    st.json(result)
                    
                    # 使用 Markdown 分区块展示具体字段
                    st.markdown(d["section_summary"])
                    st.write(result.get("summary_zh", ""))
                    
                    st.markdown(d["section_sentiment"])
                    st.write(f"{result.get('sentiment')} · {result.get('confidence')}")
                    
                    if result.get("pain_points"):
                        st.markdown(d["section_pain_points"])
                        for p in result["pain_points"]:
                            st.markdown(f"- {p}")
