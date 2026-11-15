#!/usr/bin/env python3
"""Render the model-readiness Markdown and its charts as an editable DOCX."""
from __future__ import annotations

from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "analysis" / "docs" / "MTS_Model_Readiness_Summary.md"
TARGET = SOURCE.with_suffix(".docx")
INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\[[^]]+\]\([^)]+\))")
IMAGE = re.compile(r"!\[([^]]*)\]\(([^)]+)\)")


def add_inline(paragraph, value: str) -> None:
    for part in INLINE.split(value):
        if part.startswith("**") and part.endswith("**"):
            paragraph.add_run(part[2:-2]).bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(8)
        elif part.startswith("[") and "](" in part:
            paragraph.add_run(part[1:part.index("](")])
        elif part:
            paragraph.add_run(part)


def render() -> Path:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Inches(.65)
    section.left_margin = section.right_margin = Inches(.7)
    style = doc.styles["Normal"]
    style.font.name = "Aptos"
    style.font.size = Pt(9)
    style.paragraph_format.space_after = Pt(5)
    doc.core_properties.title = "MTS Gold Forecasting: Dataset and Model Readiness"
    doc.core_properties.subject = "MTS gold training data, return distributions and first-model design"
    lines = SOURCE.read_text().splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if match := IMAGE.fullmatch(line):
            image = (SOURCE.parent / match.group(2)).resolve()
            paragraph = doc.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.add_run().add_picture(str(image), width=Inches(6.8))
            caption = doc.add_paragraph(match.group(1))
            caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
            index += 1
            continue
        if line.startswith("| "):
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[:\- ]+", cell) for cell in cells):
                    rows.append(cells)
                index += 1
            table = doc.add_table(rows=0, cols=len(rows[0]))
            table.style = "Light Shading Accent 1"
            for values in rows:
                cells = table.add_row().cells
                for cell, value in zip(cells, values):
                    paragraph = cell.paragraphs[0]
                    add_inline(paragraph, value)
                    for run in paragraph.runs:
                        run.font.size = Pt(7.5)
            doc.add_paragraph()
            continue
        if line.startswith("# "):
            doc.add_heading(line[2:], 0)
        elif line.startswith("## "):
            doc.add_heading(line[3:], 1)
        elif re.match(r"^\d+\. ", line):
            paragraph = doc.add_paragraph(style="List Number")
            add_inline(paragraph, re.sub(r"^\d+\. ", "", line))
        else:
            paragraph = doc.add_paragraph()
            add_inline(paragraph, line.removesuffix("  "))
        index += 1
    doc.save(TARGET)
    return TARGET


if __name__ == "__main__":
    print(render())
