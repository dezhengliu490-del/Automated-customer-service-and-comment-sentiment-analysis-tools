from __future__ import annotations

import asyncio
import sys
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
SS_BATCH_RESULTS = "batch_results"
SS_BATCH_FAILED = "batch_failed"
SS_BATCH_RUNNING = "batch_running"
SS_BATCH_TEXT_COL = "batch_text_col"


def _detect_review_column(df: pd.DataFrame) -> str | None:
    if df is None or df.empty:
        return None

    columns = list(df.columns)
    if not columns:
        return None

    # 1) Name-based priority
    strong_tokens = [
        "review_text",
        "review",
        "comment",
        "comments",
        "文本",
        "评论",
        "内容",
        "评价",
    ]
    for col in columns:
        name = str(col).strip().lower()
        if any(token in name for token in strong_tokens):
            return col

    # 2) Content-based fallback
    best_col = None
    best_score = -1.0
    for col in columns:
        s = df[col]
        if not (
            pd.api.types.is_object_dtype(s)
            or pd.api.types.is_string_dtype(s)
            or pd.api.types.is_categorical_dtype(s)
        ):
            continue

        sample = s.dropna().astype("string").str.strip().head(200)
        if sample.empty:
            continue
        non_empty_ratio = (sample.str.len() > 0).mean()
        avg_len = sample.str.len().mean()
        unique_ratio = sample.nunique() / max(len(sample), 1)
        score = non_empty_ratio * 0.5 + min(avg_len / 60.0, 1.0) * 0.3 + unique_ratio * 0.2
        if score > best_score:
            best_score = score
            best_col = col

    return best_col


def _find_time_columns(df: pd.DataFrame) -> list[str]:
    candidates: list[str] = []
    for col in df.columns:
        s = df[col]
        col_name = str(col).strip().lower()
        name_hint = any(token in col_name for token in ["time", "date", "日期", "时间"])
        if pd.api.types.is_datetime64_any_dtype(s):
            candidates.append(col)
            continue
        if (
            pd.api.types.is_object_dtype(s)
            or pd.api.types.is_string_dtype(s)
            or pd.api.types.is_categorical_dtype(s)
        ):
            cleaned = s.astype("string").str.strip()
            parsed = pd.to_datetime(cleaned, errors="coerce")
            # 列名命中时间关键词时，降低识别阈值；否则保持较高阈值
            threshold = 0.4 if name_hint else 0.7
            if len(parsed) > 0 and parsed.notna().mean() >= threshold:
                candidates.append(col)
    return candidates


