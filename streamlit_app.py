import os
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
import plotly.graph_objects as go
import streamlit as st

try:
    import av
except Exception:
    av = None

try:
    from streamlit_webrtc import RTCConfiguration, VideoProcessorBase, webrtc_streamer
except Exception:
    RTCConfiguration = None
    VideoProcessorBase = object
    webrtc_streamer = None

from qr_static_detector import CATEGORY_CHOICES, CATEGORY_LABELS, QRStaticDetector, detections_to_legacy_dicts
from qr_static_detector.visualize import draw_detections

DETECTOR = QRStaticDetector(enable_pyzbar=True)

CUSTOM_CSS = """
<style>
.stApp {
    background: linear-gradient(135deg, #0e1117 0%, #161b22 50%, #0d1117 100%);
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
    border-right: 1px solid rgba(0, 240, 255, 0.12);
}
.gradient-title {
    background: linear-gradient(135deg, #00f0ff 0%, #7c3aed 50%, #f472b6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
}
.gradient-sub {
    color: rgba(255,255,255,0.45);
    font-size: 0.82rem;
    font-weight: 300;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
}
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(0,240,255,0.15);
    border-radius: 12px;
    padding: 16px 20px;
    backdrop-filter: blur(10px);
    box-shadow: 0 0 20px rgba(0,240,255,0.06);
}
[data-testid="stMetric"] label {
    color: rgba(255,255,255,0.55) !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.08em;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #00f0ff !important;
    font-weight: 600;
}
.data-text {
    color: #a5b4fc;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.82rem;
    background: rgba(99,102,241,0.08);
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid rgba(99,102,241,0.15);
    word-break: break-all;
}
.badge-ok {
    background: rgba(16,185,129,0.15);
    color: #34d399;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-fail {
    background: rgba(239,68,68,0.15);
    color: #f87171;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
}
.section-header {
    color: #e2e8f0;
    font-size: 1.1rem;
    font-weight: 600;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(0,240,255,0.12);
    margin: 1.5rem 0 1rem 0;
}
</style>
"""


def _detect_single(img_bytes: bytes, filename: str, category: str | None) -> dict:
    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
        tmp.write(img_bytes)
        tmp_path = tmp.name
    try:
        t0 = time.perf_counter()
        image = cv2.imread(tmp_path)
        detections = DETECTOR.detect_adaptive(image, category) if category else DETECTOR.detect(image)
        elapsed = time.perf_counter() - t0
        annotated = draw_detections(image, detections) if detections else image
        return {
            "filename": filename,
            "results": detections_to_legacy_dicts(detections),
            "annotated": annotated,
            "original": image,
            "elapsed": elapsed,
            "ok": bool(detections),
        }
    finally:
        os.unlink(tmp_path)


def _render_kpi(total: int, detected: int, qr_count: int):
    c1, c2, c3, c4 = st.columns(4)
    rate = detected / total * 100 if total else 0
    c1.metric("图片总数", total)
    c2.metric("检测成功", f"{detected}/{total}")
    c3.metric("检测率", f"{rate:.1f}%")
    c4.metric("QR 码总数", qr_count)


def _render_single_result(result: dict):
    col_img, col_info = st.columns([3, 2])
    with col_img:
        st.image(cv2.cvtColor(result["annotated"], cv2.COLOR_BGR2RGB), use_container_width=True)
    with col_info:
        st.markdown(f"### `{result['filename']}`")
        if result["ok"]:
            st.markdown(
                f'<span class="badge-ok">检测成功</span> &nbsp; {len(result["results"])} 个 QR 码 &nbsp;|&nbsp; {result["elapsed"]*1000:.0f}ms',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f'<span class="badge-fail">未检测到</span> &nbsp; {result["elapsed"]*1000:.0f}ms', unsafe_allow_html=True)
        for index, qr in enumerate(result["results"], 1):
            st.markdown(f'<div class="data-text">[{index}] {qr["data"]}</div>', unsafe_allow_html=True)
            st.caption(f"类型: {qr['type']}  |  位置: ({qr['rect']['x']}, {qr['rect']['y']}, {qr['rect']['w']}×{qr['rect']['h']})")


