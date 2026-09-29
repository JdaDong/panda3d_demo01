"""L20 线性代数与几何工具（panda3d.core 的 L* 数学库）。

约定
----
* 坐标系：**Z 向上、Y 向前、X 向右**（右手系）
* 欧拉角 HPR（度）：H 绕 Z（偏航）、P 绕 X（俯仰）、R 绕 Y（翻滚）
* ``LPoint3`` 是点（受平移影响），``LVector3`` 是向量（不受平移影响）
  —— ``mat.xform_point`` vs ``mat.xform_vec`` 的区别就在这里
* 矩阵是**行向量约定**：``v' = v * M``，组合变换从左往右读

还包括：LQuaternion（旋转插值）、TransformState（不可变变换缓存）、
BoundingSphere/BoundingBox、LPlane、Randomizer、PerlinNoise3。
"""

from __future__ import annotations

import math

from panda3d.core import (
    BoundingBox,
    BoundingSphere,
    LMatrix4,
    LPlane,
    LPoint3,
    LQuaternion,
    LVector3,
    PerlinNoise3,
    Randomizer,
    TransformState,
    look_at,
)

from ..core import Lesson, register
from ..core.procedural import make_axes, make_cube, make_grid, make_uv_sphere


def nlerp(a: LQuaternion, b: LQuaternion, t: float) -> LQuaternion:
    """归一化线性插值（slerp 的廉价近似），注意走“最短弧”：点积为负时取反。"""
    if a.dot(b) < 0:
        b = -b
    q = a * (1 - t) + b * t
    q.normalize()
    return q


def slerp(a: LQuaternion, b: LQuaternion, t: float) -> LQuaternion:
    """球面线性插值：角速度恒定。"""
    d = a.dot(b)
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        return nlerp(a, b, t)
    theta = math.acos(d)
    s = math.sin(theta)
    q = a * (math.sin((1 - t) * theta) / s) + b * (math.sin(t * theta) / s)
    q.normalize()
    return q


def compose(pos, hpr, scale) -> LMatrix4:
    """TransformState.make_pos_hpr_scale：用 (位置, 欧拉角, 缩放) 构造 4x4 矩阵。"""
    return LMatrix4(TransformState.make_pos_hpr_scale(LPoint3(*pos), LVector3(*hpr), LVector3(*scale)).get_mat())


def ray_plane(origin: LPoint3, direction: LVector3, plane: LPlane) -> LPoint3 | None:
    """LPlane.intersects_line：射线与平面求交（例如“鼠标点在地面的哪里”）。"""
    hit = LPoint3()
    return hit if plane.intersects_line(hit, origin, origin + direction) else None