def _render_sentiment_charts(res_df: pd.DataFrame, source_df: pd.DataFrame, i18n: dict[str, str]) -> None:
    if "sentiment" not in res_df.columns:
        return

    chart_df = res_df[res_df["sentiment"].notna()].copy()
    if chart_df.empty:
        return

    sentiment_order = ["positive", "neutral", "negative"]
    sentiment_counts = chart_df["sentiment"].value_counts().reindex(sentiment_order, fill_value=0).reset_index()
    sentiment_counts.columns = ["sentiment", "count"]

    st.divider()
    st.subheader(i18n["chart_title"])

    c1, c2 = st.columns(2)
    with c1:
        bar_chart = alt.Chart(sentiment_counts).mark_bar(size=36).encode(
            x=alt.X("sentiment:N", sort=sentiment_order, title="Sentiment", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("count:Q", title="Count"),
            color=alt.Color(
                "sentiment:N",
                scale=alt.Scale(
                    domain=sentiment_order,
                    range=["#2ecc71", "#f1c40f", "#e74c3c"],
                ),
                legend=None,
            ),
            tooltip=["sentiment", "count"],
        ).properties(height=320)
        st.altair_chart(bar_chart, use_container_width=True)

    with c2:
        pie_chart = alt.Chart(sentiment_counts).mark_arc(innerRadius=55).encode(
            theta=alt.Theta("count:Q"),
            color=alt.Color(
                "sentiment:N",
                scale=alt.Scale(
                    domain=sentiment_order,
                    range=["#2ecc71", "#f1c40f", "#e74c3c"],
                ),
                title="Sentiment",
            ),
            tooltip=["sentiment", "count"],
        ).properties(height=320)
        st.altair_chart(pie_chart, use_container_width=True)

    st.subheader(i18n["trend_title"])
    time_cols = _find_time_columns(source_df)
    if not time_cols:
        st.info(i18n["trend_no_time"])
        return

    selected_time_col = st.selectbox(i18n["trend_pick_col"], options=time_cols, key="trend_time_col")
    mapped = source_df[[selected_time_col]].copy()
    mapped["index"] = mapped.index
    merged = chart_df.merge(mapped, on="index", how="left")
    merged["_ts"] = pd.to_datetime(merged[selected_time_col], errors="coerce")
    merged = merged[merged["_ts"].notna()]

    if merged.empty:
        st.info(i18n["trend_no_data"])
        return

    trend_df = (
        merged.assign(day=merged["_ts"].dt.date)
        .groupby(["day", "sentiment"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )

    line_chart = alt.Chart(trend_df).mark_line(point=True).encode(
        x=alt.X("day:T", title="Date"),
        y=alt.Y("count:Q", title="Count"),
        color=alt.Color(
            "sentiment:N",
            scale=alt.Scale(
                domain=sentiment_order,
                range=["#2ecc71", "#f1c40f", "#e74c3c"],
            ),
            title="Sentiment",
        ),
        tooltip=["day:T", "sentiment", "count"],
    ).properties(height=360)
    st.altair_chart(line_chart, use_container_width=True)


async def _run_batch_analysis(
    service,
    rows: list[tuple[int, str]],
    progress,
    progress_text,
    status_placeholder,
) -> list[dict]:
    total = len(rows)
    finished_count = 0
    failed_count = 0

    async def one_call(current_idx: int, raw_text: str) -> dict:
        nonlocal finished_count, failed_count
        try:
            res = await service.async_analyze_review_as_dict(str(raw_text))
            return {
                "index": current_idx,
                "preview": str(raw_text)[:80] + ("..." if len(str(raw_text)) > 80 else ""),
                "raw_text": str(raw_text),
                **res,
            }
        except Exception as exc:
            failed_count += 1
            return {
                "index": current_idx,
                "preview": str(raw_text)[:80] + ("..." if len(str(raw_text)) > 80 else ""),
                "raw_text": str(raw_text),
                "error": str(exc),
            }
        finally:
            finished_count += 1
            progress.progress(finished_count / total, text=f"{progress_text} {finished_count}/{total}")
            status_placeholder.caption(f"Completed: {finished_count}/{total} | Failed: {failed_count}")

    tasks = [one_call(idx, text) for idx, text in rows]
    return await asyncio.gather(*tasks)


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
            "subheader_sample": "分析",
            "selectbox_col": "请选择内容列",
            "auto_col_hint": "已自动识别评论列：`{col}`。如不准确可手动调整。",
            "manual_col": "手动选择评论列",
            "slider_n": "分析数量 N",
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
            "chart_title": "情感分布可视化",
            "trend_title": "情感时间趋势",
            "trend_pick_col": "选择时间列",
            "trend_no_time": "未检测到可用时间列，无法绘制趋势图。",
            "trend_no_data": "时间列存在，但当前分析结果无法映射出有效时间数据。",
            "failed_title": "失败项明细",
            "failed_retry": "重试失败项",
            "failed_none": "当前批次无失败项。",
            "running_tip": "任务执行中，请勿重复提交。",
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
            "subheader_sample": "Analysis",
            "selectbox_col": "Select Column",
            "auto_col_hint": "Auto-detected review column: `{col}`. You can switch manually if needed.",
            "manual_col": "Pick column manually",
            "slider_n": "Analysis Count N",
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
            "chart_title": "Sentiment Visuals",
            "trend_title": "Sentiment Trend Over Time",
            "trend_pick_col": "Pick a time column",
            "trend_no_time": "No usable time column detected, trend chart unavailable.",
            "trend_no_data": "Time column exists but no valid mapped dates in current results.",
            "failed_title": "Failed Items",
            "failed_retry": "Retry Failed Items",
            "failed_none": "No failed items in this batch.",
            "running_tip": "A batch is running. Please avoid duplicate submissions.",
        },
    }
    d = I18N[lang]

    st.header(d["sidebar_header"])
    st.divider()

    with st.expander(d["sidebar_config"], expanded=True):
        p_choice = st.selectbox(d["config_provider"], ["Gemini", "DeepSeek"], index=1)
        default_models = {"Gemini": "gemini-2.5-flash", "DeepSeek": "deepseek-chat"}
        selected_model = st.text_input(d["config_model"], value=default_models.get(p_choice, ""))
        st.session_state["llm_provider"] = p_choice.lower()
        st.session_state["llm_model"] = selected_model

st.title(d["page_title"])
st.markdown(d["page_subtitle"])

tab_batch, tab_single = st.tabs([d["tab_batch"], d["tab_single"]])

with st.expander(d["expander_upload"], expanded=True):
    uploaded = st.file_uploader(d["file_uploader_label"], type=["csv", "xlsx", "xls"])
    if uploaded:
        df_new = load_dataframe(uploaded)
        st.session_state[SS_DF] = df_new
        st.session_state[SS_NAME] = uploaded.name
    if st.session_state.get(SS_DF) is not None:
        if st.button(d["btn_clear"], key="btn_clear_data"):
            for k in [SS_DF, SS_NAME, SS_BATCH_RESULTS, SS_BATCH_FAILED, SS_BATCH_TEXT_COL]:
                st.session_state.pop(k, None)
            st.rerun()

df = st.session_state.get(SS_DF)

with tab_batch:
    if st.session_state.get(SS_BATCH_RUNNING):
        st.info(d["running_tip"])

    if df is None:
        st.info("Wait for upload...")
    else:
        st.subheader(d["subheader_preview"])
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(d["metric_rows"], f"{len(df):,}")
        with c2:
            st.metric(d["metric_cols"], len(df.columns))
        with c3:
            st.metric("Provider", st.session_state.llm_provider.upper())

        st.dataframe(df.head(100), use_container_width=True)

        st.subheader(d["subheader_sample"])
        auto_col = _detect_review_column(df)
        all_cols = list(df.columns)
        default_idx = all_cols.index(auto_col) if auto_col in all_cols else 0
        col_text = all_cols[default_idx]
        st.caption(d["auto_col_hint"].format(col=col_text))
        if st.checkbox(d["manual_col"], value=False, key="manual_col_toggle"):
            col_text = st.selectbox(d["selectbox_col"], all_cols, index=default_idx, key="select_col_text")

        with st.expander(d["btn_clean"]):
            c1, c2 = st.columns(2)
            with c1:
                do_dup_text = st.checkbox("去重 (Text)", value=True)
                do_empty = st.checkbox("删空 (Empty)", value=True)
            with c2:
                do_dup_row = st.checkbox("整行去重 (Row)", value=False)
                min_len = st.number_input("最小长度 (Min Len)", value=5, min_value=1)

            if st.button(d["btn_clean"], use_container_width=True, key="btn_clean_data"):
                cleaned_df, stats = clean_review_dataframe(
                    df,
                    col_text,
                    drop_duplicate_text=do_dup_text,
                    drop_empty_text=do_empty,
                    drop_full_row_duplicates=do_dup_row,
                    min_length=min_len,
                )
                st.session_state[SS_DF] = cleaned_df
                st.info(
                    f"""
                **{d['subheader_stats']}**
                - {d['metric_rows']} IN: {stats['rows_in']}
                - {d['metric_rows']} OUT: {stats['rows_out']}
                - 空文字过滤: {stats['empty_dropped']}
                - 长度过滤 (<{min_len}): {stats['too_short_dropped']}
                - 文本去重: {stats['dup_text_dropped']}
                """
                )
                st.rerun()

        n_rows = st.number_input(
            d["slider_n"],
            min_value=1,
            max_value=max(1, len(df)),
            value=min(max(1, len(df)), 5),
            step=1,
            key="number_batch_rows",
        )

        run_disabled = bool(st.session_state.get(SS_BATCH_RUNNING, False))
        if st.button(d["btn_start"], type="primary", disabled=run_disabled, key="btn_run_batch"):
            sample = df.head(int(n_rows))
            rows = [(int(idx), str(raw)) for idx, raw in sample[col_text].items()]

            progress = st.progress(0.0, text=d["progress_preparing"])
            status_placeholder = st.empty()

            try:
                st.session_state[SS_BATCH_RUNNING] = True
                service = get_llm_service(
                    provider=st.session_state.llm_provider,
                    model=st.session_state.llm_model,
                )
                results = asyncio.run(
                    _run_batch_analysis(
                        service,
                        rows,
                        progress,
                        progress_text="Analyzing",
                        status_placeholder=status_placeholder,
                    )
                )
                res_df = pd.DataFrame(results)
                st.session_state[SS_BATCH_RESULTS] = res_df
                st.session_state[SS_BATCH_TEXT_COL] = col_text
                if "error" in res_df.columns:
                    st.session_state[SS_BATCH_FAILED] = res_df[res_df["error"].notna()].copy()
                else:
                    st.session_state[SS_BATCH_FAILED] = pd.DataFrame()
                st.success(d["progress_done"])
            except Exception as exc:
                st.error(f"Failed to run batch: {exc}")
            finally:
                st.session_state[SS_BATCH_RUNNING] = False

        res_df = st.session_state.get(SS_BATCH_RESULTS)
        if isinstance(res_df, pd.DataFrame) and not res_df.empty:
            st.dataframe(res_df.drop(columns=["raw_text"], errors="ignore"), use_container_width=True)

            failed_df = st.session_state.get(SS_BATCH_FAILED)
            st.subheader(d["failed_title"])
            if isinstance(failed_df, pd.DataFrame) and not failed_df.empty:
                st.dataframe(
                    failed_df[["index", "preview", "error"]],
                    use_container_width=True,
                )

                if st.button(d["failed_retry"], key="btn_retry_failed"):
                    retry_rows = [(int(r["index"]), str(r["raw_text"])) for _, r in failed_df.iterrows()]
                    progress = st.progress(0.0, text="Retrying failed items...")
                    status_placeholder = st.empty()
                    try:
                        st.session_state[SS_BATCH_RUNNING] = True
                        service = get_llm_service(
                            provider=st.session_state.llm_provider,
                            model=st.session_state.llm_model,
                        )
                        retried = asyncio.run(
                            _run_batch_analysis(
                                service,
                                retry_rows,
                                progress,
                                progress_text="Retrying",
                                status_placeholder=status_placeholder,
                            )
                        )
                        retry_df = pd.DataFrame(retried)

                        merged = pd.concat(
                            [res_df[~res_df["index"].isin(retry_df["index"])], retry_df],
                            ignore_index=True,
                        ).sort_values("index")

                        st.session_state[SS_BATCH_RESULTS] = merged
                        if "error" in merged.columns:
                            st.session_state[SS_BATCH_FAILED] = merged[merged["error"].notna()].copy()
                        else:
                            st.session_state[SS_BATCH_FAILED] = pd.DataFrame()
                        st.success("Retry completed")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Retry failed: {exc}")
                    finally:
                        st.session_state[SS_BATCH_RUNNING] = False
            else:
                st.info(d["failed_none"])

            _render_sentiment_charts(res_df, df, d)

with tab_single:
    st.subheader(d["subheader_single"])
    text_input = st.text_area(d["label_text"], height=150)
    if st.button(d["btn_single"], type="primary", key="btn_single_analyze"):
        if not text_input.strip():
            st.warning(d["warn_empty_text"])
        else:
            with st.spinner(d["spinner_calling"]):
                try:
                    service = get_llm_service(
                        provider=st.session_state.llm_provider,
                        model=st.session_state.llm_model,
                    )
                    res = service.analyze_review_as_dict(text_input.strip())
                    st.success(d["success_done"])
                    st.json(res)
                except Exception as exc:
                    st.error(d["error_runtime"].format(e=exc))
