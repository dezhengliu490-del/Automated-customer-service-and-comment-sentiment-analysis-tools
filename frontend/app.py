"""
第三周前端（Streamlit）：提供数据上传、预览、抽样情感分析及单条分析功能。
支持多模型切换（配置于 .env 文件中）。
"""

from __future__ import annotations

import sys
import asyncio
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# --- 接入后端服务 ---
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from llm_factory import get_llm_service

# 导入前端工具函数
from utils.cleaning import clean_review_dataframe
from utils.loaders import load_dataframe

# Session State 键名
SS_DF = "workspace_df"
SS_NAME = "workspace_filename"

# 配置 Streamlit 页面属性
st.set_page_config(
    page_title="评论情感分析 · MVP",
    page_icon="📊",
    layout="wide",
)

# --- 侧边栏配置 ---
with st.sidebar:
    lang_choice = st.radio("Language / 语言", options=["中文", "English"], index=0)
    lang = "zh" if lang_choice == "中文" else "en"

    # 多语言文案
    I18N = {
        "zh": {
            "sidebar_header": "评论分析系统",
            "sidebar_config": "模型配置 (LLM Config)",
            "config_provider": "提供商 (Provider)",
            "config_model": "模型型号 (Model)",
            "page_title": "多模型评论情感分析系统",
            "page_subtitle": "基于大语言模型（LLM）的评论内容自动化情感分析与汇总。",
            "tab_batch": "批量分析",
            "tab_single": "单条评论",
            "expander_upload": "① 上传文件",
            "file_uploader_label": "选择 CSV 或 Excel",
            "btn_clear": "清空数据",
            "subheader_preview": "数据预览",
            "metric_rows": "总行数",
            "metric_cols": "总列数",
            "subheader_sample": "抽样分析",
            "selectbox_col": "请选择内容列",
            "slider_n": "抽样数量 N",
            "btn_start": "开始分析",
            "progress_preparing": "准备中...",
            "progress_done": "分析完成",
            "subheader_single": "单条交互分析",
            "label_text": "输入内容",
            "btn_single": "立即分析",
            "warn_empty_text": "文本不能为空",
            "spinner_calling": "AI 正在分析中...",
            "error_runtime": "分析失败：{e}",
            "success_done": "分析已完成",
            "btn_clean": "数据清洗",
            "subheader_stats": "清洗结果报告",
            "chart_title": "情感分布柱状图",
        },
        "en": {
            "sidebar_header": "Sentiment Analysis",
            "sidebar_config": "LLM Config",
            "config_provider": "Provider",
            "config_model": "Model",
            "page_title": "Multi-LLM Sentiment Analysis",
            "page_subtitle": "Automated review analysis dashboard powered by Large Language Models.",
            "tab_batch": "Batch Analysis",
            "tab_single": "Single Review",
            "expander_upload": "① Upload file",
            "file_uploader_label": "Select CSV or Excel",
            "btn_clear": "Clear",
            "subheader_preview": "Preview",
            "metric_rows": "Rows",
            "metric_cols": "Cols",
            "subheader_sample": "Sample Analysis",
            "selectbox_col": "Select Column",
            "slider_n": "Sample size N",
            "btn_start": "Run Analysis",
            "progress_preparing": "Preparing...",
            "progress_done": "Done",
            "subheader_single": "Single Interaction",
            "label_text": "Enter Text",
            "btn_single": "Analyze",
            "warn_empty_text": "Text cannot be empty",
            "spinner_calling": "AI analyzing...",
            "error_runtime": "Analysis failed: {e}",
            "success_done": "Completed",
            "btn_clean": "Clean Data",
            "subheader_stats": "Cleaning Stats",
            "chart_title": "Sentiment Distribution",
        },
    }
    d = I18N[lang]

    st.header(d["sidebar_header"])
    st.divider()
    
    # --- 模型配置区 ---
    with st.expander(d["sidebar_config"], expanded=True):
        p_choice = st.selectbox(d["config_provider"], ["Gemini", "DeepSeek"], index=0)
        
        default_models = {
            "Gemini": "gemini-2.5-flash",
            "DeepSeek": "deepseek-chat"
        }
        selected_model = st.text_input(d["config_model"], value=default_models.get(p_choice, ""))
        
        # 存入 session_state
        st.session_state["llm_provider"] = p_choice.lower()
        st.session_state["llm_model"] = selected_model

# --- 页面逻辑 ---
st.title(d["page_title"])
st.markdown(d["page_subtitle"])

tab_batch, tab_single = st.tabs([d["tab_batch"], d["tab_single"]])

# 文件上传
with st.expander(d["expander_upload"], expanded=True):
    uploaded = st.file_uploader(d["file_uploader_label"], type=["csv", "xlsx", "xls"])
    if uploaded:
        df_new = load_dataframe(uploaded)
        st.session_state[SS_DF] = df_new
        st.session_state[SS_NAME] = uploaded.name
    if st.session_state.get(SS_DF) is not None:
        if st.button(d["btn_clear"]):
            for k in [SS_DF, SS_NAME]:
                st.session_state.pop(k, None)
            st.rerun()

