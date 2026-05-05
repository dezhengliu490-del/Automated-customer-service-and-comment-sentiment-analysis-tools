from __future__ import annotations

import csv
import subprocess
from pathlib import Path

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
    category_counts: dict[str, int] = {}
    with (ROOT / "data" / "week3_raw_reviews_1000_unprocessed.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            category = (row.get("category") or "").strip()
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1
    cat_counts = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

    pain_counts: dict[str, int] = {}
    with (ROOT / "data" / "gold_200_end.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("sentiment") or "").strip().lower() != "negative":
                continue
            text = str(row.get("pain_points") or "").strip()
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


def build_chinese_content(metrics: dict[str, str], cats: list[tuple[str, int]], pains: list[tuple[str, int]]) -> list[tuple[str, str | None]]:
    top_cat = "、".join(f"{k}{v}条" for k, v in cats[:5])
    top_pain = "、".join(f"{k}{v}次" for k, v in pains[:5])
    return [
        ("自动化客服与评论情感分析系统商业洞察报告", "Heading1"),
        ("一、创业想法与产品核心概念", "Heading2"),
        ("本项目面向中小电商商家与本地生活服务商家，提供“自动化客服 + 评论情感分析 + 商业洞察输出”的一体化智能运营工具，帮助商家在不显著增加人力成本的前提下，提高客服响应效率、沉淀可复用规则，并把原本分散的评论数据转化为可执行的经营决策。", None),
        ("产品核心由两条能力主线构成：第一条是基于 RAG 的智能客服，系统会先检索商家 FAQ、退换货规则和标准话术，再生成符合业务边界的回复；第二条是评论洞察引擎，系统对评论执行清洗、情感分类、痛点抽取和高频问题聚合，并用图表输出问题结构与变化趋势。两者共同形成从“用户反馈”到“经营动作”的闭环。", None),
        ("二、目标市场与市场定位", "Heading2"),
        ("目标客户为评论规模较大、售后咨询频繁但缺少专业数据分析能力的中小商家，尤其适用于服饰、数码、食品生鲜、酒店和家居等高评论密度行业。典型客户画像包括：每天需要处理大量重复咨询、依赖平台评论判断产品质量、没有专门数据分析岗位、希望快速降低客服成本并提升店铺评分的商家或小型运营团队。", None),
        ("产品定位不是替代全部客服，而是成为商家的“客服效率层 + 评论洞察层”。与人工客服相比，它具备更低的边际成本和更稳定的处理速度；与传统规则机器人相比，它对自然语言和复杂场景的适应性更强；与通用 AI 相比，它通过规则约束、知识检索和结构化输出，更符合真实业务流程。", None),
        ("三、关键数据摘要", "Heading2"),
        (f"当前项目已整理 {metrics['Raw review sample size']} 条原始评论，覆盖 {metrics['Covered categories']} 个品类；在 {metrics['Gold test set size']} 条黄金测试集上，情感分析整体准确率达到 {metrics['Overall sentiment accuracy (%)']}%，平均模型置信度为 {metrics['Average model confidence']}。评估集中共识别正向 {metrics['Positive predictions in gold_200_end']} 条、中性 {metrics['Neutral predictions in gold_200_end']} 条、负向 {metrics['Negative predictions in gold_200_end']} 条。", None),
        ("这些数据说明，系统并非停留在概念验证阶段，而是已经具备了用结构化结果支撑运营判断的基础能力。尤其是对于中小商家最关心的负向评论发现与售后场景，本项目已经能提供较为稳定的识别结果和初步的痛点归因。", None),
        ("__METRICS__", "__MARKER__"),
        ("四、图表与发现", "Heading2"),
        (f"图表显示，1,000 条评论主要分布在以下品类：{top_cat}。这说明系统并非只在单一行业验证，而是在多类场景中具备基础泛化能力。负向评论高频痛点集中在：{top_pain}，其中“质量差”最突出，说明质量问题是当前最应优先优化的经营短板。", None),
        ("__FIGURE_CATEGORY__", "__MARKER__"),
        ("图 1 对应的是样本来源结构。前五大品类的评论量都在 140 条以上，说明系统训练和验证不是依赖极少数特殊样本，而是在多个典型消费场景下都具有一定适用性。对于商业落地来说，这意味着产品可以先聚焦高评论密度行业，再逐步向相邻场景复制。", None),
        ("__FIGURE_SENTIMENT__", "__MARKER__"),
        ("图 2 对应的是模型在黄金测试集上的情感输出结果。负向样本数量达到 97 条，结合 92.5% 的整体准确率，可以说明系统对“风险评论”和“售后预警评论”的识别已经具有较高可用性，这对商家最直接的价值是减少差评漏看和售后响应滞后。", None),
        ("__FIGURE_PAIN__", "__MARKER__"),
        ("图 3 则把负向评论进一步拆解成了具体问题来源。相比只知道“这条是差评”，商家更需要知道差评究竟来自质量、尺寸、包装还是客服流程。痛点结构化之后，评论数据才能真正被用于质检排查、商品详情页优化、客服培训与售后 SOP 改进。", None),
        ("从经营意义上看，图表并不是单纯展示“评论多不多”或“好评差评各多少”，而是在帮助商家建立问题优先级。例如若“尺寸不符”持续高频，说明商品详情页与尺码说明需要先改；若“客服态度差”上升，则说明客服 SOP 和培训流程存在改进空间。", None),
        ("五、商业与增长策略", "Heading2"),
        ("商业模式建议采用 SaaS 订阅 + 用量分层。基础版面向小商家提供评论分析与基础自动回复，专业版增加更高并发、知识库容量、多账号管理与导出能力，企业版提供私有部署与接口集成。这样的分层既符合预算敏感型客户的采购习惯，也有利于随着业务规模增长提升客单价。", None),
        ("市场进入策略上，应先从“差评监控 + 售后回复”这一高痛点场景切入，因为其价值最容易被客户直观感知。后续再逐步扩展到经营月报、产品改进建议和跨平台运营支持，形成由“工具”向“经营助手”的升级路径。营销上应以案例、行业模板和免费试用为主，而不是抽象强调模型技术名词。", None),
        ("六、结论", "Heading2"),
        ("基于现有原型数据，本项目已经证明其在中小商家客服降本和评论洞察增效方面具备较强落地潜力。它的核心价值不在于“能不能聊天”，而在于是否能遵守商家规则、输出可执行结论，并在前台客服与后台分析之间形成闭环。", None),
        ("后续若继续补充真实商家案例，并量化节省工时、差评响应速度和产品改进收益，本项目将更容易从课程原型走向真实商业试点，也更有机会形成可持续的 SaaS 产品路线。", None),
    ]


def build_english_content(metrics: dict[str, str], cats: list[tuple[str, int]], pains: list[tuple[str, int]]) -> list[tuple[str, str | None]]:
    top_cat = ", ".join(f"{k} {v}" for k, v in cats[:5])
    top_pain = ", ".join(f"{k} {v}" for k, v in pains[:5])
    return [
        ("Business Insight Report: Automated Customer Service and Review Sentiment Analysis System", "Heading1"),
        ("1. Venture Idea and Core Product Concept", "Heading2"),
        ("The venture is designed for small and medium-sized e-commerce sellers and local service businesses. It combines automated customer service, review sentiment analysis, and business insight generation into one workflow, helping merchants improve response efficiency, reduce repetitive support work, and turn scattered review data into operational decisions.", None),
        ("The product is built around two linked capabilities. The first is a RAG-grounded customer-service assistant that retrieves merchant rules, FAQs, and service policies before generating a reply. The second is a review-insight engine that cleans review data, classifies sentiment, extracts pain points, and summarizes recurring issues through charts and structured outputs. Together, these components create a closed loop from customer feedback to business action.", None),
        ("2. Target Market and Market Positioning", "Heading2"),
        ("The target market includes merchants with high review volume, frequent after-sales inquiries, and limited data-analysis capacity, especially in categories such as apparel, consumer electronics, fresh food, hospitality, and home products. A typical customer is a small merchant or operator who handles repetitive support requests daily, relies heavily on platform reviews, and lacks a dedicated analytics team.", None),
        ("The product is positioned not as a full replacement for human agents, but as an efficiency layer for customer service and a decision-support layer for review intelligence. Its differentiation comes from merchant-specific rule grounding, explainability, and the ability to convert feedback data into operational recommendations rather than just generic chatbot responses.", None),
        ("3. Key Metrics", "Heading2"),
        (f"The project currently includes {metrics['Raw review sample size']} raw reviews across {metrics['Covered categories']} categories. On a gold test set of {metrics['Gold test set size']} labeled reviews, sentiment analysis achieved {metrics['Overall sentiment accuracy (%)']}% overall accuracy with an average confidence score of {metrics['Average model confidence']}. In the evaluation set, the system predicted {metrics['Positive predictions in gold_200_end']} positive, {metrics['Neutral predictions in gold_200_end']} neutral, and {metrics['Negative predictions in gold_200_end']} negative cases.", None),
        ("These results show that the prototype has already moved beyond a purely conceptual stage. It can provide structured outputs that are useful for merchants, especially in negative-review detection and after-sales response scenarios where practical business value is easier to demonstrate.", None),
        ("__METRICS__", "__MARKER__"),
        ("4. Chart-Based Findings", "Heading2"),
        (f"The raw review distribution is led by these categories: {top_cat}. This indicates that the prototype has already been exercised across multiple product domains rather than a single vertical. Among negative reviews, the most frequent pain points are {top_pain}, with product quality issues standing out as the most urgent operational problem.", None),
        ("__FIGURE_CATEGORY__", "__MARKER__"),
        ("Figure 1 should be read as evidence of category breadth. The top categories all contribute substantial review volume, which suggests the prototype is not overfitted to a single niche. Commercially, this matters because it supports a phased go-to-market strategy across multiple high-review industries.", None),
        ("__FIGURE_SENTIMENT__", "__MARKER__"),
        ("Figure 2 shows the system's sentiment output on the gold evaluation set. The large number of negative predictions, combined with the measured overall accuracy, indicates that the system is already useful for risk-focused use cases such as complaint monitoring and after-sales triage.", None),
        ("__FIGURE_PAIN__", "__MARKER__"),
        ("Figure 3 goes one step further by decomposing negative reviews into specific causes. This is commercially more useful than a simple sentiment label because merchants can directly connect the extracted issues to product quality checks, product-page fixes, packaging improvements, or customer-service training.", None),
        ("The charts are commercially meaningful because they help merchants prioritize action. For example, a persistent rise in size mismatch complaints points to product-page and sizing problems, while an increase in service-attitude complaints suggests a customer-service workflow or training problem rather than a product defect.", None),
        ("5. Business and Growth Strategy", "Heading2"),
        ("The recommended business model is a SaaS subscription with usage tiers. A basic plan can provide review analysis and standard automated replies for small merchants, while advanced tiers can add higher concurrency, larger knowledge-base capacity, reporting, multi-account management, and private deployment. This structure fits budget-sensitive merchants while preserving expansion room as their operations grow.", None),
        ("The most practical market-entry strategy is to start from high-pain scenarios such as negative-review monitoring and after-sales reply automation, because the value is immediate and easy for merchants to perceive. Over time, the product can expand into monthly insight reporting, product-improvement recommendations, and broader workflow automation. Early marketing should focus on case-driven outcomes rather than abstract AI terminology.", None),
        ("6. Conclusion", "Heading2"),
        ("The current prototype already demonstrates strong commercial potential in reducing customer-service workload and turning unstructured review data into actionable business decisions. Its value lies not only in generating replies, but in grounding those replies in merchant rules and connecting customer feedback to operational action.", None),
        ("With more real merchant case studies and quantified ROI indicators such as labor hours saved, faster complaint response, and product-quality improvement, the venture can become significantly more convincing for investors, partners, and pilot customers.", None),
    ]


def add_metrics_block(doc: Path, metrics: dict[str, str], lang: str) -> None:
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


def add_figure_block(doc: Path, fig_key: str, lang: str) -> None:
    if fig_key == "__FIGURE_CATEGORY__":
        title = "Figure 1. Category Distribution" if lang == "en" else "图 1. 品类分布"
        note = (
            "This chart shows that the project already covers ten categories and is not limited to a single niche."
            if lang == "en"
            else "该图表说明项目样本已经覆盖 10 个品类，并非局限于单一细分场景。"
        )
        image = ASSETS_DIR / "category_distribution.svg"
        alt = "Category distribution"
    elif fig_key == "__FIGURE_SENTIMENT__":
        title = "Figure 2. Sentiment Distribution" if lang == "en" else "图 2. 情感分布"
        note = (
            "The evaluation distribution confirms that the system is able to capture negative reviews at a useful level for operations."
            if lang == "en"
            else "该分布说明系统已经能够较稳定地识别负向评论，适合用于商家日常监控与预警。"
        )
        image = ASSETS_DIR / "sentiment_distribution.svg"
        alt = "Sentiment distribution"
    else:
        title = "Figure 3. Top Pain Points" if lang == "en" else "图 3. 高频痛点"
        note = (
            "The concentration of quality-related complaints suggests that product quality should be treated as the first operational priority."
            if lang == "en"
            else "高频痛点集中在质量相关问题上，说明供应链质量与质检流程应成为第一优先级改进对象。"
        )
        image = ASSETS_DIR / "top_pain_points.svg"
        alt = "Top pain points"

    add_paragraph(doc, title, style="Heading2")
    add_picture(doc, image, alt=alt)
    add_paragraph(doc, note)


def build_doc(doc: Path, title_blocks: list[tuple[str, str | None]], metrics: dict[str, str], lang: str) -> None:
    if doc.exists():
        doc.unlink()
    run_officecli("create", str(doc))

    for text, style in title_blocks:
        if style == "__MARKER__":
            if text == "__METRICS__":
                add_metrics_block(doc, metrics, lang)
            else:
                add_figure_block(doc, text, lang)
            continue
        add_paragraph(doc, text, style=style or "Normal")


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
