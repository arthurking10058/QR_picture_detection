import os
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
    background:
        radial-gradient(circle at top left, rgba(232, 175, 88, 0.18), transparent 30%),
        linear-gradient(180deg, #f8f3ea 0%, #f3ecdf 52%, #ede3d3 100%);
    color: #1b2a2f;
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
}
[data-testid="stHeader"] {
    background: transparent;
}
[data-testid="stToolbar"] {
    display: none;
}
#MainMenu, footer {
    visibility: hidden;
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #16352d 0%, #1f443a 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}
.sidebar-card {
    background: rgba(255, 248, 240, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 22px;
    padding: 18px 16px;
    margin: 0.4rem 0 1rem 0;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
}
.sidebar-card h3 {
    color: #f7fbf8;
    font-size: 1.15rem;
    margin: 0 0 0.7rem 0;
    font-weight: 700;
}
.sidebar-card p {
    color: rgba(239, 245, 241, 0.88);
    margin: 0;
    line-height: 1.7;
    font-size: 0.95rem;
}
.gradient-title {
    color: #17312c;
    font-size: 2.7rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin-bottom: 0.35rem;
}
.gradient-sub {
    color: rgba(23, 49, 44, 0.58);
    font-size: 0.88rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}
.hero-card {
    background: rgba(255, 251, 245, 0.86);
    border: 1px solid rgba(23, 49, 44, 0.08);
    border-radius: 28px;
    padding: 28px 30px;
    box-shadow: 0 24px 60px rgba(76, 57, 30, 0.10);
    margin-bottom: 1.2rem;
}
.hero-copy {
    color: rgba(27, 42, 47, 0.72);
    line-height: 1.75;
    font-size: 1rem;
    max-width: 880px;
}
.hero-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 14px;
    margin-top: 18px;
}
.hero-pill {
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid rgba(23, 49, 44, 0.08);
    border-radius: 18px;
    padding: 14px 16px;
}
.hero-pill span {
    display: block;
    font-size: 0.76rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: rgba(23, 49, 44, 0.5);
}
.hero-pill strong {
    display: block;
    margin-top: 6px;
    color: #17312c;
    font-size: 1rem;
}
.hint-card {
    background: rgba(255, 255, 255, 0.62);
    border: 1px dashed rgba(23, 49, 44, 0.18);
    border-radius: 18px;
    padding: 16px 18px;
    color: rgba(27, 42, 47, 0.76);
    margin-bottom: 1rem;
}
[data-testid="stMetric"] {
    background: rgba(255, 251, 245, 0.78);
    border: 1px solid rgba(23, 49, 44, 0.08);
    border-radius: 18px;
    padding: 16px 20px;
    box-shadow: 0 10px 28px rgba(76, 57, 30, 0.08);
}
[data-testid="stMetric"] label {
    color: rgba(23, 49, 44, 0.55) !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.08em;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #17312c !important;
    font-weight: 600;
}
.data-text {
    color: #17312c;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.82rem;
    background: rgba(23, 49, 44, 0.06);
    padding: 8px 12px;
    border-radius: 12px;
    border: 1px solid rgba(23, 49, 44, 0.08);
    word-break: break-all;
}
.badge-ok {
    background: rgba(33, 177, 115, 0.12);
    color: #1a7f58;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-fail {
    background: rgba(179, 69, 53, 0.12);
    color: #b34535;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
}
.section-header {
    color: #17312c;
    font-size: 1.15rem;
    font-weight: 600;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(23, 49, 44, 0.12);
    margin: 1.5rem 0 1rem 0;
}
.result-card {
    background: rgba(255, 251, 245, 0.8);
    border: 1px solid rgba(23, 49, 44, 0.08);
    border-radius: 22px;
    padding: 18px 20px;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] div {
    color: #eef5f1;
}
[data-testid="stSidebar"] .stRadio > label,
[data-testid="stSidebar"] .stSelectbox > label {
    color: #f7fbf8 !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.01em;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
    color: #f4f8f6 !important;
    font-size: 0.98rem !important;
    font-weight: 600 !important;
    padding: 0.18rem 0 !important;
}
[data-testid="stSidebar"] [role="radiogroup"] label p {
    color: #f4f8f6 !important;
    font-size: 0.98rem !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:hover {
    background: rgba(255,255,255,0.04);
    border-radius: 12px;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(255, 252, 247, 0.98) !important;
    border: 1px solid rgba(23, 49, 44, 0.10) !important;
    border-radius: 16px !important;
    min-height: 48px;
}
[data-testid="stSidebar"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-baseweb="select"] div,
[data-testid="stSidebar"] [data-baseweb="select"] input,
[data-testid="stSidebar"] [data-baseweb="select"] svg {
    color: #17312c !important;
    fill: #17312c !important;
}
div[role="listbox"] {
    background: #fffaf3 !important;
    border: 1px solid rgba(23, 49, 44, 0.10) !important;
    border-radius: 16px !important;
    box-shadow: 0 18px 40px rgba(23, 49, 44, 0.12) !important;
}
div[role="option"] {
    color: #17312c !important;
    background: transparent !important;
    font-size: 0.96rem !important;
    font-weight: 500 !important;
}
div[role="option"][aria-selected="true"] {
    background: rgba(23, 49, 44, 0.08) !important;
    color: #17312c !important;
}
div[role="option"]:hover {
    background: rgba(201, 107, 75, 0.10) !important;
}
.stButton > button {
    background: #17312c;
    color: #fff7ef;
    border: none;
    border-radius: 999px;
    padding: 0.68rem 1.4rem;
    font-weight: 600;
    box-shadow: 0 10px 24px rgba(23, 49, 44, 0.16);
}
.stButton > button:hover {
    background: #21443d;
}
[data-testid="stFileUploaderDropzone"] {
    background: rgba(255, 251, 245, 0.88);
    border: 1px dashed rgba(23, 49, 44, 0.18);
    border-radius: 20px;
}
[data-testid="stExpander"] {
    background: rgba(255, 251, 245, 0.7);
    border: 1px solid rgba(23, 49, 44, 0.08);
    border-radius: 18px;
}
</style>
"""


def _detect_single(img_bytes: bytes, filename: str, category: str | None) -> dict:
    array = np.frombuffer(img_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"无法读取图片文件: {filename}")
    t0 = time.perf_counter()
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


def _show_image(image, caption: str | None = None):
    try:
        st.image(image, caption=caption, use_container_width=True)
    except TypeError:
        st.image(image, caption=caption, use_column_width=True)


def _plotly_base_layout(fig: go.Figure, *, xaxis_title: str = "", yaxis_title: str = ""):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#17312c"),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(23,49,44,0.12)", zeroline=False)


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
        _show_image(cv2.cvtColor(result["annotated"], cv2.COLOR_BGR2RGB))
    with col_info:
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)


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
                    marker=dict(colors=["#1a7f58", "#b34535"]),
                    textinfo="label+percent",
                    textfont=dict(size=13, color="#17312c"),
                )
            ]
        )
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#17312c"))
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_bar:
        times = [result["elapsed"] * 1000 for result in all_results]
        fig_bar = go.Figure(
            data=[
                go.Bar(
                    x=[result["filename"] for result in all_results],
                    y=times,
                    marker_color=["#17312c" if result["ok"] else "#c96b4b" for result in all_results],
                    marker_line_color="rgba(23,49,44,0.08)",
                    marker_line_width=1,
                )
            ]
        )
        _plotly_base_layout(fig_bar, xaxis_title="文件", yaxis_title="耗时 (ms)")
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
        fig = go.Figure(
            data=[
                go.Scatter(
                    x=[p["time"] for p in points],
                    y=[p["count"] for p in points],
                    mode="lines+markers",
                    line=dict(color="#17312c", width=3),
                    marker=dict(color="#c96b4b", size=7),
                )
            ]
        )
        _plotly_base_layout(fig, xaxis_title="时间 (s)", yaxis_title="检测数")
        st.plotly_chart(fig, use_container_width=True)
    for frame in video_result["frames"]:
        _show_image(cv2.cvtColor(frame["annotated"], cv2.COLOR_BGR2RGB), caption=frame["label"])
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
    st.markdown(
        """
        <div class="hero-card">
          <div class="gradient-sub">Adaptive QR Detection Workspace</div>
          <div class="gradient-title">QR 智能检测工作台</div>
          <div class="hero-copy">
            适合做单图验证、批量巡检、视频抽帧检测和摄像头演示。当前界面优先强调快速试跑、
            结果可读性和课堂展示时的观感，而不是实验性质的调试布局。
          </div>
          <div class="hero-grid">
            <div class="hero-pill"><span>输入类型</span><strong>图片 / 视频 / 实时画面</strong></div>
            <div class="hero-pill"><span>输出能力</span><strong>标注图 + 统计面板</strong></div>
            <div class="hero-pill"><span>建议路径</span><strong>先跑 demo，再试完整数据</strong></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-card">
              <h3>操作面板</h3>
              <p>建议先用 <code>qrcodes/demo</code> 对应样例快速验证，再切换到更重的批量或视频模式。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        mode = st.radio("选择模式", ["单张图片", "批量上传", "视频检测", "摄像头实时"])
        category = st.selectbox(
            "场景类别",
            options=[""] + list(CATEGORY_CHOICES),
            format_func=lambda value: "自动识别" if value == "" else f"{CATEGORY_LABELS.get(value, value)} ({value})",
        )

    if mode == "单张图片":
        st.session_state.pop("batch_results", None)
        st.session_state.pop("video_result", None)
        st.markdown('<div class="section-header">单张检测</div>', unsafe_allow_html=True)
        st.markdown('<div class="hint-card">上传一张图片后点击“开始检测”。如果只是验证项目是否正常运行，推荐先用 <code>qrcodes/demo</code> 中的样例图。</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("上传图片", type=["jpg", "jpeg", "png", "bmp", "webp"])
        if st.button("开始检测", key="single_detect"):
            if uploaded is None:
                st.warning("请先上传一张图片。")
            else:
                with st.spinner("正在分析图片..."):
                    st.session_state["single_result"] = _detect_single(uploaded.getvalue(), uploaded.name, category or None)
        if st.session_state.get("single_result"):
            _render_single_result(st.session_state["single_result"])
    elif mode == "批量上传":
        st.session_state.pop("single_result", None)
        st.session_state.pop("video_result", None)
        st.markdown('<div class="section-header">批量检测</div>', unsafe_allow_html=True)
        st.markdown('<div class="hint-card">适合做小批量对比验证。上传多张图片后点击“开始批量检测”，处理时间会随图片数和复杂度上升。</div>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader("上传多张图片", type=["jpg", "jpeg", "png", "bmp", "webp"], accept_multiple_files=True)
        if st.button("开始批量检测", key="batch_detect"):
            if not uploaded_files:
                st.warning("请至少上传一张图片。")
            else:
                with st.spinner(f"正在处理 {len(uploaded_files)} 张图片..."):
                    st.session_state["batch_results"] = [_detect_single(file.getvalue(), file.name, category or None) for file in uploaded_files]
        if st.session_state.get("batch_results"):
            _render_batch_results(st.session_state["batch_results"])
    elif mode == "视频检测":
        st.session_state.pop("single_result", None)
        st.session_state.pop("batch_results", None)
        st.markdown('<div class="section-header">视频检测</div>', unsafe_allow_html=True)
        st.markdown('<div class="hint-card">视频模式会按一定间隔抽帧检测，更适合快速查看某段视频里二维码出现的时间点和稳定性。</div>', unsafe_allow_html=True)
        uploaded_video = st.file_uploader("上传视频", type=["mp4", "mov", "avi", "mkv"])
        if st.button("开始视频检测", key="video_detect"):
            if uploaded_video is None:
                st.warning("请先上传一个视频文件。")
            else:
                with st.spinner("正在抽帧并分析视频..."):
                    st.session_state["video_result"] = _process_video(uploaded_video, category or None)
        if st.session_state.get("video_result"):
            _render_video_result(st.session_state["video_result"])
    else:
        st.session_state.pop("single_result", None)
        st.session_state.pop("batch_results", None)
        st.session_state.pop("video_result", None)
        st.markdown('<div class="section-header">摄像头实时检测</div>', unsafe_allow_html=True)
        st.markdown('<div class="hint-card">这个模式更适合课堂演示或现场验证。如果当前环境缺少 WebRTC 依赖，页面会给出安装提示。</div>', unsafe_allow_html=True)
        _render_camera_mode()


if __name__ == "__main__":
    main()
