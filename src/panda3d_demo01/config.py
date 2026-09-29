"""PRC 配置系统 —— Panda3D 的“全局配置中心”。

知识点
------
1. Panda3D 所有运行参数（窗口大小、音频后端、垂直同步、日志级别……）都来自
   *.prc 配置文件。加载顺序：内置默认 → $PANDA_PRC_DIR/*.prc → 代码里的
   ``loadPrcFileData`` / ``loadPrcFile``。后加载的页面优先级更高。
2. **必须在创建 ShowBase 之前**写入与窗口/音频相关的配置，否则不会生效。
3. ``ConfigVariableXxx`` 用来在代码里读取（也可定义新的）配置变量，
   例如 ``ConfigVariableInt('win-size')``。

本模块只提供纯函数，不创建任何 Panda3D 全局对象，方便单测。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from panda3d.core import (
    ConfigPage,
    ConfigPageManager,
    ConfigVariableBool,
    ConfigVariableString,
    loadPrcFile,
    loadPrcFileData,
)

PACKAGE_DIR = Path(__file__).resolve().parent
ASSET_DIR = PACKAGE_DIR / "assets"
PRC_FILE = ASSET_DIR / "prc" / "demo01.prc"


class RunMode(str, Enum):
    """运行模式。

    - WINDOW:    正常开窗交互
    - OFFSCREEN: 离屏缓冲（GraphicsBuffer），能渲染/截图但不弹窗，适合 CI 冒烟
    - HEADLESS:  ``window-type none``，完全不创建图形上下文，只跑场景图/逻辑
    """

    WINDOW = "window"
    OFFSCREEN = "offscreen"
    HEADLESS = "headless"


@dataclass(frozen=True)
class RuntimeConfig:
    """一次运行需要的全部配置（不可变，便于测试断言）。"""

    mode: RunMode = RunMode.WINDOW
    width: int = 1280
    height: int = 720
    mute: bool = False
    show_fps: bool = True
    extra: tuple[str, ...] = field(default_factory=tuple)

    def to_prc(self) -> str:
        """把配置渲染成 PRC 文本（每行 ``变量名 值``）。"""
        window_type = {
            RunMode.WINDOW: "onscreen",
            RunMode.OFFSCREEN: "offscreen",
            RunMode.HEADLESS: "none",
        }[self.mode]
        lines = [
            f"window-type {window_type}",
            f"win-size {self.width} {self.height}",
            "window-title Panda3D Demo01 - API Learning Lab",
            # 让 RTT / 滤镜贴图不被强行放大到 2 的幂，GLSL 里 uv 才是 0..1
            "textures-power-2 none",
            # 文本使用 UTF-8，这样 TextNode 才能正确显示中文（还需要 CJK 字体）
            "text-encoding utf8",
            # 多重采样抗锯齿（配合 AntialiasAttrib）
            "framebuffer-multisample 1",
            "multisamples 4",
            f"show-frame-rate-meter {'#t' if self.show_fps and self.mode is RunMode.WINDOW else '#f'}",
            # 静音 / 无头时使用空音频后端，避免在 CI 上打开声卡
            f"audio-library-name {'null' if self.mute or self.mode is not RunMode.WINDOW else 'p3openal_audio'}",
            # 降低无关日志噪音
            "notify-level-display error",
            "notify-level-glgsg error",
            "notify-level-audio error",
            # 自定义配置变量（见 read_custom_flag）
            "demo01-greeting 你好-Panda3D",
        ]
        lines.extend(self.extra)
        return "\n".join(lines) + "\n"


def apply(cfg: RuntimeConfig) -> ConfigPage:
    """在创建 ShowBase 之前调用：先加载包内 .prc 文件，再叠加运行期配置。

    返回 ``loadPrcFileData`` 生成的 ConfigPage，可用于 ``unloadPrcFile`` 回滚。
    """
    if PRC_FILE.exists():
        # loadPrcFile 接收 Filename/字符串，演示“文件形式”的 PRC
        loadPrcFile(str(PRC_FILE))
    # name 参数只是页面名，便于 ConfigPageManager 里识别
    return loadPrcFileData("panda3d_demo01-runtime", cfg.to_prc())


def read_custom_flag() -> str:
    """ConfigVariableString：读取我们自己定义的配置变量。"""
    return ConfigVariableString("demo01-greeting", "hello").get_value()


def is_true(name: str, default: bool = False) -> bool:
    """ConfigVariableBool 读取布尔配置。"""
    return ConfigVariableBool(name, default).get_value()


def list_loaded_pages() -> list[str]:
    """ConfigPageManager：列出当前加载的所有 PRC 页面名（隐式页 = 代码写入的）。"""
    mgr = ConfigPageManager.get_global_ptr()
    names = [mgr.get_explicit_page(i).get_name() for i in range(mgr.get_num_explicit_pages())]
    names += [mgr.get_implicit_page(i).get_name() for i in range(mgr.get_num_implicit_pages())]
    return names
