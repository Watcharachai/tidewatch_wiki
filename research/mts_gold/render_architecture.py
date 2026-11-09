"""Render the editable architecture Markdown as a DOCX (requires python-docx)."""

from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "analysis" / "docs" / "Gold_Price_Predictive_Model_Architecture.md"
TARGET = ROOT / "analysis" / "docs" / "Gold_Price_Predictive_Model_Architecture.docx"


def main() -> None:
    document = Document()
    section = document.sections[0]
    section.top_margin = section.bottom_margin = Inches(0.75)
    section.left_margin = section.right_margin = Inches(0.85)
    document.styles["Normal"].font.name = "Aptos"
    document.styles["Normal"].font.size = Pt(9.5)
    document.styles["Normal"].paragraph_format.space_after = Pt(5)
    for line in SOURCE.read_text().splitlines():
        if not line.strip():
            continue
        if line.startswith("# "):
            document.add_heading(line[2:], 0)
        elif line.startswith("## "):
            document.add_heading(line[3:], 1)
        elif line.startswith("- "):
            document.add_paragraph(line[2:], style="List Bullet")
        elif line[0].isdigit() and ". " in line[:4]:
            document.add_paragraph(line.split(". ", 1)[1], style="List Number")
        elif line.startswith("`") and line.endswith("`"):
            paragraph = document.add_paragraph()
            run = paragraph.add_run(line[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(8.5)
        else:
            document.add_paragraph(line)
    document.core_properties.title = "MTS Gold Price and Return Forecast Architecture"
    document.core_properties.subject = "Quantitative, JEV and forecast-fusion MDP research specification"
    document.save(TARGET)
    print(TARGET)


if __name__ == "__main__":
    main()
