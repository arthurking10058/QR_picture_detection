# 分类预处理策略说明

本文件整合自早期 `FH` / `RBA` 版本，用于说明根目录统一主线中的 16 类 QR 场景预处理策略。

## 场景类别

- `nominal`：正常条件
- `blurred`：模糊
- `bright_spots`：亮斑
- `brightness`：亮度异常
- `close`：特写
- `curved`：曲面
- `damaged`：损坏
- `glare`：眩光
- `high_version`：高版本
- `lots`：多码共存
- `monitor`：屏幕截图
- `noncompliant`：非标准码
- `pathological`：极端码
- `perspective`：透视
- `rotations`：旋转
- `shadows`：阴影

## 核心思路

- 先按类别生成多组候选灰度图
- 再按类别选择更合适的解码顺序
- 对部分难例追加旋转、裁剪、透视展开和多尺度兜底

## 各类别处理摘要

- `nominal`：CLAHE + 原始灰度
- `blurred`：反锐化、多尺度增强、Sauvola、Otsu
- `bright_spots`：Blackhat 去亮斑 + CLAHE
- `brightness`：Gamma 校正 + CLAHE
- `close`：多尺度缩放
- `curved`：CLAHE + 自适应阈值 + Sauvola
- `damaged`：多尺度 CLAHE + 闭运算 + 阈值化
- `glare`：高亮区域修复 + 多尺度
- `high_version`：更大范围多尺度 + 阈值化
- `lots`：CLAHE + 原始灰度
- `monitor`：多尺度 + CLAHE
- `noncompliant`：CLAHE + 多组自适应阈值
- `pathological`：原始灰度 + CLAHE + 锐化
- `perspective`：CLAHE + 自适应阈值 + 旋转/透视兜底
- `rotations`：CLAHE + 旋转候选
- `shadows`：高对比 CLAHE + Sauvola
