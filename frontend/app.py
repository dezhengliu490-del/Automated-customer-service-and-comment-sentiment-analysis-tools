from __future__ import annotations

import asyncio
import ast
import re
import sys
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

# --- 接入后端服务 ---
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from llm_factory import get_llm_service
from customer_service import generate_customer_service_reply_as_dict
from insights import top_pain_points_from_results
from rag_utils import SimpleRAGIndex

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
SS_CS_CHAT_HISTORY = "customer_service_chat_history"


_EN_WORD = re.compile(r"[A-Za-z]+")
_CJK_CHAR = re.compile(r"[\u4e00-\u9fff]")
_KB_DIR = _ROOT / "data" / "kb"
_SENTIMENT_ORDER = ["positive", "neutral", "negative"]
_SENTIMENT_COLORS = ["#10b981", "#f59e0b", "#ef4444"]

_DEMO_POSITIVE_WORDS = [
    "好",
    "满意",
    "喜欢",
    "不错",
    "流畅",
    "推荐",
    "excellent",
    "great",
    "good",
    "love",
    "satisfied",
]
_DEMO_NEGATIVE_WORDS = [
    "差",
    "坏",
    "慢",
    "破",
    "退款",
    "退货",
    "失望",
    "问题",
    "broken",
    "bad",
    "slow",
    "poor",
    "refund",
    "disappointed",
]
_DEMO_PAIN_KEYWORDS = {
    "物流慢": ["物流", "快递", "配送", "送货", "shipping", "delivery", "slow"],
    "包装破损": ["包装", "破损", "压坏", "漏", "package", "packaging", "damaged"],
    "质量不稳定": ["质量", "做工", "瑕疵", "坏", "断", "裂", "quality", "defect", "broken"],
    "尺寸不符": ["尺码", "尺寸", "偏大", "偏小", "size", "fit"],
    "客服响应慢": ["客服", "没人", "回复", "售后", "service", "support", "reply"],
    "价格体验不佳": ["贵", "价格", "优惠", "price", "expensive"],
    "功能故障": ["卡顿", "闪退", "不能用", "故障", "bug", "crash", "stuck"],
}


def _should_reply_in_english(config_lang: str, text: str) -> bool:
    """Use English when config is en, or input text is likely English."""
    if (config_lang or "").strip().lower() == "en":
        return True
    src = (text or "").strip()
    if not src:
        return False

    en_words = _EN_WORD.findall(src)
    cjk_chars = _CJK_CHAR.findall(src)
    if len(en_words) >= 3 and len(cjk_chars) == 0:
        return True
    ascii_letters = sum(ch.isascii() and ch.isalpha() for ch in src)
    if ascii_letters >= 12 and ascii_letters > len(cjk_chars) * 2:
        return True
    return False


def _inject_demo_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2.4rem;
        }
        [data-testid="stSidebar"] {
            background: #f8fafc;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 14px 16px;
        }
        div[data-testid="stMetric"] label {
            color: #475569;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            padding: 10px 16px;
        }
        .stButton > button {
            border-radius: 7px;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _available_kb_files(lang: str) -> list[Path]:
    if not _KB_DIR.exists():
        return []
    files = sorted(_KB_DIR.glob("*.md"))
    if lang == "en":
        return sorted(files, key=lambda p: (not p.stem.endswith("_en"), p.name))
    return sorted(files, key=lambda p: (p.stem.endswith("_en"), p.name))


def _read_kb_files(paths: list[Path]) -> str:
    chunks: list[str] = []
    for path in paths:
        try:
            chunks.append(f"# {path.stem}\n{path.read_text(encoding='utf-8')}")
        except OSError:
            continue
    return "\n\n".join(chunks).strip()


def _coerce_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, float) and pd.isna(value):
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(x).strip() for x in value if str(x).strip()]

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return []

    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            return _coerce_text_list(parsed)
        except (SyntaxError, ValueError):
            pass

    for sep in ["，", ",", "；", ";", "|", "\n"]:
        if sep in text:
            return [x.strip() for x in text.split(sep) if x.strip()]
    return [text]


