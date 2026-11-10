#!/usr/bin/env python3
"""Typeset the v0.2 Markdown source, avoiding a second hand-maintained paper."""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image, KeepTogether, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/research/papers/unigram_undersegments_chichewa_v0_2.md"
OUTPUT = SOURCE.with_suffix(".pdf")
FIGURES = (ROOT / "data/reports/figures/paper_v0_2").resolve()
FONTS = Path("/usr/share/fonts/truetype/dejavu")
TOKEN = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))")


def inline(text: str) -> str:
    parts = []
    for part in TOKEN.split(text):
        if part.startswith("`") and part.endswith("`"):
            parts.append('<font name="PubMono">' + html.escape(part[1:-1]) + '</font>')
        elif part.startswith("**") and part.endswith("**"):
            parts.append("<b>" + html.escape(part[2:-2]) + "</b>")
        else:
            link = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", part)
            if link:
                label, url = link.groups()
                if url.startswith("https://"):
                    parts.append('<link href="' + html.escape(url, quote=True) + '" color="#125d85">' + html.escape(label) + '</link>')
                else:
                    parts.append(html.escape(label))
            else:
                parts.append(html.escape(part))
    return "".join(parts)


def styles() -> dict:
    for name, file in [
        ("PubSerif", "DejaVuSerif.ttf"), ("PubSerifBold", "DejaVuSerif-Bold.ttf"),
        ("PubSans", "DejaVuSans.ttf"), ("PubSansBold", "DejaVuSans-Bold.ttf"),
        ("PubMono", "DejaVuSansMono.ttf"),
    ]:
        pdfmetrics.registerFont(TTFont(name, str(FONTS / file)))
    pdfmetrics.registerFontFamily("PubSerif", normal="PubSerif", bold="PubSerifBold", italic="PubSerif", boldItalic="PubSerifBold")
    pdfmetrics.registerFontFamily("PubSans", normal="PubSans", bold="PubSansBold", italic="PubSans", boldItalic="PubSansBold")
    body = ParagraphStyle("Body", fontName="PubSerif", fontSize=9.3, leading=12.1, spaceAfter=6, alignment=TA_JUSTIFY)
    return {
        "body": body,
        "title": ParagraphStyle("Title", parent=body, fontName="PubSerifBold", fontSize=15, leading=18, alignment=TA_CENTER, spaceAfter=10),
        "meta": ParagraphStyle("Meta", parent=body, fontName="PubSans", fontSize=8.5, leading=11.3, alignment=TA_CENTER, spaceAfter=7),
        "h1": ParagraphStyle("Heading1", parent=body, fontName="PubSerifBold", fontSize=11.2, leading=14, spaceBefore=9, spaceAfter=5, keepWithNext=True),
        "h2": ParagraphStyle("Heading2", parent=body, fontName="PubSerifBold", fontSize=9.8, leading=13, spaceBefore=7, spaceAfter=4, keepWithNext=True),
        "caption": ParagraphStyle("Caption", parent=body, fontSize=8.2, leading=10.6, spaceBefore=4, spaceAfter=8, alignment=0),
        "table_caption": ParagraphStyle("TableCaption", parent=body, fontSize=8.4, leading=11, spaceAfter=4, keepWithNext=True),
        "cell": ParagraphStyle("Cell", parent=body, fontName="PubSans", fontSize=8.0, leading=10.4, alignment=0, spaceAfter=0),
        "ref": ParagraphStyle("Reference", parent=body, fontSize=8.1, leading=10.5, leftIndent=10, firstLineIndent=-10, alignment=0, spaceAfter=5),
        "code": ParagraphStyle("Code", fontName="PubMono", fontSize=7.4, leading=10, spaceAfter=8),
    }


def parse_markdown(text: str, s: dict, width: float) -> list:
    lines = text.splitlines()
    flow = []
    i = 0
    in_refs = False
    body_started = False
    while i < len(lines):
        line = lines[i].strip()
        if not line or line == "---":
            i += 1
            continue
        heading = re.match(r"^(#{1,3}) (.*)$", line)
        if heading:
            level, title = heading.groups()
            if len(level) == 1:
                style = s["title"]
            else:
                body_started = True
                in_refs = title == "References"
                style = s["h1" if len(level) == 2 else "h2"]
            flow.append(Paragraph(inline(title), style))
            i += 1
            continue
        image = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if image:
            path = (SOURCE.parent / image.group(2)).resolve()
            if path.parent != FIGURES or path.suffix != ".png":
                raise ValueError("PDF image outside the versioned publication figure directory")
            from reportlab.lib.utils import ImageReader
            w, h = ImageReader(str(path)).getSize()
            display_width = width * .89
            img = Image(str(path), width=display_width, height=display_width * h / w)
            img.hAlign = "CENTER"
            block = [Spacer(1, 4), img]
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines) and lines[i].startswith("**Figure"):
                block.append(Paragraph(inline(lines[i]), s["caption"]))
                i += 1
            flow.append(KeepTogether(block))
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append([Paragraph(inline(c), s["cell"]) for c in cells])
                i += 1
            n = len(rows[0])
            first = .30 if n >= 5 else .34
            widths = [width * first] + [width * (1-first) / (n-1)] * (n-1)
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign="CENTER")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e9f0f4")),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
                ("LINEBELOW", (0,0), (-1,0), .6, colors.HexColor("#607080")),
                ("LINEBELOW", (0,-1), (-1,-1), .4, colors.HexColor("#b6bdc5")),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("TOPPADDING", (0,0), (-1,-1), 5),
                ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                ("LEFTPADDING", (0,0), (-1,-1), 5),
                ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ]))
            flow.extend([table, Spacer(1, 7)])
            continue
        if line.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            flow.append(Preformatted("\n".join(code), s["code"]))
            i += 1
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip():
            if lines[i].startswith(("#", "|", "![", "```")):
                break
            paragraph.append(lines[i].strip())
            i += 1
        text = " ".join(paragraph)
        style = s["meta"] if not body_started else s["ref"] if in_refs else s["table_caption"] if text.startswith("**Table") else s["body"]
        flow.append(Paragraph(inline(text), style))
    return flow


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("PubSans", 7)
    canvas.setFillColor(colors.HexColor("#555b63"))
    canvas.drawString(doc.leftMargin, 10*mm, "Mthandizi · working draft v0.2 · development/validation evidence")
    canvas.drawRightString(A4[0]-doc.rightMargin, 10*mm, str(doc.page))
    canvas.restoreState()


def main() -> int:
    s = styles()
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=15*mm, bottomMargin=17*mm,
                            title="Unigram Undersegments Chichewa", author="Hyston Kayange")
    def canvasmaker(*args, **kwargs):
        kwargs["invariant"] = 1
        return Canvas(*args, **kwargs)
    doc.build(parse_markdown(SOURCE.read_text(), s, doc.width), onFirstPage=footer, onLaterPages=footer, canvasmaker=canvasmaker)
    print(OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
