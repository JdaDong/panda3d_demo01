"""L15 渲染状态（RenderAttrib）与特效节点。

Panda3D 渲染状态 = 一组不可变的 RenderAttrib（RenderState 是它们的集合）。
``NodePath.set_xxx()`` 本质上都是 ``set_attrib(XxxAttrib.make(...), priority)``，
子节点继承父节点状态，``priority`` 高的覆盖低的。

本课覆盖：
* Fog（线性 / 指数）
* 透明：TransparencyAttrib + set_bin + set_depth_write
* 混合：ColorBlendAttrib（加法混合做“发光”）
* 线框/双面/剔除：RenderModeAttrib / CullFaceAttrib
* 深度偏移：DepthOffsetAttrib（贴花防 Z-fighting）
* 裁剪平面：PlaneNode + set_clip_plane
* RenderEffect：Billboard（面向相机）、Compass（锁定朝向）
* LODNode：按距离切换细节层级
* AntialiasAttrib：多重采样抗锯齿
"""

from __future__ import annotations

import math

from panda3d.core import (
    AntialiasAttrib,
    ColorBlendAttrib,
    CompassEffect,
    CullFaceAttrib,
    Fog,
    LODNode,
    LPoint3,
    LVector3,
    NodePath,
    Plane,
    PlaneNode,
    RenderModeAttrib,
    TransparencyAttrib,
)

from ..core import Lesson, register
from ..core.procedural import make_cube, make_plane, make_uv_sphere


