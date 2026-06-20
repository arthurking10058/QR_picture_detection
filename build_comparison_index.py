from __future__ import annotations

import argparse
from pathlib import Path

from qr_static_detector.reporting import (
    build_comparison_index_html,
    build_comparison_index_markdown,
    build_index_chart_paths,
    collect_comparison_index_items,
    configure_matplotlib_chinese,
    generate_comparison_index_charts,
    write_json_file,
)

try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None
else:
    configure_matplotlib_chinese(plt)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建多次实验对比总览页")
    parser.add_argument("--comparisons-root", default="outputs/comparisons", help="对比结果根目录")
    parser.add_argument("-o", "--output-dir", default="outputs", help="总览页输出目录")
    parser.add_argument("--name", default="comparison_index", help="输出文件名前缀")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    comparisons_root = Path(args.comparisons_root)
    output_dir = Path(args.output_dir)

    if not comparisons_root.is_dir():
        print(f"对比根目录不存在: {comparisons_root}")
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)

    items = collect_comparison_index_items(comparisons_root)
    if not items:
        print(f"未找到可用的对比结果: {comparisons_root}")
        return 1

    chart_paths = build_index_chart_paths(output_dir, args.name)
    charts = generate_comparison_index_charts(
        plt,
        items,
        chart_paths["trend_chart"],
        chart_paths["risk_chart"],
    )

    md_path = output_dir / f"{args.name}.md"
    html_path = output_dir / f"{args.name}.html"
    json_path = output_dir / f"{args.name}.json"

    write_json_file(json_path, items)
    md_path.write_text(build_comparison_index_markdown(items, charts), encoding="utf-8")
    html_path.write_text(build_comparison_index_html(items, charts), encoding="utf-8")

    print(f"总览 JSON: {json_path}")
    print(f"总览 Markdown: {md_path}")
    print(f"总览 HTML: {html_path}")
    for chart in charts:
        print(f"趋势图: {chart}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
