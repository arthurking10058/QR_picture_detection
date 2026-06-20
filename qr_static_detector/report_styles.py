from __future__ import annotations

from .config import REPORT_CONFIG


def build_base_html_style(*, include_line_height: bool = False, page_padding: str = "40px 24px 56px") -> str:
    line_height = "\n      line-height: 1.6;" if include_line_height else ""
    return f"""
    body {{
      margin: 0;
      background: {REPORT_CONFIG.html_page_background};
      color: {REPORT_CONFIG.html_text_color};
      font-family: {REPORT_CONFIG.html_font_family};{line_height}
    }}
    .page {{
      max-width: 1200px;
      margin: 0 auto;
      padding: {page_padding};
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
    .meta {{
      margin-top: 12px;
      color: {REPORT_CONFIG.html_meta_color};
      font-size: 14px;
    }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 16px;
      margin-top: 24px;
    }}
    .kpi {{
      background: {REPORT_CONFIG.html_kpi_background};
      border: 1px solid {REPORT_CONFIG.html_panel_border_color};
      border-radius: 14px;
      padding: 16px 18px;
    }}
    .kpi-label {{
      color: {REPORT_CONFIG.html_kpi_label_color};
      font-size: 13px;
    }}
    .kpi-value {{
      margin-top: 6px;
      font-size: 28px;
      font-weight: 700;
      color: {REPORT_CONFIG.html_kpi_value_color};
    }}
    .up {{
      color: {REPORT_CONFIG.html_positive_color};
      font-weight: 700;
    }}
    .down {{
      color: {REPORT_CONFIG.html_negative_color};
      font-weight: 700;
    }}
    .flat {{
      color: {REPORT_CONFIG.html_neutral_color};
      font-weight: 700;
    }}
    """
