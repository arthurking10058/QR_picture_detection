from __future__ import annotations

import argparse
import csv
import json
import locale
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from qr_static_detector import CATEGORY_CHOICES, QRStaticDetector
from qr_static_detector.utils import iter_image_files, read_image, safe_stem, write_image
from qr_static_detector.visualize import draw_detections


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QR码静态图片检测系统")
    parser.add_argument("input", nargs="?", default="qrcodes/detection", help="输入图片或图片目录，默认 qrcodes/detection")
    parser.add_argument("-o", "--output", default="record/runtime_outputs", help="输出目录，默认 record/runtime_outputs")
    parser.add_argument("--category", choices=CATEGORY_CHOICES, help="按场景类别启用自适应预处理")
    parser.add_argument("--batch-root", help="按类别批量检测数据集根目录，例如 qrcodes/detection")
    parser.add_argument("--no-pyzbar", action="store_true", help="仅使用OpenCV检测，不调用pyzbar")
    parser.add_argument("--save-json", action="store_true", help="保存JSON格式结果")
    parser.add_argument("--summarize", action="store_true", help="检测完成后自动生成汇总报告")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output)
    image_output_dir = output_dir / "images"
    report_path = output_dir / "results.csv"
    json_path = output_dir / "results.json"
    diagnostic_path = output_dir / "diagnostics.json"
    run_meta_path = output_dir / "run_meta.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    image_output_dir.mkdir(parents=True, exist_ok=True)

    detector = QRStaticDetector(enable_pyzbar=not args.no_pyzbar)
    rows: list[dict[str, object]] = []
    json_rows: list[dict[str, object]] = []
    diagnostic_rows: list[dict[str, object]] = []

    if args.batch_root:
        image_jobs = list(iter_category_jobs(args.batch_root, args.category))
        source_label = args.batch_root
    else:
        image_jobs = [(image_path, args.category) for image_path in iter_image_files(args.input)]
        source_label = args.input

    if not image_jobs:
        print(f"未找到图片: {source_label}")
        return 1

    run_started_at = datetime.now().astimezone()
    started = time.perf_counter()

    for image_path, category in image_jobs:
        start = time.perf_counter()
        try:
            image = read_image(image_path)
            diagnostic = detector.diagnose_adaptive(image, category) if category else detector.diagnose_adaptive(image, None)
            diagnostic_rows.append(
                {
                    "image": str(image_path),
                    "category": category or "",
                    **diagnostic.to_dict(),
                }
            )
            detections = detector.detect_adaptive(image, category) if category else detector.detect(image)
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

            annotated = draw_detections(image, detections)
            annotated_path = image_output_dir / f"{safe_stem(image_path)}_detected.png"
            write_image(annotated_path, annotated)

            if detections:
                for index, detection in enumerate(detections, start=1):
                    rows.append(
                        {
                            "image": str(image_path),
                            "category": category or "",
                            "index": index,
                            "success": True,
                            "data": detection.data,
                            "method": detection.method,
                            "variant": detection.variant,
                            "points": detection.points,
                            "time_ms": elapsed_ms,
                            "output": str(annotated_path),
                        }
                    )
                    json_rows.append(
                        {
                            "image": str(image_path),
                            "category": category or "",
                            **detection.to_dict(),
                            "time_ms": elapsed_ms,
                        }
                    )
                print(
                    f"[OK] {image_path}"
                    + (f" [{category}]" if category else "")
                    + f" -> 检测到 {len(detections)} 个QR码，用时 {elapsed_ms} ms"
                )
            else:
                rows.append(
                    {
                        "image": str(image_path),
                        "category": category or "",
                        "index": 0,
                        "success": False,
                        "data": "",
                        "method": "",
                        "variant": "",
                        "points": "",
                        "time_ms": elapsed_ms,
                        "output": str(annotated_path),
                    }
                )
                json_rows.append(
                    {
                        "image": str(image_path),
                        "category": category or "",
                        "detections": [],
                        "time_ms": elapsed_ms,
                    }
                )
                print(
                    f"[MISS] {image_path}"
                    + (f" [{category}]" if category else "")
                    + f" -> 未检测到QR码，用时 {elapsed_ms} ms"
                )
        except Exception as exc:
            rows.append(
                {
                    "image": str(image_path),
                    "category": category or "",
                    "index": 0,
                    "success": False,
                    "data": f"ERROR: {exc}",
                    "method": "",
                    "variant": "",
                    "points": "",
                    "time_ms": "",
                    "output": "",
                }
            )
            print(f"[ERROR] {image_path}" + (f" [{category}]" if category else "") + f" -> {exc}")

    write_csv(report_path, rows)
    if args.save_json:
        json_path.write_text(json.dumps(json_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    diagnostic_path.write_text(json.dumps(diagnostic_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    write_run_meta(
        run_meta_path,
        args=args,
        source_label=source_label,
        image_jobs=image_jobs,
        rows=rows,
        run_started_at=run_started_at.isoformat(),
        elapsed_seconds=round(time.perf_counter() - started, 3),
    )

    if args.summarize:
        summarize_results(report_path, output_dir)

    print(f"检测报告: {report_path}")
    print(f"标注图片: {image_output_dir}")
    return 0


def iter_category_jobs(batch_root: str | Path, category: str | None):
    root = Path(batch_root)
    if not root.is_dir():
        raise FileNotFoundError(f"批量数据目录不存在: {root}")

    categories = [category] if category else sorted(item.name for item in root.iterdir() if item.is_dir())
    for category_name in categories:
        category_dir = root / category_name
        if not category_dir.is_dir():
            raise FileNotFoundError(f"类别目录不存在: {category_dir}")
        for image_path in iter_image_files(category_dir):
            yield image_path, category_name


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = ["image", "category", "index", "success", "data", "method", "variant", "points", "time_ms", "output"]
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize_results(report_path: Path, output_dir: Path) -> None:
    script_path = Path(__file__).with_name("summarize_results.py")
    if not script_path.is_file():
        print(f"[WARN] 汇总脚本不存在: {script_path}")
        return
    completed = subprocess.run(
        [sys.executable, str(script_path), str(report_path), "--output-dir", str(output_dir)],
        capture_output=True,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors="replace",
    )
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if completed.returncode == 0:
        if stdout:
            print(stdout)
    else:
        print(stderr or stdout or "[WARN] summarize_results.py returned non-zero exit status")
        print(f"[WARN] 汇总失败: {completed.stderr.strip() or completed.stdout.strip()}")


def write_run_meta(
    path: Path,
    args: argparse.Namespace,
    source_label: str,
    image_jobs: list[tuple[Path, str | None]],
    rows: list[dict[str, object]],
    run_started_at: str,
    elapsed_seconds: float,
) -> None:
    success_images = len({str(row["image"]) for row in rows if row["success"] is True})
    meta = {
        "run_started_at": run_started_at,
        "elapsed_seconds": elapsed_seconds,
        "command": build_command(args),
        "cwd": os.getcwd(),
        "input_source": source_label,
        "image_job_count": len(image_jobs),
        "category_filter": args.category or "",
        "batch_root": args.batch_root or "",
        "output_dir": str(path.parent),
        "save_json": args.save_json,
        "summarize": args.summarize,
        "enable_pyzbar": not args.no_pyzbar,
        "success_image_count": success_images,
    }
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def build_command(args: argparse.Namespace) -> str:
    parts = ["python", "app.py"]
    if args.batch_root:
        parts.extend(["--batch-root", str(args.batch_root)])
    else:
        parts.append(str(args.input))
    if args.category:
        parts.extend(["--category", args.category])
    if args.output != "record/runtime_outputs":
        parts.extend(["-o", str(args.output)])
    if args.no_pyzbar:
        parts.append("--no-pyzbar")
    if args.save_json:
        parts.append("--save-json")
    if args.summarize:
        parts.append("--summarize")
    return " ".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
