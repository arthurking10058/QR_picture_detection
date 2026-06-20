from __future__ import annotations

import argparse
from pathlib import Path

from qr_static_detector.reporting import ensure_output_dir, read_csv_rows, write_csv_rows, write_json_file
from qr_static_detector.summary_reporting import (
    build_summary_markdown_report,
    build_summary_report_context,
    read_run_meta,
    summarize_images_by_category,
    summarize_overall_results,
    summarize_result_rows_by_image,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="汇总 QR 检测 results.csv 结果")
    parser.add_argument("input", nargs="?", default="outputs/runtime_outputs/results.csv", help="输入 results.csv 路径")
    parser.add_argument("-o", "--output-dir", help="汇总结果输出目录，默认与输入文件同目录")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"结果文件不存在: {input_path}")
        return 1

    output_dir = ensure_output_dir(Path(args.output_dir)) if args.output_dir else input_path.parent
    if output_dir is None:
        print(f"无法创建输出目录: {args.output_dir}")
        return 1

    rows = read_rows(input_path)
    if not rows:
        print(f"结果文件为空: {input_path}")
        return 1

    image_summary = summarize_result_rows_by_image(rows)
    category_summary = summarize_images_by_category(image_summary)
    overall_summary = summarize_overall_results(image_summary)
    run_meta = read_run_meta(input_path.parent / "run_meta.json")
    report_context = build_summary_report_context(input_path, overall_summary, category_summary, run_meta)

    write_csv_rows(output_dir / "summary_by_image.csv", image_summary)
    write_csv_rows(output_dir / "summary_by_category.csv", category_summary)
    write_json_file(output_dir / "summary_overall.json", {**overall_summary, "run_meta": run_meta})
    (output_dir / "summary_report.md").write_text(
        build_summary_markdown_report(report_context),
        encoding="utf-8",
    )

    print(f"按图片汇总: {output_dir / 'summary_by_image.csv'}")
    print(f"按类别汇总: {output_dir / 'summary_by_category.csv'}")
    print(f"总体汇总: {output_dir / 'summary_overall.json'}")
    print(f"Markdown报告: {output_dir / 'summary_report.md'}")
    return 0


def read_rows(path: Path) -> list[dict[str, str]]:
    return read_csv_rows(path)

if __name__ == "__main__":
    raise SystemExit(main())
