"""Data loader and validator for report-data.json."""
import json
import re
import sys
from pathlib import Path
from typing import Any

ROLES = {"Arch", "Dev", "QA", "PM", "UX", "Sec", "Ops", "Perf", "DBA"}

ID_PATTERN = re.compile(r"^[A-Z][a-zA-Z]+-[A-Z][a-zA-Z]+-\d{3}$")
ID_PATTERN_RELAXED = re.compile(r"^[A-Z][a-zA-Z]+-\d{3}$")
ID_PATTERN_TEMPLATE = re.compile(r"^.+-\d+$")  # relaxed for template-defined IDs

DEFAULT_REQUIRED_FIELDS = ("level1", "feature", "title", "steps", "expected", "priority")


def load_report_data(path: Path) -> dict[str, Any]:
    """Load and parse report-data.json."""
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_case_id(cid: str, template_context: dict | None = None) -> bool:
    """Check if a case ID matches acceptable patterns."""
    if not cid:
        return False
    if ID_PATTERN.match(cid) or ID_PATTERN_RELAXED.match(cid):
        return True
    if template_context and ID_PATTERN_TEMPLATE.match(cid):
        return True
    return False


def _get_valid_priorities(template_context: dict | None = None) -> set[str]:
    """Get valid priority values, using template values if available."""
    if template_context:
        for sheet in template_context.get("sheets", []):
            pv = sheet.get("priority_values")
            if pv:
                return set(pv)
    return {"P0", "P1", "P2", "P3"}


def validate(data: dict, template_context: dict | None = None) -> list[str]:
    """Validate report-data.json structure and return list of errors."""
    errors = []
    valid_priorities = _get_valid_priorities(template_context)

    # Validate raw_cases
    case_ids = set()
    for case in data.get("raw_cases", []):
        cid = case.get("id", "")
        if not _validate_case_id(cid, template_context):
            errors.append(f"用例 ID 格式错误: {cid}")
        case_ids.add(cid)
        for field in DEFAULT_REQUIRED_FIELDS:
            if not case.get(field):
                errors.append(f"用例 {cid} 缺少必填字段: {field}")
        if case.get("priority") and case.get("priority") not in valid_priorities:
            errors.append(f"用例 {cid} 优先级非法: {case.get('priority')}")

    # Validate optimized_cases
    for case in data.get("optimized_cases", []):
        cid = case.get("id", "")
        if not _validate_case_id(cid, template_context):
            errors.append(f"优化用例 ID 格式错误: {cid}")
        for field in DEFAULT_REQUIRED_FIELDS:
            if not case.get(field):
                errors.append(f"优化用例 {cid} 缺少必填字段: {field}")

    # Validate review_findings references
    ambiguity_ids = {a.get("id") for a in data.get("requirements", {}).get("ambiguities", [])}
    for f in data.get("review_findings", []):
        ref_id = f.get("case_id", "")
        if ref_id not in case_ids and ref_id not in ambiguity_ids:
            errors.append(f"评审发现引用不存在的用例: {ref_id}")
        if f.get("role") not in ROLES:
            errors.append(f"评审角色非法: {f.get('role')}")

    return errors


def validate_strict(data: dict, template_context: dict | None = None) -> None:
    """Validate and raise on errors."""
    errors = validate(data, template_context)
    if errors:
        raise ValueError("数据校验失败:\n" + "\n".join(errors))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate report-data.json")
    parser.add_argument("data", type=Path, nargs="?", default=Path("output/report-data.json"),
                        help="Path to report-data.json")
    parser.add_argument("--template", type=Path, default=None,
                        help="Template context JSON for relaxed validation")
    args = parser.parse_args()

    data = load_report_data(args.data)
    template_ctx = None
    if args.template and args.template.exists():
        template_ctx = json.loads(args.template.read_text(encoding="utf-8"))
    errors = validate(data, template_ctx)
    if errors:
        print(f"发现 {len(errors)} 个问题:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("数据校验通过")
