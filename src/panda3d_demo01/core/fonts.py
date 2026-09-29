"""字体：Panda3D 默认字体只有 ASCII，显示中文必须加载含 CJK 字形的 TTF/TTC。

``loader.load_font`` 基于 FreeType，返回 ``DynamicTextFont``（运行期按需光栅化字形）。
"""

from __future__ import annotations

import os
from pathlib import Path

CJK_FONT_CANDIDATES = [
    os.environ.get("PANDA3D_DEMO01_FONT", ""),
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "C:/Windows/Fonts/msyh.ttc",
]


def find_cjk_font() -> Path | None:
    for c in CJK_FONT_CANDIDATES:
        if c and Path(c).is_file():
            return Path(c)
    return None


def load_ui_font(loader):
    """返回 (font, supports_cjk)。找不到 CJK 字体则用默认字体 + 英文 HUD。"""
    from panda3d.core import TextNode

    from .paths import panda_str

    path = find_cjk_font()
    if path is not None:
        font = loader.load_font(panda_str(path))
        if font is not None and font.is_valid():
            # 像素/单位越大字越清晰，但字形纹理越占显存
            font.set_pixels_per_unit(48)
            return font, True
    return TextNode.get_default_font(), False
