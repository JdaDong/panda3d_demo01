"""L03 纹理 —— 从 PNMImage 到多重纹理、TexGen、动态纹理。

关键对象
--------
* ``PNMImage``   CPU 侧图像（可读写像素、缩放、保存文件）
* ``Texture``    GPU 侧纹理（持有 RAM image，按需上传显存）
* ``SamplerState`` 过滤 / 环绕方式
* ``TextureStage`` 纹理层：一个模型可叠多层纹理，每层有自己的混合模式与 UV
* ``TexGenAttrib`` 自动生成 UV（球面映射、世界坐标投射等），无需模型自带 UV
"""

from __future__ import annotations

import math

from panda3d.core import (
    PNMImage,
    PerlinNoise2,
    SamplerState,
    TexGenAttrib,
    Texture,
    TextureStage,
)

from ..core import Lesson, register
from ..core.procedural import make_checker_texture, make_cube, make_plane, make_uv_sphere


@register
class TextureLesson(Lesson):
    key = "textures"
    order = 3
    title = "纹理与纹理层"
    title_en = "Textures & TextureStages"
    summary = "PNMImage 程序化贴图、过滤/环绕、多层混合、UV 动画、TexGen、动态 RAM 纹理"
    apis = (
        "PNMImage", "PNMImage.set_xel/get_xel", "PNMImage.gaussian_filter", "Texture.load",
        "Texture.setup_2d_texture", "Texture.set_ram_image_as", "Texture.set_minfilter/set_magfilter",
        "Texture.set_anisotropic_degree", "Texture.set_wrap_u/v", "SamplerState",
        "loader.load_texture", "TextureStage", "TextureStage.set_mode", "TextureStage.set_sort",
        "NodePath.set_texture", "NodePath.set_tex_scale", "NodePath.set_tex_offset",
        "NodePath.set_tex_rotate", "NodePath.set_tex_gen", "TexGenAttrib", "PerlinNoise2",
    )
    controls = ("M 切换细节层混合模式（modulate/add/decal）",)

    DYN = 32  # 动态纹理边长

    def setup(self) -> None:
        self.place_camera((0, -16, 7))

        # 1) 程序化棋盘地面 + UV 滚动
        self.ground = make_plane(20, color=(1, 1, 1, 1))
        self.ground.reparent_to(self.root)
        self.ground.set_texture(make_checker_texture(64, 8), 1)

        # 2) 文件纹理（panda3d 自带 models/maps）+ 多层纹理
        self.cube = make_cube(2.5, color=(1, 1, 1, 1))
        self.cube.reparent_to(self.root)
        self.cube.set_pos(-4, 0, 2)
        base_tex = self.base.loader.load_texture("maps/envir-rock1.jpg")
        base_tex.set_anisotropic_degree(4)
        self.cube.set_texture(base_tex)  # 默认层 TextureStage.get_default()

        self.detail_stage = TextureStage("detail")
        self.detail_stage.set_sort(10)  # sort 大的层后叠加
        self.modes = [TextureStage.M_modulate, TextureStage.M_add, TextureStage.M_decal]
        self.mode_names = ["modulate", "add", "decal"]
        self.mode_idx = 0
        self.detail_stage.set_mode(self.modes[0])
        self.cube.set_texture(self.detail_stage, self.make_noise_texture(64))
        self.cube.set_tex_scale(self.detail_stage, 3, 3)  # 该层 UV 放大 3 倍（重复）

        # 3) TexGen：球面反射映射 —— 模型不需要 UV
        self.sphere = make_uv_sphere(1.5, 24, 32)
        self.sphere.reparent_to(self.root)
        self.sphere.set_pos(0, 0, 2)
        self.sphere.set_texture(self.base.loader.load_texture("maps/envir-mountain1.png"))
        self.sphere.set_tex_gen(TextureStage.get_default(), TexGenAttrib.M_eye_sphere_map)

        # 4) 动态纹理：每 0.1s 在 CPU 上重算一张“等离子”图并上传
        self.dyn_tex = Texture("plasma")
        self.dyn_tex.setup_2d_texture(self.DYN, self.DYN, Texture.T_unsigned_byte, Texture.F_rgba8)
        self.dyn_tex.set_magfilter(SamplerState.FT_linear)
        self.screen = make_cube(2.5, color=(1, 1, 1, 1))
        self.screen.reparent_to(self.root)
        self.screen.set_pos(4, 0, 2)
        self.screen.set_texture(self.dyn_tex)
        self.update_plasma(0.0)

        self.accept("m", self.cycle_mode)
        self.add_task(self._animate, "uv-anim")
        self.add_task(self._plasma_task, "plasma", delay=0.1)
        self.status("地面 UV 滚动 / 立方体双层纹理 / 球面环境映射 / 右侧动态纹理")

    # ------------------------------------------------------------ 纹理工厂
    @staticmethod
    def make_noise_texture(size: int) -> Texture:
        """PerlinNoise2 生成灰度噪声 → PNMImage → 高斯模糊 → Texture。"""
        noise = PerlinNoise2(8, 8, 256, 42)  # (x 缩放, y 缩放, 表大小, 种子)
        img = PNMImage(size, size, 3)
        for y in range(size):
            for x in range(size):
                v = noise.noise(x / size * 8, y / size * 8) * 0.5 + 0.5
                img.set_xel(x, y, v, v, v)
        img.gaussian_filter(1.0)
        tex = Texture("noise")
        tex.load(img)
        tex.set_wrap_u(SamplerState.WM_repeat)
        tex.set_wrap_v(SamplerState.WM_repeat)
        return tex

    def update_plasma(self, t: float) -> bytes:
        """直接拼 RGBA 字节写入 RAM image（set_ram_image_as 可指定通道顺序）。"""
        n = self.DYN
        buf = bytearray(n * n * 4)
        for y in range(n):
            for x in range(n):
                v = math.sin(x * 0.4 + t) + math.sin(y * 0.3 + t * 1.3) + math.sin((x + y) * 0.2 + t * 0.7)
                i = (y * n + x) * 4
                buf[i] = int(127 + 127 * math.sin(v))
                buf[i + 1] = int(127 + 127 * math.sin(v + 2.1))
                buf[i + 2] = int(127 + 127 * math.sin(v + 4.2))
                buf[i + 3] = 255
        data = bytes(buf)
        self.dyn_tex.set_ram_image_as(data, "RGBA")
        return data

    # ------------------------------------------------------------ 行为
    def cycle_mode(self) -> str:
        self.mode_idx = (self.mode_idx + 1) % len(self.modes)
        self.detail_stage.set_mode(self.modes[self.mode_idx])
        name = self.mode_names[self.mode_idx]
        self.state["detail_mode"] = name
        self.status(f"细节层混合模式: {name}")
        return name

    def _animate(self, task):
        t = task.time
        # 默认层的 UV 偏移：地面缓慢滚动
        self.ground.set_tex_offset(TextureStage.get_default(), t * 0.05, t * 0.02)
        self.cube.set_tex_rotate(self.detail_stage, t * 10)  # 细节层旋转（度）
        self.sphere.set_h(t * 20)
        return task.cont

    def _plasma_task(self, task):
        self.update_plasma(task.time)
        return task.again  # again = 按 delay 再次调度（周期任务）
