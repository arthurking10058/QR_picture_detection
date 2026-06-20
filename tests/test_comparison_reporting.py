from __future__ import annotations

import unittest

from qr_static_detector.comparison_checklists import build_recommendation_checklist
from qr_static_detector.comparison_metrics import compare_summary_rows, summarize_comparison_delta


class ComparisonReportingTests(unittest.TestCase):
    def test_compare_summary_rows_and_delta(self) -> None:
        baseline_rows = [
            {"category": "glare", "image_count": "10", "success_count": "8", "success_rate": "80", "avg_time_ms": "100"},
            {"category": "nominal", "image_count": "5", "success_count": "5", "success_rate": "100", "avg_time_ms": "50"},
        ]
        candidate_rows = [
            {"category": "glare", "image_count": "10", "success_count": "9", "success_rate": "90", "avg_time_ms": "110"},
            {"category": "nominal", "image_count": "5", "success_count": "4", "success_rate": "80", "avg_time_ms": "45"},
        ]

        rows = compare_summary_rows(baseline_rows, candidate_rows)
        overall = summarize_comparison_delta(rows)

        self.assertEqual(len(rows), 2)
        self.assertEqual(overall["category_count"], 2)
        self.assertEqual(overall["improved_categories"], 1)
        self.assertEqual(overall["regressed_categories"], 1)

    def test_build_recommendation_checklist(self) -> None:
        checks = build_recommendation_checklist(
            "glare",
            "双解码器都未命中",
            [("pyzbar", 3)],
            [("glare_01", 2)],
        )
        self.assertTrue(checks)
        self.assertTrue(any("pyzbar" in item["text"] or "OpenCV" in item["text"] for item in checks))


if __name__ == "__main__":
    unittest.main()
