from __future__ import annotations

import html

from .config import REPORT_CONFIG
from .reporting_common import safe_float


def build_sample_ref(row: dict[str, str]) -> dict[str, str]:
    return {
        "image": row.get("image", ""),
        "output": row.get("output", ""),
        "time_ms": str(row.get("time_ms", "")),
    }


def build_category_sample_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if row.get("success") == "True":
            continue
        category = row.get("category", "") or "(uncategorized)"
        grouped.setdefault(category, []).append(build_sample_ref(row))
    return grouped


def format_sample_refs_inline(samples: list[dict[str, str]]) -> str:
    if not samples:
        return "无"
    parts = []
    for sample in samples:
        image = sample.get("image", "")
        output = sample.get("output", "")
        parts.append(f"{image} -> {output or '-'}")
    return " | ".join(parts)


def render_html_sample_refs_inline(samples: list[dict[str, str]]) -> str:
    if not samples:
        return "无"
    parts = []
    for sample in samples:
        image = html.escape(sample.get("image", ""))
        output = html.escape(sample.get("output", "") or "-")
        parts.append(f"<code>{image}</code> -> <code>{output}</code>")
    return "<br>".join(parts)


def aggregate_method_hits(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        methods = [item.strip() for item in row.get("methods", "").split("|") if item.strip()]
        for method in methods:
            counts[method] = counts.get(method, 0) + 1
    return counts


def aggregate_variant_hits(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        if row.get("success") != "True":
            continue
        variant = row.get("variant", "").strip()
        if not variant:
            continue
        counts[variant] = counts.get(variant, 0) + 1
    return counts


def build_rankings(counter: dict[str, int], limit: int = REPORT_CONFIG.ranking_limit) -> list[str]:
    ranked = sorted(counter.items(), key=lambda item: item[1], reverse=True)
    return [f"{name}: {count}" for name, count in ranked[:limit]]


def compare_summary_rows(baseline_rows: list[dict[str, str]], candidate_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    baseline_map = {row["category"]: row for row in baseline_rows}
    candidate_map = {row["category"]: row for row in candidate_rows}
    categories = sorted(set(baseline_map) | set(candidate_map))
    rows: list[dict[str, object]] = []
    for category in categories:
        baseline = baseline_map.get(category, {})
        candidate = candidate_map.get(category, {})
        baseline_rate = safe_float(baseline.get("success_rate"))
        candidate_rate = safe_float(candidate.get("success_rate"))
        baseline_count = safe_float(baseline.get("success_count"))
        candidate_count = safe_float(candidate.get("success_count"))
        rows.append(
            {
                "category": category,
                "baseline_image_count": baseline.get("image_count", ""),
                "candidate_image_count": candidate.get("image_count", ""),
                "baseline_success_rate": baseline_rate,
                "candidate_success_rate": candidate_rate,
                "delta_success_rate": round(candidate_rate - baseline_rate, 2),
                "baseline_success_count": int(baseline_count) if baseline_count else 0,
                "candidate_success_count": int(candidate_count) if candidate_count else 0,
                "delta_success_count": int(candidate_count - baseline_count),
                "baseline_avg_time_ms": safe_float(baseline.get("avg_time_ms")),
                "candidate_avg_time_ms": safe_float(candidate.get("avg_time_ms")),
                "delta_avg_time_ms": round(
                    safe_float(candidate.get("avg_time_ms")) - safe_float(baseline.get("avg_time_ms")),
                    2,
                ),
            }
        )
    return rows


def summarize_comparison_delta(rows: list[dict[str, object]]) -> dict[str, object]:
    deltas = [float(row["delta_success_rate"]) for row in rows]
    improved = sum(1 for delta in deltas if delta > 0)
    regressed = sum(1 for delta in deltas if delta < 0)
    unchanged = sum(1 for delta in deltas if delta == 0)
    return {
        "category_count": len(rows),
        "improved_categories": improved,
        "regressed_categories": regressed,
        "unchanged_categories": unchanged,
        "avg_delta_success_rate": round(sum(deltas) / len(deltas), 2) if deltas else 0,
        "best_delta_success_rate": max(deltas) if deltas else 0,
        "worst_delta_success_rate": min(deltas) if deltas else 0,
    }


def build_summary_insights(
    rows: list[dict[str, object]],
    baseline_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
    baseline_image_rows: list[dict[str, str]],
    candidate_image_rows: list[dict[str, str]],
) -> list[str]:
    insights: list[str] = []
    if rows:
        best = max(rows, key=lambda row: float(row["delta_success_rate"]))
        worst = min(rows, key=lambda row: float(row["delta_success_rate"]))
        insights.append(f"最佳提升类别为 {best['category']}，成功率变化 {best['delta_success_rate']}%。")
        insights.append(f"最大退化类别为 {worst['category']}，成功率变化 {worst['delta_success_rate']}%。")

    base_total = sum(int(safe_float(row.get("image_count"))) for row in baseline_rows)
    cand_total = sum(int(safe_float(row.get("image_count"))) for row in candidate_rows)
    if base_total or cand_total:
        insights.append(f"输入样本规模：baseline {base_total} 张，candidate {cand_total} 张。")

    baseline_methods = aggregate_method_hits(baseline_image_rows)
    candidate_methods = aggregate_method_hits(candidate_image_rows)
    if baseline_methods or candidate_methods:
        top_base = max(baseline_methods.items(), key=lambda item: item[1], default=("", 0))
        top_cand = max(candidate_methods.items(), key=lambda item: item[1], default=("", 0))
        if top_base[0]:
            insights.append(f"baseline 命中最多的方法是 {top_base[0]}，覆盖 {top_base[1]} 张图片。")
        if top_cand[0]:
            insights.append(f"candidate 命中最多的方法是 {top_cand[0]}，覆盖 {top_cand[1]} 张图片。")
    return insights


def build_risk_categories(rows: list[dict[str, object]], image_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    image_index = build_category_sample_index(image_rows)
    risk_items: list[dict[str, object]] = []
    for row in rows:
        category = str(row["category"] or "(uncategorized)")
        candidate_rate = float(row["candidate_success_rate"])
        delta_rate = float(row["delta_success_rate"])
        delta_time = float(row["delta_avg_time_ms"])
        reasons: list[str] = []
        if candidate_rate < REPORT_CONFIG.risk_success_rate_threshold:
            reasons.append(f"成功率偏低({candidate_rate}%)")
        if delta_rate < REPORT_CONFIG.risk_delta_success_rate_threshold:
            reasons.append(f"成功率明显下降({delta_rate}%)")
        if delta_time > REPORT_CONFIG.risk_delta_time_ms_threshold:
            reasons.append(f"平均耗时上升({delta_time} ms)")
        if reasons:
            risk_items.append(
                {
                    "category": category,
                    "reasons": reasons,
                    "samples": image_index.get(category, [])[: REPORT_CONFIG.sample_reference_limit],
                }
            )
    return risk_items
