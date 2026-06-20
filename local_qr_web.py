from __future__ import annotations

import base64
import html
import io
import os
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs
from email.parser import BytesParser
from email.policy import default

import cv2

ROOT = Path(__file__).resolve().parent

from qr_static_detector import CATEGORY_CHOICES, CATEGORY_LABELS, QRStaticDetector
from qr_static_detector.visualize import draw_detections

DETECTOR = QRStaticDetector(enable_pyzbar=True)


def parse_form_data(handler: BaseHTTPRequestHandler):
    content_type = handler.headers.get("Content-Type", "")
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    body = handler.rfile.read(content_length)

    if "multipart/form-data" in content_type:
        message = BytesParser(policy=default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
        )
        fields: dict[str, list[str]] = {}
        files: list[dict[str, object]] = []
        for part in message.iter_parts():
            disposition = part.get_content_disposition()
            if disposition != "form-data":
                continue
            name = part.get_param("name", header="content-disposition")
            filename = part.get_filename()
            payload = part.get_payload(decode=True) or b""
            if filename:
                files.append({"name": name, "filename": filename, "data": payload})
            elif name:
                fields.setdefault(name, []).append(payload.decode("utf-8", errors="replace"))
        return fields, files

    if "application/x-www-form-urlencoded" in content_type:
        parsed = parse_qs(body.decode("utf-8", errors="replace"))
        return parsed, []

    return {}, []


