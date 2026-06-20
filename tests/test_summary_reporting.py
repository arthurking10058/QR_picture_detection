from __future__ import annotations

import unittest
from pathlib import Path

from qr_static_detector.summary_reporting import (
    build_summary_html_report,
    build_summary_markdown_report,
    build_summary_report_context,
    summarize_images_by_category,
    summarize_overall_results,
    summarize_result_rows_by_image,
)


class SummaryReportingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            {
                "image": "qrcodes/demo/nominal_image001.jpg",
                "category": "nominal",
                "index": "1",
                "success": "True",
                "data": "payload-1",
                "method": "pyzbar",
                "variant": "nominal_01",
                "points": "",
                "time_ms": "12.5",
                "output": "outputs/runtime_outputs/images/nominal_image001_detected.png",
            },
            {
                "image": "qrcodes/demo/glare_image001.jpg",
                "category": "glare",
                "index": "0",
                "success": "False",
                "data": "",
                "method": "",
                "variant": "",
                "points": "",
                "time_ms": "30.0",
                "output": "outputs/runtime_outputs/images/glare_image001_detected.png",
            },
        ]

    def test_summary_aggregation_and_reports(self) -> None:
        image_summary = summarize_result_rows_by_image(self.rows)
        self.assertEqual(len(image_summary), 2)
        self.assertTrue(image_summary[1]["success"] is True or image_summary[0]["success"] is True)

        category_summary = summarize_images_by_category(image_summary)
        overall_summary = summarize_overall_results(image_summary)

        self.assertEqual(overall_summary["image_count"], 2)
        self.assertEqual(overall_summary["success_count"], 1)
        self.assertEqual(overall_summary["success_rate"], 50.0)

        context = build_summary_report_context(
            Path("outputs/runtime_outputs/results.csv"),
            overall_summary,
            category_summary,
            {
                "run_started_at": "2026-06-20T10:00:00+08:00",
                "command": "python app.py qrcodes/demo --save-json --summarize",
                "input_source": "qrcodes/demo",
            },
        )

        markdown = build_summary_markdown_report(context)
        html = build_summary_html_report(context)

        self.assertIn("QR 检测结果汇总", markdown)
        self.assertIn("分类汇总", markdown)
        self.assertIn("QR 检测结果汇总", html)
        self.assertIn("<table>", html)
        self.assertIn("nominal", html)


if __name__ == "__main__":
    unittest.main()
