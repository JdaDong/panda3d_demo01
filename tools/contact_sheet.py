"""把 autopilot 截图拼成一张总览图（纯 PNMImage 实现，无第三方依赖）。

    python tools/contact_sheet.py out/shots docs/images/contact_sheet.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from panda3d.core import Filename, PNMImage


def build(shots: Path, out: Path, cols: int = 4, tile: tuple[int, int] = (480, 270)) -> int:
    files = sorted(shots.glob("*.png"))
    if not files:
        raise SystemExit(f"no png in {shots}")
    tw, th = tile
    rows = (len(files) + cols - 1) // cols
    sheet = PNMImage(cols * tw, rows * th, 3)
    for i, f in enumerate(files):
        img = PNMImage()
        img.read(Filename.from_os_specific(str(f)))
        small = PNMImage(tw, th, 3)
        small.gaussian_filter_from(1.0, img)   # 带抗混叠的缩放
        sheet.copy_sub_image(small, (i % cols) * tw, (i // cols) * th)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.write(Filename.from_os_specific(str(out)))
    return len(files)


if __name__ == "__main__":
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "out/shots")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else "out/contact_sheet.png")
    print(f"{build(src, dst)} shots → {dst}")
