"""L21 地形：GeoMipTerrain（基于高度图的分块 LOD 地形）。

* 高度图：灰度 PNMImage，尺寸必须是 2^n + 1（本课 129×129）
* ``set_block_size``：每块多少格（块是 LOD 的最小单位）
* ``set_near / set_far``：焦点附近 near 内最高精度，far 外最低精度
* ``set_focal_point``：LOD 的参考点（通常是相机）
* ``generate()`` 首次构建；``update()`` 每帧按焦点重算 LOD（返回是否有块改变）
* ``get_elevation(x, y)``：采样高度（0..1，需乘以根节点 Z 缩放）→ 让物体贴地
* ``set_color_map``：可以直接给一张彩色图做顶点着色

高度图用 StackedPerlinNoise2（多倍频噪声 = 分形地形）生成。
"""

from __future__ import annotations

import math

from panda3d.core import GeoMipTerrain, PNMImage, StackedPerlinNoise2

from ..core import Lesson, register
from ..core.procedural import make_uv_sphere

SIZE = 129
HEIGHT = 12.0


def make_heightmap(size: int = SIZE, seed: int = 3) -> PNMImage:
    # 参数：x/y 缩放、倍频数(num_levels)、每级缩放比、振幅衰减、表大小、种子
    noise = StackedPerlinNoise2(0.02, 0.02, 5, 2.0, 0.5, 256, seed)
    img = PNMImage(size, size, 1, 65535)  # 16 位灰度 → 高度更平滑
    for y in range(size):
        for x in range(size):
            v = noise.noise(x, y) * 0.5 + 0.5
            # 中间挖一个盆地，边缘抬高
            d = math.hypot(x - size / 2, y - size / 2) / (size / 2)
            img.set_gray(x, y, max(0.0, min(1.0, v * 0.7 + d * 0.3)))
    return img


def make_colormap(height: PNMImage) -> PNMImage:
    """按高度上色：水 → 沙 → 草 → 岩 → 雪。"""
    w, h = height.get_x_size(), height.get_y_size()
    img = PNMImage(w, h, 3)
    for y in range(h):
        for x in range(w):
            g = height.get_gray(x, y)
            if g < 0.35:
                c = (0.15, 0.35, 0.7)
            elif g < 0.4:
                c = (0.85, 0.8, 0.55)
            elif g < 0.6:
                c = (0.25, 0.6, 0.25)
            elif g < 0.75:
                c = (0.45, 0.4, 0.35)
            else:
                c = (0.95, 0.95, 0.95)
            img.set_xel(x, y, *c)
    return img


@register
class TerrainLesson(Lesson):
    key = "terrain"
    order = 21
    title = "GeoMipTerrain 地形"
    title_en = "GeoMipTerrain"
    summary = "高度图地形、分块 LOD、focal point、get_elevation 贴地、color map、StackedPerlinNoise2"
    apis = (
        "GeoMipTerrain", "GeoMipTerrain.set_heightfield", "GeoMipTerrain.set_color_map",
        "GeoMipTerrain.set_block_size", "GeoMipTerrain.set_near/set_far", "GeoMipTerrain.set_focal_point",
        "GeoMipTerrain.set_bruteforce", "GeoMipTerrain.generate", "GeoMipTerrain.update",
        "GeoMipTerrain.get_elevation", "GeoMipTerrain.get_root", "StackedPerlinNoise2", "PNMImage(16-bit)",
    )
    controls = ("B 切换 bruteforce(无 LOD)",)

    def setup(self) -> None:
        self.place_camera((SIZE / 2, -70, 80), (SIZE / 2, SIZE / 2, 0))
        self.heightmap = make_heightmap()
        self.terrain = GeoMipTerrain("terrain")
        self.terrain.set_heightfield(self.heightmap)
        self.terrain.set_color_map(make_colormap(self.heightmap))
        self.terrain.set_block_size(32)
        self.terrain.set_near(30)
        self.terrain.set_far(120)
        focal = self.base.camera if getattr(self.base, "camera", None) is not None else self.root
        self.terrain.set_focal_point(focal)
        self.troot = self.terrain.get_root()
        self.troot.reparent_to(self.root)
        self.troot.set_sz(HEIGHT)  # 高度图 0..1 → 0..HEIGHT
        self.terrain.generate()

        self.rover = make_uv_sphere(1.0, color=(1, 0.3, 0.3, 1))
        self.rover.reparent_to(self.root)
        self.bruteforce = False
        self.accept("b", self.toggle_bruteforce)
        self.add_task(self._update, "update")
        self.status("红球沿着地形表面行驶（get_elevation）")

    def ground_z(self, x: float, y: float) -> float:
        return self.terrain.get_elevation(x, y) * self.troot.get_sz()

    def toggle_bruteforce(self) -> bool:
        self.bruteforce = not self.bruteforce
        self.terrain.set_bruteforce(self.bruteforce)
        self.terrain.generate()
        return self.bruteforce

    def _update(self, task):
        changed = self.terrain.update()
        t = task.time * 0.3
        x = SIZE / 2 + math.cos(t) * SIZE * 0.35
        y = SIZE / 2 + math.sin(t) * SIZE * 0.35
        self.rover.set_pos(x, y, self.ground_z(x, y) + 1.0)
        self.state["rover_z"] = round(self.rover.get_z(), 2)
        self.state["lod_changed"] = bool(changed)
        return task.cont
