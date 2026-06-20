# qrcodes 数据说明

当前 `qrcodes/` 目录包含两类资源：

## 1. `qrcodes/detection/`

这是主线静态图片检测所使用的分类数据集，按场景类别组织。

当前仓库版本仍保留完整目录，主要用于：

- 本地批量检测验证
- 分类预处理策略联调
- 汇总 / 对比 / 总览链路回归

如果后续需要进一步缩小仓库体积，优先考虑迁出的就是这一部分。

## 2. `qrcodes/decoding/`

这是历史解码样例与编码内容对照资源，主要用于：

- 说明 QR 编码内容类型
- 做少量功能演示

## 3. `qrcodes/demo/`

这是轻量演示入口目录，只保留极少量示例图，适合：

- README 快速演示
- 新环境最小 smoke test
- 不想直接跑完整分类数据集时的快速验证

建议优先使用：

```bash
python app.py qrcodes/demo --save-json
```

如果需要完整分类实验，再使用：

```bash
python app.py --batch-root qrcodes/detection --save-json --summarize
```
