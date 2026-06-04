#!/usr/bin/env python3
"""Generate test case review report from report-data.json.

Usage:
  python generate_report.py                              # Default paths, timestamped output
  python generate_report.py data.json                    # Custom data file
  python generate_report.py data.json out.html           # Custom output path
  python generate_report.py --template template.xlsx     # With template parsing
  python generate_report.py --template-ctx context.json  # With existing template context
"""
import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

from scripts.data_loader import load_report_data, validate
from scripts.report_builder import generate_report


def main():
    parser = argparse.ArgumentParser(description="Generate test case review report")
    parser.add_argument("data", type=Path, nargs="?", default=Path("output/report-data.json"),
                        help="Path to report-data.json")
    parser.add_argument("output", type=Path, nargs="?", default=None,
                        help="Output HTML path (default: auto-timestamped)")
    parser.add_argument("--template", type=Path, default=None,
                        help="Template Excel file for column mapping")
    parser.add_argument("--template-ctx", type=Path, default=None,
                        help="Existing template-context.json file")
    args = parser.parse_args()

    data_path = args.data
    output_path = args.output
    template_path = Path("assets/report-template.html")
    xlsx_styles_path = Path("assets/xlsx-styles.json")
    template_context = None

    if not data_path.exists():
        print(f"Error: Data file not found: {data_path}")
        return

    # Load template context if provided
    template_ctx_path = args.template_ctx or Path("output/template-context.json")
    if template_ctx_path.exists():
        template_context = json.loads(template_ctx_path.read_text(encoding="utf-8"))
        print(f"Template context loaded: {template_ctx_path}")

    # Load and validate
    data = load_report_data(data_path)
    errors = validate(data, template_context)
    if errors:
        print(f"Warning: {len(errors)} validation issues:")
        for e in errors:
            print(f"  - {e}")

    # Determine output path with timestamp
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        timestamped_path = output_dir / f"report_{timestamp}.html"
        latest_path = output_dir / "report.html"
    else:
        timestamped_path = output_path
        latest_path = None

    # Generate timestamped report
    generate_report(data_path, template_path, timestamped_path, xlsx_styles_path)

    # Copy to latest if needed
    if latest_path:
        shutil.copy2(timestamped_path, latest_path)
        print(f"Report generated:")
        print(f"  Timestamped: {timestamped_path}")
        print(f"  Latest:      {latest_path}")
    else:
        print(f"Report generated: {timestamped_path}")

    print(f"  Original cases: {len(data.get('raw_cases', []))}")
    print(f"  Optimized cases: {len(data.get('optimized_cases', []))}")
    print(f"  Review findings: {len(data.get('review_findings', []))}")


if __name__ == "__main__":
    main()
