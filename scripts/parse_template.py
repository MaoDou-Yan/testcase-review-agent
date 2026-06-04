"""Parse a template Excel (.xlsx) file to extract column structure, sample data,
and semantic column mapping for test case generation.

Pure Python implementation — no third-party dependencies (uses zipfile + xml.etree).

Usage:
    python scripts/parse_template.py <template.xlsx> [output.json] [--samples N]

Output: template-context.json with column metadata and sample rows.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile

# Shared strings namespace
NS_SS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

# ---------------------------------------------------------------------------
# Semantic column mapping — synonyms for internal field names
# ---------------------------------------------------------------------------

FIELD_SYNONYMS: dict[str, list[str]] = {
    "id":           ["用例编号", "编号", "ID", "用例ID", "Case ID", "测试编号", "用例编号 ", "caseid", "case_id"],
    "level1":       ["一级模块", "模块", "一级分类", "Module", "所属模块", "功能模块", "一级功能"],
    "level2":       ["二级模块", "子模块", "二级分类", "Sub Module", "二级功能", "子功能"],
    "feature":      ["功能点", "功能", "Feature", "功能名称", "测试功能"],
    "title":        ["用例标题", "标题", "用例名称", "Title", "Test Case", "测试标题", "用例描述"],
    "precondition": ["前置条件", "前提条件", "Precondition", "前置", "前提"],
    "steps":        ["用例步骤", "步骤", "测试步骤", "Steps", "操作步骤", "测试过程", "执行步骤"],
    "expected":     ["预期结果", "预期", "Expected", "期望结果", "预期输出", "期望结果"],
    "priority":     ["用例优先级", "优先级", "Priority", "等级", "重要程度", "优先级 "],
    "category":     ["分类", "用例类型", "Category", "测试类型", "用例分类", "case_type"],
}

# Fuzzy keywords for second-pass matching
FUZZY_KEYWORDS: dict[str, list[str]] = {
    "id":           ["编号", "ID", "id"],
    "level1":       ["模块", "module", "一级"],
    "level2":       ["子模块", "二级", "sub"],
    "feature":      ["功能", "feature"],
    "title":        ["标题", "名称", "title", "用例"],
    "precondition": ["前置", "前提", "precondition"],
    "steps":        ["步骤", "step", "操作", "过程"],
    "expected":     ["预期", "期望", "expected", "结果"],
    "priority":     ["优先级", "priority", "等级", "重要"],
    "category":     ["分类", "类型", "category", "type"],
}


# ---------------------------------------------------------------------------
# xlsx reading helpers
# ---------------------------------------------------------------------------

def _parse_shared_strings(zf: ZipFile) -> list[str]:
    """Read shared strings table from xlsx."""
    try:
        tree = ET.parse(zf.open("xl/sharedStrings.xml"))
    except KeyError:
        return []
    strings = []
    for si in tree.iter(f"{{{NS_SS}}}si"):
        parts = []
        for t in si.iter(f"{{{NS_SS}}}t"):
            if t.text:
                parts.append(t.text)
        strings.append("".join(parts))
    return strings


def _parse_sheet_names(zf: ZipFile) -> list[str]:
    """Get sheet names from workbook.xml."""
    tree = ET.parse(zf.open("xl/workbook.xml"))
    names = []
    for sheet in tree.iter(f"{{{NS_SS}}}sheet"):
        name = sheet.get("name", "")
        if name:
            names.append(name)
    return names


def _col_index(ref: str) -> int:
    """Convert column letter (e.g., 'A', 'AB') to 0-based index."""
    col_str = re.match(r"^([A-Z]+)", ref)
    if not col_str:
        return 0
    result = 0
    for ch in col_str.group(1):
        result = result * 26 + (ord(ch) - 64)
    return result - 1


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    """Extract the display value from a cell element."""
    cell_type = cell.get("t", "")
    # Check for inline string
    is_elem = cell.find(f"{{{NS_SS}}}is")
    if is_elem is not None:
        t_elem = is_elem.find(f"{{{NS_SS}}}t")
        return t_elem.text if t_elem is not None and t_elem.text else ""
    # Check for value
    v_elem = cell.find(f"{{{NS_SS}}}v")
    if v_elem is None or v_elem.text is None:
        return ""
    if cell_type == "s":
        # Shared string reference
        try:
            return shared_strings[int(v_elem.text)]
        except (IndexError, ValueError):
            return v_elem.text
    return v_elem.text


def _read_sheet_data(zf: ZipFile, sheet_index: int, shared_strings: list[str]) -> list[list[str]]:
    """Read all rows from a specific sheet. Returns list of rows, each row is list of cell values."""
    sheet_path = f"xl/worksheets/sheet{sheet_index}.xml"
    try:
        tree = ET.parse(zf.open(sheet_path))
    except KeyError:
        return []
    rows_data: list[list[str]] = []
    for row_elem in tree.iter(f"{{{NS_SS}}}row"):
        row_cells: dict[int, str] = {}
        for cell in row_elem.iter(f"{{{NS_SS}}}c"):
            ref = cell.get("r", "A1")
            col_idx = _col_index(ref)
            row_cells[col_idx] = _cell_value(cell, shared_strings)
        if row_cells:
            max_col = max(row_cells.keys()) + 1
            row = [row_cells.get(i, "") for i in range(max_col)]
            rows_data.append(row)
    return rows_data


# ---------------------------------------------------------------------------
# Semantic analysis
# ---------------------------------------------------------------------------

def _map_column(col_name: str) -> str | None:
    """Map a template column name to an internal field name using synonyms."""
    col_lower = col_name.strip().lower()
    # Pass 1: exact match
    for field, synonyms in FIELD_SYNONYMS.items():
        if col_name.strip() in synonyms:
            return field
        for syn in synonyms:
            if col_lower == syn.lower():
                return field
    # Pass 2: fuzzy match (column name contains keyword)
    for field, keywords in FUZZY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in col_lower:
                return field
    return None


def _detect_id_pattern(values: list[str]) -> str:
    """Analyze ID column values to detect naming pattern."""
    patterns: dict[str, int] = {}
    for v in values:
        v = v.strip()
        if not v:
            continue
        # XX-NNN or XX-XX-NNN
        m = re.match(r"^([A-Za-z]+(?:-[A-Za-z]+)*)-\d+$", v)
        if m:
            parts = m.group(1).split("-")
            pattern = "-".join(["XX"] * len(parts)) + "-NNN"
            patterns[pattern] = patterns.get(pattern, 0) + 1
        # Pure number
        elif re.match(r"^\d+$", v):
            patterns["NNN"] = patterns.get("NNN", 0) + 1
    if not patterns:
        return "XX-NNN"
    return max(patterns, key=patterns.get)  # type: ignore


def _detect_priority_values(values: list[str]) -> list[str]:
    """Detect unique priority values from the priority column."""
    unique = sorted(set(v.strip() for v in values if v.strip()))
    return unique if unique else ["P0", "P1", "P2", "P3"]


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_template(xlsx_path: Path, max_samples: int = 5) -> dict[str, Any]:
    """Parse a template xlsx file and return structured metadata."""
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Template file not found: {xlsx_path}")

    with ZipFile(xlsx_path, "r") as zf:
        shared_strings = _parse_shared_strings(zf)
        sheet_names = _parse_sheet_names(zf)

        sheets_result: list[dict[str, Any]] = []

        for idx, sheet_name in enumerate(sheet_names, start=1):
            all_rows = _read_sheet_data(zf, idx, shared_strings)
            if not all_rows:
                continue

            # First row = headers
            headers = [h.strip() for h in all_rows[0]]
            data_rows = all_rows[1:]

            # Column mapping
            column_mapping: dict[str, str] = {}
            extra_columns: list[str] = []
            for col in headers:
                mapped = _map_column(col)
                if mapped:
                    column_mapping[col] = mapped
                else:
                    extra_columns.append(col)

            # Sample rows (dict format)
            sample_rows: list[dict[str, str]] = []
            for row in data_rows[:max_samples]:
                row_dict: dict[str, str] = {}
                for i, val in enumerate(row):
                    if i < len(headers):
                        row_dict[headers[i]] = val
                sample_rows.append(row_dict)

            # Detect ID pattern
            id_pattern = "XX-NNN"
            for col, field in column_mapping.items():
                if field == "id":
                    col_idx = headers.index(col)
                    id_values = [row[col_idx] for row in data_rows if col_idx < len(row)]
                    id_pattern = _detect_id_pattern(id_values)
                    break

            # Detect priority values
            priority_values: list[str] = ["P0", "P1", "P2", "P3"]
            for col, field in column_mapping.items():
                if field == "priority":
                    col_idx = headers.index(col)
                    p_values = [row[col_idx] for row in data_rows if col_idx < len(row)]
                    priority_values = _detect_priority_values(p_values)
                    break

            sheets_result.append({
                "name": sheet_name,
                "columns": headers,
                "column_mapping": column_mapping,
                "extra_columns": extra_columns,
                "sample_rows": sample_rows,
                "total_rows": len(data_rows),
                "id_pattern": id_pattern,
                "priority_values": priority_values,
            })

    return {
        "template_file": xlsx_path.name,
        "sheets": sheets_result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse template Excel file for test case generation")
    parser.add_argument("template", type=Path, help="Template .xlsx file path")
    parser.add_argument("output", type=Path, nargs="?", default=Path("output/template-context.json"),
                        help="Output JSON path (default: output/template-context.json)")
    parser.add_argument("--samples", type=int, default=5, help="Number of sample rows to extract (default: 5)")
    args = parser.parse_args()

    result = parse_template(args.template, max_samples=args.samples)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # Print summary
    for sheet in result["sheets"]:
        mapped = len(sheet["column_mapping"])
        extra = len(sheet["extra_columns"])
        print(f"Sheet '{sheet['name']}': {len(sheet['columns'])} columns "
              f"({mapped} mapped, {extra} extra), {sheet['total_rows']} data rows")
        if sheet["extra_columns"]:
            print(f"  Extra columns: {', '.join(sheet['extra_columns'])}")
        print(f"  ID pattern: {sheet['id_pattern']}")
        print(f"  Priority values: {sheet['priority_values']}")

    print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
