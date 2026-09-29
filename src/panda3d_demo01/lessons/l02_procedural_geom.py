"""L02 程序化几何 —— 从顶点开始自己造模型。

Panda3D 几何管线（从下往上）::

    GeomVertexArrayFormat  一个 array 里有哪些 column（名字/分量数/类型/语义）
    GeomVertexFormat       若干 array 组成的完整格式，register_format 后才能用
    GeomVertexData         按格式存放的顶点表
    GeomVertexWriter/Reader/Rewriter  按列读写的游标
    GeomPrimitive          GeomTriangles / GeomTristrips / GeomLines / GeomPoints ...
    Geom                   = 1 份 GeomVertexData + N 个 GeomPrimitive
    GeomNode               持有多个 (Geom, RenderState) 的场景图节点

本课内容：
1. 自定义顶点格式 + 动态波浪网格（每帧用 GeomVertexRewriter 改顶点）
2. GeomLines 画法线、GeomPoints 画点云
3. CardMaker（四边形）、LineSegs（折线）、Rope（NURBS 曲线）
"""

from __future__ import annotations

import math

from direct.showutil.Rope import Rope
from panda3d.core import (
    CardMaker,
    Geom,
    GeomEnums,
    GeomLines,
    GeomNode,
    GeomPoints,
    GeomTriangles,
    GeomVertexArrayFormat,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexReader,
    GeomVertexRewriter,
    GeomVertexWriter,
    InternalName,
    LineSegs,
    NodePath,
)

from ..core import Lesson, register
from ..core.procedural import make_grid


def make_custom_format() -> GeomVertexFormat:
    """手工拼一个顶点格式：vertex(float32×3) + normal(float32×3) + color(uint8×4)。

    颜色用 NT_uint8 + C_color 语义，比 float32×4 省 75% 显存。
    """
    arr = GeomVertexArrayFormat()
    arr.add_column(InternalName.get_vertex(), 3, GeomEnums.NT_float32, GeomEnums.C_point)
    arr.add_column(InternalName.get_normal(), 3, GeomEnums.NT_float32, GeomEnums.C_normal)
    arr.add_column(InternalName.get_color(), 4, GeomEnums.NT_uint8, GeomEnums.C_color)
    fmt = GeomVertexFormat()
    fmt.add_array(arr)
    # register_format 会返回一个“规范化”的共享实例（相同格式全局唯一）
    return GeomVertexFormat.register_format(fmt)