STYLE = """
<style>
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  background: #0b1118;
  color: #e5edf8;
  font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
}
.app { display: grid; grid-template-columns: 330px 1fr; min-height: 100vh; }
.sidebar {
  background: linear-gradient(180deg, #0a1017, #111820);
  border-right: 1px solid rgba(0, 240, 255, .14);
  padding: 72px 28px 28px;
}
.brand {
  font-size: 34px;
  font-weight: 800;
  letter-spacing: -1px;
  background: linear-gradient(135deg, #22d3ee, #6366f1 55%, #a855f7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.sub { margin-top: 10px; color: rgba(229,237,248,.48); letter-spacing: 4px; font-size: 13px; }
.label { margin-top: 34px; margin-bottom: 12px; color: #e5edf8; font-weight: 700; }
.mode-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 14px; }
.mode {
  display: flex; gap: 9px; align-items: center; color: #d9e2ee; font-weight: 700;
  cursor: pointer;
}
.dot { width: 15px; height: 15px; border-radius: 50%; background: #303643; border: 1px solid #485163; }
.mode input { display: none; }
.mode:has(input:checked) .dot { background: #ff5b5f; box-shadow: inset 0 0 0 5px #ff5b5f, inset 0 0 0 7px #fff; }
select, input[type=file] {
  width: 100%;
  background: #0a1017;
  border: 1px solid rgba(255,255,255,.06);
  color: #eef6ff;
  border-radius: 9px;
  padding: 13px 14px;
  font-size: 15px;
}
.filebox {
  background: #090f16;
  border-radius: 10px;
  padding: 16px;
  border: 1px solid rgba(255,255,255,.04);
}
.btn {
  width: 100%;
  margin-top: 18px;
  border: 0;
  padding: 15px 18px;
  border-radius: 10px;
  color: #08111a;
  font-size: 17px;
  font-weight: 800;
  cursor: pointer;
  background: linear-gradient(135deg, #22d3ee, #6366f1 65%, #7c3aed);
  box-shadow: 0 0 0 2px rgba(239,68,68,.55);
}
.main {
  background: linear-gradient(180deg, #0f141c, #0b1118 45%, #0b1118);
  padding: 92px 72px;
}
.section-title {
  max-width: 1120px;
  border-bottom: 1px solid rgba(34,211,238,.16);
  padding-bottom: 12px;
  font-size: 24px;
  font-weight: 800;
}
.result { display: grid; grid-template-columns: minmax(360px, 560px) minmax(300px, 1fr); gap: 34px; margin-top: 26px; align-items: start; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 18px; margin-top: 24px; max-width: 1200px; }
.thumb-card { background: rgba(255,255,255,.03); border: 1px solid rgba(148,163,184,.18); border-radius: 10px; padding: 12px; }
.thumb-card img { width: 100%; height: 190px; object-fit: contain; background: #fff; border-radius: 7px; }
.kpi-row { display: grid; grid-template-columns: repeat(4, minmax(130px, 1fr)); gap: 16px; max-width: 960px; margin-top: 24px; }
.kpi { background: rgba(255,255,255,.035); border: 1px solid rgba(34,211,238,.14); border-radius: 10px; padding: 14px 16px; }
.kpi-label { color: rgba(229,237,248,.55); font-size: 13px; }
.kpi-value { margin-top: 6px; color: #22d3ee; font-size: 25px; font-weight: 900; }
.timeline { margin-top: 24px; max-width: 1180px; }
.bar { height: 18px; border-radius: 4px; background: #1f2937; overflow: hidden; margin-top: 8px; }
.bar span { display: block; height: 100%; background: linear-gradient(90deg, #22d3ee, #22c55e); }
.image-card {
  background: #fff;
  border-radius: 9px;
  padding: 18px;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 420px;
}
.image-card img { max-width: 100%; max-height: 660px; object-fit: contain; }
.info-card {
  background: rgba(255,255,255,.025);
  border-radius: 9px;
  padding: 18px 20px;
}
.filename {
  color: #6ee7b7;
  font-family: Consolas, "JetBrains Mono", monospace;
  font-size: 23px;
  font-weight: 800;
  word-break: break-all;
}
.badge {
  display: inline-block;
  margin-top: 18px;
  padding: 3px 10px;
  border-radius: 18px;
  background: rgba(16,185,129,.16);
  color: #34d399;
  font-weight: 800;
  font-size: 13px;
}
.badge.fail { background: rgba(239,68,68,.14); color: #f87171; }
.meta { color: #f3f4f6; margin-left: 10px; font-weight: 700; }
.data {
  margin-top: 16px;
  color: #c7d2fe;
  font-family: Consolas, "JetBrains Mono", monospace;
  background: rgba(99,102,241,.12);
  border: 1px solid rgba(99,102,241,.22);
  border-radius: 8px;
  padding: 12px 14px;
  word-break: break-all;
}
.caption { margin-top: 8px; color: rgba(229,237,248,.62); }
.empty {
  margin-top: 32px;
  color: rgba(229,237,248,.66);
  border: 1px dashed rgba(148,163,184,.35);
  border-radius: 12px;
  padding: 30px;
  max-width: 760px;
}
.hint { margin-top: 18px; color: rgba(229,237,248,.45); font-size: 13px; line-height: 1.8; }
.error { color: #fecaca; background: rgba(239,68,68,.12); padding: 14px; border-radius: 8px; margin-top: 20px; }
@media (max-width: 900px) {
  .app { grid-template-columns: 1fr; }
  .sidebar { padding-top: 32px; }
  .main { padding: 34px 22px; }
  .result { grid-template-columns: 1fr; }
}
</style>
"""


def encode_png(image) -> str:
    ok, buf = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("Cannot encode result image")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def convert_detections(detections):
    converted = []
    for detection in detections:
        xs = [point[0] for point in detection.points]
        ys = [point[1] for point in detection.points]
        converted.append(
            {
                "data": detection.data,
                "type": "QRCODE",
                "method": detection.method,
                "variant": detection.variant,
                "rect": {
                    "x": min(xs),
                    "y": min(ys),
                    "w": max(xs) - min(xs),
                    "h": max(ys) - min(ys),
                },
                "polygon": detection.points,
            }
        )
    return converted


def filter_by_category(results: list[dict], category: str | None) -> list[dict]:
    if not category:
        return results
    return [result for result in results if result.get("variant") == category]