@register
class RenderStatesLesson(Lesson):
    key = "render_states"
    order = 15
    title = "渲染状态与特效"
    title_en = "Render States & Effects"
    summary = "Fog、透明/排序 bin、加法混合、线框、双面、深度偏移、裁剪平面、Billboard/Compass、LOD"
    apis = (
        "Fog", "Fog.set_exp_density", "Fog.set_linear_range", "NodePath.set_fog", "TransparencyAttrib",
        "NodePath.set_transparency", "NodePath.set_alpha_scale", "NodePath.set_bin", "NodePath.set_depth_write",
        "NodePath.set_depth_test", "ColorBlendAttrib", "NodePath.set_attrib", "RenderModeAttrib",
        "NodePath.set_render_mode_wireframe", "NodePath.set_render_mode_filled_wireframe",
        "NodePath.set_two_sided", "CullFaceAttrib", "NodePath.set_depth_offset", "PlaneNode",
        "NodePath.set_clip_plane", "NodePath.set_billboard_point_eye", "CompassEffect", "LODNode",
        "LODNode.add_switch", "AntialiasAttrib", "NodePath.get_attrib", "NodePath.get_net_state",
    )
    controls = ("F 切换雾(off/linear/exp)", "W 线框", "C 裁剪平面", "D 拉远/拉近看 LOD")

    def setup(self) -> None:
        self.place_camera((0, -24, 8), (0, 0, 2))
        ground = make_plane(60, color=(0.4, 0.45, 0.4, 1))
        ground.reparent_to(self.root)
        # 远处一排柱子 → 雾效最明显
        for i in range(12):
            p = make_cube(1, color=(0.8, 0.6, 0.4, 1))
            p.reparent_to(self.root)
            p.set_pos(-11 + i * 2, 8 + i * 3, 1.5)
            p.set_scale(1, 1, 3)

        # --- 透明：alpha 混合物体需要从后往前画 → 放进 "transparent" bin（自动排序）
        self.glass = make_cube(2, color=(0.5, 0.8, 1, 1))
        self.glass.reparent_to(self.root)
        self.glass.set_pos(-6, 0, 1)
        self.glass.set_transparency(TransparencyAttrib.M_alpha)
        self.glass.set_alpha_scale(0.35)
        self.glass.set_bin("transparent", 10)
        self.glass.set_depth_write(False)
        self.glass.set_two_sided(True)

        # --- 加法混合：颜色 = 源 × alpha + 目标 × 1 → 越叠越亮
        self.glow = make_uv_sphere(1.0, color=(1, 0.5, 0.1, 1))
        self.glow.reparent_to(self.root)
        self.glow.set_pos(-2, 0, 1.2)
        self.glow.set_attrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add,
                                                   ColorBlendAttrib.O_incoming_alpha, ColorBlendAttrib.O_one))
        self.glow.set_depth_write(False)
        self.glow.set_bin("fixed", 20)

        # --- 线框 + 填充线框
        self.wire = make_uv_sphere(1.0, 12, 16, color=(0.3, 1, 0.5, 1))
        self.wire.reparent_to(self.root)
        self.wire.set_pos(2, 0, 1.2)
        self.wire.set_render_mode_filled_wireframe((0, 0, 0, 1))

        # --- 反向剔除：只画背面 → 看到“内壁”
        self.inside = make_cube(2, name="inside-out")
        self.inside.reparent_to(self.root)
        self.inside.set_pos(6, 0, 1)
        self.inside.set_attrib(CullFaceAttrib.make_reverse())

        # --- 贴花：与地面共面，用 depth offset 抬高一点避免闪烁
        decal = make_plane(3, color=(1, 1, 0.2, 1), name="decal")
        decal.reparent_to(self.root)
        decal.set_pos(0, -4, 0)
        decal.set_depth_offset(1)

        # --- Billboard：永远正对相机的“树”
        self.bill = make_plane(2, color=(0.3, 0.8, 0.3, 1), name="billboard")
        self.bill.reparent_to(self.root)
        self.bill.set_pos(0, 3, 2)
        self.bill.set_p(90)  # XY 平面转成竖直
        holder = self.root.attach_new_node("billboard-holder")
        holder.set_pos(0, 3, 2)
        self.bill.reparent_to(holder)
        self.bill.set_pos(0, 0, 0)
        holder.set_billboard_point_eye()
        self.billboard_holder = holder

        # --- Compass：旋转父节点时，子节点保持相对 render 的朝向（例如小地图指北针）
        self.spinner = self.root.attach_new_node("spinner")
        self.spinner.set_pos(0, 0, 4.5)
        arm = make_cube(0.4, color=(0.9, 0.3, 0.9, 1))
        arm.reparent_to(self.spinner)
        arm.set_x(2)
        self.compass_child = make_cube(0.4, color=(0.3, 0.9, 0.9, 1))
        self.compass_child.reparent_to(arm)
        self.compass_child.set_z(0.6)
        self.compass_child.set_effect(CompassEffect.make(self.base.render, CompassEffect.P_rot))

        # --- LOD：近处高模，远处低模（add_switch(远, 近)）
        lod = LODNode("lod-ball")
        self.lod_np = self.root.attach_new_node(lod)
        self.lod_np.set_pos(10, 6, 1.5)
        for (rings, segs, color), (far, near) in zip(
            [(24, 32, (1, 0.3, 0.3, 1)), (8, 12, (1, 1, 0.3, 1)), (3, 4, (0.3, 0.3, 1, 1))],
            [(15, 0), (35, 15), (200, 35)],
        ):
            lod.add_switch(far, near)
            make_uv_sphere(1.4, rings, segs, color=color).reparent_to(self.lod_np)

        # --- 裁剪平面
        self.clip_np = self.root.attach_new_node(PlaneNode("clip", Plane(LVector3(0, 0, -1), LPoint3(0, 0, 1.4))))
        self.clip_on = False

        self.root.set_antialias(AntialiasAttrib.M_multisample)
        self.fog = Fog("scene-fog")
        self.fog.set_color(0.12, 0.13, 0.16)
        self.fog_modes = ["off", "linear", "exp"]
        self.fog_idx = 0
        self.far = False

        self.accept("f", self.cycle_fog)
        self.accept("w", self.toggle_wireframe)
        self.accept("c", self.toggle_clip)
        self.accept("d", self.toggle_distance)
        self.add_task(self._spin, "spin")
        self.status("F 雾 / W 线框 / C 裁剪 / D 远近切换 LOD")

    # ------------------------------------------------------------ 行为
    def cycle_fog(self) -> str:
        self.fog_idx = (self.fog_idx + 1) % 3
        mode = self.fog_modes[self.fog_idx]
        if mode == "off":
            self.root.clear_fog()
        elif mode == "linear":
            self.fog.set_linear_range(10, 60)   # 10 以内无雾，60 处完全被雾吞没
            self.root.set_fog(self.fog)
        else:
            self.fog.set_exp_density(0.04)      # 指数雾：f = e^(-density·d)
            self.root.set_fog(self.fog)
        self.state["fog"] = mode
        return mode

    def toggle_wireframe(self) -> bool:
        attrib = self.root.get_attrib(RenderModeAttrib)
        on = attrib is None or attrib.get_mode() != RenderModeAttrib.M_wireframe
        if on:
            self.root.set_render_mode_wireframe()
        else:
            self.root.clear_render_mode()
        self.state["wireframe"] = on
        return on

    def toggle_clip(self) -> bool:
        self.clip_on = not self.clip_on
        if self.clip_on:
            self.root.set_clip_plane(self.clip_np)
        else:
            self.root.clear_clip_plane()
        self.state["clip"] = self.clip_on
        return self.clip_on

    def toggle_distance(self) -> None:
        self.far = not self.far
        self.place_camera((0, -60, 14) if self.far else (0, -24, 8), (0, 0, 2))

    def lod_level_for(self, distance: float) -> int:
        """查询 LODNode：给定距离会选中第几个子节点。"""
        lod: LODNode = self.lod_np.node()
        for i in range(lod.get_num_switches()):
            if lod.get_out(i) <= distance < lod.get_in(i):
                return i
        return -1

    def net_transparency(self, np: NodePath) -> int:
        """get_net_state：从根到该节点累积后的最终状态。"""
        attrib = np.get_net_state().get_attrib(TransparencyAttrib)
        return -1 if attrib is None else attrib.get_mode()

    def _spin(self, task):
        self.spinner.set_h(task.time * 60)
        self.glow.set_scale(1 + 0.15 * math.sin(task.time * 4))
        return task.cont