@register
class ProceduralGeomLesson(Lesson):
    key = "procedural_geom"
    order = 2
    title = "程序化几何"
    title_en = "Procedural Geometry"
    summary = "自定义顶点格式、动态网格、线/点图元、CardMaker、LineSegs、Rope"
    apis = (
        "GeomVertexArrayFormat.add_column", "GeomVertexFormat.register_format", "GeomVertexData",
        "GeomVertexWriter", "GeomVertexReader", "GeomVertexRewriter", "Geom.UH_dynamic",
        "GeomTriangles", "GeomLines", "GeomPoints", "Geom.add_primitive", "GeomNode.add_geom",
        "GeomNode.modify_geom", "Geom.modify_vertex_data", "CardMaker.set_frame/generate",
        "LineSegs", "direct.showutil.Rope", "NodePath.set_render_mode_thickness",
        "NodePath.set_render_mode_perspective", "InternalName",
    )
    controls = ("SPACE 暂停/继续波浪", "N 显示/隐藏法线")

    GRID = 24          # 网格分辨率
    SIZE = 12.0        # 网格边长

    def setup(self) -> None:
        self.place_camera((0, -22, 14))
        self.root.attach_new_node(make_grid(12).node())
        self.paused = False

        # 1) 动态波浪网格
        self.wave = self._build_wave_mesh()
        self.wave.reparent_to(self.root)
        self.wave.set_two_sided(True)

        # 2) 点云：GeomPoints + 渲染模式粗细
        self.points = self._build_point_cloud(200)
        self.points.reparent_to(self.root)
        self.points.set_pos(0, 8, 3)
        self.points.set_render_mode_thickness(4)
        self.points.set_render_mode_perspective(True)  # 点大小随距离缩放

        # 3) CardMaker：最常用的“造一个四边形”工具（HUD 背景、广告牌、地面…）
        cm = CardMaker("card")
        cm.set_frame(-2, 2, -1, 1)      # 左 右 下 上
        cm.set_color(0.9, 0.5, 0.2, 1)
        self.card = self.root.attach_new_node(cm.generate())
        self.card.set_pos(-8, 6, 2)

        # 4) LineSegs：多段折线（螺旋）
        ls = LineSegs("spiral")
        ls.set_thickness(3)
        for i in range(120):
            a = i * 0.2
            ls.set_color(i / 120, 0.4, 1 - i / 120, 1)
            (ls.move_to if i == 0 else ls.draw_to)(8 + math.cos(a) * 1.5, 6 + math.sin(a) * 1.5, i * 0.04)
        self.spiral = self.root.attach_new_node(ls.create())

        # 5) Rope：基于 NurbsCurveEvaluator 的平滑曲线；verts 是 (参考节点, 点) 列表
        self.rope = Rope("rope")
        self.rope.setup(4, [(None, (-10, -6, 0)), (None, (-6, -2, 6)), (None, (-2, -8, 1)), (None, (2, -4, 5))])
        self.rope.ropeNode.set_thickness(4)
        self.rope.reparent_to(self.root)

        self.accept("space", self.toggle_pause)
        self.accept("n", self.toggle_normals)
        self.add_task(self._animate, "wave")
        self.state["vertex_count"] = self.vertex_count(self.wave)
        self.status("GeomVertexRewriter 每帧改写 z 坐标")

    # ------------------------------------------------------------ 构建
    def _build_wave_mesh(self) -> NodePath:
        n, size = self.GRID, self.SIZE
        fmt = make_custom_format()
        # UH_dynamic：提示驱动“这份数据会频繁修改”，放在更合适的显存区域
        vdata = GeomVertexData("wave", fmt, Geom.UH_dynamic)
        vdata.set_num_rows((n + 1) * (n + 1))
        vw = GeomVertexWriter(vdata, "vertex")
        nw = GeomVertexWriter(vdata, "normal")
        cw = GeomVertexWriter(vdata, "color")
        for j in range(n + 1):
            for i in range(n + 1):
                x, y = -size / 2 + size * i / n, -size / 2 + size * j / n
                vw.add_data3(x, y, 0)
                nw.add_data3(0, 0, 1)
                cw.add_data4(0.2 + 0.6 * i / n, 0.5, 0.9 - 0.6 * j / n, 1)
        tris = GeomTriangles(Geom.UH_static)
        for j in range(n):
            for i in range(n):
                a = j * (n + 1) + i
                tris.add_vertices(a, a + 1, a + n + 1)
                tris.add_vertices(a + 1, a + n + 2, a + n + 1)
        geom = Geom(vdata)
        geom.add_primitive(tris)
        node = GeomNode("wave")
        node.add_geom(geom)
        self._normals_np: NodePath | None = None
        return NodePath(node)

    def _build_point_cloud(self, count: int) -> NodePath:
        vdata = GeomVertexData("points", GeomVertexFormat.get_v3c4(), Geom.UH_static)
        vw, cw = GeomVertexWriter(vdata, "vertex"), GeomVertexWriter(vdata, "color")
        pts = GeomPoints(Geom.UH_static)
        for i in range(count):
            # 黄金角螺旋在球面上均匀分布点
            y = 1 - 2 * (i + 0.5) / count
            r = math.sqrt(1 - y * y)
            th = math.pi * (3 - math.sqrt(5)) * i
            vw.add_data3(math.cos(th) * r * 2, y * 2, math.sin(th) * r * 2)
            cw.add_data4(1, 0.9 * (y + 1) / 2, 0.3, 1)
            pts.add_vertex(i)
        geom = Geom(vdata)
        geom.add_primitive(pts)
        node = GeomNode("points")
        node.add_geom(geom)
        return NodePath(node)

    # ------------------------------------------------------------ 动画
    def _animate(self, task):
        if not self.paused:
            self.update_wave(task.time)
        return task.cont

    def update_wave(self, t: float) -> None:
        """GeomVertexRewriter = 可同时读写的游标：读 x,y → 写新的 z 和法线。"""
        geom = self.wave.node().modify_geom(0)          # modify_* 获取可写副本（写时复制）
        vdata = geom.modify_vertex_data()
        vr = GeomVertexRewriter(vdata, "vertex")
        nr = GeomVertexRewriter(vdata, "normal")
        while not vr.is_at_end():
            v = vr.get_data3()
            k, w = 0.8, 2.5
            z = 0.6 * math.sin(k * v.x + w * t) * math.cos(k * v.y + w * t * 0.7)
            vr.set_data3(v.x, v.y, z)
            # 解析法线：n = (-dz/dx, -dz/dy, 1) 归一化
            dzdx = 0.6 * k * math.cos(k * v.x + w * t) * math.cos(k * v.y + w * t * 0.7)
            dzdy = -0.6 * k * math.sin(k * v.x + w * t) * math.sin(k * v.y + w * t * 0.7)
            ln = math.sqrt(dzdx * dzdx + dzdy * dzdy + 1)
            nr.set_data3(-dzdx / ln, -dzdy / ln, 1 / ln)
        self.state["wave_t"] = round(t, 2)

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def toggle_normals(self) -> NodePath:
        """GeomLines：每两个顶点一条线段 —— 可视化法线。"""
        if self._normals_np is not None:
            self._normals_np.remove_node()
            self._normals_np = None
            return NodePath()
        src = self.wave.node().get_geom(0).get_vertex_data()
        vr, nr = GeomVertexReader(src, "vertex"), GeomVertexReader(src, "normal")
        vdata = GeomVertexData("normals", GeomVertexFormat.get_v3(), Geom.UH_static)
        vw = GeomVertexWriter(vdata, "vertex")
        lines = GeomLines(Geom.UH_static)
        i = 0
        while not vr.is_at_end():
            p, n = vr.get_data3(), nr.get_data3()
            vw.add_data3(p)
            vw.add_data3(p + n * 0.5)
            lines.add_vertices(i, i + 1)
            i += 2
        geom = Geom(vdata)
        geom.add_primitive(lines)
        node = GeomNode("normals")
        node.add_geom(geom)
        self._normals_np = self.wave.attach_new_node(node)
        self._normals_np.set_color(1, 1, 0, 1)
        return self._normals_np

    # ------------------------------------------------------------ 查询
    @staticmethod
    def vertex_count(np: NodePath) -> int:
        return np.node().get_geom(0).get_vertex_data().get_num_rows()

    def max_height(self) -> float:
        """GeomVertexReader 遍历，求当前最高 z。"""
        vr = GeomVertexReader(self.wave.node().get_geom(0).get_vertex_data(), "vertex")
        best = -1e9
        while not vr.is_at_end():
            best = max(best, vr.get_data3().z)
        return best
