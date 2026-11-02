"""证据图片取证检测模块的单元测试。"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageDraw

from app.services.evidence_forensics import analyze_image


def _to_bytes(img: Image.Image, fmt: str = "PNG", exif=None) -> bytes:
    buf = io.BytesIO()
    kwargs = {"format": fmt}
    if exif is not None:
        kwargs["exif"] = exif
    img.save(buf, **kwargs)
    return buf.getvalue()


def _make_screenshot() -> bytes:
    """正常屏幕截图：浅色背景 + 深色文字 + 彩色元素。"""
    img = Image.new("RGB", (400, 300), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    # 彩色元素（头像 / 气泡），使截图不是纯灰度
    draw.rectangle([20, 20, 60, 60], fill=(80, 180, 90))
    draw.rectangle([20, 90, 180, 120], fill=(200, 240, 200))
    draw.text((30, 30), "工资条 2026年10月 实发 8500元", fill=(20, 20, 20))
    draw.text((30, 60), "老板：下个月发", fill=(60, 60, 60))
    return _to_bytes(img)


def _make_mosaic() -> bytes:
    """含一块马赛克涂抹的图片。"""
    img = Image.new("RGB", (400, 300), (245, 245, 245))
    # 96x96 的 8x8 色块网格，块内均匀、块间颜色离散
    size = 96
    block = 8
    mosaic = np.zeros((size, size, 3), dtype=np.uint8)
    n = size // block
    for i in range(n):
        for j in range(n):
            color = ((i * 37) % 256, (j * 53) % 256, ((i + j) * 29) % 256)
            mosaic[i * block : (i + 1) * block, j * block : (j + 1) * block] = color
    img.paste(Image.fromarray(mosaic), (152, 102))
    return _to_bytes(img)


def _make_spliced() -> bytes:
    """左右两半内容差异明显的拼接图。"""
    arr = np.zeros((300, 400, 3), dtype=np.uint8)
    arr[:, :200] = 250
    arr[:, 200:] = 10
    return _to_bytes(Image.fromarray(arr))


def _make_camera_photo() -> bytes:
    """带相机 EXIF 标记的照片。"""
    img = Image.new("RGB", (400, 300), (80, 120, 160))
    exif = Image.Exif()
    exif[0x010F] = "Canon"  # Make
    exif[0x0110] = "Canon EOS 5D"  # Model
    return _to_bytes(img, "JPEG", exif=exif)


def _make_photoshop() -> bytes:
    """EXIF Software 标记为编辑软件的图片。"""
    img = Image.new("RGB", (400, 300), (200, 200, 200))
    exif = Image.Exif()
    exif[0x0131] = "Adobe Photoshop 2024"
    return _to_bytes(img, "JPEG", exif=exif)


def test_normal_screenshot_not_suspicious():
    result = analyze_image("evidence.png", _make_screenshot())
    assert result.image_type == "screenshot"
    assert result.suspicious is False


def test_mosaic_detected():
    result = analyze_image("evidence.png", _make_mosaic())
    assert result.image_type == "screenshot"
    assert result.suspicious is True
    assert any("马赛克" in reason for reason in result.reasons)


def test_splice_detected():
    result = analyze_image("evidence.png", _make_spliced())
    assert result.suspicious is True
    assert any("拼接" in reason for reason in result.reasons)


def test_camera_photo_classified_and_not_suspicious():
    result = analyze_image("evidence.jpg", _make_camera_photo())
    assert result.image_type == "camera_photo"
    assert result.suspicious is False


def test_photoshop_exif_detected():
    result = analyze_image("evidence.jpg", _make_photoshop())
    assert result.suspicious is True
    assert any("编辑软件" in reason for reason in result.reasons)


def test_invalid_image_handled():
    result = analyze_image("evidence.png", b"not an image")
    assert result.image_type == "unknown"
    assert result.suspicious is False


def test_plain_background_not_mosaic():
    """纯色背景不应被误判为马赛克。"""
    img = Image.new("RGB", (400, 300), (245, 245, 245))
    result = analyze_image("evidence.png", _to_bytes(img))
    assert result.suspicious is False
