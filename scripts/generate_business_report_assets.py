from __future__ import annotations

from pathlib import Path
from textwrap import wrap
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "report" / "assets"


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def svg_header(width: int, height: int) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'


def wrap_svg(body: str, width: int, height: int) -> str:
    return (
        f"{svg_header(width, height)}"
        "<style>"
        '.title{font:700 22px "Segoe UI","Microsoft YaHei",sans-serif;fill:#1f3c5b;}'
        '.subtitle{font:400 12px "Segoe UI","Microsoft YaHei",sans-serif;fill:#61758a;}'
        '.label{font:600 13px "Segoe UI","Microsoft YaHei",sans-serif;fill:#1f2d3d;}'
        '.small{font:400 11px "Segoe UI","Microsoft YaHei",sans-serif;fill:#51606f;}'
        '.value{font:700 18px "Segoe UI","Microsoft YaHei",sans-serif;fill:#0f2740;}'
        '.pill{font:700 12px "Segoe UI","Microsoft YaHei",sans-serif;fill:#ffffff;}'
        '.axis{font:400 11px "Segoe UI","Microsoft YaHei",sans-serif;fill:#566573;}'
        "</style>"
        f"{body}</svg>"
    )


def text_block(x: int, y: int, text: str, klass: str, *, max_chars: int, line_height: int = 18, fill: str | None = None) -> str:
    lines = wrap(text, width=max_chars) or [text]
    fill_attr = f' fill="{fill}"' if fill else ""
    parts = [f'<text x="{x}" y="{y}" class="{klass}"{fill_attr}>']
    for idx, line in enumerate(lines):
        dy = "0" if idx == 0 else str(line_height)
        parts.append(f'<tspan x="{x}" dy="{dy}">{escape(line)}</tspan>')
    parts.append("</text>")
    return "".join(parts)


def build_value_prop_svg() -> str:
    width, height = 980, 600
    body = [
        '<rect width="100%" height="100%" fill="#f8fbff"/>',
        text_block(40, 48, "Value Proposition and Differentiation", "title", max_chars=40),
        text_block(40, 72, "Our product sits between generic AI tools and operational SaaS by combining reply automation, review insight, and merchant-rule grounding.", "subtitle", max_chars=105, line_height=15),
    ]
    cards = [
        (50, 120, 270, 175, "#eaf4ff", "Customer Service Efficiency", "Automates repetitive after-sales replies", "RAG-grounded replies reduce response time and keep policy consistency."),
        (355, 120, 270, 175, "#eef8ef", "Review Insight Engine", "Turns reviews into action items", "Sentiment and pain-point extraction helps merchants prioritize quality, sizing, and service issues."),
        (660, 120, 270, 175, "#fff4e8", "Closed-loop Operations", "From feedback to execution", "The same system supports support response, issue detection, and business reporting."),
    ]
    for x, y, w, h, color, title, line1, line2 in cards:
        body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{color}" stroke="#d7e3f1"/>')
        body.append(text_block(x + 18, y + 30, title, "label", max_chars=28, line_height=16))
        body.append(text_block(x + 18, y + 64, line1, "value", max_chars=24, line_height=20))
        body.append(text_block(x + 18, y + 114, line2, "small", max_chars=36, line_height=16))

    body.extend([
        text_block(40, 350, "Why it is different", "label", max_chars=30),
        '<rect x="40" y="370" width="900" height="185" rx="20" fill="#ffffff" stroke="#d9e3ec"/>',
    ])
    cols = [(65, "Alternative"), (270, "Typical Weakness"), (560, "Our Advantage")]
    for x, title in cols:
        body.append(text_block(x, 402, title, "label", max_chars=22))
    rows = [
        ("Human outsourcing", "High labor cost, knowledge not reusable", "Lower marginal cost and reusable policy knowledge"),
        ("Rule-based bot", "Rigid intents, weak at unstructured complaints", "Better natural-language coverage with rule grounding"),
        ("Generic LLM", "Can hallucinate and is hard to control for tone or policy", "Merchant-specific rules, retrieval context, and structured outputs"),
    ]
    y = 438
    for alt, weak, adv in rows:
        body.append(text_block(65, y, alt, "small", max_chars=20, line_height=15))
        body.append(text_block(270, y, weak, "small", max_chars=34, line_height=15))
        body.append(text_block(560, y, adv, "small", max_chars=38, line_height=15))
        body.append(f'<line x1="58" y1="{y + 26}" x2="918" y2="{y + 26}" stroke="#edf2f7"/>')
        y += 50
    return wrap_svg("".join(body), width, height)


