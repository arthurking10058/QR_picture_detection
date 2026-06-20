from __future__ import annotations

import html

from .comparison_analysis import render_html_sample_refs_inline
from .report_styles import build_base_html_style
from .report_text import (
    COMPARISON_REPORT_TITLE,
    NO_FAILURE_REASONS_TEXT,
    NO_METHOD_DATA_TEXT,
    NO_STABLE_FAILURES_TEXT,
    NO_TREND_TEXT,
    NO_VARIANT_DATA_TEXT,
)
from .reporting_common import extract_meta_text


def render_html_risk_categories(items: list[dict[str, object]]) -> str:
    if not items:
        return "<ul><li>无明显高风险类别。</li></ul>"
    lis = []
    for item in items:
        sample_html = ""
        if item.get("samples"):
            sample_html = f"<div class='meta'>关联样本:<br>{render_html_sample_refs_inline(item['samples'])}</div>"
        lis.append(f"<li><strong>{html.escape(str(item['category']))}</strong>: {'，'.join(html.escape(str(r)) for r in item['reasons'])}{sample_html}</li>")
    return "<ul>" + "".join(lis) + "</ul>"


def render_html_failure_clusters(items: list[dict[str, object]]) -> str:
    if not items:
        return "<ul><li>未发现显著失败聚类。</li></ul>"
    lis = []
    for item in items:
        lis.append(
            f"<li><strong>{html.escape(str(item['category']))}</strong>: 失败图片 {item['count']} 张"
            f"<div class='meta'>关联样本:<br>{render_html_sample_refs_inline(item.get('samples', []))}</div></li>"
        )
    return "<ul>" + "".join(lis) + "</ul>"


def render_category_portrait_cards(portraits: list[dict[str, object]]) -> str:
    if not portraits:
        return "<p>当前缺少足够的类别级失败轨迹。</p>"
    cards = []
    for portrait in portraits:
        cards.append(
            f"""
            <section class="panel" style="margin-top: 16px;">
              <h3>{html.escape(str(portrait['category']))}</h3>
              <p><strong>主要失败原因:</strong> {html.escape(str(portrait['primary_reason']))}</p>
              <p><strong>次要失败原因:</strong> {html.escape(str(portrait['secondary_reason']))}</p>
              <p><strong>常见失效方法:</strong> {html.escape(', '.join(portrait['common_failed_methods']) or '无')}</p>
              <p><strong>常见失效变体:</strong> {html.escape(', '.join(portrait['common_failed_variants']) or '无')}</p>
              <p><strong>关联失败样本:</strong> {render_html_sample_refs_inline(portrait.get('sample_refs', []))}</p>
              <p><strong>推荐排查方向:</strong></p>
              <ul>
                {''.join(f"<li><strong>[{html.escape(item['priority'])}]</strong> {'[触发]' if item['triggered'] else '[观察]'} {'[已覆盖]' if item['covered'] else '[待排查]'} {html.escape(item['text'])}</li>" for item in portrait['recommended_checks'])}
              </ul>
            </section>
            """
        )
    return "".join(cards)