def detect_image_bytes(data: bytes, filename: str, category: str | None) -> dict:
    suffix = Path(filename).suffix or ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        t0 = time.perf_counter()
        image = cv2.imread(tmp_path)
        if image is None:
            raise RuntimeError("图片读取失败")
        detections = DETECTOR.detect(image)
        results = filter_by_category(convert_detections(detections), category or None)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        annotated = draw_detections(image, detections) if detections else image
        return {
            "filename": filename,
            "results": results or [],
            "elapsed_ms": elapsed_ms,
            "image_b64": encode_png(annotated),
            "ok": bool(results),
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def detect_video_bytes(data: bytes, filename: str, category: str | None) -> dict:
    suffix = Path(filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    cap = cv2.VideoCapture(tmp_path)
    try:
        if not cap.isOpened():
            raise RuntimeError("视频读取失败")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = frame_count / fps if fps else 0
        step = max(1, int(fps / 2))
        frames = []
        sampled = 0
        detected = 0
        unique = set()
        idx = 0
        t0 = time.perf_counter()
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % step == 0:
                sampled += 1
                detections = DETECTOR.detect(frame)
                results = filter_by_category(convert_detections(detections), category or None)
                if results:
                    detected += 1
                    for r in results:
                        unique.add(str(r.get("data", "")))
                    annotated = draw_detections(frame, detections)
                    frames.append({
                        "time": idx / fps if fps else 0,
                        "frame": idx,
                        "count": len(results),
                        "data": " | ".join(str(r.get("data", ""))[:70] for r in results),
                        "image_b64": encode_png(annotated),
                    })
                    if len(frames) >= 12:
                        pass
            idx += 1
            if sampled >= 180:
                break
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return {
            "filename": filename,
            "sampled": sampled,
            "detected": detected,
            "unique": len(unique),
            "duration": duration,
            "fps": fps,
            "elapsed_ms": elapsed_ms,
            "frames": frames[:12],
            "ok": detected > 0,
        }
    finally:
        cap.release()
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def render_single_result(result: dict) -> str:
    safe_name = html.escape(result["filename"])
    if result["ok"]:
        rows = []
        for i, qr in enumerate(result["results"], 1):
            data = html.escape(str(qr.get("data", "")))
            qr_type = html.escape(str(qr.get("type", "QRCODE")))
            rect = qr.get("rect", {})
            pos = f"{rect.get('x', '-')}, {rect.get('y', '-')}, {rect.get('w', '-')}x{rect.get('h', '-')}"
            rows.append(
                f'<div class="data">[{i}] {data}</div>'
                f'<div class="caption">类型: {qr_type} | 位置: ({html.escape(pos)})</div>'
            )
        detail = "".join(rows)
        badge = f'<span class="badge">检测成功</span><span class="meta">{len(result["results"])} 个 QR 码 | {result["elapsed_ms"]:.0f}ms</span>'
    else:
        badge = f'<span class="badge fail">未检测到</span><span class="meta">{result["elapsed_ms"]:.0f}ms</span>'
        detail = '<div class="caption">可以切换检测类别后重试，例如模糊、反光、旋转、透视等。</div>'
    return f"""
    <div class="result">
      <div class="image-card"><img src="data:image/png;base64,{result["image_b64"]}" alt="检测结果"></div>
      <div class="info-card">
        <div class="filename">{safe_name}</div>
        <div>{badge}</div>
        {detail}
      </div>
    </div>
    """


def render_batch_results(results: list[dict]) -> str:
    total = len(results)
    detected = sum(1 for r in results if r["ok"])
    qr_count = sum(len(r["results"]) for r in results)
    avg = sum(r["elapsed_ms"] for r in results) / total if total else 0
    cards = []
    for r in results:
        status = "检测成功" if r["ok"] else "未检测到"
        badge_cls = "badge" if r["ok"] else "badge fail"
        data = html.escape(" | ".join(str(q.get("data", ""))[:55] for q in r["results"]) or "无")
        cards.append(f"""
        <div class="thumb-card">
          <img src="data:image/png;base64,{r["image_b64"]}" alt="">
          <div class="filename" style="font-size:15px;margin-top:10px">{html.escape(r["filename"])}</div>
          <span class="{badge_cls}">{status}</span>
          <div class="caption">{len(r["results"])} 个 QR 码 | {r["elapsed_ms"]:.0f}ms</div>
          <div class="caption">{data}</div>
        </div>
        """)
    rate = detected / total * 100 if total else 0
    return f"""
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">图片总数</div><div class="kpi-value">{total}</div></div>
      <div class="kpi"><div class="kpi-label">检测成功</div><div class="kpi-value">{detected}/{total}</div></div>
      <div class="kpi"><div class="kpi-label">检测率</div><div class="kpi-value">{rate:.1f}%</div></div>
      <div class="kpi"><div class="kpi-label">QR 码总数</div><div class="kpi-value">{qr_count}</div></div>
    </div>
    <div class="caption">平均耗时：{avg:.0f}ms / 张</div>
    <div class="grid">{''.join(cards)}</div>
    """


def render_video_result(result: dict) -> str:
    frames = []
    for f in result["frames"]:
        frames.append(f"""
        <div class="thumb-card">
          <img src="data:image/png;base64,{f["image_b64"]}" alt="">
          <div class="filename" style="font-size:15px;margin-top:10px">{f["time"]:.1f}s / 帧 {f["frame"]}</div>
          <span class="badge">检测成功</span>
          <div class="caption">{f["count"]} 个 QR 码</div>
          <div class="caption">{html.escape(f["data"])}</div>
        </div>
        """)
    rate = result["detected"] / result["sampled"] * 100 if result["sampled"] else 0
    width = max(2, min(100, rate))
    return f"""
    <div class="filename">{html.escape(result["filename"])}</div>
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">视频时长</div><div class="kpi-value">{result["duration"]:.1f}s</div></div>
      <div class="kpi"><div class="kpi-label">抽样帧数</div><div class="kpi-value">{result["sampled"]}</div></div>
      <div class="kpi"><div class="kpi-label">检测到 QR 的帧</div><div class="kpi-value">{result["detected"]}</div></div>
      <div class="kpi"><div class="kpi-label">去重 QR 数</div><div class="kpi-value">{result["unique"]}</div></div>
    </div>
    <div class="timeline">
      <div class="caption">帧检测率：{rate:.1f}% | 处理耗时：{result["elapsed_ms"]:.0f}ms</div>
      <div class="bar"><span style="width:{width}%"></span></div>
    </div>
    <div class="grid">{''.join(frames) if frames else '<div class="empty">抽样帧中未检测到 QR 码。</div>'}</div>
    """


def render_page(
    result: dict | None = None,
    batch_results: list[dict] | None = None,
    video_result: dict | None = None,
    error: str | None = None,
    category: str = "",
    mode: str = "single",
) -> bytes:
    options = ['<option value="">自动识别 -- 基础灰度解码</option>']
    for cat in CATEGORY_CHOICES:
        selected = " selected" if cat == category else ""
        options.append(f'<option value="{cat}"{selected}>{CATEGORY_LABELS.get(cat, cat)} ({cat})</option>')

    if result:
        content = f"""
        <div class="section-title">检测结果</div>
        {render_single_result(result)}
        """
    elif batch_results is not None:
        content = f'<div class="section-title">批量检测结果</div>{render_batch_results(batch_results)}'
    elif video_result is not None:
        content = f'<div class="section-title">视频检测结果</div>{render_video_result(video_result)}'
    else:
        title = {"single": "检测结果", "batch": "批量检测结果", "video": "视频检测结果"}.get(mode, "检测结果")
        msg = {
            "single": "请在左侧上传图片，选择检测类别，然后点击“开始检测”。",
            "batch": "请选择多张图片，点击“开始检测”后会生成批量统计和逐图结果。",
            "video": "请上传视频文件，系统会抽帧检测并展示关键帧。",
        }.get(mode, "请选择文件后开始检测。")
        content = """
        <div class="section-title">{title}</div>
        <div class="empty">{msg}</div>
        """.format(title=title, msg=msg)
    if error:
        content += f'<div class="error">{html.escape(error)}</div>'

    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>QR 码智能检测系统</title>
  {STYLE}
</head>
<body>
  <form class="app" method="post" enctype="multipart/form-data">
    <aside class="sidebar">
      <div class="brand">QR 码检测</div>
      <div class="sub">自适应预处理引擎</div>

      <div class="label">上传模式</div>
      <div class="mode-row">
        <label class="mode"><input type="radio" name="mode" value="single" {"checked" if mode == "single" else ""}><span class="dot"></span>单张图片</label>
        <label class="mode"><input type="radio" name="mode" value="batch" {"checked" if mode == "batch" else ""}><span class="dot"></span>批量上传</label>
        <label class="mode"><input type="radio" name="mode" value="video" {"checked" if mode == "video" else ""}><span class="dot"></span>视频检测</label>
        <label class="mode"><input type="radio" name="mode" value="camera" {"checked" if mode == "camera" else ""}><span class="dot"></span>摄像头实时</label>
      </div>

      <div class="label">检测类别</div>
      <select name="category">{''.join(options)}</select>

      <div class="label">上传图片</div>
      <div class="filebox">
        <input id="file-input" type="file" name="files" accept="image/*" multiple required>
        <div class="hint">单张/批量请选择图片；视频检测请选择 mp4/avi/mov/mkv/webm。</div>
      </div>

      <button class="btn" type="submit">开始检测</button>
      <div class="hint">本页面是本地主线演示入口，直接调用 qr_static_detector 核心模块，不依赖 rba 历史分支。</div>
    </aside>
    <main class="main">{content}</main>
  </form>
  <script>
    const fileInput = document.getElementById('file-input');
    const radios = document.querySelectorAll('input[name="mode"]');
    function syncFileInput() {{
      const mode = document.querySelector('input[name="mode"]:checked').value;
      if (mode === 'video') {{
        fileInput.accept = 'video/*,.mp4,.avi,.mov,.mkv,.webm';
        fileInput.multiple = false;
      }} else if (mode === 'single') {{
        fileInput.accept = 'image/*';
        fileInput.multiple = false;
      }} else {{
        fileInput.accept = 'image/*';
        fileInput.multiple = true;
      }}
    }}
    radios.forEach(r => r.addEventListener('change', syncFileInput));
    syncFileInput();
  </script>
</body>
</html>"""
    return page.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.respond(render_page())

    def do_POST(self):
        category = ""
        mode = "single"
        try:
            fields, files = parse_form_data(self)
            category = (fields.get("category") or [""])[0] or ""
            mode = (fields.get("mode") or ["single"])[0] or "single"
            if mode == "camera":
                self.respond(render_page(error="备用页面暂不支持摄像头实时，请使用视频检测截图。", category=category, mode=mode))
                return
            items = [item for item in files if item.get("name") == "files" and item.get("filename")]
            if not items:
                self.respond(render_page(error="没有收到上传文件", category=category, mode=mode))
                return
            if mode == "video":
                item = items[0]
                video_result = detect_video_bytes(item["data"], str(item["filename"]), category or None)
                self.respond(render_page(video_result=video_result, category=category, mode=mode))
            elif mode == "batch":
                results = [detect_image_bytes(item["data"], str(item["filename"]), category or None) for item in items]
                self.respond(render_page(batch_results=results, category=category, mode=mode))
            else:
                item = items[0]
                result = detect_image_bytes(item["data"], str(item["filename"]), category or None)
                self.respond(render_page(result=result, category=category, mode=mode))
        except Exception as exc:
            self.respond(render_page(error=str(exc), category=category, mode=mode))

    def respond(self, body: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


if __name__ == "__main__":
    port = int(os.environ.get("QR_WEB_PORT", "8600"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"QR web app running at http://127.0.0.1:{port}")
    server.serve_forever()
