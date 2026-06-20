from __future__ import annotations

import html
from pathlib import Path

from .config import REPORT_CONFIG
from .report_text import NO_CATEGORY_PORTRAITS_TEXT
from .reporting_common import extract_meta_text, safe_float


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


def build_failure_clusters(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for row in rows:
        if row.get("success") == "True":
            continue
        category = row.get("category", "") or "(uncategorized)"
        grouped.setdefault(category, {"count": 0, "samples": []})
        grouped[category]["count"] += 1
        grouped[category]["samples"].append(build_sample_ref(row))

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


def make_check(text: str, priority: str, trigger_token: str) -> dict[str, object]:
    return {
        "text": text,
        "priority": priority,
        "trigger_token": trigger_token,
        "triggered": False,
        "covered": False,
    }


def top_method_check(methods: list[tuple[str, int]]) -> dict[str, object] | None:
    return make_check(f"优先复核方法 {methods[0][0]} 的命中条件。", "高", "双解码器") if methods else None


def top_variant_check(variants: list[tuple[str, int]]) -> dict[str, object] | None:
    return make_check(f"优先复核变体 {variants[0][0]} 的生成逻辑与触发顺序。", "高", "展开") if variants else None


def prioritize_checks(primary_reason: str, items: list[dict[str, object]]) -> list[dict[str, object]]:
    unique_items = []
    seen = set()
    for item in items:
        if not item:
            continue
        key = str(item["text"])
        if key in seen:
            continue
        seen.add(key)
        item["triggered"] = bool(item.get("trigger_token") and item["trigger_token"] in primary_reason)
        item["covered"] = item["triggered"] or item["priority"] == "中"
        unique_items.append(item)
    if "双解码器" in primary_reason:
        unique_items.sort(key=lambda item: 0 if "解码器" in item["text"] or "OpenCV" in item["text"] or "pyzbar" in item["text"] else 1)
    elif "多尺度" in primary_reason:
        unique_items.sort(key=lambda item: 0 if "尺度" in item["text"] or "缩放" in item["text"] else 1)
    elif "透视" in primary_reason or "展开" in primary_reason:
        unique_items.sort(key=lambda item: 0 if "透视" in item["text"] or "warp" in item["text"] or "展开" in item["text"] else 1)
    return unique_items


def build_recommendation_checklist(
    category: str,
    primary_reason: str,
    methods: list[tuple[str, int]],
    variants: list[tuple[str, int]],
) -> list[dict[str, object]]:
    category_key = category.lower()
    if category_key == "glare":
        return prioritize_checks(
            primary_reason,
            [
                make_check("核对高亮掩膜阈值是否过高或过低，确认反光区域被完整捕获。", "高", "高亮"),
                make_check("复查 inpaint 半径与高亮修复后的残留反光斑点。", "高", "高亮"),
                make_check("确认 glare 多尺度候选是否覆盖到有效码区尺寸。", "中", "多尺度"),
                make_check("检查高亮修复后 pyzbar / OpenCV 的解码顺序是否合理。", "高", "双解码器"),
                top_method_check(methods),
                top_variant_check(variants),
            ],
        )
    if category_key == "high_version":
        return prioritize_checks(
            primary_reason,
            [
                make_check("核对高版本码的大尺度候选是否过早缩小，保留高密度细节。", "高", "多尺度"),
                make_check("复查 threshold / CLAHE 分支是否覆盖高版本样本。", "高", "多尺度"),
                make_check("检查高密度码是否在模糊或阈值阶段被抹平。", "高", "多尺度"),
                make_check("确认双解码器顺序是否适合高版本码。", "高", "双解码器"),
                top_method_check(methods),
                top_variant_check(variants),
            ],
        )
    if category_key == "curved":
        return prioritize_checks(
            primary_reason,
            [
                make_check("复查曲面样本的 warp 兜底和透视展开是否真正触发。", "高", "透视"),
                make_check("检查 Sauvola / 自适应阈值组合是否适合曲面局部对比度。", "中", "展开"),
                make_check("确认是否需要增加更强的几何展开候选。", "高", "展开"),
                make_check("核对曲面样本是否在旋转候选后仍存在局部遮挡。", "中", "透视"),
                top_method_check(methods),
                top_variant_check(variants),
            ],
        )
    if category_key == "perspective":
        return prioritize_checks(
            primary_reason,
            [
                make_check("检查 perspective 类的 warp 校正链路是否被触发。", "高", "透视"),
                make_check("复查旋转候选和二值化组合对大角度透视样本的覆盖。", "中", "透视"),
                make_check("确认透视兜底后的码区是否仍保留有效定位图案。", "高", "透视"),
                top_method_check(methods),
                top_variant_check(variants),
            ],
        )
    if category_key == "damaged":
        return prioritize_checks(
            primary_reason,
            [
                make_check("检查闭运算、阈值化与多尺度顺序是否保留了定位图案。", "高", "多尺度"),
                make_check("确认损伤样本的关键数据区是否在预处理后进一步丢失。", "高", "展开"),
                make_check("复查损伤样本是否需要更保守的锐化或二值化策略。", "中", "双解码器"),
                top_method_check(methods),
                top_variant_check(variants),
            ],
        )
    if category_key == "brightness":
        return prioritize_checks(
            primary_reason,
            [
                make_check("检查 gamma 校正范围是否过强或过弱。", "高", "多尺度"),
                make_check("复查 CLAHE 强度对过曝 / 欠曝样本的影响。", "中", "双解码器"),
                make_check("确认亮暗样本分流是否合理，避免细节继续丢失。", "中", "多尺度"),
                top_method_check(methods),
                top_variant_check(variants),
            ],
        )
    if "透视" in primary_reason or "展开" in primary_reason:
        return prioritize_checks(primary_reason, [make_check("优先检查透视校正链路。", "高", "透视"), make_check("复查 warp 兜底是否被触发。", "高", "透视"), top_variant_check(variants)])
    if "多尺度" in primary_reason:
        return prioritize_checks(primary_reason, [make_check("优先检查缩放范围。", "高", "多尺度"), make_check("复查阈值策略。", "中", "多尺度"), top_method_check(methods), top_variant_check(variants)])
    if "双解码器" in primary_reason:
        return prioritize_checks(primary_reason, [make_check("优先检查 OpenCV / pyzbar 顺序。", "高", "双解码器"), make_check("复查输入灰度质量。", "中", "双解码器"), top_method_check(methods)])
    if methods:
        return prioritize_checks(primary_reason, [top_method_check(methods), make_check("检查相关预处理是否过强。", "中", "双解码器")])
    if variants:
        return prioritize_checks(primary_reason, [top_variant_check(variants), make_check("复查该类别的解码顺序与兜底路径。", "中", "双解码器")])
    return prioritize_checks(primary_reason, [make_check("优先检查该类别的预处理参数。", "中", "多尺度"), make_check("复查解码顺序和兜底路径是否匹配。", "中", "双解码器")])


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
        portraits.append(
            {
                "category": category,
                "primary_reason": primary_reason,
                "secondary_reason": secondary_reason,
                "common_failed_methods": [name for name, _ in methods[: REPORT_CONFIG.sample_reference_limit]],
                "common_failed_variants": [name for name, _ in variants[: REPORT_CONFIG.sample_reference_limit]],
                "recommended_checks": build_recommendation_checklist(
                    category,
                    primary_reason,
                    methods,
                    variants,
                ),
                "sample_refs": image_index.get(category, [])[: REPORT_CONFIG.sample_reference_limit],
                "sample_refs_inline": format_sample_refs_inline(image_index.get(category, [])[: REPORT_CONFIG.sample_reference_limit]),
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
