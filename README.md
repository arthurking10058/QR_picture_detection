# QR 静态图检测与多场景鲁棒性验证

这份根目录版本已经把你之前的 `FH` 和 `RBA` 两套代码主干整合成一份统一实现：保留了原来主线的简洁入口，也吸收了分类自适应预处理、复杂场景兜底检测、视频/摄像头 Web 演示等增强能力。

## 当前推荐入口

命令行检测：

```bash
python app.py qrcodes/detection --save-json
```

分类数据集批量检测：

```bash
python app.py --batch-root qrcodes/detection --save-json --summarize
python app.py --batch-root qrcodes/detection --category glare --save-json
```

汇总结果对比：

```bash
python compare_summaries.py record/runtime_outputs/summary_by_category.csv another_run/summary_by_category.csv --name glare_compare
```

多次实验总览：

```bash
python build_comparison_index.py --comparisons-root record/comparisons --output-dir record
```

本地网页演示：

```bash
python local_qr_web.py
```

增强版 Streamlit UI：

```bash
streamlit run streamlit_app.py
```

## 整合后的根目录结构

```text
picture_detection/
├─ app.py                       # 统一 CLI：单图、目录、分类数据集批量检测
├─ streamlit_app.py             # 整合自 RBA 的增强版 Web UI
├─ local_qr_web.py              # 轻量本地网页演示入口
├─ qr_static_detector/          # 统一检测核心
├─ qrcodes/                     # 从 RBA/FH 合并出的历史数据集与样例
├─ CATEGORY_PREPROCESSING.md    # 16 类分类预处理策略说明
├─ .streamlit/config.toml       # Streamlit 本地配置
├─ record/runtime_outputs/      # 默认运行输出目录
├─ record/                      # 归档脚本、课程资料、整理记录
```

## 整合内容

- `FH` / `RBA` 共有的 16 类分类预处理策略，已并入 [qr_static_detector/adaptive.py](/D:/github/picture_detection/qr_static_detector/adaptive.py:1)
- `RBA` 更完整的多后端检测、旋转/透视/裁剪兜底逻辑，已并入 [qr_static_detector/detector.py](/D:/github/picture_detection/qr_static_detector/detector.py:1)
- `RBA` 的帧检测能力，已并入 `QRStaticDetector.detect_frame()`
- `RBA` 的 Streamlit 交互模式，已整理为根目录 [streamlit_app.py](/D:/github/picture_detection/streamlit_app.py:1)
- `RBA/FH` 的 `qrcodes/` 数据资源，已复制到根目录 [qrcodes](/D:/github/picture_detection/qrcodes)
- 关键检测参数与类别策略，已集中到 [qr_static_detector/config.py](/D:/github/picture_detection/qr_static_detector/config.py:1)

## 检测能力

当前根目录统一版本支持：

- 普通静态图检测
- 分类自适应预处理检测
- 多图批量检测与结果导出
- 检测后自动生成汇总 CSV / JSON / Markdown 报告
- 视频抽帧检测
- 摄像头实时检测（需要完整依赖）

场景类别共 16 类：

- `nominal`
- `blurred`
- `bright_spots`
- `brightness`
- `close`
- `curved`
- `damaged`
- `glare`
- `high_version`
- `lots`
- `monitor`
- `noncompliant`
- `pathological`
- `perspective`
- `rotations`
- `shadows`

具体策略见 [CATEGORY_PREPROCESSING.md](/D:/github/picture_detection/CATEGORY_PREPROCESSING.md:1)。

## 安装依赖

基础版：

```bash
pip install -r requirements.txt
```

增强版：

```bash
pip install -r requirements-full.txt
```

## 推荐运行方式

当前这台 Windows 环境里，PATH 中的 `python` 可能会误指向不可用的 `msys2 python`，导致 `cv2`、`matplotlib`、`pyzbar` 等依赖不可用。

推荐优先使用以下两种方式之一：

```bash
D:\programme\anaconda\python.exe app.py qrcodes/detection --save-json
```

或先进入你自己的虚拟环境，再运行：

```bash
python app.py qrcodes/detection --save-json
```

如果要跑完整验收链路，推荐命令如下：

```bash
D:\programme\anaconda\python.exe app.py --batch-root qrcodes/detection -o record/runtime_outputs/baseline_full --save-json --summarize
D:\programme\anaconda\python.exe compare_summaries.py record/runtime_outputs/baseline_full/summary_by_category.csv record/runtime_outputs/candidate_no_pyzbar/summary_by_category.csv -o record/comparisons --name baseline_vs_no_pyzbar
D:\programme\anaconda\python.exe build_comparison_index.py --comparisons-root record/comparisons --output-dir record
```

如果当前环境没有 `pyzbar` 或底层 `zbar`，可以先退回 OpenCV 检测：

```bash
python app.py qrcodes/detection --no-pyzbar
```

## 输出结果

- `record/runtime_outputs/images/*_detected.png`
  - 标注后的检测结果图
- `record/runtime_outputs/results.csv`
  - 检测结果汇总
- `record/runtime_outputs/results.json`
  - 使用 `--save-json` 时生成
- `record/runtime_outputs/summary_by_image.csv`
  - 按图片汇总检测结果
- `record/runtime_outputs/summary_by_category.csv`
  - 按类别汇总成功率与耗时
- `record/runtime_outputs/summary_overall.json`
  - 总体统计指标
- `record/runtime_outputs/summary_report.md`
  - 面向阅读的 Markdown 汇总报告
- `record/runtime_outputs/run_meta.json`
  - 单次运行的时间、命令、输入摘要等元数据
- `record/runtime_outputs/diagnostics.json`
  - 单次运行的诊断轨迹，供失败原因模型与长期分析使用
- `record/comparisons/<name>/...`
  - 长期保存的多次实验对比目录
- `record/comparisons/<name>/*comparison*.csv / json / md`
  - 不同实验结果之间的分类对比报告
- `record/comparisons/<name>/*comparison*_report.html`
  - 单文件 HTML 实验报告页，内含总体结论、图表、失败聚类、类别级根因画像卡片，以及 `glare` / `high_version` / `curved` 等类别的定制排查清单
- `record/comparisons/<name>/*comparison*_success_rate_delta.png`
  - 按类别成功率变化柱状图
- `record/comparisons/<name>/*comparison*_avg_time_delta.png`
  - 按类别平均耗时变化柱状图
- `record/comparisons/<name>/*comparison*_input_distribution.png`
  - 基线与对比运行的输入样本分布图
- `record/comparisons/<name>/*comparison*_method_hits.png`
  - 基线与对比运行的方法命中分布图
- `record/comparison_index.html`
  - 多次实验对比总览页
- `record/comparison_index.md`
  - 多次实验对比总览摘要
- `record/comparison_index.json`
  - 多次实验总览的结构化索引数据
- `record/comparisons/<name>/*comparison*_report.html`
  - 报告页中还会包含失败样本聚类、失败原因归类、高风险类别提示、方法/变体命中排行榜、风险趋势摘要

## 说明

- 根目录这套代码已经是整合后的主版本，后续建议继续只维护根目录实现
- `samples/` 和 `outputs/` 已不再是主线必需目录，可在确认后删除
