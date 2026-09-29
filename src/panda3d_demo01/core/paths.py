"""运行期文件路径：程序化生成的资源统一写到缓存目录。

Panda3D 的 ``Filename`` 使用 Unix 风格路径（即使在 Windows 上也是 /c/Users/...），
与操作系统路径互转必须使用 ``Filename.from_os_specific`` / ``to_os_specific``。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from panda3d.core import Filename


def cache_dir() -> Path:
    """环境变量 PANDA3D_DEMO01_CACHE 可覆盖，默认系统临时目录。"""
    p = Path(os.environ.get("PANDA3D_DEMO01_CACHE", Path(tempfile.gettempdir()) / "panda3d_demo01"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def to_panda(path: Path | str) -> Filename:
    """OS 路径 → Panda Filename。"""
    return Filename.from_os_specific(str(path))


def panda_str(path: Path | str) -> str:
    """OS 路径 → Panda 风格字符串（loader.load_model 接收它）。"""
    return to_panda(path).get_fullpath()
