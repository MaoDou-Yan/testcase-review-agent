"""Write a styled .xlsx workbook from JSON without third-party dependencies.

Input JSON shape:
{
  "sheets": [
    {"name": "优化后用例集", "columns": ["用例编号"], "rows": [{"用例编号": "A-001"}]}
  ]
}
Rows may be dictionaries keyed by column name or lists matching column order.

Enhancements over v1:
- Header row: bold font + light-blue background fill.
- Priority column auto-coloring: P0=red, P1=orange, P2=yellow, P3=default.
- Auto column width: estimated from max content length per column (capped at 60).
- All other columns use wrap-text style for readability.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def col_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def clean_sheet_name(name: str, fallback: str) -> str:
    cleaned = re.sub(r"[\[\]\:\*\?\/\\]", "_", name or fallback).strip()
    return (cleaned or fallback)[:31]


def estimate_col_width(values: list[str]) -> int:
    """Estimate column width in Excel units based on max content length."""
    max_len = max((len(str(v)) for v in values), default=8)
    # Chinese chars are ~2x wide; rough heuristic: cap at 60
    return min(max(max_len * 1.2, 8), 60)


# ---------------------------------------------------------------------------
# Style index constants (must match styles.xml below)
# ---------------------------------------------------------------------------
# xf index in cellXfs:
# 0 = default (normal cell)
# 1 = header (bold, blue fill, border, wrap)
# 2 = normal wrap (border, wrap)
# 3 = P0 cell (red fill, wrap)
# 4 = P1 cell (orange fill, wrap)
# 5 = P2 cell (yellow fill, wrap)

STYLE_DEFAULT   = 0
STYLE_HEADER    = 1
STYLE_WRAP      = 2
STYLE_P0        = 3
STYLE_P1        = 4
STYLE_P2        = 5

PRIORITY_STYLES = {
    "P0": STYLE_P0,
    "P1": STYLE_P1,
    "P2": STYLE_P2,
}

PRIORITY_COL_NAMES = {"用例优先级", "优先级", "priority"}


def cell_xml(value: Any, row_idx: int, col_idx: int, style_idx: int = STYLE_WRAP) -> str:
    ref = f"{col_name(col_idx)}{row_idx}"
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return (
        f'<c r="{ref}" t="inlineStr" s="{style_idx}">'
        f'<is><t xml:space="preserve">{escape(text)}</t></is></c>'
    )


def sheet_xml(columns: list[str], rows: list[Any], priority_cols: set[str] | None = None) -> tuple[str, list[int]]:
    """Return (sheet XML string, list of estimated col widths)."""
    # Determine which column indices are priority columns
    pcols = priority_cols if priority_cols is not None else PRIORITY_COL_NAMES
    priority_col_indices = {
        i for i, c in enumerate(columns) if c in pcols
    }

    xml_rows = []

    # --- header row ---
    header_cells = "".join(
        cell_xml(col, 1, idx, STYLE_HEADER) for idx, col in enumerate(columns)
    )
    xml_rows.append(f'<row r="1">{header_cells}</row>')

    # --- data rows ---
    for r_idx, row in enumerate(rows, start=2):
        if isinstance(row, dict):
            values = [row.get(col, "") for col in columns]
        else:
            values = list(row)

        cells = []
        for c_idx, value in enumerate(values):
            if c_idx in priority_col_indices:
                val_str = str(value).strip().upper() if value is not None else ""
                style = PRIORITY_STYLES.get(val_str, STYLE_WRAP)
            else:
                style = STYLE_WRAP
            cells.append(cell_xml(value, r_idx, c_idx, style))
        xml_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')

    # --- dimension ---
    last_col = col_name(max(len(columns) - 1, 0))
    last_row = max(len(rows) + 1, 1)
    dimension = f"A1:{last_col}{last_row}" if columns else "A1"

    # --- estimate column widths ---
    col_widths: list[int] = []
    for c_idx, col in enumerate(columns):
        col_values = [col]
        for row in rows:
            if isinstance(row, dict):
                col_values.append(str(row.get(col, "")))
            else:
                col_values.append(str(row[c_idx]) if c_idx < len(row) else "")
        col_widths.append(int(estimate_col_width(col_values)))

    # --- cols element for widths ---
    col_elements = "".join(
        f'<col min="{i+1}" max="{i+1}" width="{w}" bestFit="1" customWidth="1"/>'
        for i, w in enumerate(col_widths)
    )

    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0" showGridLines="1"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15" customHeight="1"/>'
        f'<cols>{col_elements}</cols>'
        f'<sheetData>{"".join(xml_rows)}</sheetData>'
        '</worksheet>'
    )
    return xml, col_widths


def build_styles_xml() -> str:
    """Return a styles.xml with header, wrap, and priority fill styles."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'

        # fonts: 0=normal, 1=bold (header)
        '<fonts count="2">'
        '<font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font>'
        '</fonts>'

        # fills: 0=none, 1=gray(reserved), 2=header-blue, 3=P0-red, 4=P1-orange, 5=P2-yellow
        '<fills count="6">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFD6E4F0"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFFFC7CE"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFFFEB9C"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFFFFFCC"/></patternFill></fill>'
        '</fills>'

        # borders: 0=none, 1=thin-all
        '<borders count="2">'
        '<border/>'
        '<border>'
        '<left style="thin"><color rgb="FFD9DEE8"/></left>'
        '<right style="thin"><color rgb="FFD9DEE8"/></right>'
        '<top style="thin"><color rgb="FFD9DEE8"/></top>'
        '<bottom style="thin"><color rgb="FFD9DEE8"/></bottom>'
        '</border>'
        '</borders>'

        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'

        # cellXfs: 0=default, 1=header, 2=wrap, 3=P0, 4=P1, 5=P2
        '<cellXfs count="6">'
        # 0 default
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        # 1 header: bold font, blue fill, border, wrap
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">'
        '<alignment wrapText="1" vertical="center"/></xf>'
        # 2 normal wrap: border, wrap
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1">'
        '<alignment wrapText="1" vertical="top"/></xf>'
        # 3 P0 red fill + wrap
        '<xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1">'
        '<alignment wrapText="1" vertical="top"/></xf>'
        # 4 P1 orange fill + wrap
        '<xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1">'
        '<alignment wrapText="1" vertical="top"/></xf>'
        # 5 P2 yellow fill + wrap
        '<xf numFmtId="0" fontId="0" fillId="5" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1">'
        '<alignment wrapText="1" vertical="top"/></xf>'
        '</cellXfs>'

        '</styleSheet>'
    )


