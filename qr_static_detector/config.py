from __future__ import annotations

from dataclasses import dataclass


CATEGORY_CHOICES: tuple[str, ...] = (
    "nominal",
    "blurred",
    "bright_spots",
    "brightness",
    "close",
    "curved",
    "damaged",
    "glare",
    "high_version",
    "lots",
    "monitor",
    "noncompliant",
    "pathological",
    "perspective",
    "rotations",
    "shadows",
)

CATEGORY_LABELS: dict[str, str] = {
    "nominal": "正常",
    "blurred": "模糊",
    "bright_spots": "亮斑",
    "brightness": "亮度异常",
    "close": "特写",
    "curved": "弯曲",
    "damaged": "损坏",
    "glare": "眩光",
    "high_version": "高版本",
    "lots": "多码共存",
    "monitor": "屏幕截图",
    "noncompliant": "非标准",
    "pathological": "极端码",
    "perspective": "透视",
    "rotations": "旋转",
    "shadows": "阴影",
}


@dataclass(frozen=True)
class PreprocessConfig:
    close_resize_dims: tuple[int, ...] = (300, 500, 700, 1000, 1500, 2000)
    damaged_resize_dims: tuple[int, ...] = (800, 1000, 500, 1500, 2000, 300)
    damaged_threshold_dims: tuple[int, ...] = (800, 1000, 500, 1500)
    damaged_extra_threshold_dims: tuple[int, ...] = (800, 1000)
    glare_resize_dims: tuple[int, ...] = (800, 1000, 500, 1500, 2000)
    glare_clahe_dims: tuple[int, ...] = (800, 1000, 500, 1500)
    high_version_resize_dims: tuple[int, ...] = (3000, 2500, 2000, 1500, 1200, 800, 600, 400)
    high_version_clahe_dims: tuple[int, ...] = (2000, 1500, 1200)
    high_version_blur_dims: tuple[int, ...] = (2000, 1500)
    high_version_threshold_dims: tuple[int, ...] = (2000, 1500)
    monitor_resize_dims: tuple[int, ...] = (300, 500, 800, 1000, 1500, 2000)
    curved_threshold_params: tuple[tuple[int, int], ...] = ((21, 3), (31, 5), (41, 7))
    perspective_threshold_params: tuple[tuple[int, int], ...] = ((21, 3), (31, 5))
    noncompliant_threshold_params: tuple[tuple[int, int], ...] = ((11, 2), (21, 3), (31, 5))
    pathological_threshold_params: tuple[tuple[int, int], ...] = ((11, 2), (21, 3))
    sauvola_default: tuple[int, float] = (25, 0.2)
    sauvola_curved_alt: tuple[int, float] = (31, 0.15)
    gamma_values: tuple[float, float] = (0.5, 2.0)
    glare_inpaint_threshold: int = 240
    glare_inpaint_radius: int = 10
    glare_dilate_kernel: tuple[int, int] = (5, 5)
    bright_spots_kernel: tuple[int, int] = (15, 15)


@dataclass(frozen=True)
class DetectorConfig:
    rotation_categories: tuple[str, ...] = ("rotations", "perspective")
    cv2_first_categories: tuple[str, ...] = ("high_version", "curved", "damaged")
    warp_categories: tuple[str, ...] = (
        "high_version",
        "curved",
        "damaged",
        "perspective",
        "blurred",
        "bright_spots",
        "nominal",
        "rotations",
        "glare",
        "close",
        "monitor",
        "noncompliant",
        "shadows",
        "pathological",
        "brightness",
    )
    warp_crop_targets: tuple[int, ...] = (500, 800, 1000, 1500, 2000)
    warp_upscale_factors: tuple[float, ...] = (2.0, 3.0)
    multi_variant_resize_limits: tuple[int, ...] = (800, 1200)
    detected_padding: int = 30
    min_crop_side: int = 50
    min_warp_scale: float = 0.5
    pyzbar_signature_rounding: int = 8
    frame_variant_name: str = "frame_gray"
    rotation_variant_names: tuple[tuple[str, int | None], ...] = (
        ("r0", None),
        ("r90", 0),
        ("r180", 1),
        ("r270", 2),
    )


@dataclass(frozen=True)
class ReportConfig:
    preferred_fonts: tuple[str, ...] = (
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "KaiTi",
        "FangSong",
        "Microsoft JhengHei",
    )
    html_font_family: str = '"Segoe UI", "Microsoft YaHei", sans-serif'
    csv_encoding: str = "utf-8-sig"
    json_encoding: str = "utf-8"
    comparison_glob_pattern: str = "*_overall.json"
    chart_dpi: int = 180
    chart_line_color: str = "#2563eb"
    chart_zero_line_color: str = "#64748b"
    chart_grid_alpha: float = 0.3
    comparison_success_positive_color: str = "#16a34a"
    comparison_success_negative_color: str = "#dc2626"
    comparison_time_positive_color: str = "#ea580c"
    comparison_time_negative_color: str = "#2563eb"
    input_baseline_color: str = "#2563eb"
    input_candidate_color: str = "#16a34a"
    method_baseline_color: str = "#7c3aed"
    method_candidate_color: str = "#ea580c"
    index_risk_bar_color: str = "#dc2626"
    chart_width: float = 12.0
    grouped_bar_height: float = 0.38
    risk_success_rate_threshold: float = 60.0
    risk_delta_success_rate_threshold: float = -5.0
    risk_delta_time_ms_threshold: float = 100.0
    failure_slow_ms_threshold: float = 1500.0
    ranking_limit: int = 5
    sample_reference_limit: int = 3
    failure_cluster_limit: int = 5
    stable_failure_limit: int = 3
    chart_min_height: float = 4.0
    chart_row_height_factor: float = 0.35
    html_page_background: str = "#0f172a"
    html_text_color: str = "#e2e8f0"
    html_meta_color: str = "#cbd5e1"
    html_kpi_label_color: str = "#94a3b8"
    html_kpi_value_color: str = "#f8fafc"
    html_kpi_background: str = "rgba(15,23,42,.55)"
    html_panel_background: str = "rgba(15,23,42,.52)"
    html_panel_border_color: str = "rgba(148,163,184,.14)"
    html_hero_background: str = "linear-gradient(135deg, rgba(14,165,233,.18), rgba(59,130,246,.12), rgba(16,185,129,.12))"
    html_hero_border_color: str = "rgba(148,163,184,.16)"
    html_hero_shadow: str = "0 18px 50px rgba(2,6,23,.28)"
    html_table_header_background: str = "rgba(30,41,59,.85)"
    html_table_row_border_color: str = "rgba(148,163,184,.1)"
    html_positive_color: str = "#34d399"
    html_negative_color: str = "#f87171"
    html_neutral_color: str = "#fbbf24"


PREPROCESS_CONFIG = PreprocessConfig()
DETECTOR_CONFIG = DetectorConfig()
REPORT_CONFIG = ReportConfig()
