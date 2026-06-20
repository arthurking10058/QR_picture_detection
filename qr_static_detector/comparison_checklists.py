from __future__ import annotations


def make_check(text: str, priority: str, trigger_token: str) -> dict[str, object]:
    return {
        "text": text,
        "priority": priority,
        "trigger_token": trigger_token,
        "triggered": False,
        "covered": False,
    }


def top_method_check(methods: list[tuple[str, int]]) -> dict[str, object] | None:
    return make_check(f"优先复核方法 {methods[0][0]} 的命中条件。", "高", "双解码器") if methods else None


def top_variant_check(variants: list[tuple[str, int]]) -> dict[str, object] | None:
    return make_check(f"优先复核变体 {variants[0][0]} 的生成逻辑与触发顺序。", "高", "展开") if variants else None


def prioritize_checks(primary_reason: str, items: list[dict[str, object]]) -> list[dict[str, object]]:
    unique_items = []
    seen = set()
    for item in items:
        if not item:
            continue
        key = str(item["text"])
        if key in seen:
            continue
        seen.add(key)
        item["triggered"] = bool(item.get("trigger_token") and item["trigger_token"] in primary_reason)
        item["covered"] = item["triggered"] or item["priority"] == "中"
        unique_items.append(item)
    if "双解码器" in primary_reason:
        unique_items.sort(key=lambda item: 0 if "解码器" in item["text"] or "OpenCV" in item["text"] or "pyzbar" in item["text"] else 1)
    elif "多尺度" in primary_reason:
        unique_items.sort(key=lambda item: 0 if "尺度" in item["text"] or "缩放" in item["text"] else 1)
    elif "透视" in primary_reason or "展开" in primary_reason:
        unique_items.sort(key=lambda item: 0 if "透视" in item["text"] or "warp" in item["text"] or "展开" in item["text"] else 1)
    return unique_items


def build_recommendation_checklist(
    category: str,
    primary_reason: str,
    methods: list[tuple[str, int]],
    variants: list[tuple[str, int]],
) -> list[dict[str, object]]:
    category_key = category.lower()
    if category_key == "glare":
        return prioritize_checks(
            primary_reason,
            [
                make_check("核对高亮掩膜阈值是否过高或过低，确认反光区域被完整捕获。", "高", "高亮"),
                make_check("复查 inpaint 半径与高亮修复后的残留反光斑点。", "高", "高亮"),
                make_check("确认 glare 多尺度候选是否覆盖到有效码区尺寸。", "中", "多尺度"),
                make_check("检查高亮修复后 pyzbar / OpenCV 的解码顺序是否合理。", "高", "双解码器"),
                top_method_check(methods),
                top_variant_check(variants),
            ],
        )
    if category_key == "high_version":
        return prioritize_checks(
            primary_reason,
            [
                make_check("核对高版本码的大尺度候选是否过早缩小，保留高密度细节。", "高", "多尺度"),
                make_check("复查 threshold / CLAHE 分支是否覆盖高版本样本。", "高", "多尺度"),
                make_check("检查高密度码是否在模糊或阈值阶段被抹平。", "高", "多尺度"),
                make_check("确认双解码器顺序是否适合高版本码。", "高", "双解码器"),
                top_method_check(methods),
                top_variant_check(variants),
            ],
        )
    if category_key == "curved":
        return prioritize_checks(
            primary_reason,
            [
                make_check("复查曲面样本的 warp 兜底和透视展开是否真正触发。", "高", "透视"),
                make_check("检查 Sauvola / 自适应阈值组合是否适合曲面局部对比度。", "中", "展开"),
                make_check("确认是否需要增加更强的几何展开候选。", "高", "展开"),
                make_check("核对曲面样本是否在旋转候选后仍存在局部遮挡。", "中", "透视"),
                top_method_check(methods),
                top_variant_check(variants),
            ],
        )
    if category_key == "perspective":
        return prioritize_checks(
            primary_reason,
            [
                make_check("检查 perspective 类的 warp 校正链路是否被触发。", "高", "透视"),
                make_check("复查旋转候选和二值化组合对大角度透视样本的覆盖。", "中", "透视"),
                make_check("确认透视兜底后的码区是否仍保留有效定位图案。", "高", "透视"),
                top_method_check(methods),
                top_variant_check(variants),
            ],
        )
    if category_key == "damaged":
        return prioritize_checks(
            primary_reason,
            [
                make_check("检查闭运算、阈值化与多尺度顺序是否保留了定位图案。", "高", "多尺度"),
                make_check("确认损伤样本的关键数据区是否在预处理后进一步丢失。", "高", "展开"),
                make_check("复查损伤样本是否需要更保守的锐化或二值化策略。", "中", "双解码器"),
                top_method_check(methods),
                top_variant_check(variants),
            ],
        )
    if category_key == "brightness":
        return prioritize_checks(
            primary_reason,
            [
                make_check("检查 gamma 校正范围是否过强或过弱。", "高", "多尺度"),
                make_check("复查 CLAHE 强度对过曝 / 欠曝样本的影响。", "中", "双解码器"),
                make_check("确认亮暗样本分流是否合理，避免细节继续丢失。", "中", "多尺度"),
                top_method_check(methods),
                top_variant_check(variants),
            ],
        )
    if "透视" in primary_reason or "展开" in primary_reason:
        return prioritize_checks(
            primary_reason,
            [
                make_check("优先检查透视校正链路。", "高", "透视"),
                make_check("复查 warp 兜底是否被触发。", "高", "透视"),
                top_variant_check(variants),
            ],
        )
    if "多尺度" in primary_reason:
        return prioritize_checks(
            primary_reason,
            [
                make_check("优先检查缩放范围。", "高", "多尺度"),
                make_check("复查阈值策略。", "中", "多尺度"),
                top_method_check(methods),
                top_variant_check(variants),
            ],
        )
    if "双解码器" in primary_reason:
        return prioritize_checks(
            primary_reason,
            [
                make_check("优先检查 OpenCV / pyzbar 顺序。", "高", "双解码器"),
                make_check("复查输入灰度质量。", "中", "双解码器"),
                top_method_check(methods),
            ],
        )
    if methods:
        return prioritize_checks(
            primary_reason,
            [
                top_method_check(methods),
                make_check("检查相关预处理是否过强。", "中", "双解码器"),
            ],
        )
    if variants:
        return prioritize_checks(
            primary_reason,
            [
                top_variant_check(variants),
                make_check("复查该类别的解码顺序与兜底路径是否匹配。", "中", "双解码器"),
            ],
        )
    return prioritize_checks(
        primary_reason,
        [
            make_check("优先检查该类别的预处理参数。", "中", "多尺度"),
            make_check("复查解码顺序和兜底路径是否匹配。", "中", "双解码器"),
        ],
    )
