"""Build HTML report from report-data.json and template."""
import json
from pathlib import Path
from typing import Any

# Deduction rules for auto-scoring
DEDUCTION_RULES = {
    ("逻辑遗漏", "P0"): 8,
    ("逻辑遗漏", "P1"): 8,
    ("场景遗漏", "P0"): 8,
    ("场景遗漏", "P1"): 8,
    ("安全漏洞", "P0"): 6,
    ("安全漏洞", "P1"): 6,
    ("数据一致性风险", "P0"): 6,
    ("数据一致性风险", "P1"): 6,
    ("数据完整性风险", "P0"): 6,
    ("数据完整性风险", "P1"): 6,
    ("性能风险", "P0"): 6,
    ("性能风险", "P1"): 6,
    ("边界遗漏", "P0"): 6,
    ("边界遗漏", "P1"): 6,
    ("可验证性不足", "P0"): 4,
    ("可验证性不足", "P1"): 4,
    ("可验证性不足", "P2"): 4,
    ("运维盲区", "P0"): 4,
    ("运维盲区", "P1"): 4,
    ("运维盲区", "P2"): 4,
    ("架构腐化风险", "P0"): 4,
    ("架构腐化风险", "P1"): 4,
    ("架构腐化风险", "P2"): 4,
    ("表述不清", "P0"): 2,
    ("表述不清", "P1"): 2,
    ("表述不清", "P2"): 2,
    ("优先级不准", "P0"): 2,
    ("优先级不准", "P1"): 2,
    ("优先级不准", "P2"): 2,
    ("易用性缺陷", "P0"): 2,
    ("易用性缺陷", "P1"): 2,
    ("易用性缺陷", "P2"): 2,
    ("交互不符", "P0"): 3,
    ("交互不符", "P1"): 3,
    ("交互不符", "P2"): 3,
}

ROLES = ["Arch", "Dev", "QA", "PM", "UX", "Sec", "Ops", "Perf", "DBA"]

ROLE_NAMES = {
    "Arch": "开发架构师",
    "Dev": "开发工程师",
    "QA": "测试工程师",
    "PM": "产品经理",
    "UX": "用户体验设计师",
    "Sec": "安全工程师",
    "Ops": "运维工程师",
    "Perf": "性能工程师",
    "DBA": "数据工程师",
}


def compute_role_scores(findings: list[dict], raw_cases: list[dict]) -> dict:
    """Compute role scores from review findings and raw cases."""
    case_priority_map = {c["id"]: c.get("priority", "P2") for c in raw_cases}
    scores = {role: 100 for role in ROLES}
    breakdown = {role: [] for role in ROLES}

    for f in findings:
        role = f.get("role")
        if role not in scores:
            continue
        case_id = f.get("case_id", "")
        priority = case_priority_map.get(case_id, "P2")
        defect_type = f.get("defect_type", "")
        deduction = DEDUCTION_RULES.get((defect_type, priority), 0)
        if deduction == 0:
            continue
        scores[role] = max(0, scores[role] - deduction)
        breakdown[role].append(f"{deduction}x1({defect_type})")

    result = {}
    for role in ROLES:
        detail_parts = breakdown[role]
        detail = f"100 - {' - '.join(detail_parts)} = {scores[role]}" if detail_parts else f"100 = {scores[role]}"
        result[role] = {
            "name": ROLE_NAMES[role],
            "score": scores[role],
            "breakdown": detail,
        }
    return result


def build_html(data: dict, template_path: Path, xlsx_styles_path: Path | None = None) -> str:
    """Build complete HTML report from data and template."""
    template = template_path.read_text(encoding="utf-8")

    # Load xlsx styles if available
    xlsx_styles = {}
    if xlsx_styles_path and xlsx_styles_path.exists():
        xlsx_styles = json.loads(xlsx_styles_path.read_text(encoding="utf-8"))

    # Inject data as global variable
    data_json = json.dumps(data, ensure_ascii=False, indent=2)
    data_script = f'<script>window.__REPORT_DATA__ = {data_json};</script>'

    # Inject xlsx styles
    styles_script = ""
    if xlsx_styles:
        styles_json = json.dumps(xlsx_styles, ensure_ascii=False)
        styles_script = f'<script>window.__XLSX_STYLES__ = {styles_json};</script>'

    # Find insertion point (after <head>)
    head_end = template.find("</head>")
    if head_end == -1:
        head_end = template.find("<body>")

    html = template[:head_end] + "\n" + data_script + "\n" + styles_script + "\n" + template[head_end:]

    return html


def generate_report(data_path: Path, template_path: Path, output_path: Path, xlsx_styles_path: Path | None = None) -> None:
    """Generate HTML report from data file."""
    data = json.loads(data_path.read_text(encoding="utf-8"))
    html = build_html(data, template_path, xlsx_styles_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Report generated: {output_path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python report_builder.py <report-data.json> [output.html]")
        sys.exit(1)
    data_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output/report.html")
    template_path = Path("assets/report-template.html")
    xlsx_styles_path = Path("assets/xlsx-styles.json")
    generate_report(data_path, template_path, output_path, xlsx_styles_path)
