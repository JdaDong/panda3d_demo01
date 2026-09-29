"""程序化资源：不依赖外部美术文件，用代码生成几何体、贴图、音频。

这里集中了 Panda3D 底层几何管线的核心类（l02 课程会再逐个拆解）::

    GeomVertexFormat   顶点格式（有哪些列：vertex/normal/color/texcoord）
    GeomVertexData     顶点数据表（行 = 顶点，列 = 属性）
    GeomVertexWriter   按列写入的游标
    GeomTriangles      图元（索引三角形）
    Geom               顶点数据 + 若干图元
    GeomNode           可挂到场景图的节点，持有若干 Geom
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path
from typing import Sequence

from panda3d.core import (
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    LineSegs,
    LVector3,
    NodePath,
    PNMImage,
    SamplerState,
    Texture,
)

Color = tuple[float, float, float, float]


# --------------------------------------------------------------------------- 几何
def make_cube(size: float = 1.0, color: Color | None = None, name: str = "cube") -> NodePath:
    """带法线 + UV 的立方体（24 顶点：每个面 4 个独立顶点，法线才能是硬边）。"""
    h = size / 2.0
    # 每个面：法线, 4 个角（逆时针，从外向里看）
    faces: list[tuple[tuple[int, int, int], list[tuple[float, float, float]]]] = [
        ((0, 0, 1), [(-h, -h, h), (h, -h, h), (h, h, h), (-h, h, h)]),      # +Z 顶
        ((0, 0, -1), [(-h, h, -h), (h, h, -h), (h, -h, -h), (-h, -h, -h)]),  # -Z 底
        ((0, -1, 0), [(-h, -h, -h), (h, -h, -h), (h, -h, h), (-h, -h, h)]),  # -Y 前
        ((0, 1, 0), [(h, h, -h), (-h, h, -h), (-h, h, h), (h, h, h)]),       # +Y 后
        ((1, 0, 0), [(h, -h, -h), (h, h, -h), (h, h, h), (h, -h, h)]),       # +X 右
        ((-1, 0, 0), [(-h, h, -h), (-h, -h, -h), (-h, -h, h), (-h, h, h)]),  # -X 左
    ]
    # v3n3c4t2 = 位置(3) + 法线(3) + 颜色(4) + 纹理坐标(2)，内置的常用格式
    vdata = GeomVertexData(name, GeomVertexFormat.get_v3n3c4t2(), Geom.UH_static)
    vdata.set_num_rows(24)
    vw, nw = GeomVertexWriter(vdata, "vertex"), GeomVertexWriter(vdata, "normal")
    cw, tw = GeomVertexWriter(vdata, "color"), GeomVertexWriter(vdata, "texcoord")
    tris = GeomTriangles(Geom.UH_static)
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for fi, (normal, corners) in enumerate(faces):
        # 未指定颜色时每个面给一个不同的颜色，方便看清朝向
        c = color or _face_palette(fi)
        for (x, y, z), (u, v) in zip(corners, uvs):
            vw.add_data3(x, y, z)
            nw.add_data3(*normal)
            cw.add_data4(*c)
            tw.add_data2(u, v)
        base = fi * 4
        tris.add_vertices(base, base + 1, base + 2)
        tris.add_vertices(base, base + 2, base + 3)
    geom = Geom(vdata)
    geom.add_primitive(tris)
    node = GeomNode(name)
    node.add_geom(geom)
    return NodePath(node)


def make_uv_sphere(radius: float = 1.0, rings: int = 16, segments: int = 24,
                   color: Color = (1, 1, 1, 1), name: str = "sphere") -> NodePath:
    """经纬球：rings × segments 网格，展示“顶点共享 + 索引复用”。"""
    rings, segments = max(rings, 2), max(segments, 3)
    vdata = GeomVertexData(name, GeomVertexFormat.get_v3n3c4t2(), Geom.UH_static)
    vdata.set_num_rows((rings + 1) * (segments + 1))
    vw, nw = GeomVertexWriter(vdata, "vertex"), GeomVertexWriter(vdata, "normal")
    cw, tw = GeomVertexWriter(vdata, "color"), GeomVertexWriter(vdata, "texcoord")
    for r in range(rings + 1):
        phi = math.pi * r / rings  # 0 → π（北极 → 南极）
        for s in range(segments + 1):
            theta = 2 * math.pi * s / segments
            n = LVector3(math.sin(phi) * math.cos(theta), math.sin(phi) * math.sin(theta), math.cos(phi))
            vw.add_data3(n * radius)
            nw.add_data3(n)
            cw.add_data4(*color)
            tw.add_data2(s / segments, 1 - r / rings)
    tris = GeomTriangles(Geom.UH_static)
    stride = segments + 1
    for r in range(rings):
        for s in range(segments):
            a, b = r * stride + s, (r + 1) * stride + s
            tris.add_vertices(a, b, a + 1)
            tris.add_vertices(a + 1, b, b + 1)
    geom = Geom(vdata)
    geom.add_primitive(tris)
    node = GeomNode(name)
    node.add_geom(geom)
    return NodePath(node)


def make_plane(size: float = 10.0, color: Color = (0.5, 0.5, 0.5, 1), name: str = "plane") -> NodePath:
    """XY 平面上的地面（法线 +Z）。"""
    h = size / 2
    vdata = GeomVertexData(name, GeomVertexFormat.get_v3n3c4t2(), Geom.UH_static)
    vw, nw = GeomVertexWriter(vdata, "vertex"), GeomVertexWriter(vdata, "normal")
    cw, tw = GeomVertexWriter(vdata, "color"), GeomVertexWriter(vdata, "texcoord")
    for (x, y), (u, v) in zip([(-h, -h), (h, -h), (h, h), (-h, h)], [(0, 0), (1, 0), (1, 1), (0, 1)]):
        vw.add_data3(x, y, 0)
        nw.add_data3(0, 0, 1)
        cw.add_data4(*color)
        tw.add_data2(u * size / 2, v * size / 2)  # uv 重复 size/2 次，配合棋盘贴图
    tris = GeomTriangles(Geom.UH_static)
    tris.add_vertices(0, 1, 2)
    tris.add_vertices(0, 2, 3)
    geom = Geom(vdata)
    geom.add_primitive(tris)
    node = GeomNode(name)
    node.add_geom(geom)
    return NodePath(node)


def make_axes(length: float = 1.0, thickness: float = 2.0) -> NodePath:
    """LineSegs：最简单的“画线”API，红X 绿Y 蓝Z。"""
    ls = LineSegs("axes")
    ls.set_thickness(thickness)
    for color, end in (((1, 0, 0, 1), (length, 0, 0)), ((0, 1, 0, 1), (0, length, 0)), ((0, 0, 1, 1), (0, 0, length))):
        ls.set_color(*color)
        ls.move_to(0, 0, 0)
        ls.draw_to(*end)
    return NodePath(ls.create())


def make_grid(size: int = 10, step: float = 1.0, color: Color = (0.4, 0.4, 0.45, 1)) -> NodePath:
    """地面网格线。"""
    ls = LineSegs("grid")
    ls.set_color(*color)
    half = size * step / 2
    for i in range(size + 1):
        p = -half + i * step
        ls.move_to(p, -half, 0)
        ls.draw_to(p, half, 0)
        ls.move_to(-half, p, 0)
        ls.draw_to(half, p, 0)
    return NodePath(ls.create())


def count_geom_nodes(np: NodePath) -> int:
    """find_all_matches 的 ``+类型名`` 语法：匹配某种节点类型。"""
    return np.find_all_matches("**/+GeomNode").get_num_paths()


def scene_tree(np: NodePath, depth: int = 0, max_depth: int = 6) -> list[str]:
    """手写一个 NodePath.ls()：递归遍历子节点，返回可读的树形文本。"""
    lines = [f"{'  ' * depth}{np.node().get_type().get_name()} {np.get_name()}"]
    if depth < max_depth:
        for child in np.get_children():
            lines.extend(scene_tree(child, depth + 1, max_depth))
    return lines


# --------------------------------------------------------------------------- 贴图
def make_checker_image(size: int = 64, cells: int = 8,
                       c1: tuple[float, float, float] = (0.9, 0.9, 0.9),
                       c2: tuple[float, float, float] = (0.2, 0.2, 0.25)) -> PNMImage:
    """PNMImage：CPU 端图像缓冲，可逐像素读写，然后交给 Texture 上传到 GPU。"""
    img = PNMImage(size, size, 4)  # 4 通道 RGBA
    cell = max(size // cells, 1)
    for y in range(size):
        for x in range(size):
            c = c1 if ((x // cell) + (y // cell)) % 2 == 0 else c2
            img.set_xel(x, y, *c)
            img.set_alpha(x, y, 1.0)
    return img


def make_checker_texture(size: int = 64, cells: int = 8, **kw) -> Texture:
    tex = Texture("checker")
    tex.load(make_checker_image(size, cells, **kw))
    # 采样器状态：放大用最近邻（像素风），缩小用三线性 mipmap
    tex.set_magfilter(SamplerState.FT_nearest)
    tex.set_minfilter(SamplerState.FT_linear_mipmap_linear)
    tex.set_wrap_u(SamplerState.WM_repeat)
    tex.set_wrap_v(SamplerState.WM_repeat)
    return tex


def make_radial_sprite(size: int = 64) -> Texture:
    """径向渐变圆点（粒子精灵用），alpha 从中心 1 衰减到边缘 0。"""
    img = PNMImage(size, size, 4)
    c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            d = min(math.hypot(x - c, y - c) / c, 1.0)
            a = (1 - d) ** 2
            img.set_xel_a(x, y, 1, 1, 1, a)
    tex = Texture("sprite")
    tex.load(img)
    return tex


# --------------------------------------------------------------------------- 音频
def write_tone_wav(path: Path, freqs: Sequence[float] = (440.0,), duration: float = 0.4,
                   rate: int = 22050, volume: float = 0.4) -> Path:
    """用标准库 wave 生成一段正弦音（多个频率 → 依次滑音），供 AudioManager 加载。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(rate * duration)
    frames = bytearray()
    for i in range(n):
        t = i / rate
        f = freqs[min(int(len(freqs) * i / n), len(freqs) - 1)]
        env = min(1.0, i / (rate * 0.01), (n - i) / (rate * 0.05))  # 起止淡入淡出，防爆音
        sample = int(32767 * volume * env * math.sin(2 * math.pi * f * t))
        frames += struct.pack("<h", sample)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return path


def _face_palette(i: int) -> Color:
    palette = [
        (0.95, 0.35, 0.35, 1), (0.35, 0.8, 0.45, 1), (0.35, 0.55, 0.95, 1),
        (0.95, 0.8, 0.3, 1), (0.8, 0.45, 0.9, 1), (0.3, 0.85, 0.85, 1),
    ]
    return palette[i % len(palette)]