def build_market_drivers_svg() -> str:
    width, height = 980, 620
    body = [
        '<rect width="100%" height="100%" fill="#fbfcfe"/>',
        text_block(40, 48, "Market Drivers Backing the Venture", "title", max_chars=40),
        text_block(40, 72, "External signals show that AI-enabled customer service, review response, and digital support are moving into the mainstream.", "subtitle", max_chars=105, line_height=15),
    ]
    cards = [
        (40, 120, 205, 195, "#1f77b4", "58%", "Consumers comfortable with chatbots or AI-powered support", "Qualtrics 2024 Consumer Experience Trends"),
        (270, 120, 205, 195, "#2ca02c", "88%", "Consumers would use a business that replies to all reviews", "BrightLocal 2024 Local Consumer Review Survey"),
        (500, 120, 205, 195, "#ff7f0e", "75%", "Consumers always or regularly read online reviews", "BrightLocal 2024 Local Consumer Review Survey"),
        (730, 120, 205, 195, "#9467bd", "95%", "Shoppers say delivery options influence where they shop online", "DHL 2024 Online Purchasing Behavior Report"),
    ]
    for x, y, w, h, color, big, title, source in cards:
        body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{color}"/>')
        body.append(f'<text x="{x + 18}" y="{y + 54}" class="pill" style="font-size:34px">{escape(big)}</text>')
        body.append(text_block(x + 18, y + 92, title, "pill", max_chars=24, line_height=16))
        body.append(text_block(x + 18, y + 154, source, "pill", max_chars=26, line_height=13))

    body.extend([
        text_block(40, 372, "Industry growth signals", "label", max_chars=30),
        text_block(40, 394, "AI for customer service is forecast to grow rapidly, with retail and e-commerce among the fastest-growing end-use sectors.", "small", max_chars=120, line_height=15),
        '<line x1="85" y1="548" x2="915" y2="548" stroke="#b8c6d6"/>',
        '<rect x="170" y="478" width="130" height="70" rx="14" fill="#90caf9"/>',
        '<rect x="650" y="278" width="130" height="270" rx="14" fill="#1565c0"/>',
        text_block(150, 574, "2024 market size", "axis", max_chars=18, line_height=14),
        text_block(615, 574, "2033 projected size", "axis", max_chars=18, line_height=14),
        text_block(188, 470, "$13.0B", "label", max_chars=10),
        text_block(668, 270, "$83.9B", "label", max_chars=10),
        text_block(365, 484, "23.2% CAGR", "value", max_chars=18, line_height=18),
        text_block(365, 510, "Global AI for customer service market, 2025-2033 forecast", "small", max_chars=50, line_height=15),
        text_block(365, 540, "Retail and e-commerce expected fastest end-use CAGR: 26.0%", "small", max_chars=52, line_height=15),
        text_block(365, 586, "Source: Grand View Research, 2025 report using 2024 base-year estimates", "small", max_chars=60, line_height=14),
    ])
    return wrap_svg("".join(body), width, height)


def build_competitor_matrix_svg() -> str:
    width, height = 980, 600
    body = [
        '<rect width="100%" height="100%" fill="#f8fbff"/>',
        text_block(40, 48, "Competitive Positioning Matrix", "title", max_chars=38),
        text_block(40, 72, "The project is differentiated by being both controllable and insight-oriented, not just a cheaper chatbot.", "subtitle", max_chars=100, line_height=15),
        '<rect x="40" y="105" width="900" height="410" rx="20" fill="#ffffff" stroke="#d9e3ec"/>',
    ]
    x_positions = [60, 250, 390, 540, 690, 820]
    headers = ["Solution Type", "Policy Control", "Reply Flexibility", "Review Analytics", "Setup Cost", "Best Fit"]
    for x, header in zip(x_positions, headers):
        body.append(text_block(x, 140, header, "label", max_chars=14, line_height=14))
    rows = [
        ("Human outsourcing", "High", "High", "Low", "High", "Complex escalations"),
        ("Rule-based bot", "High", "Low", "Low", "Medium", "Simple FAQs"),
        ("Generic LLM workflow", "Low", "High", "Medium", "Low", "Fast prototyping"),
        ("Integrated AI ops tool", "High", "High", "High", "Medium", "SMB e-commerce"),
    ]
    y = 190
    for idx, row in enumerate(rows):
        bg = "#f8fbff" if idx % 2 == 0 else "#eef4f9"
        body.append(f'<rect x="52" y="{y - 30}" width="876" height="64" rx="10" fill="{bg}"/>')
        first_class = "label" if idx == 3 else "small"
        first_fill = "#1565c0" if idx == 3 else "#6b7c93"
        body.append(text_block(x_positions[0], y, row[0], first_class, max_chars=18, line_height=15, fill=first_fill))
        for col in range(1, len(row)):
            body.append(text_block(x_positions[col], y, row[col], "small", max_chars=16, line_height=15, fill="#44576a"))
        y += 78
    body.append(text_block(60, 490, "Interpretation: our strongest wedge is the combination of policy control, reply flexibility, and review insight in one workflow.", "small", max_chars=100, line_height=15))
    body.append(text_block(60, 530, "That positioning is especially attractive for merchants who cannot afford enterprise CX suites but need more than a simple bot.", "small", max_chars=98, line_height=15))
    return wrap_svg("".join(body), width, height)


