"""GSG 能力探测 —— 同一份代码要能在“有 GPU / 无 GPU / 无 Cg”环境下都跑。

GSG = GraphicsStateGuardian，是 Panda3D 对“某个图形 API 上下文”的抽象，
所有“显卡支持什么”的问题都问它：``base.win.get_gsg()``。

在 Apple Silicon + Panda3D 1.10 上：
  * OpenGL 为 legacy 2.1 context，GLSL 1.20 可用；
  * ``supports_basic_shaders``（Cg 基础着色器）为 False → CommonFilters 不可用，
    所以 l16 课程用 FilterManager + 自写 GLSL 实现后处理。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Capabilities:
    has_window: bool
    renderer: str = "none"
    gl_version: str = "-"
    glsl: bool = False
    glsl_version: tuple[int, int] = (0, 0)
    cg_basic_shaders: bool = False
    shadow_filter: bool = False
    max_texture_size: int = 0

    @property
    def summary(self) -> str:
        if not self.has_window:
            return "headless (no GSG)"
        return (f"{self.renderer} | GL {self.gl_version} | GLSL {self.glsl_version[0]}.{self.glsl_version[1]}"
                f" | Cg={'Y' if self.cg_basic_shaders else 'N'}")


def detect(base) -> Capabilities:
    win = getattr(base, "win", None)
    if win is None:
        return Capabilities(has_window=False)
    gsg = win.get_gsg()
    if gsg is None:  # pragma: no cover - 窗口尚未打开
        return Capabilities(has_window=True)
    return Capabilities(
        has_window=True,
        renderer=gsg.get_driver_renderer(),
        gl_version=gsg.get_driver_version(),
        glsl=bool(gsg.get_supports_glsl()),
        glsl_version=(gsg.get_driver_shader_version_major(), gsg.get_driver_shader_version_minor()),
        cg_basic_shaders=bool(gsg.get_supports_basic_shaders()),
        shadow_filter=bool(gsg.get_supports_shadow_filter()),
        max_texture_size=gsg.get_max_texture_dimension(),
    )


def get(base) -> Capabilities:
    """优先使用 App 上缓存的结果。"""
    caps = getattr(base, "caps", None)
    return caps if isinstance(caps, Capabilities) else detect(base)
