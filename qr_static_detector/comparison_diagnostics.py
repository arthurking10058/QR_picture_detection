from __future__ import annotations

from pathlib import Path

from .comparison_checklists import build_recommendation_checklist
from .comparison_metrics import (
    aggregate_method_hits,
    aggregate_variant_hits,
    build_category_sample_index,
    build_rankings,
    build_risk_categories,
    build_summary_insights,
    format_sample_refs_inline,
)
from .config import REPORT_CONFIG
from .report_text import NO_CATEGORY_PORTRAITS_TEXT
from .reporting_common import extract_meta_text, safe_float


def build_failure_clusters(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for row in rows:
        if row.get("success") == "True":
            continue
        category = row.get("category", "") or "(uncategorized)"
        grouped.setdefault(category, {"count": 0, "samples": []})
        grouped[category]["count"] += 1
        grouped[category]["samples"].append(
            {
                "image": row.get("image", ""),
                "output": row.get("output", ""),
                "time_ms": str(row.get("time_ms", "")),
            }
        )

    ranked = sorted(grouped.items(), key=lambda item: int(item[1]["count"]), reverse=True)
    return [
        {
            "category": category,
            "count": stats["count"],
            "samples": stats["samples"][: REPORT_CONFIG.sample_reference_limit],
        }
        for category, stats in ranked[: REPORT_CONFIG.failure_cluster_limit]
        if stats["count"] > 0
    ]


def build_failure_reason_clusters(rows: list[dict[str, object]]) -> list[str]:
    buckets = {
        "低成功率类别": 0,
        "高耗时失败": 0,
        "兜底路径耗尽": 0,
        "双解码器均未命中": 0,
    }
    for row in rows:
        if row.get("final_status") == "success":
            continue
        buckets["低成功率类别"] += 1
        reason = str(row.get("dominant_failure_reason", ""))
        if "exhausted" in reason:
            buckets["兜底路径耗尽"] += 1
        if "dual_decoder" in reason or "cv2_and_pyzbar" in reason:
            buckets["双解码器均未命中"] += 1
        time_ms = safe_float(row.get("elapsed_ms"))
        if time_ms > REPORT_CONFIG.failure_slow_ms_threshold:
            buckets["高耗时失败"] += 1
    return [f"{name}: {count} 张失败图片" for name, count in buckets.items() if count > 0]


def build_trend_lines(
    rows: list[dict[str, object]],
    baseline_meta: dict[str, object],
    candidate_meta: dict[str, object],
    baseline_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
) -> list[str]:
    lines: list[str] = []
    base_time = extract_meta_text(baseline_meta, "run_started_at")
    cand_time = extract_meta_text(candidate_meta, "run_started_at")
    if base_time or cand_time:
        lines.append(f"时间序列对比：baseline={base_time or '-'}，candidate={cand_time or '-'}。")

    if rows:
        improved = [row for row in rows if float(row["delta_success_rate"]) > 0]
        regressed = [row for row in rows if float(row["delta_success_rate"]) < 0]
        lines.append(f"类别趋势：提升 {len(improved)} 类，退化 {len(regressed)} 类。")

    base_total = sum(int(safe_float(row.get("image_count"))) for row in baseline_rows)
    cand_total = sum(int(safe_float(row.get("image_count"))) for row in candidate_rows)
    if base_total or cand_total:
        lines.append(f"样本规模趋势：baseline {base_total} 张，对比运行 {cand_total} 张。")

    return lines


def build_stable_failure_lines(rows: list[dict[str, object]]) -> list[str]:
    method_failures: dict[str, int] = {}
    variant_failures: dict[str, int] = {}
    for row in rows:
        if row.get("final_status") == "success":
            continue
        for method in row.get("attempted_methods", []):
            name = str(method).strip()
            if name:
                method_failures[name] = method_failures.get(name, 0) + 1
        for variant in row.get("attempted_variants", []):
            name = str(variant).strip()
            if name:
                variant_failures[name] = variant_failures.get(name, 0) + 1

    lines: list[str] = []
    for name, count in sorted(method_failures.items(), key=lambda item: item[1], reverse=True)[: REPORT_CONFIG.stable_failure_limit]:
        lines.append(f"方法 {name} 在失败链路中出现 {count} 次，可能是稳定失效方法。")
    for name, count in sorted(variant_failures.items(), key=lambda item: item[1], reverse=True)[: REPORT_CONFIG.stable_failure_limit]:
        lines.append(f"变体 {name} 在失败链路中出现 {count} 次，建议重点复核。")
    return lines


def normalize_failure_reason(reason: str) -> str:
    mapping = {
        "warp_and_multi_fallback_exhausted": "透视展开与多重兜底都未命中",
        "warp_fallback_exhausted": "透视/展开兜底不足",
        "multi_decode_exhausted": "多尺度与多重解码兜底都耗尽",
        "cv2_and_pyzbar_exhausted": "OpenCV 与 pyzbar 双解码器都耗尽",
        "dual_decoder_exhausted": "双解码器都未命中",
        "adaptive_variants_exhausted": "分类预处理变体全部未命中",
        "baseline_pipeline_miss": "基础检测链路未命中",
        "none": "无明显失败原因",
    }
    return mapping.get(reason, reason or "未知原因")


def build_category_portraits(rows: list[dict[str, object]], image_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    image_index = build_category_sample_index(image_rows)
    for row in rows:
        if row.get("final_status") == "success":
            continue
        category = str(row.get("category", "") or "(uncategorized)")
        reason = normalize_failure_reason(str(row.get("dominant_failure_reason", "")))
        grouped.setdefault(
            category,
            {
                "reasons": {},
                "methods": {},
                "variants": {},
            },
        )
        grouped[category]["reasons"][reason] = grouped[category]["reasons"].get(reason, 0) + 1
        for method in row.get("attempted_methods", []):
            method_name = str(method).strip()
            if method_name:
                grouped[category]["methods"][method_name] = grouped[category]["methods"].get(method_name, 0) + 1
        for variant in row.get("attempted_variants", []):
            variant_name = str(variant).strip()
            if variant_name:
                grouped[category]["variants"][variant_name] = grouped[category]["variants"].get(variant_name, 0) + 1

    portraits: list[dict[str, object]] = []
    for category, payload in sorted(grouped.items()):
        reasons = sorted(payload["reasons"].items(), key=lambda item: item[1], reverse=True)
        methods = sorted(payload["methods"].items(), key=lambda item: item[1], reverse=True)
        variants = sorted(payload["variants"].items(), key=lambda item: item[1], reverse=True)
        primary_reason = reasons[0][0] if reasons else "未知原因"
        secondary_reason = reasons[1][0] if len(reasons) > 1 else "无明显次要原因"
        sample_refs = image_index.get(category, [])[: REPORT_CONFIG.sample_reference_limit]
        portraits.append(
            {
                "category": category,
                "primary_reason": primary_reason,
                "secondary_reason": secondary_reason,
                "common_failed_methods": [name for name, _ in methods[: REPORT_CONFIG.sample_reference_limit]],
                "common_failed_variants": [name for name, _ in variants[: REPORT_CONFIG.sample_reference_limit]],
                "recommended_checks": build_recommendation_checklist(category, primary_reason, methods, variants),
                "sample_refs": sample_refs,
                "sample_refs_inline": format_sample_refs_inline(sample_refs),
            }
        )
    return portraits


def build_comparison_report_context(
    baseline_path: Path,
    candidate_path: Path,
    overall: dict[str, object],
    rows: list[dict[str, object]],
    generated_charts: list[Path],
    baseline_meta: dict[str, object],
    candidate_meta: dict[str, object],
    baseline_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
    baseline_image_rows: list[dict[str, str]],
    candidate_image_rows: list[dict[str, str]],
    candidate_result_rows: list[dict[str, str]],
    candidate_diagnostics: list[dict[str, object]],
) -> dict[str, object]:
    best_improved = max(rows, key=lambda row: float(row["delta_success_rate"]), default=None)
    worst_regressed = min(rows, key=lambda row: float(row["delta_success_rate"]), default=None)
    return {
        "baseline_path": baseline_path,
        "candidate_path": candidate_path,
        "overall": overall,
        "rows": rows,
        "generated_charts": generated_charts,
        "baseline_meta": baseline_meta,
        "candidate_meta": candidate_meta,
        "best_improved": best_improved,
        "worst_regressed": worst_regressed,
        "insight_lines": build_summary_insights(rows, baseline_rows, candidate_rows, baseline_image_rows, candidate_image_rows),
        "risk_categories": build_risk_categories(rows, candidate_image_rows),
        "failure_clusters": build_failure_clusters(candidate_image_rows),
        "failure_reasons": build_failure_reason_clusters(candidate_diagnostics),
        "category_portraits": build_category_portraits(candidate_diagnostics, candidate_image_rows),
        "method_rankings": build_rankings(aggregate_method_hits(candidate_image_rows)),
        "variant_rankings": build_rankings(aggregate_variant_hits(candidate_result_rows)),
        "trend_lines": build_trend_lines(rows, baseline_meta, candidate_meta, baseline_rows, candidate_rows),
        "stable_failures": build_stable_failure_lines(candidate_diagnostics),
    }


def render_markdown_risk_categories(items: list[dict[str, object]]) -> list[str]:
    if not items:
        return ["- 无明显高风险类别。"]
    lines: list[str] = []
    for item in items:
        lines.append(f"- {item['category']}: {'，'.join(item['reasons'])}")
        samples = item.get("samples", [])
        if samples:
            lines.append(f"  - 关联样本: {format_sample_refs_inline(samples)}")
    return lines


def render_markdown_failure_clusters(items: list[dict[str, object]]) -> list[str]:
    if not items:
        return ["- 未发现显著失败聚类。"]
    lines: list[str] = []
    for item in items:
        lines.append(f"- {item['category']}: 失败图片 {item['count']} 张")
        lines.append(f"  - 关联样本: {format_sample_refs_inline(item.get('samples', []))}")
    return lines


def build_markdown_category_portraits(portraits: list[dict[str, object]]) -> list[str]:
    if not portraits:
        return [f"- {NO_CATEGORY_PORTRAITS_TEXT}"]

    lines: list[str] = []
    for portrait in portraits:
        lines.extend(
            [
                f"### {portrait['category']}",
                f"- 主要失败原因: {portrait['primary_reason']}",
                f"- 次要失败原因: {portrait['secondary_reason']}",
                f"- 常见失效方法: {', '.join(portrait['common_failed_methods']) or '无'}",
                f"- 常见失效变体: {', '.join(portrait['common_failed_variants']) or '无'}",
                f"- 关联失败样本: {portrait['sample_refs_inline']}",
                "- 推荐排查方向:",
                *[
                    f"  - [{item['priority']}] {'[触发]' if item['triggered'] else '[观察]'} {'[已覆盖]' if item['covered'] else '[待排查]'} {item['text']}"
                    for item in portrait["recommended_checks"]
                ],
                "",
            ]
        )
    return lines
