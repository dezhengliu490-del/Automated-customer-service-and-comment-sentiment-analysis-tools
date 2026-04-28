from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OFFICECLI = Path(r"C:\Users\DenseFog\AppData\Local\OfficeCli\officecli.exe")
REPORT_DIR = ROOT / "report"
ASSETS_DIR = REPORT_DIR / "assets"


def run_officecli(*args: str) -> None:
    cmd = [str(OFFICECLI), *args]
    subprocess.run(cmd, check=True, cwd=ROOT)


def load_metrics() -> dict[str, str]:
    path = REPORT_DIR / "business_insight_key_metrics.csv"
    metrics: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics[row["metric"]] = row["value"]
    return metrics


def load_distribution_summary() -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    reviews = pd.read_csv(ROOT / "data" / "week3_raw_reviews_1000_unprocessed.csv")
    preds = pd.read_csv(ROOT / "data" / "gold_200_end.csv")
    cat_counts = list(reviews["category"].value_counts().sort_values(ascending=False).items())

    pain_counts: dict[str, int] = {}
    neg = preds[preds["sentiment"] == "negative"]
    for val in neg["pain_points"].dropna():
        text = str(val).strip()
        if not text or text.lower() == "nan":
            continue
        parts = [p.strip() for p in text.replace("；", ",").replace("、", ",").replace(";", ",").split(",") if p.strip()]
        for part in parts:
            pain_counts[part] = pain_counts.get(part, 0) + 1
    pain_top = sorted(pain_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    return cat_counts, pain_top


def add_paragraph(doc: Path, text: str, *, style: str | None = None, bold: bool | None = None) -> None:
    args = ["add", str(doc), "/body", "--type", "paragraph", "--prop", f"text={text}"]
    if style:
        args.extend(["--prop", f"style={style}"])
    if bold is not None:
        args.extend(["--prop", f"bold={'true' if bold else 'false'}"])
    run_officecli(*args)


def add_picture(doc: Path, image: Path, *, alt: str) -> None:
    run_officecli(
        "add",
        str(doc),
        "/body",
        "--type",
        "picture",
        "--prop",
        f"path={image}",
        "--prop",
        "width=5.8in",
        "--prop",
        "height=3.5in",
        "--prop",
        f"alt={alt}",
    )


def build_chinese_content(metrics: dict[str, str], cats: list[tuple[str, int]], pains: list[tuple[str, int]]) -> list[tuple[str, str]]:
    top_cat = "、".join(f"{k}{v}条" for k, v in cats[:5])
    top_pain = "、".join(f"{k}{v}次" for k, v in pains[:5])
    return [
        ("自动化客服与评论情感分析系统商业洞察报告", "Heading1"),
        ("一、创业想法与产品核心概念", "Heading2"),
        ("本项目面向中小电商商家与本地生活服务商家，提供“自动化客服 + 评论情感分析 + 商业洞察输出”的一体化智能运营工具。系统一方面通过 RAG 检索商家 FAQ、退换货规则和标准话术生成合规客服回复，另一方面对海量评论进行清洗、情感分类和痛点抽取，帮助商家将评论数据转化为运营决策。", None),
        ("二、目标市场与市场定位", "Heading2"),
        ("目标客户为评论规模较大、售后咨询频繁但缺少专业数据分析能力的中小商家，尤其适用于服饰、数码、食品生鲜、酒店等高评论密度行业。产品定位不是替代全部客服，而是作为“客服效率层 + 评论洞察层”，通过规则增强与可视化输出，区别于纯人工客服、传统规则机器人和通用大模型工具。", None),
        ("三、关键数据摘要", "Heading2"),
        (f"当前项目已整理 {metrics['Raw review sample size']} 条原始评论，覆盖 {metrics['Covered categories']} 个品类；在 {metrics['Gold test set size']} 条黄金测试集上，情感分析整体准确率达到 {metrics['Overall sentiment accuracy (%)']}%，平均模型置信度为 {metrics['Average model confidence']}。评估集中共识别正向 {metrics['Positive predictions in gold_200_end']} 条、中性 {metrics['Neutral predictions in gold_200_end']} 条、负向 {metrics['Negative predictions in gold_200_end']} 条。", None),
        ("四、图表与发现", "Heading2"),
        (f"图表显示，1,000 条评论主要分布在以下品类：{top_cat}。这说明系统并非只在单一行业验证，而是在多类场景中具备基础泛化能力。负向评论高频痛点集中在：{top_pain}，其中“质量差”最突出，说明质量问题是当前最应优先优化的经营短板。", None),
        ("五、商业与增长策略", "Heading2"),
        ("商业模式建议采用 SaaS 订阅 + 用量分层。基础版面向小商家提供评论分析与基础自动回复，专业版增加更高并发、知识库容量和导出能力，企业版提供私有部署与接口集成。市场进入策略上，应先从“差评监控 + 售后回复”这一高痛点场景切入，再逐步扩展到经营月报和产品改进建议。", None),
        ("六、结论", "Heading2"),
        ("基于现有原型数据，本项目已经证明其在中小商家客服降本和评论洞察增效方面具备较强落地潜力。后续若继续补充真实商家案例，并量化节省工时、差评响应速度和产品改进收益，其商业说服力将进一步增强。", None),
    ]


def build_english_content(metrics: dict[str, str], cats: list[tuple[str, int]], pains: list[tuple[str, int]]) -> list[tuple[str, str]]:
    top_cat = ", ".join(f"{k} {v}" for k, v in cats[:5])
    top_pain = ", ".join(f"{k} {v}" for k, v in pains[:5])
    return [
        ("Business Insight Report: Automated Customer Service and Review Sentiment Analysis System", "Heading1"),
        ("1. Venture Idea and Core Product Concept", "Heading2"),
        ("The venture is designed for small and medium-sized e-commerce sellers and local service businesses. It combines automated customer service, review sentiment analysis, and business insight generation into one workflow. The system uses RAG to retrieve merchant rules, FAQ content, and standard scripts before generating compliant customer-service replies, while also converting large volumes of reviews into structured operational insight.", None),
        ("2. Target Market and Market Positioning", "Heading2"),
        ("The target market includes merchants with high review volume, frequent after-sales inquiries, and limited data-analysis capacity. The product is positioned not as a full replacement for human agents, but as an efficiency layer for customer service and a decision-support layer for review intelligence. Its differentiation comes from merchant-specific rule grounding, explainability, and closed-loop insight generation.", None),
        ("3. Key Metrics", "Heading2"),
        (f"The project currently includes {metrics['Raw review sample size']} raw reviews across {metrics['Covered categories']} categories. On a gold test set of {metrics['Gold test set size']} labeled reviews, sentiment analysis achieved {metrics['Overall sentiment accuracy (%)']}% overall accuracy with an average confidence score of {metrics['Average model confidence']}. In the evaluation set, the system predicted {metrics['Positive predictions in gold_200_end']} positive, {metrics['Neutral predictions in gold_200_end']} neutral, and {metrics['Negative predictions in gold_200_end']} negative cases.", None),
        ("4. Chart-Based Findings", "Heading2"),
        (f"The raw review distribution is led by these categories: {top_cat}. This indicates that the prototype has already been exercised across multiple product domains rather than a single vertical. Among negative reviews, the most frequent pain points are {top_pain}, with product quality issues standing out as the most urgent operational problem.", None),
        ("5. Business and Growth Strategy", "Heading2"),
        ("The recommended business model is a SaaS subscription with usage tiers. A basic plan can provide review analysis and standard automated replies for small merchants, while advanced tiers can add higher concurrency, larger knowledge-base capacity, reporting, and private deployment. The most practical market-entry strategy is to start from high-pain scenarios such as negative-review monitoring and after-sales reply automation, then expand into monthly insight reporting and product improvement recommendations.", None),
        ("6. Conclusion", "Heading2"),
        ("The current prototype already demonstrates strong commercial potential in reducing customer-service workload and turning unstructured review data into actionable business decisions. With more real merchant case studies and quantified ROI indicators such as labor hours saved, faster complaint response, and product-quality improvement, the venture can become significantly more convincing for investors, partners, and pilot customers.", None),
    ]


def build_doc(doc: Path, title_blocks: list[tuple[str, str]], metrics: dict[str, str], lang: str) -> None:
    if doc.exists():
        doc.unlink()
    run_officecli("create", str(doc))

    for text, style in title_blocks:
        add_paragraph(doc, text, style=style or "Normal")

    metric_lines = [
        f"Raw review sample size: {metrics['Raw review sample size']} | Covered categories: {metrics['Covered categories']}"
        if lang == "en"
        else f"原始评论样本量：{metrics['Raw review sample size']} | 覆盖品类数：{metrics['Covered categories']}",
        f"Gold test set size: {metrics['Gold test set size']} | Overall sentiment accuracy: {metrics['Overall sentiment accuracy (%)']}%"
        if lang == "en"
        else f"黄金测试集规模：{metrics['Gold test set size']} | 情感分析整体准确率：{metrics['Overall sentiment accuracy (%)']}%",
        f"Average model confidence: {metrics['Average model confidence']}"
        if lang == "en"
        else f"模型平均置信度：{metrics['Average model confidence']}",
    ]
    for line in metric_lines:
        add_paragraph(doc, line)

    add_paragraph(doc, "Figure 1. Category Distribution" if lang == "en" else "图 1. 品类分布", style="Heading2")
    add_picture(doc, ASSETS_DIR / "category_distribution.svg", alt="Category distribution")
    add_paragraph(
        doc,
        "This chart shows that the project already covers ten categories and is not limited to a single niche."
        if lang == "en"
        else "该图表说明项目样本已经覆盖 10 个品类，并非局限于单一细分场景。",
    )

    add_paragraph(doc, "Figure 2. Sentiment Distribution" if lang == "en" else "图 2. 情感分布", style="Heading2")
    add_picture(doc, ASSETS_DIR / "sentiment_distribution.svg", alt="Sentiment distribution")
    add_paragraph(
        doc,
        "The evaluation distribution confirms that the system is able to capture negative reviews at a useful level for operations."
        if lang == "en"
        else "该分布说明系统已经能够较稳定地识别负向评论，适合用于商家日常监控与预警。",
    )

    add_paragraph(doc, "Figure 3. Top Pain Points" if lang == "en" else "图 3. 高频痛点", style="Heading2")
    add_picture(doc, ASSETS_DIR / "top_pain_points.svg", alt="Top pain points")
    add_paragraph(
        doc,
        "The concentration of quality-related complaints suggests that product quality should be treated as the first operational priority."
        if lang == "en"
        else "高频痛点集中在质量相关问题上，说明供应链质量与质检流程应成为第一优先级改进对象。",
    )


def main() -> None:
    metrics = load_metrics()
    cats, pains = load_distribution_summary()

    cn_doc = REPORT_DIR / "business_insight_report_cn.docx"
    en_doc = REPORT_DIR / "business_insight_report_en.docx"

    build_doc(cn_doc, build_chinese_content(metrics, cats, pains), metrics, "zh")
    build_doc(en_doc, build_english_content(metrics, cats, pains), metrics, "en")

    print(cn_doc)
    print(en_doc)


if __name__ == "__main__":
    main()