@register
class MathLesson(Lesson):
    key = "math"
    order = 20
    title = "数学库"
    title_en = "Math Library"
    summary = "LVector/LPoint、叉积点积、LMatrix4、TransformState、四元数 slerp、包围体、平面、噪声、随机数"
    apis = (
        "LVector3.cross/dot/normalized/length", "LPoint3", "LMatrix4", "LMatrix4.xform_point/xform_vec",
        "LMatrix4.invert_from", "TransformState.make_pos_hpr_scale", "TransformState.compose",
        "LQuaternion.set_hpr/get_hpr", "LQuaternion.xform", "look_at()", "BoundingSphere.contains",
        "BoundingBox", "LPlane.dist_to_plane", "LPlane.intersects_line", "PerlinNoise3", "Randomizer",
        "NodePath.set_quat", "NodePath.get_mat",
    )
    controls = ()

    def setup(self) -> None:
        self.place_camera((0, -16, 9), (0, 0, 1))
        self.root.attach_new_node(make_grid(12).node())

        # 两个朝向，四元数在它们之间 slerp
        self.q_from = LQuaternion()
        self.q_from.set_hpr(LVector3(0, 0, 0))
        self.q_to = LQuaternion()
        self.q_to.set_hpr(LVector3(160, 60, 30))
        self.slerp_obj = make_cube(1.2)
        self.slerp_obj.reparent_to(self.root)
        self.slerp_obj.set_pos(-4, 0, 1.5)
        make_axes(1.2).reparent_to(self.slerp_obj)

        # 噪声驱动的一排“浮标”
        self.noise = PerlinNoise3(4, 4, 4, 256, 1)
        self.buoys = []
        for i in range(12):
            b = make_uv_sphere(0.25, color=(0.3, 0.8, 1, 1))
            b.reparent_to(self.root)
            b.set_pos(-5.5 + i, 4, 0)
            self.buoys.append(b)

        # 随机点 + 包围球：包含测试
        rnd = Randomizer(2024)
        self.sphere_bound = BoundingSphere(LPoint3(4, 0, 1.5), 1.8)
        self.inside = 0
        for _ in range(60):
            p = LPoint3(4 + rnd.random_real(5) - 2.5, rnd.random_real(5) - 2.5, 1.5 + rnd.random_real(5) - 2.5)
            dot = make_uv_sphere(0.08, 4, 6)
            dot.reparent_to(self.root)
            dot.set_pos(p)
            inside = self.sphere_bound.contains(p) != 0
            self.inside += inside
            dot.set_color((0.2, 1, 0.3, 1) if inside else (1, 0.3, 0.3, 1))

        # 用 look_at() 生成朝向目标的四元数
        self.pointer = make_cube(0.3, color=(1, 1, 0, 1))
        self.pointer.reparent_to(self.root)
        self.pointer.set_scale(0.4, 2.0, 0.4)
        self.pointer.set_pos(0, -2, 1)
        self.add_task(self._update, "update")
        self.state["inside_sphere"] = self.inside
        self.status(f"左：四元数 slerp；右：{self.inside}/60 个随机点落在包围球内")

    def _update(self, task):
        t = (math.sin(task.time) + 1) / 2
        self.slerp_obj.set_quat(slerp(self.q_from, self.q_to, t))
        for i, b in enumerate(self.buoys):
            b.set_z(1 + self.noise.noise(i * 0.3, 0, task.time * 0.5) * 1.5)
        # 黄色指针永远指向 slerp 立方体
        target = self.slerp_obj.get_pos() - self.pointer.get_pos()
        q = LQuaternion()
        look_at(q, target, LVector3.up())
        self.pointer.set_quat(q)
        return task.cont

    # ------------------------------------------------------------ 纯函数（UT）
    @staticmethod
    def vector_basics() -> dict:
        x, y = LVector3(1, 0, 0), LVector3(0, 1, 0)
        return {
            "cross": tuple(x.cross(y)),                 # 右手定则 → +Z
            "dot": x.dot(y),
            "len": LVector3(3, 4, 0).length(),
            "normalized": tuple(LVector3(0, 0, 5).normalized()),
            "angle_deg": x.angle_deg(y),
        }

    @staticmethod
    def point_vs_vector() -> tuple[LPoint3, LVector3]:
        m = compose((10, 0, 0), (90, 0, 0), (1, 1, 1))
        return m.xform_point(LPoint3(1, 0, 0)), m.xform_vec(LVector3(1, 0, 0))

    @staticmethod
    def inverse_roundtrip() -> LPoint3:
        m = compose((1, 2, 3), (30, 45, 60), (2, 2, 2))
        inv = LMatrix4()
        inv.invert_from(m)
        return inv.xform_point(m.xform_point(LPoint3(5, 6, 7)))

    @staticmethod
    def compose_transforms() -> LPoint3:
        """TransformState 组合：parent.compose(child) = 先 child 后 parent。"""
        parent = TransformState.make_pos(LVector3(0, 0, 10))
        child = TransformState.make_hpr(LVector3(90, 0, 0)).compose(TransformState.make_pos(LVector3(1, 0, 0)))
        return parent.compose(child).get_mat().xform_point(LPoint3(0, 0, 0))

    @staticmethod
    def plane_queries() -> tuple[float, LPoint3 | None]:
        ground = LPlane(LVector3(0, 0, 1), LPoint3(0, 0, 0))
        return ground.dist_to_plane(LPoint3(0, 0, 5)), ray_plane(LPoint3(0, -10, 10), LVector3(0, 1, -1), ground)

    @staticmethod
    def box_contains() -> bool:
        box = BoundingBox(LPoint3(-1, -1, -1), LPoint3(1, 1, 1))
        return box.contains(LPoint3(0.5, 0.5, 0.5)) != 0 and box.contains(LPoint3(2, 0, 0)) == 0
