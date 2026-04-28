from __future__ import annotations

import csv
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OFFICECLI = Path(r"C:\Users\DenseFog\AppData\Local\OfficeCli\officecli.exe")
REPORT_DIR = ROOT / "report"
ASSETS_DIR = REPORT_DIR / "assets"


def run_officecli(*args: str) -> None:
    subprocess.run([str(OFFICECLI), *args], check=True, cwd=ROOT)


def add_paragraph(doc: Path, text: str, *, style: str | None = None) -> None:
    args = ["add", str(doc), "/body", "--type", "paragraph", "--prop", f"text={text}"]
    if style:
        args += ["--prop", f"style={style}"]
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
        "width=6.2in",
        "--prop",
        "height=3.55in",
        "--prop",
        f"alt={alt}",
    )


def load_metrics() -> dict[str, str]:
    metrics: dict[str, str] = {}
    with (REPORT_DIR / "business_insight_key_metrics.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            metrics[row["metric"]] = row["value"]
    return metrics


def load_distribution_summary() -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    category_counts: dict[str, int] = {}
    with (ROOT / "data" / "week3_raw_reviews_1000_unprocessed.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            category = (row.get("category") or "").strip()
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1

    pain_counts: dict[str, int] = {}
    with (ROOT / "data" / "gold_200_end.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("sentiment") or "").strip().lower() != "negative":
                continue
            text = (row.get("pain_points") or "").strip()
            if not text:
                continue
            for part in [p.strip() for p in text.replace("；", ",").replace("、", ",").replace(";", ",").split(",") if p.strip()]:
                pain_counts[part] = pain_counts.get(part, 0) + 1

    cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    pains = sorted(pain_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    return cats, pains


def add_metrics_block(doc: Path, metrics: dict[str, str], lang: str) -> None:
    lines = [
        f"原始评论样本量：{metrics['Raw review sample size']} | 覆盖品类数：{metrics['Covered categories']}",
        f"黄金测试集规模：{metrics['Gold test set size']} | 情感分析整体准确率：{metrics['Overall sentiment accuracy (%)']}%",
        f"模型平均置信度：{metrics['Average model confidence']}",
    ] if lang == "zh" else [
        f"Raw review sample size: {metrics['Raw review sample size']} | Covered categories: {metrics['Covered categories']}",
        f"Gold test set size: {metrics['Gold test set size']} | Overall sentiment accuracy: {metrics['Overall sentiment accuracy (%)']}%",
        f"Average model confidence: {metrics['Average model confidence']}",
    ]
    for line in lines:
        add_paragraph(doc, line)


def add_figure(doc: Path, title: str, image_name: str, note: str) -> None:
    add_paragraph(doc, title, style="Heading2")
    add_picture(doc, ASSETS_DIR / image_name, alt=title)
    add_paragraph(doc, note)


def chinese_blocks(metrics: dict[str, str], cats: list[tuple[str, int]], pains: list[tuple[str, int]]) -> list[tuple[str, str]]:
    top_cat = "、".join(f"{k}{v}条" for k, v in cats[:5])
    top_pain = "、".join(f"{k}{v}次" for k, v in pains[:5])
    return [
        ("自动化客服与评论情感分析系统商业洞察报告", "Heading1"),
        ("一、创业想法与产品核心概念", "Heading2"),
        ("本项目的创业想法是面向中小电商商家与本地生活服务商家，提供一套“自动化客服 + 评论情感分析 + 商业洞察输出”的智能运营工具，帮助商家在不显著增加人力成本的前提下，提高客服响应效率、沉淀可复用规则，并把原本分散的评论数据转化为可执行的经营决策。", "Normal"),
        ("产品核心由两条能力主线构成。第一条是基于 RAG 的智能客服，系统会先检索商家 FAQ、退换货规则和标准话术，再生成符合业务边界的回复。第二条是评论洞察引擎，系统对评论执行清洗、情感分类、痛点抽取和高频问题聚合，并用图表输出问题结构与变化趋势。两者共同形成从“用户反馈”到“经营动作”的闭环。", "Normal"),
        ("二、价值主张与差异化定位", "Heading2"),
        ("本项目的核心价值主张不是“替代全部人工客服”，而是成为商家的“客服效率层 + 评论洞察层 + 规则执行层”。它的目标客户不是大型企业联络中心，而是客服和运营都高度依赖少量人员、但日常要面对大量重复咨询与分散评论数据的中小电商团队。", "Normal"),
        ("__FIG_VALUE__", "__MARKER__"),
        ("从价值结构上看，产品的差异化主要来自三个维度。第一，客服回复不是纯生成，而是带有商家规则约束的检索增强回复，因此在退款、补发、售后流程等敏感场景下更可控。第二，评论分析不是只给正负标签，而是进一步抽取质量、尺寸、包装、服务态度等具体痛点。第三，系统把前台客户沟通和后台经营分析打通，使“回复客户”和“复盘问题”发生在同一套工作流中。", "Normal"),
        ("三、目标市场与市场定位", "Heading2"),
        ("本项目的首要目标市场是评论规模较大、售后咨询频繁、但客服和数据分析能力有限的中小电商商家，尤其适用于服饰、数码、食品生鲜、酒店和家居等高评论密度行业。典型客户画像包括：每天需要处理大量重复咨询、依赖平台评论判断产品质量、没有专门数据分析岗位、希望快速降低客服成本并提升店铺评分的商家或小型运营团队。", "Normal"),
        ("在定位上，产品不应与大型 CRM 或企业联络中心系统正面竞争，而应作为“低门槛、高 ROI、快速上线”的商家运营工具进入市场。对用户来说，它的采购逻辑更接近“能不能一周内用起来、能不能看出差评原因、能不能减少重复咨询”，而不是“是否具备全渠道联络中心的复杂治理能力”。", "Normal"),
        ("四、市场环境分析", "Heading2"),
        ("当前市场存在三个清晰的需求驱动。第一，消费者越来越习惯数字化支持，但并不接受体验很差的自动化服务。第二，评论对购买决策的影响越来越强。第三，电商经营对履约体验极为敏感。上述驱动共同说明，商家今天面临的不是“要不要做自动化”，而是“如何把自动化做得既高效又不损害客户体验”。", "Normal"),
        ("从竞争格局看，当前可替代方案大致可以分为四类：人工客服与外包、规则机器人、通用大模型工作流，以及大型客户体验平台。我们的竞争切口不是做“最全”的客服平台，而是做“最贴近中小商家经营动作”的智能运营工具。", "Normal"),
        ("__FIG_COMPETITOR__", "__MARKER__"),
        ("从行业趋势看，AI 客服与体验运营已经不是单纯的概念赛道，而是明确增长的市场。市场报告显示，AI for Customer Service 在 2024 年已达到约 130.1 亿美元规模，零售与电商是增长最快的终端场景之一。", "Normal"),
        ("五、数据与证据支撑", "Heading2"),
        (f"当前项目已整理 {metrics['Raw review sample size']} 条原始评论，覆盖 {metrics['Covered categories']} 个品类；在 {metrics['Gold test set size']} 条黄金测试集上，情感分析整体准确率达到 {metrics['Overall sentiment accuracy (%)']}%，平均模型置信度为 {metrics['Average model confidence']}。评估集中共识别正向 {metrics['Positive predictions in gold_200_end']} 条、中性 {metrics['Neutral predictions in gold_200_end']} 条、负向 {metrics['Negative predictions in gold_200_end']} 条。", "Normal"),
        ("这些数据说明，系统并非停留在概念验证阶段，而是已经具备了用结构化结果支撑运营判断的基础能力。尤其是对于中小商家最关心的负向评论发现与售后场景，本项目已经能提供较为稳定的识别结果和初步的痛点归因。", "Normal"),
        ("__METRICS__", "__MARKER__"),
        (f"图表显示，1,000 条评论主要分布在以下品类：{top_cat}。负向评论高频痛点集中在：{top_pain}，其中“质量差”最突出，说明质量问题是当前最应优先优化的经营短板。", "Normal"),
        ("__FIG_CATEGORY__", "__MARKER__"),
        ("__FIG_SENTIMENT__", "__MARKER__"),
        ("__FIG_PAIN__", "__MARKER__"),
        ("六、商业模式与增长策略", "Heading2"),
        ("从中小商家的采购逻辑出发，最合理的定价方式是 SaaS 订阅 + 用量分层。基础版解决“先用起来”的门槛问题，专业版强化高并发、知识库容量与导出报告能力，企业版提供私有部署、接口集成和多品牌治理。", "Normal"),
        ("市场进入策略应采用“从单点高痛场景切入”的方式。最现实的切入点是差评监控和售后回复，因为这两类场景价值明确、效果容易被感知，也最容易形成复购和口碑传播。", "Normal"),
        ("__FIG_GROWTH__", "__MARKER__"),
        ("在营销策略上，应以结果导向的案例展示为主，而不是技术概念宣传。对中小商家来说，真正有说服力的是“客服响应更快了”“差评原因更清晰了”“复盘报告能指导补货和产品改进”。", "Normal"),
        ("七、结论", "Heading2"),
        ("综合来看，本项目不是单纯的“AI 聊天工具”，而是一个以真实商家经营问题为出发点的智能运营系统。其核心商业价值在于：用规则增强的客服回复降低人工成本，用评论洞察提升问题发现与决策效率，并通过可视化与结构化输出把 AI 能力转化为商家愿意持续付费的经营价值。", "Normal"),
        ("基于当前原型在 200 条黄金测试集上达到 92.5% 的情感分析准确率、已覆盖 1000 条跨 10 个品类的评论数据，以及已经实现的检索增强客服回复链路，本项目具备从课程原型向真实商业试点进一步推进的可行性。", "Normal"),
        ("八、外部参考来源", "Heading2"),
        ("1. Qualtrics 2024 Consumer Experience Trends Report", "Normal"),
        ("2. BrightLocal Local Consumer Review Survey 2024", "Normal"),
        ("3. DHL 2024 Online Purchasing Behavior Report", "Normal"),
        ("4. Grand View Research AI for Customer Service Market Report", "Normal"),
        ("5. McKinsey Where is customer care in 2024?", "Normal"),
        ("6. Pax8 2024 Artificial Intelligence Buying Trends Report", "Normal"),
    ]


def english_blocks(metrics: dict[str, str], cats: list[tuple[str, int]], pains: list[tuple[str, int]]) -> list[tuple[str, str]]:
    top_cat = ", ".join(f"{k} {v}" for k, v in cats[:5])
    top_pain = ", ".join(f"{k} {v}" for k, v in pains[:5])
    return [
        ("Business Insight Report: Automated Customer Service and Review Sentiment Analysis System", "Heading1"),
        ("1. Venture Idea and Core Product Concept", "Heading2"),
        ("The venture is designed for small and medium-sized e-commerce sellers and local service businesses. It combines automated customer service, review sentiment analysis, and business insight generation into one workflow, helping merchants improve response efficiency, reduce repetitive support work, and turn scattered review data into operational decisions.", "Normal"),
        ("The product is built around two linked capabilities: a RAG-grounded customer-service assistant and a review-insight engine. Together, they create a closed loop from customer feedback to business action.", "Normal"),
        ("2. Value Proposition and Differentiation", "Heading2"),
        ("The product is not positioned as a total replacement for human agents. Instead, it acts as a customer-service efficiency layer, a review-intelligence layer, and a policy-execution layer for merchants that lack enterprise-scale support systems.", "Normal"),
        ("__FIG_VALUE__", "__MARKER__"),
        ("Its differentiation comes from merchant-specific rule grounding, structured pain-point extraction, and the ability to connect customer-facing replies with back-office review analytics in one workflow.", "Normal"),
        ("3. Target Market and Positioning", "Heading2"),
        ("The target market includes merchants with high review volume, frequent after-sales inquiries, and limited analytics capacity, especially in categories such as apparel, consumer electronics, fresh food, hospitality, and home products.", "Normal"),
        ("The product should enter the market as a low-friction, high-ROI operating tool rather than compete head-on with enterprise CRM or full contact-center suites.", "Normal"),
        ("4. Market Landscape", "Heading2"),
        ("Three forces support the opportunity: consumers increasingly accept digital support, reviews heavily influence purchase decisions, and e-commerce experience is highly sensitive to service and fulfillment quality.", "Normal"),
        ("Competing alternatives include human outsourcing, rule-based bots, generic LLM workflows, and large customer-experience suites. The opportunity lies in serving SMB merchants who need more control than generic AI but less complexity than enterprise platforms.", "Normal"),
        ("__FIG_COMPETITOR__", "__MARKER__"),
        ("Industry growth is also supportive. AI for customer service is now a rapidly expanding market, with retail and e-commerce among the fastest-growing end-use segments.", "Normal"),
        ("5. Evidence and Internal Data", "Heading2"),
        (f"The project currently includes {metrics['Raw review sample size']} raw reviews across {metrics['Covered categories']} categories. On a gold test set of {metrics['Gold test set size']} labeled reviews, sentiment analysis achieved {metrics['Overall sentiment accuracy (%)']}% overall accuracy with an average confidence score of {metrics['Average model confidence']}. In the evaluation set, the system predicted {metrics['Positive predictions in gold_200_end']} positive, {metrics['Neutral predictions in gold_200_end']} neutral, and {metrics['Negative predictions in gold_200_end']} negative cases.", "Normal"),
        ("These results show that the prototype has already moved beyond a purely conceptual stage. It can provide structured outputs that are useful for merchants, especially in negative-review detection and after-sales response scenarios.", "Normal"),
        ("__METRICS__", "__MARKER__"),
        (f"The raw review distribution is led by these categories: {top_cat}. Among negative reviews, the most frequent pain points are {top_pain}, with product quality issues standing out as the most urgent operational problem.", "Normal"),
        ("__FIG_CATEGORY__", "__MARKER__"),
        ("__FIG_SENTIMENT__", "__MARKER__"),
        ("__FIG_PAIN__", "__MARKER__"),
        ("6. Business Model and Growth Strategy", "Heading2"),
        ("A SaaS subscription with usage tiers is the most practical pricing model. The Basic plan lowers adoption friction, the Pro plan supports growth-stage merchants, and the Enterprise plan addresses deployment and governance needs.", "Normal"),
        ("The recommended market-entry strategy is to start with negative-review monitoring and after-sales reply automation, then expand into monthly insight reporting, knowledge-base features, and broader workflow automation.", "Normal"),
        ("__FIG_GROWTH__", "__MARKER__"),
        ("Marketing should emphasize measurable outcomes rather than AI buzzwords. What sells is faster response, clearer issue diagnosis, and operational recommendations tied to review data.", "Normal"),
        ("7. Conclusion", "Heading2"),
        ("The project is not simply an AI chatbot. It is an operations-oriented AI system designed around real merchant pain points. Its value lies in reducing support workload, improving issue detection, and turning unstructured review data into merchant decisions.", "Normal"),
        ("With more real merchant pilots and quantified ROI metrics such as labor hours saved, faster complaint response, and product-quality improvement, the venture can become significantly more compelling to partners and early customers.", "Normal"),
    ]


def insert_marker(doc: Path, marker: str, metrics: dict[str, str], lang: str) -> None:
    if marker == "__METRICS__":
        add_metrics_block(doc, metrics, lang)
    elif marker == "__FIG_VALUE__":
        add_figure(doc, "图 1. 价值主张与差异化" if lang == "zh" else "Figure 1. Value Proposition and Differentiation", "value_proposition.svg", "图示强调本项目不是单纯客服机器人，而是把回复自动化、评论洞察和规则执行打包为一个运营工具。" if lang == "zh" else "This figure shows that the product is positioned as an operations tool, not just a chatbot.")
    elif marker == "__FIG_COMPETITOR__":
        add_figure(doc, "图 2. 竞争定位矩阵" if lang == "zh" else "Figure 2. Competitive Positioning Matrix", "competitor_matrix.svg", "矩阵说明本项目的关键切口在于同时兼顾规则可控性、回复灵活性和评论分析能力。" if lang == "zh" else "The matrix highlights the project’s wedge: combining policy control, reply flexibility, and review analytics.")
    elif marker == "__FIG_CATEGORY__":
        add_figure(doc, "图 3. 品类分布" if lang == "zh" else "Figure 3. Category Distribution", "category_distribution.svg", "该图表说明项目样本已经覆盖 10 个品类，并非局限于单一细分场景。" if lang == "zh" else "This chart shows that the project already covers ten categories and is not limited to a single niche.")
    elif marker == "__FIG_SENTIMENT__":
        add_figure(doc, "图 4. 情感分布" if lang == "zh" else "Figure 4. Sentiment Distribution", "sentiment_distribution.svg", "该分布说明系统已经能够较稳定地识别负向评论，适合用于商家日常监控与预警。" if lang == "zh" else "The evaluation distribution confirms that the system is able to capture negative reviews at a useful level for operations.")
    elif marker == "__FIG_PAIN__":
        add_figure(doc, "图 5. 高频痛点" if lang == "zh" else "Figure 5. Top Pain Points", "top_pain_points.svg", "高频痛点集中在质量相关问题上，说明供应链质量与质检流程应成为第一优先级改进对象。" if lang == "zh" else "The concentration of quality-related complaints suggests that product quality should be treated as the first operational priority.")
    elif marker == "__FIG_GROWTH__":
        add_figure(doc, "图 6. 定价与增长路径" if lang == "zh" else "Figure 6. Pricing and Growth Path", "growth_strategy.svg", "图示说明建议采用分层订阅与阶段式市场进入路径，以降低早期获客阻力并保留扩展空间。" if lang == "zh" else "The figure outlines a tiered pricing model and a phased go-to-market path designed to reduce early adoption friction.")


def build_doc(doc: Path, blocks: list[tuple[str, str]], metrics: dict[str, str], lang: str) -> None:
    if doc.exists():
        try:
            doc.unlink()
        except PermissionError:
            pass
    run_officecli("create", str(doc))
    for text, style in blocks:
        if style == "__MARKER__":
            insert_marker(doc, text, metrics, lang)
        else:
            add_paragraph(doc, text, style=style)


def main() -> None:
    metrics = load_metrics()
    cats, pains = load_distribution_summary()
    build_doc(REPORT_DIR / "business_insight_report_cn_market.docx", chinese_blocks(metrics, cats, pains), metrics, "zh")
    build_doc(REPORT_DIR / "business_insight_report_en_market.docx", english_blocks(metrics, cats, pains), metrics, "en")
    print("Generated rich market report documents.")


if __name__ == "__main__":
    main()
