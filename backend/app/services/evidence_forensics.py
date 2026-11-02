"""证据图片取证检测模块（第一版）。

对上传的证据图片做初步伪造痕迹筛查，输出「可疑 / 正常 + 原因」。
结果仅作为风险提示，不构成真伪鉴定结论。

检测策略按图片类型区分：

- camera_photo（相机照片）：ELA 重压缩误差分析
- screenshot（屏幕截图）：拼接边界 + 马赛克 / 涂抹检测
- document（扫描 / 文档件）：按截图处理

所有类型都会做 EXIF 编辑软件痕迹检测。

说明：
- 该模块只做「初步筛查」，不保证 100% 准确，存在误报与漏报。
- 屏幕截图、裁剪过的图片属于正常证据形态，不做相机照片的噪声 / ELA 标准，
  避免误伤聊天记录、工资条、转账等常见截图证据。
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image, UnidentifiedImageError

DISCLAIMER = "系统初步筛查仅供参考，不构成真伪鉴定结论。"

# 常见编辑软件在 EXIF Software 字段中可能留下的名称痕迹。
# 只保留明确属于编辑软件的关键词，避免把相机 / 手机型号误判为编辑软件。
EDITOR_SOFTWARE_HINTS = (
    "photoshop",
    "adobe",
    "gimp",
    "picsart",
    "snapseed",
    "lightroom",
    "meitu",
    "xingtu",
    "canva",
    "醒图",
    "美图",
    "美颜",
)

# 相机照片常见的 EXIF 标签 ID（Make / Model / FNumber / ISO / 快门 / 焦距）
_CAMERA_TAG_IDS = {0x010F, 0x0110, 0x829D, 0x8827, 0x829A, 0x920A}
_SOFTWARE_TAG = 0x0131

# 分析前缩放的最长边，控制计算量
_MAX_DIMENSION = 1600


@dataclass
class ForensicsResult:
    """取证检测结果。checks 中 True 表示该项通过（正常），False 表示可疑。"""

    image_type: str
    suspicious: bool
    reasons: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


def analyze_image(filename: str, content: bytes) -> ForensicsResult:
    """分析证据图片，返回初步取证检测结果。

    解码失败时返回 image_type="unknown"、suspicious=False（不因无法分析而拦截）。
    """
    try:
        img: Image.Image = Image.open(io.BytesIO(content))
        img.load()
    except (UnidentifiedImageError, OSError, ValueError):
        return ForensicsResult(
            image_type="unknown",
            suspicious=False,
            reasons=["无法解析图片，跳过取证检测"],
        )

    exif = img.getexif() if hasattr(img, "getexif") else None
    image_type = _classify_image(img, exif)

    # 统一缩放到合理尺寸，避免大图拖慢分析
    img = _resize_for_analysis(img)
    arr = np.asarray(img.convert("RGB")).astype(np.int16)

    checks: dict[str, bool] = {}
    reasons: list[str] = []

    # 通用：EXIF 编辑软件痕迹
    exif_ok, exif_reason = _exif_check(exif)
    checks["exif"] = exif_ok
    if not exif_ok:
        reasons.append(exif_reason)

    if image_type == "camera_photo":
        ela_ok, ela_reason = _ela_check(img)
        checks["ela"] = ela_ok
        if not ela_ok:
            reasons.append(ela_reason)
    else:
        splice_ok, splice_reason = _splice_check(arr)
        mosaic_ok, mosaic_reason = _mosaic_check(arr)
        checks["splice"] = splice_ok
        checks["mosaic"] = mosaic_ok
        if not splice_ok:
            reasons.append(splice_reason)
        if not mosaic_ok:
            reasons.append(mosaic_reason)

    suspicious = not all(checks.values())
    if not reasons:
        reasons = ["未发现明显伪造痕迹"]

    return ForensicsResult(
        image_type=image_type,
        suspicious=suspicious,
        reasons=reasons,
        checks=checks,
    )


def _resize_for_analysis(img: Image.Image) -> Image.Image:
    """按最长边缩放到 _MAX_DIMENSION 以内，保持宽高比。"""
    w, h = img.size
    if max(w, h) <= _MAX_DIMENSION:
        return img
    ratio = _MAX_DIMENSION / max(w, h)
    return img.resize(
        (int(w * ratio), int(h * ratio)),
        Image.Resampling.LANCZOS,
    )


def _classify_image(img: Image.Image, exif: Any) -> str:
    """识别图片类型：camera_photo / document / screenshot。"""
    if _has_camera_exif(exif):
        return "camera_photo"
    arr = np.asarray(img.convert("RGB"))
    if _is_grayscale(arr):
        return "document"
    return "screenshot"


def _has_camera_exif(exif: Any) -> bool:
    if not exif:
        return False
    try:
        tag_ids = set(dict(exif).keys())
    except (TypeError, ValueError):
        return False
    return bool(_CAMERA_TAG_IDS.intersection(tag_ids))


def _is_grayscale(arr: Any) -> bool:
    """RGB 三通道几乎一致判定为灰度（文档 / 扫描件）。"""
    r = arr[:, :, 0].astype(np.int16)
    g = arr[:, :, 1].astype(np.int16)
    b = arr[:, :, 2].astype(np.int16)
    return bool(int(np.abs(r - g).max()) + int(np.abs(g - b).max()) < 24)


def _exif_check(exif: Any) -> tuple[bool, str]:
    """检查 EXIF Software 字段是否留有编辑软件痕迹。"""
    if not exif:
        return True, ""
    try:
        software = dict(exif).get(_SOFTWARE_TAG, "")
    except (TypeError, ValueError):
        return True, ""
    if not software:
        return True, ""
    software_str = str(software).lower()
    for hint in EDITOR_SOFTWARE_HINTS:
        if hint in software_str:
            return False, f"图片元数据显示曾使用编辑软件处理（{software}）"
    return True, ""


def _ela_check(img: Image.Image) -> tuple[bool, str]:
    """ELA 错误级别分析：重压缩后误差异常的区域提示局部编辑。"""
    rgb = img.convert("RGB")
    buf = io.BytesIO()
    rgb.save(buf, "JPEG", quality=85)
    buf.seek(0)
    recompressed = Image.open(buf).convert("RGB")

    original = np.asarray(rgb).astype(np.int16)
    recomp = np.asarray(recompressed).astype(np.int16)
    diff = np.abs(original - recomp).mean(axis=2)

    # 真实照片重压缩误差整体均匀；局部编辑区域误差会异常偏高。
    high_ratio = float((diff > 30).mean())
    if high_ratio > 0.12:
        return False, "图像局部重压缩误差异常，疑似编辑痕迹"
    return True, ""


def _splice_check(arr: Any) -> tuple[bool, str]:
    """拼接边界检测：寻找贯穿的强边界线，且两侧内容差异明显。"""
    gray = arr.mean(axis=2)
    h, w = gray.shape

    # 垂直方向（列边界）
    col_diff = np.abs(np.diff(gray, axis=1)).mean(axis=0)
    if w > 20:
        col_threshold = float(col_diff.mean()) * 5 + 20
        for x in np.where(col_diff > col_threshold)[0]:
            if 10 < x < w - 10:
                left = float(gray[:, : x + 1].mean())
                right = float(gray[:, x + 1 :].mean())
                if abs(left - right) > 40:
                    return False, "检测到贯穿边界，疑似拼接痕迹"

    # 水平方向（行边界）
    row_diff = np.abs(np.diff(gray, axis=0)).mean(axis=1)
    if h > 20:
        row_threshold = float(row_diff.mean()) * 5 + 20
        for y in np.where(row_diff > row_threshold)[0]:
            if 10 < y < h - 10:
                top = float(gray[: y + 1, :].mean())
                bottom = float(gray[y + 1 :, :].mean())
                if abs(top - bottom) > 40:
                    return False, "检测到贯穿边界，疑似拼接痕迹"

    return True, ""


def _mosaic_check(arr: Any) -> tuple[bool, str]:
    """马赛克 / 涂抹检测：滑动窗口查找规则色块网格区域。"""
    gray = arr.mean(axis=2).astype(np.float32)
    h, w = gray.shape
    window = 64
    step = 32
    if h < window or w < window:
        return True, ""

    for y in range(0, h - window + 1, step):
        for x in range(0, w - window + 1, step):
            if _is_mosaic_patch(gray[y : y + window, x : x + window]):
                return False, "检测到规则色块网格，疑似马赛克或涂抹痕迹"
    return True, ""


def _is_mosaic_patch(patch: Any) -> bool:
    """判断窗口是否呈现马赛克特征（多条等间距的贯穿跳变线）。

    马赛克块边界是贯穿整行 / 整列的强跳变且等间距；纯色背景无跳变，文字跳变局部。
    """
    hdiff = np.abs(np.diff(patch, axis=1))
    vdiff = np.abs(np.diff(patch, axis=0))

    col_jump = (hdiff > 15).mean(axis=0)
    row_jump = (vdiff > 15).mean(axis=1)

    strong_cols = np.where(col_jump > 0.8)[0]
    strong_rows = np.where(row_jump > 0.8)[0]

    return _is_regular_grid(strong_cols) or _is_regular_grid(strong_rows)


def _is_regular_grid(positions: Any) -> bool:
    """至少 3 条且间距一致的贯穿线，判定为规则网格。"""
    if positions.size < 3:
        return False
    gaps = np.diff(positions)
    median_gap = float(np.median(gaps))
    if median_gap < 4:
        return False
    return bool(float((gaps == median_gap).mean()) > 0.6)
