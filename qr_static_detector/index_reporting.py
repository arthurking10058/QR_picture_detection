from __future__ import annotations

from pathlib import Path

from .config import REPORT_CONFIG
from .reporting_common import extract_meta_text, read_json_dict, safe_float


def collect_comparison_index_items(root: Path) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    seen_paths: set[Path] = set()
    for overall_file in sorted(root.rglob(REPORT_CONFIG.comparison_glob_pattern)):
        payload = read_json_dict(overall_file)
        if not payload:
            continue
        parent = overall_file.parent
        resolved_parent = parent.resolve()
        if resolved_parent in seen_paths:
            continue
        seen_paths.add(resolved_parent)
        name = parent.name
        items.append(
            {
                "name": name,
                "path": str(parent),
                "avg_delta_success_rate": safe_float(payload.get("avg_delta_success_rate")),
                "improved_categories": int(safe_float(payload.get("improved_categories"))),
                "regressed_categories": int(safe_float(payload.get("regressed_categories"))),
                "best_delta_success_rate": safe_float(payload.get("best_delta_success_rate")),
                "worst_delta_success_rate": safe_float(payload.get("worst_delta_success_rate")),
                "baseline_run": extract_meta_text(payload.get("baseline_meta", {}), "run_started_at")
                if isinstance(payload.get("baseline_meta", {}), dict)
                else "",
                "candidate_run": extract_meta_text(payload.get("candidate_meta", {}), "run_started_at")
                if isinstance(payload.get("candidate_meta", {}), dict)
                else "",
                "report_html": str(parent / f"{name}_report.html"),
            }
        )
    return items


def build_index_chart_paths(output_dir: Path, name: str) -> dict[str, Path]:
    return {
        "trend_chart": output_dir / f"{name}_avg_delta_trend.png",
        "risk_chart": output_dir / f"{name}_risk_category_trend.png",
    }


def create_index_line_chart(
    plt_module,
    labels: list[str],
    values: list[float],
    title: str,
    ylabel: str,
    output: Path,
) -> None:
    fig, ax = plt_module.subplots(figsize=(REPORT_CONFIG.chart_width, 4.5))
    ax.plot(labels, values, marker="o", color=REPORT_CONFIG.chart_line_color)
    ax.axhline(0, color=REPORT_CONFIG.chart_zero_line_color, linewidth=1)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", linestyle="--", alpha=REPORT_CONFIG.chart_grid_alpha)
    fig.autofmt_xdate(rotation=20)
    fig.tight_layout()
    fig.savefig(output, dpi=REPORT_CONFIG.chart_dpi, bbox_inches="tight")
    plt_module.close(fig)


def create_index_bar_chart(
    plt_module,
    labels: list[str],
    values: list[int],
    title: str,
    ylabel: str,
    output: Path,
) -> None:
    fig, ax = plt_module.subplots(figsize=(REPORT_CONFIG.chart_width, 4.5))
    ax.bar(labels, values, color=REPORT_CONFIG.index_risk_bar_color)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", linestyle="--", alpha=REPORT_CONFIG.chart_grid_alpha)
    fig.autofmt_xdate(rotation=20)
    fig.tight_layout()
    fig.savefig(output, dpi=REPORT_CONFIG.chart_dpi, bbox_inches="tight")
    plt_module.close(fig)


def generate_comparison_index_charts(
    plt_module,
    items: list[dict[str, object]],
    trend_chart: Path,
    risk_chart: Path,
) -> list[Path]:
    if plt_module is None or not items:
        return []
    names = [str(item["name"]) for item in items]
    avg_deltas = [float(item["avg_delta_success_rate"]) for item in items]
    risk_counts = [int(item["regressed_categories"]) for item in items]

    charts: list[Path] = []
    create_index_line_chart(plt_module, names, avg_deltas, "多次实验平均成功率变化", "avg delta success rate (%)", trend_chart)
    charts.append(trend_chart)
    create_index_bar_chart(plt_module, names, risk_counts, "多次实验退化类别数", "regressed categories", risk_chart)
    charts.append(risk_chart)
    return charts


def build_comparison_index_markdown(items: list[dict[str, object]], charts: list[Path]) -> str:
    lines = [
        "# 多次实验对比总览",
        "",
        f"- 对比次数: `{len(items)}`",
        "",
    ]
    for chart in charts:
        lines.append(f"![{chart.stem}]({chart.name})")
        lines.append("")
    lines.extend(
        [
            "| name | avg_delta | improved | regressed | best_delta | worst_delta | report_html |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for item in items:
        lines.append(
            f"| {item['name']} | {item['avg_delta_success_rate']} | {item['improved_categories']} | {item['regressed_categories']} | {item['best_delta_success_rate']} | {item['worst_delta_success_rate']} | {item['report_html']} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_comparison_index_html(items: list[dict[str, object]], charts: list[Path]) -> str:
    chart_html = "".join(
        f"<section class='panel'><h2>{chart.stem}</h2><img src='{chart.name}' alt='{chart.stem}'></section>"
        for chart in charts
    )
    row_html = "".join(
        f"""
        <tr>
          <td>{item['name']}</td>
          <td>{item['avg_delta_success_rate']}</td>
          <td>{item['improved_categories']}</td>
          <td>{item['regressed_categories']}</td>
          <td>{item['best_delta_success_rate']}</td>
          <td>{item['worst_delta_success_rate']}</td>
          <td><code>{item['report_html']}</code></td>
        </tr>
        """
        for item in items
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>多次实验对比总览</title>
  <style>
    body {{
      margin: 0;
      background: {REPORT_CONFIG.html_page_background};
      color: {REPORT_CONFIG.html_text_color};
      font-family: {REPORT_CONFIG.html_font_family};
    }}
    .page {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 36px 24px 52px;
    }}
    .hero {{
      padding: 24px 28px;
      border-radius: 18px;
      background: {REPORT_CONFIG.html_hero_background};
      border: 1px solid {REPORT_CONFIG.html_hero_border_color};
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
      margin-top: 24px;
    }}
    .panel {{
      background: {REPORT_CONFIG.html_panel_background};
      border: 1px solid {REPORT_CONFIG.html_panel_border_color};
      border-radius: 16px;
      padding: 18px;
    }}
    img {{
      width: 100%;
      border-radius: 12px;
      background: #fff;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 24px;
      background: {REPORT_CONFIG.html_panel_background};
      border: 1px solid {REPORT_CONFIG.html_panel_border_color};
    }}
    th, td {{
      padding: 12px 14px;
      border-bottom: 1px solid {REPORT_CONFIG.html_table_row_border_color};
      text-align: left;
      font-size: 14px;
    }}
    th {{
      color: {REPORT_CONFIG.html_meta_color};
      background: {REPORT_CONFIG.html_table_header_background};
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>多次实验对比总览</h1>
      <p>对比次数：{len(items)}</p>
    </section>
    <div class="grid">{chart_html}</div>
    <table>
      <thead>
        <tr>
          <th>name</th>
          <th>avg_delta</th>
          <th>improved</th>
          <th>regressed</th>
          <th>best_delta</th>
          <th>worst_delta</th>
          <th>report_html</th>
        </tr>
      </thead>
      <tbody>{row_html}</tbody>
    </table>
  </div>
</body>
</html>
"""
