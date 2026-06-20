from __future__ import annotations

import html

from .report_styles import build_base_html_style
from .report_text import SUMMARY_REPORT_TITLE


def build_summary_html_report(context: dict[str, object]) -> str:
    input_path = context["input_path"]
    overall_summary = context["overall_summary"]
    category_summary = context["category_summary"]
    run_meta = context["run_meta"]

    table_rows = []
    for row in category_summary:
        success_rate = float(row["success_rate"])
        rate_class = "up" if success_rate >= 80 else "flat" if success_rate >= 50 else "down"
        table_rows.append(
            f"""
            <tr>
              <td>{html.escape(str(row['category'] or '(uncategorized)'))}</td>
              <td>{row['image_count']}</td>
              <td>{row['success_count']}</td>
              <td class="{rate_class}">{row['success_rate']}%</td>
              <td>{row['detection_count']}</td>
              <td>{row['avg_time_ms']}</td>
            </tr>
            """
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{SUMMARY_REPORT_TITLE}</title>
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
      <h1>{SUMMARY_REPORT_TITLE}</h1>
      <div class="meta">输入文件：{html.escape(str(input_path))}</div>
      <div class="meta">运行时间：{html.escape(str(run_meta.get('run_started_at', '')))}</div>
      <div class="meta">运行命令：{html.escape(str(run_meta.get('command', '')))}</div>
      <div class="meta">输入摘要：{html.escape(str(run_meta.get('input_source', '')))}</div>
      <div class="kpis">
        <div class="kpi"><div class="kpi-label">图片总数</div><div class="kpi-value">{overall_summary['image_count']}</div></div>
        <div class="kpi"><div class="kpi-label">检测成功</div><div class="kpi-value">{overall_summary['success_count']}</div></div>
        <div class="kpi"><div class="kpi-label">成功率</div><div class="kpi-value">{overall_summary['success_rate']}%</div></div>
        <div class="kpi"><div class="kpi-label">平均耗时</div><div class="kpi-value">{overall_summary['avg_time_ms']} ms</div></div>
      </div>
    </section>
    <section class="panel" style="margin-top: 24px;">
      <h2>分类汇总</h2>
      <table>
        <thead>
          <tr>
            <th>category</th>
            <th>images</th>
            <th>success</th>
            <th>success_rate</th>
            <th>detections</th>
            <th>avg_time_ms</th>
          </tr>
        </thead>
        <tbody>
          {''.join(table_rows)}
        </tbody>
      </table>
    </section>
  </div>
</body>
</html>
"""