def _render_batch_results(all_results: list[dict]):
    total = len(all_results)
    detected = sum(1 for result in all_results if result["ok"])
    qr_count = sum(len(result["results"]) for result in all_results)
    st.markdown('<div class="section-header">数据看板</div>', unsafe_allow_html=True)
    _render_kpi(total, detected, qr_count)

    col_pie, col_bar = st.columns(2)
    with col_pie:
        fig_pie = go.Figure(
            data=[
                go.Pie(
                    labels=["检测成功", "未检测到"],
                    values=[detected, total - detected],
                    hole=0.55,
                    marker=dict(colors=["#10b981", "#ef4444"]),
                    textinfo="label+percent",
                    textfont=dict(size=13, color="#e2e8f0"),
                )
            ]
        )
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_bar:
        times = [result["elapsed"] * 1000 for result in all_results]
        fig_bar = go.Figure(
            data=[
                go.Bar(
                    x=[result["filename"] for result in all_results],
                    y=times,
                    marker_color=["#00f0ff" if result["ok"] else "#f87171" for result in all_results],
                )
            ]
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="文件",
            yaxis_title="耗时 (ms)",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown('<div class="section-header">逐图结果</div>', unsafe_allow_html=True)
    for result in all_results:
        with st.expander(result["filename"], expanded=False):
            _render_single_result(result)


def _render_video_result(video_result: dict):
    st.markdown('<div class="section-header">视频检测结果</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("抽样帧数", video_result["sampled"])
    c2.metric("检测到 QR 的帧", video_result["detected"])
    c3.metric("去重 QR 数", video_result["unique"])
    points = video_result["timeline"]
    if points:
        fig = go.Figure(data=[go.Scatter(x=[p["time"] for p in points], y=[p["count"] for p in points], mode="lines+markers")])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="时间 (s)", yaxis_title="检测数")
        st.plotly_chart(fig, use_container_width=True)
    for frame in video_result["frames"]:
        st.image(cv2.cvtColor(frame["annotated"], cv2.COLOR_BGR2RGB), caption=frame["label"], use_container_width=True)
        for qr in frame["results"]:
            st.markdown(f'<div class="data-text">{qr["data"]}</div>', unsafe_allow_html=True)


def _render_camera_mode():
    if av is None or webrtc_streamer is None or RTCConfiguration is None:
        st.error("摄像头实时检测需要安装 av、aiortc、streamlit-webrtc。当前环境缺少这些依赖。")
        st.code("pip install av aiortc streamlit-webrtc", language="bash")
        return

    class QRVideoProcessor(VideoProcessorBase):
        def recv(self, frame):
            img = frame.to_ndarray(format="bgr24")
            detections = DETECTOR.detect_frame(img)
            annotated = draw_detections(img, detections)
            return av.VideoFrame.from_ndarray(annotated, format="bgr24")

    rtc_config = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
    webrtc_streamer(key="qr-camera", video_processor_factory=QRVideoProcessor, rtc_configuration=rtc_config)


def _process_video(uploaded_file, category: str | None) -> dict:
    with tempfile.NamedTemporaryFile(suffix=Path(uploaded_file.name).suffix, delete=False) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    try:
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise RuntimeError("无法打开视频文件")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        sample_step = max(int(fps), 1)

        sampled = 0
        detected = 0
        unique_data: set[str] = set()
        timeline: list[dict[str, float | int]] = []
        frames: list[dict] = []

        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % sample_step != 0:
                idx += 1
                continue
            sampled += 1
            hits = DETECTOR.detect_adaptive(frame, category) if category else DETECTOR.detect_frame(frame)
            results = detections_to_legacy_dicts(hits)
            if results:
                detected += 1
                for qr in results:
                    unique_data.add(str(qr["data"]))
                annotated = draw_detections(frame, hits)
                if len(frames) < 8:
                    frames.append(
                        {
                            "label": f"{idx / fps:.1f}s",
                            "annotated": annotated,
                            "results": results,
                        }
                    )
            timeline.append({"time": round(idx / fps, 2), "count": len(results)})
            idx += 1

        cap.release()
        return {
            "sampled": sampled,
            "detected": detected,
            "unique": len(unique_data),
            "timeline": timeline,
            "frames": frames,
            "frame_count": frame_count,
        }
    finally:
        os.unlink(tmp_path)


def main():
    st.set_page_config(page_title="QR 码智能检测系统", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown('<div class="gradient-title">QR 码智能检测系统</div>', unsafe_allow_html=True)
    st.markdown('<div class="gradient-sub">Adaptive QR Detection Workspace</div>', unsafe_allow_html=True)

    with st.sidebar:
        mode = st.radio("选择模式", ["单张图片", "批量上传", "视频检测", "摄像头实时"])
        category = st.selectbox(
            "场景类别",
            options=[""] + list(CATEGORY_CHOICES),
            format_func=lambda value: "自动识别" if value == "" else f"{CATEGORY_LABELS.get(value, value)} ({value})",
        )

    if mode == "单张图片":
        uploaded = st.file_uploader("上传图片", type=["jpg", "jpeg", "png", "bmp", "webp"])
        if uploaded:
            result = _detect_single(uploaded.read(), uploaded.name, category or None)
            _render_single_result(result)
    elif mode == "批量上传":
        uploaded_files = st.file_uploader("上传多张图片", type=["jpg", "jpeg", "png", "bmp", "webp"], accept_multiple_files=True)
        if uploaded_files:
            results = [_detect_single(file.read(), file.name, category or None) for file in uploaded_files]
            _render_batch_results(results)
    elif mode == "视频检测":
        uploaded_video = st.file_uploader("上传视频", type=["mp4", "mov", "avi", "mkv"])
        if uploaded_video:
            video_result = _process_video(uploaded_video, category or None)
            _render_video_result(video_result)
    else:
        _render_camera_mode()


if __name__ == "__main__":
    main()
