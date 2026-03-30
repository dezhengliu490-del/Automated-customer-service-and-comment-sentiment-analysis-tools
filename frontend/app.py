"""
第三周前端（Streamlit）：提供数据上传、预览、抽样情感分析及单条分析功能。
支持多模型选择与配置。
"""

from __future__ import annotations

import sys
import asyncio
import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# --- 接入后端服务 ---
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# 导入工厂函数和基类
from llm_factory import get_llm_service

# 导入前端工具函数
from utils.cleaning import clean_review_dataframe
from utils.loaders import load_dataframe

# Session State 键名
SS_DF = "workspace_df"
SS_NAME = "workspace_filename"
SS_CLEAN_DF = "workspace_df_cleaned"
SS_CLEAN_STATS = "workspace_clean_stats"

# 配置 Streamlit 页面属性
st.set_page_config(
    page_title="评论情感分析 · MVP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 侧边栏配置 ---
with st.sidebar:
    lang_choice = st.radio(
        "Language / 语言",
        options=["中文", "English"],
        index=0,
        horizontal=False,
    )
    lang = "zh" if lang_choice == "中文" else "en"

    # 多语言文案
    I18N = {
        "zh": {
            "sidebar_header": "第三周 · 前端",
            "sidebar_config": "模型配置 (LLM Config)",
            "config_provider": "提供商 (Provider)",
            "config_api_key": "API 密钥 (API Key)",
            "config_model": "模型型号 (Model)",
            "sidebar_bullets": "- **上传 CSV / Excel** → 预览\n- **选列 + 抽样**：分析前 N 条\n- **单条**：手动输入单条评论",
            "page_title": "自动化客服与评论情感分析系统",
            "page_subtitle": "**阶段一 · Week 3**：数据上传预览与多模型情感分析交互系统。",
            "tab_batch": "批量分析",
            "tab_single": "单条评论",
            "expander_upload": "① 上传数据文件",
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
            "error_api": "API 调用异常：{e}",
            "error_runtime": "错误：{e}",
            "error_no_key": "请先在侧边栏配置 API 密钥。",
            "success_done": "分析已圆满完成",
            "col_index": "原行号",
            "col_excerpt": "摘要",
            "source_raw": "原始数据",
            "source_cleaned": "清洗后数据",
            "subheader_chart": "情感分布图",
            "tag_positive": "好评",
            "tag_negative": "差评",
            "tag_neutral": "中评",
        },
        "en": {
            "sidebar_header": "Week 3 · Frontend",
            "sidebar_config": "LLM Config",
            "config_provider": "Provider",
            "config_api_key": "API Key",
            "config_model": "Model",
            "sidebar_bullets": "- **Upload CSV/Excel** → Preview\n- **Sample Analysis**: analyze first N rows\n- **Single**: manual text input",
            "page_title": "Sentiment Analysis System",
            "page_subtitle": "**Week 3**: Multi-LLM interaction & analysis dashboard.",
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
            "error_api": "API Error: {e}",
            "error_runtime": "Error: {e}",
            "error_no_key": "Please configure API Key in the sidebar first.",
            "success_done": "Completed",
            "col_index": "Index",
            "col_excerpt": "Excerpt",
            "source_raw": "Raw",
            "source_cleaned": "Cleaned",
            "subheader_chart": "Chart",
            "tag_positive": "Positive",
            "tag_negative": "Negative",
            "tag_neutral": "Neutral",
        },
    }
    d = I18N[lang]

    st.header(d["sidebar_header"])
    st.markdown(d["sidebar_bullets"])
    st.divider()
    
    # --- 模型配置区 ---
    with st.expander(d["sidebar_config"], expanded=True):
        p_idx = 0
        p_choice = st.selectbox(d["config_provider"], ["Gemini", "DeepSeek"], index=p_idx)
        
        # 默认模型型号
        default_models = {
            "Gemini": "gemini-2.0-flash",
            "DeepSeek": "deepseek-chat"
        }
        
        selected_key = st.text_input(d["config_api_key"], type="password", help="API Key 不会持久化保存。")
        selected_model = st.text_input(d["config_model"], value=default_models.get(p_choice, ""))
        
        # 存入 session_state
        st.session_state["llm_provider"] = p_choice.lower()
        st.session_state["llm_api_key"] = selected_key
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
            for k in [SS_DF, SS_NAME, SS_CLEAN_DF, SS_CLEAN_STATS]:
                st.session_state.pop(k, None)
            st.rerun()

df = st.session_state.get(SS_DF)

# 批量分析
with tab_batch:
    if df is None:
        st.info("Wait for upload...")
    else:
        # 数据统计指标展示
        st.subheader(d["subheader_preview"])
        c1, c2, c3 = st.columns(3)
        with c1: st.metric(d["metric_rows"], f"{len(df):,}")
        with c2: st.metric(d["metric_cols"], len(df.columns))
        with c3: st.metric("Provider", st.session_state.llm_provider.upper())
        
        st.dataframe(df.head(100), use_container_width=True)

        # 抽样配置
        st.subheader(d["subheader_sample"])
        col_text = st.selectbox(d["selectbox_col"], list(df.columns))
        n_rows = st.slider(d["slider_n"], 1, min(50, len(df)), 5)

        if st.button(d["btn_start"], type="primary"):
            if not st.session_state.get("llm_api_key"):
                st.error(d["error_no_key"])
                st.stop()

            sample = df.head(n_rows)
            texts = sample[col_text]
            progress = st.progress(0.0, text=d["progress_preparing"])

            async def run_batch():
                # 获取服务实例
                service = get_llm_service(
                    provider=st.session_state.llm_provider,
                    api_key=st.session_state.llm_api_key,
                    model=st.session_state.llm_model
                )
                
                tasks = []
                for i, (idx, raw) in enumerate(texts.items()):
                    async def one_call(t, pos):
                        try:
                            res = await service.async_analyze_review_as_dict(str(t))
                            progress.progress((pos + 1) / n_rows, text=f"Analyzing {pos+1}/{n_rows}")
                            return {"index": idx, "text": str(t)[:50]+"...", **res}
                        except Exception as e:
                            return {"index": idx, "text": str(t)[:50]+"...", "error": str(e)}
                    tasks.append(one_call(raw, i))
                
                return await asyncio.gather(*tasks)

            results = asyncio.run(run_batch())
            st.success(d["progress_done"])
            res_df = pd.DataFrame(results)
            st.dataframe(res_df, use_container_width=True)

# 单条分析
with tab_single:
    st.subheader(d["subheader_single"])
    text_input = st.text_area(d["label_text"], height=150)
    if st.button(d["btn_single"], type="primary"):
        if not text_input.strip():
            st.warning(d["warn_empty_text"])
        elif not st.session_state.get("llm_api_key"):
            st.error(d["error_no_key"])
        else:
            with st.spinner(d["spinner_calling"]):
                try:
                    service = get_llm_service(
                        provider=st.session_state.llm_provider,
                        api_key=st.session_state.llm_api_key,
                        model=st.session_state.llm_model
                    )
                    # 同步调用
                    res = service.analyze_review_as_dict(text_input.strip())
                    st.success(d["success_done"])
                    st.json(res)
                except Exception as e:
                    st.error(d["error_runtime"].format(e=e))
