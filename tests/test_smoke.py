"""Smoke tests for report generation pipeline."""
import json
from pathlib import Path

import pytest

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.data_loader import load_report_data, validate
from scripts.report_builder import build_html, compute_role_scores


@pytest.fixture
def sample_data():
    """Load sample report data."""
    data_path = Path(__file__).parent.parent / "output" / "report-data.json"
    if not data_path.exists():
        pytest.skip("report-data.json not found")
    return load_report_data(data_path)


@pytest.fixture
def template():
    """Load report template."""
    template_path = Path(__file__).parent.parent / "assets" / "report-template.html"
    return template_path.read_text(encoding="utf-8")


def test_data_loads_successfully(sample_data):
    """Verify report-data.json loads and has required keys."""
    assert "meta" in sample_data
    assert "raw_cases" in sample_data
    assert "review_findings" in sample_data
    assert "optimized_cases" in sample_data
    assert "scoring" in sample_data


def test_data_validation(sample_data):
    """Verify data passes validation."""
    errors = validate(sample_data)
    # Allow warnings but no critical errors
    critical_errors = [e for e in errors if "缺少必填字段" in e or "优先级非法" in e]
    assert len(critical_errors) == 0, f"Critical validation errors: {critical_errors}"


def test_raw_cases_have_required_fields(sample_data):
    """Verify all raw cases have required fields."""
    required = {"id", "level1", "feature", "title", "steps", "expected", "priority"}
    for case in sample_data["raw_cases"]:
        missing = required - set(case.keys())
        assert not missing, f"Case {case.get('id')} missing fields: {missing}"


def test_review_findings_reference_valid_cases(sample_data):
    """Verify review findings reference existing cases."""
    case_ids = {c["id"] for c in sample_data["raw_cases"]}
    ambiguity_ids = {a["id"] for a in sample_data.get("requirements", {}).get("ambiguities", [])}
    valid_ids = case_ids | ambiguity_ids

    for finding in sample_data["review_findings"]:
        assert finding["case_id"] in valid_ids, \
            f"Finding references non-existent case: {finding['case_id']}"


def test_role_scores_computed(sample_data):
    """Verify role scores are computed correctly."""
    scores = compute_role_scores(
        sample_data["review_findings"],
        sample_data["raw_cases"]
    )
    assert len(scores) == 9
    for role, data in scores.items():
        assert 0 <= data["score"] <= 100
        assert "name" in data
        assert "breakdown" in data


def test_html_generation(sample_data, template):
    """Verify HTML report generates successfully."""
    template_path = Path(__file__).parent.parent / "assets" / "report-template.html"
    xlsx_styles_path = Path(__file__).parent.parent / "assets" / "xlsx-styles.json"

    html = build_html(sample_data, template_path, xlsx_styles_path)

    # Verify data injection
    assert "window.__REPORT_DATA__" in html
    assert "window.__XLSX_STYLES__" in html

    # Verify template structure
    assert 'data-tab="requirements"' in html
    assert 'data-tab="raw"' in html
    assert 'data-tab="review"' in html
    assert 'data-tab="optimized"' in html
    assert 'data-tab="report"' in html

    # Verify interactive features
    assert "downloadXlsx()" in html
    assert "copyOptimized()" in html
    assert "toggleEdit()" in html


def test_scoring_structure(sample_data):
    """Verify scoring data structure."""
    scoring = sample_data["scoring"]

    assert "role_scores" in scoring
    assert len(scoring["role_scores"]) == 9

    assert "defect_distribution" in scoring
    assert len(scoring["defect_distribution"]) > 0

    assert "quality_radar" in scoring
    assert len(scoring["quality_radar"]) == 8

    assert "coverage" in scoring
    assert "rtm" in scoring


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