def _results_to_records(res_df: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in res_df.to_dict("records"):
        row["sentiment"] = str(row.get("sentiment", "")).strip().lower()
        row["pain_points"] = _coerce_text_list(row.get("pain_points"))
        records.append(row)
    return records


def _record_summary(row: dict[str, Any], lang: str) -> str:
    keys = ["summary_en", "summary", "summary_zh"] if lang == "en" else ["summary_zh", "summary", "summary_en"]
    for key in keys:
        val = str(row.get(key, "") or "").strip()
        if val:
            return val
    return ""


def _shorten(text: Any, limit: int = 220) -> str:
    val = re.sub(r"\s+", " ", str(text or "")).strip()
    return val if len(val) <= limit else f"{val[:limit]}..."


def _local_analyze_review(review_text: str, summary_language: str = "zh") -> dict[str, Any]:
    text = (review_text or "").strip()
    lower_text = text.lower()
    pos_score = sum(1 for word in _DEMO_POSITIVE_WORDS if word in lower_text or word in text)
    neg_score = sum(1 for word in _DEMO_NEGATIVE_WORDS if word in lower_text or word in text)

    if neg_score > pos_score:
        sentiment = "negative"
    elif pos_score > neg_score:
        sentiment = "positive"
    else:
        sentiment = "neutral"

    pain_points: list[str] = []
    if sentiment in {"negative", "neutral"}:
        for label, keywords in _DEMO_PAIN_KEYWORDS.items():
            if any(keyword in lower_text or keyword in text for keyword in keywords):
                pain_points.append(label)
    if sentiment == "negative" and not pain_points:
        pain_points.append("综合体验不佳")

    confidence = min(0.96, 0.62 + 0.08 * abs(pos_score - neg_score) + 0.04 * len(pain_points))
    summary_zh = f"该评论整体偏{ {'positive': '正向', 'neutral': '中性', 'negative': '负向'}[sentiment] }，核心关注点为{('、'.join(pain_points) if pain_points else '常规体验反馈')}。"
    summary_en = (
        f"The review is {sentiment}; key issue: "
        f"{(', '.join(pain_points) if pain_points else 'general customer experience')}."
    )
    return {
        "sentiment": sentiment,
        "confidence": round(confidence, 2),
        "pain_points": pain_points,
        "summary_zh": summary_zh,
        "summary_en": summary_en,
        "demo_mode": True,
    }


def _run_demo_batch_analysis(
    rows: list[tuple[int, str]],
    summary_language: str,
    progress,
    progress_text: str,
    status_placeholder,
) -> list[dict[str, Any]]:
    total = max(1, len(rows))
    results: list[dict[str, Any]] = []
    for finished_count, (idx, raw_text) in enumerate(rows, start=1):
        res = _local_analyze_review(raw_text, summary_language=summary_language)
        results.append(
            {
                "index": idx,
                "preview": str(raw_text)[:80] + ("..." if len(str(raw_text)) > 80 else ""),
                "raw_text": str(raw_text),
                **res,
            }
        )
        progress.progress(finished_count / total, text=f"{progress_text} {finished_count}/{total}")
        status_placeholder.caption(f"Completed: {finished_count}/{total} | Failed: 0")
    return results


def _generate_demo_reply_as_dict(
    *,
    review_text: str,
    merchant_rules: str,
    sentiment: str | None,
    pain_points: list[str] | None,
    style_hint: str | None,
    reply_language: str,
    knowledge_base_text: str,
    kb_top_k: int,
) -> dict[str, Any]:
    kb_source = (knowledge_base_text or "").strip() or (merchant_rules or "").strip()
    retrieved_chunks: list[str] = []
    if kb_source:
        hits = SimpleRAGIndex.from_text(kb_source, chunk_size=300, overlap=60).retrieve(
            review_text,
            top_k=kb_top_k,
        )
        retrieved_chunks = [hit.text for hit in hits]

    points = pain_points or _local_analyze_review(review_text).get("pain_points", [])
    if reply_language == "en":
        reply = (
            "Hi, thanks for sharing this with us. "
            f"We are sorry about {', '.join(points) if points else 'the experience you mentioned'}. "
            "We will check the order details and offer a practical next step based on the store policy."
        )
    else:
        reply = (
            "您好，感谢您把这个情况告诉我们。"
            f"关于{('、'.join(points) if points else '您反馈的问题')}，我们已经记录并会结合订单情况核实。"
            "我们会按店铺规则尽快给出补发、换货或售后处理方案。"
        )
    if style_hint:
        reply = f"{reply}\n\n语气备注：{style_hint}"

    return {
        "reply_text": reply,
        "provider": "demo",
        "model": "local-template",
        "reply_language": reply_language,
        "used_rules": bool(kb_source),
        "retrieved_chunks": retrieved_chunks,
    }


def _detect_review_column(df: pd.DataFrame) -> str | None:
    if df is None or df.empty:
        return None

    columns = list(df.columns)
    if not columns:
        return None

    # 1) Name-based priority (strict -> fuzzy), explicitly exclude id-like columns
    names = {col: str(col).strip().lower() for col in columns}
    exclude_tokens = ["_id", "id_", " id", "编号", "序号", "index", "索引"]

    exact_priority = [
        "review_text",
        "reviewtext",
        "comment_text",
        "comments_text",
        "评论内容",
        "评价内容",
        "评论文本",
        "内容",
    ]
    for key in exact_priority:
        for col, name in names.items():
            if name == key:
                return col

    fuzzy_priority = ["review_text", "comment_text", "评论", "评价", "内容", "text", "comment", "review"]
    for col, name in names.items():
        if any(tok in name for tok in exclude_tokens):
            continue
        if any(token in name for token in fuzzy_priority):
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

        name = str(col).strip().lower()
        sample = s.dropna().astype("string").str.strip().head(200)
        if sample.empty:
            continue
        non_empty_ratio = (sample.str.len() > 0).mean()
        avg_len = sample.str.len().mean()
        unique_ratio = sample.nunique() / max(len(sample), 1)
        score = non_empty_ratio * 0.45 + min(avg_len / 60.0, 1.0) * 0.35 + unique_ratio * 0.2
        if any(tok in name for tok in exclude_tokens):
            score -= 0.7
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

    sentiment_counts = chart_df["sentiment"].value_counts().reindex(_SENTIMENT_ORDER, fill_value=0).reset_index()
    sentiment_counts.columns = ["sentiment", "count"]

    st.divider()
    st.subheader(i18n["chart_title"])

    c1, c2 = st.columns(2)
    with c1:
        bar_chart = alt.Chart(sentiment_counts).mark_bar(size=36).encode(
            x=alt.X("sentiment:N", sort=_SENTIMENT_ORDER, title="Sentiment", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("count:Q", title="Count"),
            color=alt.Color(
                "sentiment:N",
                scale=alt.Scale(
                    domain=_SENTIMENT_ORDER,
                    range=_SENTIMENT_COLORS,
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
                    domain=_SENTIMENT_ORDER,
                    range=_SENTIMENT_COLORS,
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
                domain=_SENTIMENT_ORDER,
                range=_SENTIMENT_COLORS,
            ),
            title="Sentiment",
        ),
        tooltip=["day:T", "sentiment", "count"],
    ).properties(height=360)
    st.altair_chart(line_chart, use_container_width=True)


def _render_pain_word_cloud(pain_df: pd.DataFrame) -> None:
    if pain_df.empty:
        return

    cloud_df = pain_df.copy().reset_index(drop=True)
    max_count = max(int(cloud_df["count"].max()), 1)
    cloud_df["x"] = [12 + ((i * 37) % 76) for i in range(len(cloud_df))]
    cloud_df["y"] = [18 + ((i * 29) % 64) for i in range(len(cloud_df))]
    cloud_df["size"] = cloud_df["count"].map(lambda x: 18 + 34 * (int(x) / max_count))

    chart = alt.Chart(cloud_df).mark_text(
        align="center",
        baseline="middle",
        font="sans-serif",
        fontWeight="bold",
    ).encode(
        x=alt.X("x:Q", axis=None, scale=alt.Scale(domain=[0, 100])),
        y=alt.Y("y:Q", axis=None, scale=alt.Scale(domain=[0, 100])),
        text="pain_point:N",
        size=alt.Size("size:Q", legend=None),
        color=alt.Color(
            "count:Q",
            scale=alt.Scale(range=["#0f766e", "#2563eb", "#dc2626"]),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("pain_point:N", title="Pain Point"),
            alt.Tooltip("count:Q", title="Count"),
        ],
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)


def _render_pain_point_insights(res_df: pd.DataFrame | None, i18n: dict[str, str], lang: str) -> None:
    st.subheader(i18n["insights_title"])

    if not isinstance(res_df, pd.DataFrame) or res_df.empty:
        st.info(i18n["insights_empty"])
        return

    col_a, col_b = st.columns([1, 1])
    with col_a:
        top_k = st.slider(i18n["insights_top_k"], min_value=3, max_value=12, value=6, step=1)
    with col_b:
        include_neutral = st.checkbox(i18n["insights_include_neutral"], value=False)

    records = _results_to_records(res_df)
    top_points = top_pain_points_from_results(records, top_k=int(top_k), include_neutral=include_neutral)
    analyzed_count = len(records)
    negative_count = sum(1 for row in records if row.get("sentiment") == "negative")
    covered_count = sum(1 for row in records if row.get("pain_points"))
    unique_count = len({pp for row in records for pp in row.get("pain_points", [])})

    metric_a, metric_b, metric_c, metric_d = st.columns(4)
    metric_a.metric(i18n["insights_analyzed"], f"{analyzed_count:,}")
    metric_b.metric(i18n["insights_negative"], f"{negative_count:,}")
    metric_c.metric(i18n["insights_coverage"], f"{covered_count:,}")
    metric_d.metric(i18n["insights_unique"], f"{unique_count:,}")

    if not top_points:
        st.info(i18n["insights_no_pain"])
        return

    pain_df = pd.DataFrame(top_points)
    chart_left, chart_right = st.columns([1, 1])
    with chart_left:
        st.markdown(f"**{i18n['insights_word_cloud']}**")
        _render_pain_word_cloud(pain_df)
    with chart_right:
        st.markdown(f"**{i18n['insights_top_chart']}**")
        bar = alt.Chart(pain_df).mark_bar(cornerRadiusEnd=4).encode(
            x=alt.X("count:Q", title="Count"),
            y=alt.Y("pain_point:N", sort="-x", title=None),
            color=alt.Color("count:Q", scale=alt.Scale(range=["#0f766e", "#2563eb"]), legend=None),
            tooltip=["pain_point", "count"],
        ).properties(height=300)
        st.altair_chart(bar, use_container_width=True)

    st.markdown(f"**{i18n['insights_defect_list']}**")
    for rank, item in enumerate(top_points, start=1):
        pain_point = str(item["pain_point"])
        related = [
            row
            for row in records
            if pain_point in row.get("pain_points", [])
            and (include_neutral or row.get("sentiment") == "negative")
        ]
        with st.expander(f"{rank}. {pain_point} · {item['count']}", expanded=rank <= 3):
            for sample_idx, row in enumerate(related[:4], start=1):
                text = row.get("raw_text") or row.get("preview") or ""
                st.write(f"{sample_idx}. {_shorten(text)}")
                summary = _record_summary(row, lang)
                if summary:
                    st.caption(f"{i18n['insights_summary']}: {summary}")


async def _run_batch_analysis(
    service,
    rows: list[tuple[int, str]],
    summary_language: str,
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
            res = await service.async_analyze_review_as_dict(
                str(raw_text),
                summary_language=summary_language,
            )
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
            "config_summary_lang": "摘要语言 (Summary)",
            "config_demo_mode": "演示备用模式",
            "page_title": "多模型评论情感分析系统",
            "page_subtitle": "基于大语言模型（LLM）的评论内容自动化情感分析与汇总。",
            "tab_batch": "批量分析",
            "tab_insights": "痛点洞察",
            "tab_single": "单条评论",
            "tab_cs_chat": "模拟客服聊天",
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
            "batch_wait_upload": "等待上传数据文件。",
            "result_table": "分析结果",
            "insights_title": "深度痛点分析",
            "insights_empty": "暂无批量分析结果。",
            "insights_top_k": "Top K 痛点",
            "insights_include_neutral": "包含中性评论",
            "insights_analyzed": "已分析",
            "insights_negative": "差评数",
            "insights_coverage": "含痛点评论",
            "insights_unique": "唯一痛点",
            "insights_no_pain": "当前结果没有可聚合的痛点。",
            "insights_word_cloud": "高频负面词云",
            "insights_top_chart": "痛点排行",
            "insights_defect_list": "核心缺陷明细",
            "insights_summary": "AI 摘要",
            "cs_intro": "输入用户评论/提问，结合商家规则实时生成客服回复。",
            "cs_review": "用户评论 / 提问",
            "cs_rules": "商家规则（可留空）",
            "cs_use_kb": "使用本地知识库",
            "cs_kb_docs": "知识库文档",
            "cs_kb_empty": "未发现本地知识库文档。",
            "cs_retrieved_chunks": "RAG 命中文档片段",
            "cs_style": "语气偏好（可选）",
            "cs_sentiment": "情感提示（可选）",
            "cs_pain_points": "痛点关键词（可选，用逗号分隔）",
            "cs_btn_reply": "生成回复",
            "cs_btn_clear": "清空聊天记录",
            "cs_thinking": "客服 AI 正在生成回复...",
            "cs_error": "生成失败：{e}",
            "cs_warn_empty": "请输入用户评论或提问。",
            "cs_meta": "Provider: {provider} | Model: {model} | Rules used: {used_rules}",
            "lang_zh": "中文",
            "lang_en": "English",
        },
        "en": {
            "sidebar_header": "Sentiment Analysis",
            "sidebar_config": "LLM Config",
            "config_provider": "Provider",
            "config_model": "Model",
            "config_summary_lang": "Summary Language",
            "config_demo_mode": "Demo fallback mode",
            "page_title": "Multi-LLM Sentiment Analysis",
            "page_subtitle": "Automated review analysis dashboard powered by Large Language Models.",
            "tab_batch": "Batch Analysis",
            "tab_insights": "Pain Insights",
            "tab_single": "Single Review",
            "tab_cs_chat": "Simulated CS Chat",
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
            "batch_wait_upload": "Waiting for an uploaded data file.",
            "result_table": "Analysis Results",
            "insights_title": "Deep Pain Point Analysis",
            "insights_empty": "No batch analysis results yet.",
            "insights_top_k": "Top K Pain Points",
            "insights_include_neutral": "Include neutral reviews",
            "insights_analyzed": "Analyzed",
            "insights_negative": "Negative",
            "insights_coverage": "With Pain Points",
            "insights_unique": "Unique Points",
            "insights_no_pain": "No aggregate pain points in current results.",
            "insights_word_cloud": "High-Frequency Negative Word Cloud",
            "insights_top_chart": "Pain Point Ranking",
            "insights_defect_list": "Core Defect Details",
            "insights_summary": "AI Summary",
            "cs_intro": "Enter a customer review/question and generate an AI customer-service reply with merchant rules context.",
            "cs_review": "Customer review / question",
            "cs_rules": "Merchant rules (optional)",
            "cs_use_kb": "Use local knowledge base",
            "cs_kb_docs": "Knowledge base docs",
            "cs_kb_empty": "No local knowledge-base docs found.",
            "cs_retrieved_chunks": "RAG retrieved chunks",
            "cs_style": "Style hint (optional)",
            "cs_sentiment": "Sentiment hint (optional)",
            "cs_pain_points": "Pain points (optional, comma-separated)",
            "cs_btn_reply": "Generate reply",
            "cs_btn_clear": "Clear chat history",
            "cs_thinking": "Generating customer-service reply...",
            "cs_error": "Generation failed: {e}",
            "cs_warn_empty": "Please enter a review or question.",
            "cs_meta": "Provider: {provider} | Model: {model} | Rules used: {used_rules}",
            "lang_zh": "Chinese",
            "lang_en": "English",
        },
    }
    d = I18N[lang]

    st.header(d["sidebar_header"])
    st.divider()

    with st.expander(d["sidebar_config"], expanded=True):
        p_choice = st.selectbox(d["config_provider"], ["Gemini", "DeepSeek"], index=1)
        default_models = {"Gemini": "gemini-2.5-flash", "DeepSeek": "deepseek-chat"}
        selected_model = st.text_input(d["config_model"], value=default_models.get(p_choice, ""))
        summary_lang_label = st.selectbox(
            d["config_summary_lang"],
            options=[d["lang_zh"], d["lang_en"]],
            index=0,
        )
        demo_mode = st.checkbox(d["config_demo_mode"], value=False)
        summary_lang = "zh" if summary_lang_label == d["lang_zh"] else "en"
        st.session_state["llm_provider"] = p_choice.lower()
        st.session_state["llm_model"] = selected_model
        st.session_state["summary_language"] = summary_lang
        st.session_state["demo_mode"] = demo_mode

st.title(d["page_title"])
st.markdown(d["page_subtitle"])

_inject_demo_css()

tab_batch, tab_insights, tab_single, tab_cs = st.tabs(
    [d["tab_batch"], d["tab_insights"], d["tab_single"], d["tab_cs_chat"]]
)

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
        st.info(d["batch_wait_upload"])
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
                if st.session_state.get("demo_mode", False):
                    results = _run_demo_batch_analysis(
                        rows,
                        st.session_state.get("summary_language", "zh"),
                        progress,
                        progress_text="Demo analyzing",
                        status_placeholder=status_placeholder,
                    )
                else:
                    service = get_llm_service(
                        provider=st.session_state.llm_provider,
                        model=st.session_state.llm_model,
                    )
                    results = asyncio.run(
                        _run_batch_analysis(
                            service,
                            rows,
                            st.session_state.get("summary_language", "zh"),
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
            st.subheader(d["result_table"])
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
                        if st.session_state.get("demo_mode", False):
                            retried = _run_demo_batch_analysis(
                                retry_rows,
                                st.session_state.get("summary_language", "zh"),
                                progress,
                                progress_text="Retrying",
                                status_placeholder=status_placeholder,
                            )
                        else:
                            service = get_llm_service(
                                provider=st.session_state.llm_provider,
                                model=st.session_state.llm_model,
                            )
                            retried = asyncio.run(
                                _run_batch_analysis(
                                    service,
                                    retry_rows,
                                    st.session_state.get("summary_language", "zh"),
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

with tab_insights:
    _render_pain_point_insights(st.session_state.get(SS_BATCH_RESULTS), d, lang)

with tab_single:
    st.subheader(d["subheader_single"])
    text_input = st.text_area(d["label_text"], height=150)
    if st.button(d["btn_single"], type="primary", key="btn_single_analyze"):
        if not text_input.strip():
            st.warning(d["warn_empty_text"])
        else:
            with st.spinner(d["spinner_calling"]):
                try:
                    single_lang = (
                        "en"
                        if _should_reply_in_english(
                            st.session_state.get("summary_language", "zh"),
                            text_input,
                        )
                        else "zh"
                    )
                    if st.session_state.get("demo_mode", False):
                        res = _local_analyze_review(text_input.strip(), summary_language=single_lang)
                    else:
                        service = get_llm_service(
                            provider=st.session_state.llm_provider,
                            model=st.session_state.llm_model,
                        )
                        res = service.analyze_review_as_dict(
                            text_input.strip(),
                            summary_language=single_lang,
                        )
                    st.success(d["success_done"])
                    st.json(res)
                except Exception as exc:
                    st.error(d["error_runtime"].format(e=exc))

with tab_cs:
    st.subheader(d["tab_cs_chat"])
    st.caption(d["cs_intro"])

    if SS_CS_CHAT_HISTORY not in st.session_state:
        st.session_state[SS_CS_CHAT_HISTORY] = []

    with st.expander("Context / 上下文", expanded=True):
        review_text = st.text_area(d["cs_review"], height=120, key="cs_review_text")
        merchant_rules = st.text_area(d["cs_rules"], height=120, key="cs_rules_text")
        kb_files = _available_kb_files(lang)
        use_kb = st.checkbox(d["cs_use_kb"], value=True, disabled=not kb_files)
        if kb_files:
            default_kb = [p.name for p in kb_files[:2]]
            selected_kb_names = st.multiselect(
                d["cs_kb_docs"],
                options=[p.name for p in kb_files],
                default=default_kb,
                disabled=not use_kb,
                key="cs_kb_docs",
            )
            selected_kb_paths = [p for p in kb_files if p.name in selected_kb_names]
            knowledge_base_text = _read_kb_files(selected_kb_paths) if use_kb else ""
        else:
            st.caption(d["cs_kb_empty"])
            knowledge_base_text = ""
        col_a, col_b = st.columns(2)
        with col_a:
            style_hint = st.text_input(d["cs_style"], key="cs_style_hint")
        with col_b:
            sentiment_hint = st.selectbox(
                d["cs_sentiment"],
                options=["", "positive", "neutral", "negative"],
                index=0,
                key="cs_sentiment_hint",
            )
        pain_points_raw = st.text_input(d["cs_pain_points"], key="cs_pain_points")

    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        do_reply = st.button(d["cs_btn_reply"], type="primary", use_container_width=True)
    with btn_col2:
        do_clear = st.button(d["cs_btn_clear"], use_container_width=True)

    if do_clear:
        st.session_state[SS_CS_CHAT_HISTORY] = []
        st.rerun()

    if do_reply:
        if not review_text.strip():
            st.warning(d["cs_warn_empty"])
        else:
            pain_points = [x.strip() for x in pain_points_raw.split(",") if x.strip()] if pain_points_raw else None
            with st.spinner(d["cs_thinking"]):
                try:
                    reply_language = (
                        "en"
                        if _should_reply_in_english(
                            st.session_state.get("summary_language", "zh"),
                            review_text,
                        )
                        else "zh"
                    )
                    if st.session_state.get("demo_mode", False):
                        res = _generate_demo_reply_as_dict(
                            review_text=review_text.strip(),
                            merchant_rules=merchant_rules.strip(),
                            sentiment=sentiment_hint or None,
                            pain_points=pain_points,
                            style_hint=style_hint.strip() or None,
                            reply_language=reply_language,
                            knowledge_base_text=knowledge_base_text,
                            kb_top_k=3,
                        )
                    else:
                        res = generate_customer_service_reply_as_dict(
                            review_text=review_text.strip(),
                            merchant_rules=merchant_rules.strip(),
                            provider=st.session_state.get("llm_provider", "deepseek"),
                            model=st.session_state.get("llm_model") or None,
                            sentiment=sentiment_hint or None,
                            pain_points=pain_points,
                            style_hint=style_hint.strip() or None,
                            reply_language=reply_language,
                            knowledge_base_text=knowledge_base_text,
                            kb_top_k=3,
                        )
                    used_rules = bool(res.get("used_rules") or knowledge_base_text.strip())
                    st.session_state[SS_CS_CHAT_HISTORY].append(
                        {
                            "review_text": review_text.strip(),
                            "reply_text": res.get("reply_text", ""),
                            "meta": d["cs_meta"].format(
                                provider=res.get("provider", "-"),
                                model=res.get("model", "-"),
                                used_rules=used_rules,
                            ),
                            "retrieved_chunks": res.get("retrieved_chunks", []),
                        }
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(d["cs_error"].format(e=exc))

    for item in st.session_state.get(SS_CS_CHAT_HISTORY, []):
        with st.chat_message("user"):
            st.write(item["review_text"])
        with st.chat_message("assistant"):
            st.write(item["reply_text"])
            st.caption(item["meta"])
            chunks = item.get("retrieved_chunks") or []
            if chunks:
                with st.expander(d["cs_retrieved_chunks"], expanded=False):
                    for idx, chunk in enumerate(chunks, start=1):
                        st.write(f"{idx}. {_shorten(chunk, 320)}")
