from __future__ import annotations

import argparse
from pathlib import Path

from qr_static_detector.reporting import (
    build_report_chart_paths,
    build_comparison_html_report,
    compare_summary_rows,
    build_comparison_markdown_report,
    build_comparison_report_context,
    configure_matplotlib_chinese,
    generate_comparison_charts,
    read_csv_rows,
    read_optional_csv_rows,
    read_optional_json_list,
    read_summary_run_meta,
    safe_float,
    summarize_comparison_delta,
    write_csv_rows,
    write_json_file,
)

try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None
else:
    configure_matplotlib_chinese(plt)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="对比两份 summary_by_category.csv 汇总结果")
    parser.add_argument("baseline", help="基线 summary_by_category.csv")
    parser.add_argument("candidate", help="对比 summary_by_category.csv")
    parser.add_argument("-o", "--output-dir", default="outputs/comparisons", help="输出目录，默认 outputs/comparisons")
    parser.add_argument("--name", default="comparison", help="输出文件名前缀")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    baseline_path = Path(args.baseline)
    candidate_path = Path(args.candidate)
    output_dir = Path(args.output_dir)

    if not baseline_path.is_file():
        print(f"基线文件不存在: {baseline_path}")
        return 1
    if not candidate_path.is_file():
        print(f"对比文件不存在: {candidate_path}")
        return 1
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(f"无法创建输出目录: {output_dir}")
            return 1

    baseline_rows = read_csv_rows(baseline_path)
    candidate_rows = read_csv_rows(candidate_path)
    baseline_image_rows = read_optional_csv_rows(baseline_path.parent / "summary_by_image.csv")
    candidate_image_rows = read_optional_csv_rows(candidate_path.parent / "summary_by_image.csv")
    baseline_result_rows = read_optional_csv_rows(baseline_path.parent / "results.csv")
    candidate_result_rows = read_optional_csv_rows(candidate_path.parent / "results.csv")
    candidate_diagnostics = read_optional_json_list(candidate_path.parent / "diagnostics.json")
    comparison_rows = compare_summary_rows(baseline_rows, candidate_rows)
    overall = summarize_comparison_delta(comparison_rows)
    baseline_meta = read_summary_run_meta(baseline_path.parent / "summary_overall.json")
    candidate_meta = read_summary_run_meta(candidate_path.parent / "summary_overall.json")
    report_dir = build_report_dir(output_dir, args.name)

    csv_path = report_dir / f"{args.name}_by_category.csv"
    json_path = report_dir / f"{args.name}_overall.json"
    md_path = report_dir / f"{args.name}_report.md"
    html_path = report_dir / f"{args.name}_report.html"
    chart_paths = build_report_chart_paths(report_dir, args.name)

    write_csv_rows(csv_path, comparison_rows)
    write_json_file(
        json_path,
        {
            **overall,
            "baseline_meta": baseline_meta,
            "candidate_meta": candidate_meta,
        },
    )
    generated_charts = generate_comparison_charts(
        plt,
        comparison_rows,
        baseline_rows,
        candidate_rows,
        baseline_image_rows,
        candidate_image_rows,
        chart_paths["success_chart"],
        chart_paths["time_chart"],
        chart_paths["input_chart"],
        chart_paths["method_chart"],
    )
    report_context = build_comparison_report_context(
        baseline_path,
        candidate_path,
        overall,
        comparison_rows,
        generated_charts,
        baseline_meta,
        candidate_meta,
        baseline_rows,
        candidate_rows,
        baseline_image_rows,
        candidate_image_rows,
        candidate_result_rows,
        candidate_diagnostics,
    )
    md_path.write_text(
        build_comparison_markdown_report(report_context),
        encoding="utf-8",
    )
    html_path.write_text(
        build_comparison_html_report(report_context),
        encoding="utf-8",
    )

    print(f"分类对比: {csv_path}")
    print(f"总体对比: {json_path}")
    print(f"Markdown报告: {md_path}")
    print(f"HTML报告: {html_path}")
    if generated_charts:
        for chart in generated_charts:
            print(f"图表: {chart}")
    return 0


def build_report_dir(output_dir: Path, name: str) -> Path:
    report_dir = output_dir / name
    if not report_dir.exists():
        try:
            report_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return output_dir
    return report_dir


if __name__ == "__main__":
    raise SystemExit(main())