df = st.session_state.get(SS_DF)

# 批量分析
with tab_batch:
    if df is None:
        st.info("Wait for upload...")
    else:
        st.subheader(d["subheader_preview"])
        c1, c2, c3 = st.columns(3)
        with c1: st.metric(d["metric_rows"], f"{len(df):,}")
        with c2: st.metric(d["metric_cols"], len(df.columns))
        with c3: st.metric("Provider", st.session_state.llm_provider.upper())
        
        st.dataframe(df.head(100), use_container_width=True)

        st.subheader(d["subheader_sample"])
        col_text = st.selectbox(d["selectbox_col"], list(df.columns))

        # --- 新增：数据清洗逻辑 ---
        with st.expander(d["btn_clean"]):
            c1, c2 = st.columns(2)
            with c1:
                do_dup_text = st.checkbox("去重 (Text)", value=True)
                do_empty = st.checkbox("删空 (Empty)", value=True)
            with c2:
                do_dup_row = st.checkbox("整行去重 (Row)", value=False)
                min_len = st.number_input("最小长度 (Min Len)", value=5, min_value=1)
            
            if st.button(d["btn_clean"], use_container_width=True):
                cleaned_df, stats = clean_review_dataframe(
                    df, col_text,
                    drop_duplicate_text=do_dup_text,
                    drop_empty_text=do_empty,
                    drop_full_row_duplicates=do_dup_row,
                    min_length=min_len
                )
                st.session_state[SS_DF] = cleaned_df
                st.info(f"""
                **{d['subheader_stats']}**
                - {d['metric_rows']} IN: {stats['rows_in']}
                - {d['metric_rows']} OUT: {stats['rows_out']}
                - 空文字过滤: {stats['empty_dropped']}
                - 长度过滤 (<{min_len}): {stats['too_short_dropped']}
                - 文本去重: {stats['dup_text_dropped']}
                """)
                st.rerun()

        n_rows = st.slider(d["slider_n"], 1, min(100, len(df)), 5)

        if st.button(d["btn_start"], type="primary"):
            sample = df.head(n_rows)
            texts = sample[col_text]
            progress = st.progress(0.0, text=d["progress_preparing"])

            async def run_batch():
                # 核心：通过工厂获取服务（由于没有传 api_key，将自动读取 .env）
                try:
                    service = get_llm_service(
                        provider=st.session_state.llm_provider,
                        model=st.session_state.llm_model
                    )
                except Exception as e:
                    st.error(f"Failed to init LLM: {e}")
                    return []
                
                finished_count = 0
                tasks = []
                for i, (idx, raw) in enumerate(texts.items()):
                    async def one_call(t, current_idx=idx):
                        nonlocal finished_count
                        try:
                            res = await service.async_analyze_review_as_dict(str(t))
                            finished_count += 1
                            progress.progress(finished_count / n_rows, text=f"Analyzing {finished_count}/{n_rows}")
                            return {"index": current_idx, "text": str(t)[:50]+"...", **res}
                        except Exception as e:
                            finished_count += 1
                            progress.progress(finished_count / n_rows, text=f"Analyzing {finished_count}/{n_rows}")
                            return {"index": current_idx, "text": str(t)[:50]+"...", "error": str(e)}
                    tasks.append(one_call(raw))
                
                return await asyncio.gather(*tasks)

            results = asyncio.run(run_batch())
            if results:
                st.success(d["progress_done"])
                res_df = pd.DataFrame(results)
                st.dataframe(res_df, use_container_width=True)

                # --- 新增：柱状图可视化 ---
                if "sentiment" in res_df.columns:
                    st.divider()
                    st.subheader(d["chart_title"])
                    
                    # 统计频次
                    sentiment_counts = res_df["sentiment"].value_counts().reset_index()
                    sentiment_counts.columns = ["sentiment", "count"]
                    
                    # 使用 Altair 绘制美观柱状图
                    chart = alt.Chart(sentiment_counts).mark_bar().encode(
                        x=alt.X("sentiment:N", sort=["positive", "neutral", "negative"], title="Sentiment"),
                        y=alt.Y("count:Q", title="Count"),
                        color=alt.Color("sentiment:N", scale=alt.Scale(
                            domain=["positive", "neutral", "negative"],
                            range=["#2ecc71", "#f1c40f", "#e74c3c"]
                        ))
                    ).properties(height=400)
                    
                    st.altair_chart(chart, use_container_width=True)

# 单条分析
with tab_single:
    st.subheader(d["subheader_single"])
    text_input = st.text_area(d["label_text"], height=150)
    if st.button(d["btn_single"], type="primary"):
        if not text_input.strip():
            st.warning(d["warn_empty_text"])
        else:
            with st.spinner(d["spinner_calling"]):
                try:
                    service = get_llm_service(
                        provider=st.session_state.llm_provider,
                        model=st.session_state.llm_model
                    )
                    res = service.analyze_review_as_dict(text_input.strip())
                    st.success(d["success_done"])
                    st.json(res)
                except Exception as e:
                    st.error(d["error_runtime"].format(e=e))
