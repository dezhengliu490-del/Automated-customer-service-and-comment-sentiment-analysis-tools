from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "report"

TITLE_COLOR = RGBColor(31, 78, 121)
HEADING_COLOR = RGBColor(44, 62, 80)
ACCENT_COLOR = RGBColor(39, 73, 109)
CAPTION_COLOR = RGBColor(90, 90, 90)
BODY_COLOR = RGBColor(33, 33, 33)


def set_run_font(run, *, latin: str, east_asia: str, size: Pt | None = None, bold: bool | None = None, color: RGBColor | None = None) -> None:
    run.font.name = latin
    run._element.rPr.rFonts.set(qn("w:eastAsia"), east_asia)
    if size is not None:
        run.font.size = size
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def set_paragraph_background(paragraph, fill: str) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    shd = ppr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        ppr.append(shd)
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)


def format_runs(paragraph, *, latin: str, east_asia: str, size: Pt, bold: bool | None = None, color: RGBColor | None = None) -> None:
    for run in paragraph.runs:
        set_run_font(run, latin=latin, east_asia=east_asia, size=size, bold=bold, color=color)


def is_main_heading(text: str) -> bool:
    return bool(re.match(r"^[一二三四五六七八九十]+、", text) or re.match(r"^\d+\.\s", text))


def is_figure_heading(text: str) -> bool:
    return text.startswith("图 ") or text.startswith("Figure ")


def is_metric_line(text: str) -> bool:
    metric_keys = ["样本量", "准确率", "置信度", "Raw review sample size", "Overall sentiment accuracy", "Average model confidence", "Covered categories", "Gold test set size"]
    return any(key in text for key in metric_keys) and "|" in text or text.startswith("模型平均置信度") or text.startswith("Average model confidence")


def is_figure_note(text: str) -> bool:
    prefixes = ["该图", "该分布", "高频痛点", "This chart", "The evaluation distribution", "The concentration of quality-related"]
    return any(text.startswith(prefix) for prefix in prefixes)


def apply_document_defaults(document: Document) -> None:
    for section in document.sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(2.6)
        section.right_margin = Cm(2.6)


def format_document(doc_path: Path, *, latin: str, east_asia: str) -> None:
    document = Document(doc_path)
    apply_document_defaults(document)

    for index, paragraph in enumerate(document.paragraphs):
        text = paragraph.text.strip()
        if index == 0:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_before = Pt(6)
            paragraph.paragraph_format.space_after = Pt(18)
            paragraph.paragraph_format.line_spacing = 1.2
            format_runs(paragraph, latin=latin, east_asia=east_asia, size=Pt(18), bold=True, color=TITLE_COLOR)
        elif is_figure_heading(text):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_before = Pt(10)
            paragraph.paragraph_format.space_after = Pt(6)
            paragraph.paragraph_format.line_spacing = 1.15
            format_runs(paragraph, latin=latin, east_asia=east_asia, size=Pt(11), bold=True, color=HEADING_COLOR)
        elif is_main_heading(text):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.space_before = Pt(12)
            paragraph.paragraph_format.space_after = Pt(6)
            paragraph.paragraph_format.line_spacing = 1.2
            format_runs(paragraph, latin=latin, east_asia=east_asia, size=Pt(13), bold=True, color=HEADING_COLOR)
        elif is_figure_note(text):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent = Cm(0)
            paragraph.paragraph_format.space_after = Pt(12)
            paragraph.paragraph_format.line_spacing = 1.2
            format_runs(paragraph, latin=latin, east_asia=east_asia, size=Pt(10), color=CAPTION_COLOR)
        elif not text and paragraph.runs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_after = Pt(4)
            paragraph.paragraph_format.line_spacing = 1.0
        elif is_metric_line(text):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent = Cm(0)
            paragraph.paragraph_format.space_before = Pt(2)
            paragraph.paragraph_format.space_after = Pt(4)
            paragraph.paragraph_format.line_spacing = 1.15
            format_runs(paragraph, latin=latin, east_asia=east_asia, size=Pt(11), bold=True, color=ACCENT_COLOR)
            set_paragraph_background(paragraph, "EEF4FB")
        else:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            paragraph.paragraph_format.first_line_indent = Cm(0.74)
            paragraph.paragraph_format.space_after = Pt(8)
            paragraph.paragraph_format.line_spacing = 1.5
            format_runs(paragraph, latin=latin, east_asia=east_asia, size=Pt(11), color=BODY_COLOR)

    document.save(doc_path)


def main() -> None:
    for doc_name, east_asia in [
        ("business_insight_report_cn_market.docx", "宋体"),
        ("business_insight_report_en_market.docx", "Times New Roman"),
    ]:
        path = REPORT_DIR / doc_name
        if path.exists():
            format_document(path, latin="Times New Roman", east_asia=east_asia)
    print("Formatted market report documents.")


if __name__ == "__main__":
    main()
