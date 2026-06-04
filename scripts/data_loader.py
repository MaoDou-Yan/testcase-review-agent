"""Data loader and validator for report-data.json."""
import json
import re
from pathlib import Path
from typing import Any

ROLES = {"Arch", "Dev", "QA", "PM", "UX", "Sec", "Ops", "Perf", "DBA"}

ID_PATTERN = re.compile(r"^[A-Z][a-zA-Z]+-[A-Z][a-zA-Z]+-\d{3}$")
ID_PATTERN_RELAXED = re.compile(r"^[A-Z][a-zA-Z]+-\d{3}$")


def load_report_data(path: Path) -> dict[str, Any]:
    """Load and parse report-data.json."""
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data: dict) -> list[str]:
    """Validate report-data.json structure and return list of errors."""
    errors = []

    # Validate raw_cases
    case_ids = set()
    for case in data.get("raw_cases", []):
        cid = case.get("id", "")
        if not ID_PATTERN.match(cid) and not ID_PATTERN_RELAXED.match(cid):
            errors.append(f"用例 ID 格式错误: {cid}")
        case_ids.add(cid)
        for field in ("level1", "feature", "title", "steps", "expected", "priority"):
            if not case.get(field):
                errors.append(f"用例 {cid} 缺少必填字段: {field}")
        if case.get("priority") not in ("P0", "P1", "P2", "P3"):
            errors.append(f"用例 {cid} 优先级非法: {case.get('priority')}")

    # Validate optimized_cases
    for case in data.get("optimized_cases", []):
        cid = case.get("id", "")
        if not ID_PATTERN.match(cid) and not ID_PATTERN_RELAXED.match(cid):
            errors.append(f"优化用例 ID 格式错误: {cid}")
        for field in ("level1", "feature", "title", "steps", "expected", "priority"):
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


def validate_strict(data: dict) -> None:
    """Validate and raise on errors."""
    errors = validate(data)
    if errors:
        raise ValueError("数据校验失败:\n" + "\n".join(errors))


if __name__ == "__main__":
    import sys
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/report-data.json")
    data = load_report_data(path)
    errors = validate(data)
    if errors:
        print(f"发现 {len(errors)} 个问题:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("数据校验通过")
