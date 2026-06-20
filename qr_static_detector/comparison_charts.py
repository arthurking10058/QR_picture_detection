from __future__ import annotations

from pathlib import Path

from .comparison_metrics import aggregate_method_hits
from .config import REPORT_CONFIG
from .reporting_common import safe_float


def build_report_chart_paths(report_dir: Path, name: str) -> dict[str, Path]:
    return {
        "success_chart": report_dir / f"{name}_success_rate_delta.png",
        "time_chart": report_dir / f"{name}_avg_time_delta.png",
        "input_chart": report_dir / f"{name}_input_distribution.png",
        "method_chart": report_dir / f"{name}_method_hits.png",
    }


def compute_chart_figure_height(item_count: int) -> float:
    return max(REPORT_CONFIG.chart_min_height, item_count * REPORT_CONFIG.chart_row_height_factor)


def create_comparison_bar_chart(
    plt_module,
    categories: list[str],
    values: list[float],
    title: str,
    ylabel: str,
    output_path: Path,
    positive_color: str,
    negative_color: str,
) -> None:
    fig, ax = plt_module.subplots(figsize=(REPORT_CONFIG.chart_width, compute_chart_figure_height(len(categories))))
    colors = [positive_color if value >= 0 else negative_color for value in values]
    ax.barh(categories, values, color=colors)
    ax.axvline(0, color=REPORT_CONFIG.chart_zero_line_color, linewidth=1)
    ax.set_title(title)
    ax.set_xlabel(ylabel)
    ax.grid(axis="x", linestyle="--", alpha=REPORT_CONFIG.chart_grid_alpha)
    fig.tight_layout()
    fig.savefig(output_path, dpi=REPORT_CONFIG.chart_dpi, bbox_inches="tight")
    plt_module.close(fig)


def create_comparison_grouped_bar_chart(
    plt_module,
    categories: list[str],
    left_values: list[float],
    right_values: list[float],
    title: str,
    ylabel: str,
    output_path: Path,
    left_label: str,
    right_label: str,
    left_color: str,
    right_color: str,
) -> None:
    import numpy as np

    y = np.arange(len(categories))
    fig, ax = plt_module.subplots(figsize=(REPORT_CONFIG.chart_width, compute_chart_figure_height(len(categories))))
    height = REPORT_CONFIG.grouped_bar_height
    ax.barh(y - height / 2, left_values, height=height, color=left_color, label=left_label)
    ax.barh(y + height / 2, right_values, height=height, color=right_color, label=right_label)
    ax.set_yticks(y)
    ax.set_yticklabels(categories)
    ax.set_title(title)
    ax.set_xlabel(ylabel)
    ax.legend()
    ax.grid(axis="x", linestyle="--", alpha=REPORT_CONFIG.chart_grid_alpha)
    fig.tight_layout()
    fig.savefig(output_path, dpi=REPORT_CONFIG.chart_dpi, bbox_inches="tight")
    plt_module.close(fig)


def generate_comparison_charts(
    plt_module,
    rows: list[dict[str, object]],
    baseline_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
    baseline_image_rows: list[dict[str, str]],
    candidate_image_rows: list[dict[str, str]],
    success_chart_path: Path,
    time_chart_path: Path,
    input_chart_path: Path,
    method_chart_path: Path,
) -> list[Path]:
    if plt_module is None or not rows:
        return []

    categories = [str(row["category"] or "(uncategorized)") for row in rows]
    success_deltas = [float(row["delta_success_rate"]) for row in rows]
    time_deltas = [float(row["delta_avg_time_ms"]) for row in rows]

    chart_paths: list[Path] = []

    create_comparison_bar_chart(
        plt_module,
        categories,
        success_deltas,
        "按类别成功率变化",
        "成功率变化 (%)",
        success_chart_path,
        positive_color=REPORT_CONFIG.comparison_success_positive_color,
        negative_color=REPORT_CONFIG.comparison_success_negative_color,
    )
    chart_paths.append(success_chart_path)

    create_comparison_bar_chart(
        plt_module,
        categories,
        time_deltas,
        "按类别平均耗时变化",
        "平均耗时变化 (ms)",
        time_chart_path,
        positive_color=REPORT_CONFIG.comparison_time_positive_color,
        negative_color=REPORT_CONFIG.comparison_time_negative_color,
    )
    chart_paths.append(time_chart_path)

    baseline_counts = {row["category"]: safe_float(row.get("image_count")) for row in baseline_rows}
    candidate_counts = {row["category"]: safe_float(row.get("image_count")) for row in candidate_rows}
    create_comparison_grouped_bar_chart(
        plt_module,
        categories,
        [baseline_counts.get(category, 0.0) for category in categories],
        [candidate_counts.get(category, 0.0) for category in categories],
        "按类别输入样本分布",
        "图片数",
        input_chart_path,
        left_label="baseline",
        right_label="candidate",
        left_color=REPORT_CONFIG.input_baseline_color,
        right_color=REPORT_CONFIG.input_candidate_color,
    )
    chart_paths.append(input_chart_path)

    baseline_method_counts = aggregate_method_hits(baseline_image_rows)
    candidate_method_counts = aggregate_method_hits(candidate_image_rows)
    method_names = sorted(set(baseline_method_counts) | set(candidate_method_counts))
    if method_names:
        create_comparison_grouped_bar_chart(
            plt_module,
            method_names,
            [baseline_method_counts.get(name, 0) for name in method_names],
            [candidate_method_counts.get(name, 0) for name in method_names],
            "方法命中分布",
            "命中图片数",
            method_chart_path,
            left_label="baseline",
            right_label="candidate",
            left_color=REPORT_CONFIG.method_baseline_color,
            right_color=REPORT_CONFIG.method_candidate_color,
        )
        chart_paths.append(method_chart_path)

    return chart_paths