def build_growth_strategy_svg() -> str:
    width, height = 980, 580
    body = [
        '<rect width="100%" height="100%" fill="#fcfdff"/>',
        text_block(40, 48, "Pricing, Go-to-Market, and Scalability", "title", max_chars=44),
        text_block(40, 72, "A staged SaaS model reduces adoption friction and gives the team a clear expansion path.", "subtitle", max_chars=100, line_height=15),
        '<rect x="50" y="120" width="250" height="195" rx="18" fill="#eaf4ff" stroke="#d7e3f1"/>',
        text_block(68, 154, "Basic", "label", max_chars=12),
        text_block(68, 188, "RMB 199-399 / month", "value", max_chars=22),
        text_block(68, 228, "- Review upload and analysis", "small", max_chars=28, line_height=16),
        text_block(68, 264, "- Basic automated replies", "small", max_chars=28, line_height=16),
        text_block(68, 300, "- Single-store dashboard", "small", max_chars=28, line_height=16),
        '<rect x="365" y="120" width="250" height="195" rx="18" fill="#eef8ef" stroke="#d7e3f1"/>',
        text_block(383, 154, "Pro", "label", max_chars=12),
        text_block(383, 188, "RMB 699-1299 / month", "value", max_chars=22),
        text_block(383, 228, "- Higher monthly volume", "small", max_chars=28, line_height=16),
        text_block(383, 264, "- Knowledge base and retry workflow", "small", max_chars=28, line_height=16),
        text_block(383, 316, "- Exportable insight report", "small", max_chars=28, line_height=16),
        '<rect x="680" y="120" width="250" height="195" rx="18" fill="#fff4e8" stroke="#d7e3f1"/>',
        text_block(698, 154, "Enterprise", "label", max_chars=14),
        text_block(698, 188, "Custom quote", "value", max_chars=22),
        text_block(698, 228, "- Private deployment", "small", max_chars=28, line_height=16),
        text_block(698, 264, "- API integration", "small", max_chars=28, line_height=16),
        text_block(698, 300, "- Multi-brand governance", "small", max_chars=28, line_height=16),
        '<rect x="80" y="390" width="220" height="105" rx="16" fill="#ffffff" stroke="#cfdbe8"/>',
        text_block(96, 418, "Stage 1", "label", max_chars=12),
        text_block(96, 444, "Win with negative-review monitoring and after-sales response", "small", max_chars=28, line_height=15),
        '<rect x="340" y="390" width="220" height="105" rx="16" fill="#ffffff" stroke="#cfdbe8"/>',
        text_block(356, 418, "Stage 2", "label", max_chars=12),
        text_block(356, 444, "Upsell merchant rule base, dashboards, and monthly insight reports", "small", max_chars=28, line_height=15),
        '<rect x="600" y="390" width="220" height="105" rx="16" fill="#ffffff" stroke="#cfdbe8"/>',
        text_block(616, 418, "Stage 3", "label", max_chars=12),
        text_block(616, 444, "Expand to APIs, multi-store workflows, and adjacent service verticals", "small", max_chars=28, line_height=15),
        '<line x1="300" y1="442" x2="340" y2="442" stroke="#90a4ae" stroke-width="2"/>',
        '<line x1="560" y1="442" x2="600" y2="442" stroke="#90a4ae" stroke-width="2"/>',
    ]
    return wrap_svg("".join(body), width, height)


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    write_text(ASSETS_DIR / "value_proposition.svg", build_value_prop_svg())
    write_text(ASSETS_DIR / "market_drivers.svg", build_market_drivers_svg())
    write_text(ASSETS_DIR / "competitor_matrix.svg", build_competitor_matrix_svg())
    write_text(ASSETS_DIR / "growth_strategy.svg", build_growth_strategy_svg())
    print("Generated business report assets.")


if __name__ == "__main__":
    main()
