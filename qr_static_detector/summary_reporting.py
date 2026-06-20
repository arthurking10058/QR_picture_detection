from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .report_text import SUMMARY_REPORT_TITLE
from .reporting_common import read_json_dict, safe_float


def summarize_result_rows_by_image(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["image"]].append(row)

    summary: list[dict[str, object]] = []
    for image_path, image_rows in sorted(grouped.items()):
        first = image_rows[0]
        success_hits = [row for row in image_rows if row["success"] == "True"]
        failure_hits = [row for row in image_rows if row["success"] != "True"]
        methods = sorted({row["method"] for row in success_hits if row["method"]})
        variants = sorted({row["variant"] for row in success_hits if row["variant"]})
        failure_variants = sorted({row["variant"] for row in failure_hits if row["variant"]})
        times = [safe_float(row["time_ms"]) for row in image_rows if row["time_ms"]]
        summary.append(
            {
                "image": image_path,
                "category": first.get("category", ""),
                "success": bool(success_hits),
                "detection_count": len(success_hits),
                "unique_payload_count": len({row["data"] for row in success_hits if row["data"]}),
                "methods": " | ".join(methods),
                "variants": " | ".join(variants),
                "failure_variants": " | ".join(failure_variants),
                "time_ms": round(max(times), 2) if times else "",
                "output": first.get("output", ""),
            }
        )
    return summary


def summarize_images_by_category(image_summary: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in image_summary:
        grouped[str(row.get("category", ""))].append(row)

    summary: list[dict[str, object]] = []
    for category, items in sorted(grouped.items(), key=lambda item: item[0]):
        total = len(items)
        success = sum(1 for item in items if item["success"])
        detections = sum(int(item["detection_count"]) for item in items)
        times = [safe_float(item["time_ms"]) for item in items if item["time_ms"] != ""]
        summary.append(
            {
                "category": category,
                "image_count": total,
                "success_count": success,
                "success_rate": round(success / total * 100, 2) if total else 0,
                "detection_count": detections,
                "avg_time_ms": round(sum(times) / len(times), 2) if times else "",
            }
        )
    return summary


def summarize_overall_results(image_summary: list[dict[str, object]]) -> dict[str, object]:
    total = len(image_summary)
    success = sum(1 for item in image_summary if item["success"])
    detections = sum(int(item["detection_count"]) for item in image_summary)
    times = [safe_float(item["time_ms"]) for item in image_summary if item["time_ms"] != ""]
    return {
        "image_count": total,
        "success_count": success,
        "success_rate": round(success / total * 100, 2) if total else 0,
        "detection_count": detections,
        "avg_time_ms": round(sum(times) / len(times), 2) if times else "",
    }


def read_run_meta(path: Path) -> dict[str, object]:
    return read_json_dict(path)


def build_summary_report_context(
    input_path: Path,
    overall_summary: dict[str, object],
    category_summary: list[dict[str, object]],
    run_meta: dict[str, object],
) -> dict[str, object]:
    return {
        "input_path": input_path,
        "overall_summary": overall_summary,
        "category_summary": category_summary,
        "run_meta": run_meta,
    }


def build_summary_markdown_report(context: dict[str, object]) -> str:
    input_path = context["input_path"]
    overall_summary = context["overall_summary"]
    category_summary = context["category_summary"]
    run_meta = context["run_meta"]
    lines = [
        f"# {SUMMARY_REPORT_TITLE}",
        "",
        f"- 输入文件: `{input_path}`",
        f"- 运行时间: `{run_meta.get('run_started_at', '')}`",
        f"- 运行命令: `{run_meta.get('command', '')}`",
        f"- 输入摘要: `{run_meta.get('input_source', '')}`",
        f"- 图片总数: `{overall_summary['image_count']}`",
        f"- 检测成功: `{overall_summary['success_count']}`",
        f"- 成功率: `{overall_summary['success_rate']}%`",
        f"- 检测条目数: `{overall_summary['detection_count']}`",
        f"- 平均耗时: `{overall_summary['avg_time_ms']} ms`",
        "",
        "## 分类汇总",
        "",
        "| category | images | success | success_rate | detections | avg_time_ms |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in category_summary:
        lines.append(
            f"| {row['category'] or '(uncategorized)'} | {row['image_count']} | {row['success_count']} | {row['success_rate']}% | {row['detection_count']} | {row['avg_time_ms']} |"
        )
    lines.append("")
    return "\n".join(lines)