def build_comparison_html_report(context: dict[str, object]) -> str:
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

    chart_blocks = []
    for chart in generated_charts:
        if chart.is_file():
            chart_blocks.append(
                f"""
                <section class="panel">
                  <h2>{html.escape(chart.stem)}</h2>
                  <img src="{chart.name}" alt="{html.escape(chart.stem)}" />
                </section>
                """
            )

    table_rows = []
    for row in rows:
        delta_rate = float(row["delta_success_rate"])
        delta_time = float(row["delta_avg_time_ms"])
        rate_class = "up" if delta_rate > 0 else "down" if delta_rate < 0 else "flat"
        time_class = "up" if delta_time > 0 else "down" if delta_time < 0 else "flat"
        table_rows.append(
            f"""
            <tr>
              <td>{html.escape(str(row['category'] or '(uncategorized)'))}</td>
              <td>{row['baseline_success_rate']}%</td>
              <td>{row['candidate_success_rate']}%</td>
              <td class="{rate_class}">{row['delta_success_rate']}%</td>
              <td>{row['baseline_avg_time_ms']}</td>
              <td>{row['candidate_avg_time_ms']}</td>
              <td class="{time_class}">{row['delta_avg_time_ms']}</td>
            </tr>
            """
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{COMPARISON_REPORT_TITLE}</title>
  <style>
    {build_base_html_style(include_line_height=True)}
    .hero {{
      box-shadow: var(--hero-shadow, 0 18px 50px rgba(2,6,23,.28));
    }}
    h1, h2 {{
      margin: 0 0 12px 0;
    }}
    table {{
      border-radius: 16px;
      overflow: hidden;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>{COMPARISON_REPORT_TITLE}</h1>
      <div class="meta">基线文件：{html.escape(str(baseline_path))}</div>
      <div class="meta">对比文件：{html.escape(str(candidate_path))}</div>
      <div class="meta">基线运行：{html.escape(extract_meta_text(baseline_meta, 'run_started_at'))}</div>
      <div class="meta">对比运行：{html.escape(extract_meta_text(candidate_meta, 'run_started_at'))}</div>
      <div class="meta">基线命令：{html.escape(extract_meta_text(baseline_meta, 'command'))}</div>
      <div class="meta">对比命令：{html.escape(extract_meta_text(candidate_meta, 'command'))}</div>
      <div class="kpis">
        <div class="kpi"><div class="kpi-label">类别数</div><div class="kpi-value">{overall['category_count']}</div></div>
        <div class="kpi"><div class="kpi-label">提升类别数</div><div class="kpi-value">{overall['improved_categories']}</div></div>
        <div class="kpi"><div class="kpi-label">下降类别数</div><div class="kpi-value">{overall['regressed_categories']}</div></div>
        <div class="kpi"><div class="kpi-label">平均成功率变化</div><div class="kpi-value">{overall['avg_delta_success_rate']}%</div></div>
      </div>
    </section>
    <div class="grid">
      <section class="panel">
        <h2>最佳提升类别</h2>
        <div class="kpi-value">{html.escape(str(best_improved['category'])) if best_improved else '-'}</div>
        <div class="meta">{best_improved['delta_success_rate'] if best_improved else '-' }%</div>
      </section>
      <section class="panel">
        <h2>最大退化类别</h2>
        <div class="kpi-value">{html.escape(str(worst_regressed['category'])) if worst_regressed else '-'}</div>
        <div class="meta">{worst_regressed['delta_success_rate'] if worst_regressed else '-' }%</div>
      </section>
    </div>
    <section class="panel" style="margin-top: 24px;">
      <h2>本次实验摘要</h2>
      <ul>
        {''.join(f'<li>{html.escape(line)}</li>' for line in insight_lines)}
      </ul>
    </section>
    <div class="grid">
      <section class="panel">
        <h2>高风险类别提示</h2>
        {render_html_risk_categories(risk_categories)}
      </section>
      <section class="panel">
        <h2>失败样本聚类</h2>
        {render_html_failure_clusters(failure_clusters)}
      </section>
    </div>
    <div class="grid">
      <section class="panel">
        <h2>失败原因归类</h2>
        <ul>
          {''.join(f'<li>{html.escape(line)}</li>' for line in failure_reasons) if failure_reasons else f'<li>{NO_FAILURE_REASONS_TEXT}</li>'}
        </ul>
      </section>
      <section class="panel">
        <h2>风险趋势</h2>
        <ul>
          {''.join(f'<li>{html.escape(line)}</li>' for line in trend_lines) if trend_lines else f'<li>{NO_TREND_TEXT}</li>'}
        </ul>
      </section>
    </div>
    <section class="panel" style="margin-top: 24px;">
      <h2>类别级根因画像</h2>
      {render_category_portrait_cards(category_portraits)}
    </section>
    <section class="panel" style="margin-top: 24px;">
      <h2>稳定失效链路</h2>
      <ul>
        {''.join(f'<li>{html.escape(line)}</li>' for line in stable_failures) if stable_failures else f'<li>{NO_STABLE_FAILURES_TEXT}</li>'}
      </ul>
    </section>
    <div class="grid">
      <section class="panel">
        <h2>方法命中排行榜</h2>
        <ol>
          {''.join(f'<li>{html.escape(line)}</li>' for line in method_rankings) if method_rankings else f'<li>{NO_METHOD_DATA_TEXT}</li>'}
        </ol>
      </section>
      <section class="panel">
        <h2>变体命中排行榜</h2>
        <ol>
          {''.join(f'<li>{html.escape(line)}</li>' for line in variant_rankings) if variant_rankings else f'<li>{NO_VARIANT_DATA_TEXT}</li>'}
        </ol>
      </section>
    </div>
    <div class="grid">
      {''.join(chart_blocks)}
    </div>
    <table>
      <thead>
        <tr>
          <th>category</th>
          <th>baseline_rate</th>
          <th>candidate_rate</th>
          <th>delta_rate</th>
          <th>baseline_time</th>
          <th>candidate_time</th>
          <th>delta_time</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""