# ---------------------------------------------------------------------------
# Main writer
# ---------------------------------------------------------------------------

def write_xlsx(payload: dict[str, Any], output: Path, template_context: dict[str, Any] | None = None) -> None:
    sheets = payload.get("sheets") or []
    if not sheets:
        raise ValueError("JSON must contain at least one sheet")

    # Build dynamic priority column set from template context
    extra_priority_cols: set[str] = set()
    if template_context:
        for sheet_ctx in template_context.get("sheets", []):
            for col_name, field in sheet_ctx.get("column_mapping", {}).items():
                if field == "priority":
                    extra_priority_cols.add(col_name)
    all_priority_cols = PRIORITY_COL_NAMES | extra_priority_cols

    normalized = []
    used: set[str] = set()
    for idx, sheet in enumerate(sheets, start=1):
        name = clean_sheet_name(str(sheet.get("name", "")), f"Sheet{idx}")
        base = name
        suffix = 1
        while name in used:
            suffix += 1
            name = clean_sheet_name(f"{base}_{suffix}", f"Sheet{idx}")
        used.add(name)
        normalized.append(
            {
                "name": name,
                "columns": [str(c) for c in sheet.get("columns", [])],
                "rows": sheet.get("rows", []),
            }
        )

    workbook_sheets = []
    workbook_rels = []
    content_overrides = [
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    for idx, sheet in enumerate(normalized, start=1):
        workbook_sheets.append(f'<sheet name="{escape(sheet["name"])}" sheetId="{idx}" r:id="rId{idx}"/>')
        workbook_rels.append(
            f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>'
        )
        content_overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )

    workbook_rels.append(
        f'<Relationship Id="rId{len(normalized) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'{"".join(content_overrides)}</Types>',
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets>{"".join(workbook_sheets)}</sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'{"".join(workbook_rels)}</Relationships>',
        )
        z.writestr("xl/styles.xml", build_styles_xml())

        for idx, sheet in enumerate(normalized, start=1):
            xml, _ = sheet_xml(sheet["columns"], sheet["rows"], all_priority_cols)
            z.writestr(f"xl/worksheets/sheet{idx}.xml", xml)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json", type=Path)
    parser.add_argument("output_xlsx", type=Path)
    parser.add_argument("--template", type=Path, default=None,
                        help="Template context JSON for dynamic column mapping")
    args = parser.parse_args()
    template_ctx = None
    if args.template and args.template.exists():
        template_ctx = json.loads(args.template.read_text(encoding="utf-8"))
    write_xlsx(json.loads(args.input_json.read_text(encoding="utf-8")), args.output_xlsx, template_ctx)


if __name__ == "__main__":
    main()
