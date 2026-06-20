from __future__ import annotations

from .comparison_analysis import (
    build_markdown_category_portraits,
    render_markdown_failure_clusters,
    render_markdown_risk_categories,
)
from .report_text import (
    COMPARISON_REPORT_TITLE,
    NO_FAILURE_REASONS_TEXT,
    NO_METHOD_DATA_TEXT,
    NO_STABLE_FAILURES_TEXT,
    NO_TREND_TEXT,
    NO_VARIANT_DATA_TEXT,
)
from .reporting_common import extract_meta_text


def build_comparison_markdown_report(context: dict[str, object]) -> str:
    baseline_path = context["baseline_path"]
    candidate_path = context["candidate_path"]
    overall = context["overall"]
    rows = context["rows"]
    generated_charts = context["generated_charts"]
    best_improved = context["best_improved"]
    worst_regressed = context["worst_regressed"]
    insight_lines = context["insight_lines"]
    risk_categories = context["risk_categories"]
    failure_clusters = context["failure_clusters"]
    failure_reasons = context["failure_reasons"]
    category_portraits = context["category_portraits"]
    trend_lines = context["trend_lines"]
    stable_failures = context["stable_failures"]
    method_rankings = context["method_rankings"]
    variant_rankings = context["variant_rankings"]
    baseline_meta = context["baseline_meta"]
    candidate_meta = context["candidate_meta"]

    lines = [
        f"# {COMPARISON_REPORT_TITLE}",
        "",
        f"- 基线文件: `{baseline_path}`",
        f"- 对比文件: `{candidate_path}`",
        f"- 基线运行时间: `{extract_meta_text(baseline_meta, 'run_started_at')}`",
        f"- 对比运行时间: `{extract_meta_text(candidate_meta, 'run_started_at')}`",
        f"- 基线命令: `{extract_meta_text(baseline_meta, 'command')}`",
        f"- 对比命令: `{extract_meta_text(candidate_meta, 'command')}`",
        f"- 类别数: `{overall['category_count']}`",
        f"- 提升类别数: `{overall['improved_categories']}`",
        f"- 下降类别数: `{overall['regressed_categories']}`",
        f"- 持平类别数: `{overall['unchanged_categories']}`",
        f"- 平均成功率变化: `{overall['avg_delta_success_rate']}%`",
        "",
        "## 结论卡片",
        "",
        f"- 最佳提升类别: `{best_improved['category'] if best_improved else ''}` ({best_improved['delta_success_rate']}%)" if best_improved else "- 最佳提升类别: `-`",
        f"- 最大退化类别: `{worst_regressed['category'] if worst_regressed else ''}` ({worst_regressed['delta_success_rate']}%)" if worst_regressed else "- 最大退化类别: `-`",
        "",
        "## 本次实验摘要",
        "",
        *[f"- {line}" for line in insight_lines],
        "",
        "## 高风险类别提示",
        "",
        *render_markdown_risk_categories(risk_categories),
        "",
        "## 失败样本聚类",
        "",
        *render_markdown_failure_clusters(failure_clusters),
        "",
        "## 失败原因归类",
        "",
        *([f"- {line}" for line in failure_reasons] if failure_reasons else [f"- {NO_FAILURE_REASONS_TEXT}"]),
        "",
        "## 类别级根因画像",
        "",
        *build_markdown_category_portraits(category_portraits),
        "",
        "## 风险趋势",
        "",
        *([f"- {line}" for line in trend_lines] if trend_lines else [f"- {NO_TREND_TEXT}"]),
        "",
        "## 稳定失效链路",
        "",
        *([f"- {line}" for line in stable_failures] if stable_failures else [f"- {NO_STABLE_FAILURES_TEXT}"]),
        "",
        "## 方法命中排行榜",
        "",
        *([f"- {line}" for line in method_rankings] if method_rankings else [f"- {NO_METHOD_DATA_TEXT}"]),
        "",
        "## 变体命中排行榜",
        "",
        *([f"- {line}" for line in variant_rankings] if variant_rankings else [f"- {NO_VARIANT_DATA_TEXT}"]),
        "",
    ]
    if generated_charts:
        lines.extend(["## 对比图表", ""])
        for chart_path in generated_charts:
            lines.append(f"![{chart_path.stem}]({chart_path.name})")
            lines.append("")
    lines.extend(
        [
            "## 分类变化",
            "",
            "| category | baseline_rate | candidate_rate | delta_rate | baseline_time | candidate_time | delta_time |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['category'] or '(uncategorized)'} | {row['baseline_success_rate']}% | {row['candidate_success_rate']}% | {row['delta_success_rate']}% | {row['baseline_avg_time_ms']} | {row['candidate_avg_time_ms']} | {row['delta_avg_time_ms']} |"
        )
    lines.append("")
    return "\n".join(lines)
