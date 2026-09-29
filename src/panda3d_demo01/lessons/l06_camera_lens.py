"""L06 相机、镜头与 DisplayRegion。

渲染链路::

    GraphicsWindow/Buffer  (一块画布)
      └── DisplayRegion    (画布上的一个矩形区域，0..1 归一化坐标)
            └── Camera     (场景图里的节点，决定从哪看)
                  └── Lens (怎么投影：PerspectiveLens / OrthographicLens)

本课：
1. 主相机 PerspectiveLens：FOV、近远裁剪面，演示“滑动变焦”(dolly zoom)
2. 右上角小地图：第二个 DisplayRegion + 正交相机 + show_frustum 画出主相机视锥
3. Lens.project：3D 点 → 屏幕坐标，让 2D 标签跟随 3D 物体
4. Lens.extrude：屏幕坐标 → 3D 射线（拾取的数学基础，l10 用到）
"""

from __future__ import annotations

import math

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (
    Camera,
    GraphicsWindow,
    LPoint2,
    LPoint3,
    NodePath,
    OrthographicLens,
    PerspectiveLens,
    TextNode,
)

from ..core import Lesson, register
from ..core.procedural import make_cube, make_grid


@register
class CameraLensLesson(Lesson):
    key = "camera_lens"
    order = 6
    title = "相机、镜头与多视口"
    title_en = "Camera, Lens & DisplayRegion"
    summary = "FOV/近远面、正交镜头、多 DisplayRegion 小地图、project/extrude"
    apis = (
        "PerspectiveLens.set_fov", "Lens.set_near_far", "Lens.get_fov", "OrthographicLens.set_film_size",
        "Lens.project", "Lens.extrude", "Camera", "Camera.show_frustum", "Camera.set_lens",
        "GraphicsOutput.make_display_region", "DisplayRegion.set_camera", "DisplayRegion.set_sort",
        "DisplayRegion.set_clear_color_active", "DisplayRegion.set_clear_depth_active",
        "GraphicsOutput.remove_display_region", "base.camLens", "NodePath.get_relative_point",
        "WindowProperties", "GraphicsWindow.get_properties",
    )
    controls = ("Z 开始/停止 dolly zoom", "[ / ] 调 FOV")

    def setup(self) -> None:
        self.root.attach_new_node(make_grid(20, 1).node())
        self.target = make_cube(1.5)
        self.target.reparent_to(self.root)
        self.target.set_z(0.75)
        # 纵深方向上排一列柱子，dolly zoom 时背景“拉伸”效果更明显
        for i in range(10):
            p = make_cube(0.6, color=(0.4 + i * 0.05, 0.5, 0.9 - i * 0.05, 1))
            p.reparent_to(self.root)
            p.set_pos((-1) ** i * 3, 4 + i * 3, 1.5)
            p.set_scale(1, 1, 5)

        # 主镜头：ShowBase 的 base.camLens 就是 base.cam.node().get_lens()
        self.lens: PerspectiveLens | None = None
        if getattr(self.base, "cam", None) is not None:
            self.lens = self.base.cam.node().get_lens()
            self.orig_fov = LPoint2(self.lens.get_fov())
            self.orig_near_far = (self.lens.get_near(), self.lens.get_far())
            self.lens.set_near_far(0.5, 500)
            self.on_cleanup(self._restore_lens)
        self.place_camera((0, -16, 2), (0, 0, 1))

        self.minimap_region = None
        self.minimap_cam: NodePath | None = None
        if self.has_window:
            self._make_minimap()
            self._show_window_props()

        # 跟随 3D 物体的 2D 标签
        self.label = OnscreenText(text="target", parent=self.gui_root, scale=0.05, fg=(1, 1, 0.3, 1),
                                  align=TextNode.A_center, mayChange=True)
        self.dolly = False
        self.dolly_width = None
        self.accept("z", self.toggle_dolly)
        self.accept("[", self.change_fov, [-5])
        self.accept("]", self.change_fov, [5])
        self.add_task(self._update, "update")
        self.status("右上角是正交小地图；Z 体验希区柯克变焦")

    # ------------------------------------------------------------ 多视口
    def _make_minimap(self) -> None:
        """make_display_region(l, r, b, t)：在同一窗口上再开一个视口。"""
        dr = self.base.win.make_display_region(0.72, 0.99, 0.62, 0.97)
        # sort 大的后画。ShowBase 默认 DR：3D=0、render2d(HUD)=10、render2dp=20。
        # 取 5：盖在 3D 主画面上、但在 HUD 之下。坑：与已有 DR 同 sort（如 20）时，
        # 多重采样离屏缓冲上会出现整帧不刷新的问题 —— 务必避免重复 sort。
        dr.set_sort(5)
        dr.set_clear_color_active(True)
        dr.set_clear_color((0.05, 0.05, 0.08, 1))
        dr.set_clear_depth_active(True)
        lens = OrthographicLens()
        lens.set_film_size(40, 40 * 0.35 / 0.27)  # 按视口宽高比设置胶片尺寸
        lens.set_near_far(-100, 100)
        cam = Camera("minimap-cam", lens)
        self.minimap_cam = self.root.attach_new_node(cam)
        self.minimap_cam.set_pos(0, 10, 50)
        self.minimap_cam.set_p(-90)            # 朝下俯视
        dr.set_camera(self.minimap_cam)
        self.minimap_region = dr
        # 在主相机上显示视锥线框（小地图里能看到）
        self.base.cam.node().show_frustum()
        self.on_cleanup(self._remove_minimap)

    def _remove_minimap(self) -> None:
        if self.minimap_region is not None:
            self.base.win.remove_display_region(self.minimap_region)
            self.minimap_region = None
        self.base.cam.node().hide_frustum()

    def _show_window_props(self) -> None:
        """只有 GraphicsWindow 有 WindowProperties；离屏 GraphicsBuffer 只有尺寸。"""
        if not isinstance(self.base.win, GraphicsWindow):
            self.state["window_size"] = (self.base.win.get_x_size(), self.base.win.get_y_size())
            return
        props = self.base.win.get_properties()
        if props.has_size():
            self.state["window_size"] = (props.get_x_size(), props.get_y_size())

    def _restore_lens(self) -> None:
        if self.lens is not None:
            self.lens.set_fov(self.orig_fov)
            self.lens.set_near_far(*self.orig_near_far)

    # ------------------------------------------------------------ 数学
    def project_to_screen(self, np: NodePath) -> LPoint2 | None:
        """3D → 2D：先把点转到相机空间，再用 lens.project 得到 [-1,1] 胶片坐标。"""
        if self.lens is None:
            return None
        p_cam = self.base.cam.get_relative_point(np, LPoint3(0, 0, 0))
        p2 = LPoint2()
        return p2 if self.lens.project(p_cam, p2) else None

    def screen_ray(self, x: float, y: float) -> tuple[LPoint3, LPoint3] | None:
        """2D → 3D：extrude 得到近/远裁剪面上的两点（相机空间），再转世界坐标。"""
        if self.lens is None:
            return None
        near, far = LPoint3(), LPoint3()
        if not self.lens.extrude(LPoint2(x, y), near, far):
            return None
        r = self.base.render
        return r.get_relative_point(self.base.cam, near), r.get_relative_point(self.base.cam, far)

    def change_fov(self, delta: float) -> float:
        if self.lens is None:
            return 0.0
        fov = min(max(self.lens.get_fov()[0] + delta, 10), 120)
        self.lens.set_fov(fov)
        self.state["fov"] = round(fov, 1)
        return fov

    def toggle_dolly(self) -> None:
        """dolly zoom：保持目标画面大小不变 → 距离 d 与 FOV 满足 d·tan(fov/2) = 常数。"""
        self.dolly = not self.dolly
        if self.dolly and self.lens is not None:
            d = self.base.camera.get_distance(self.target)
            self.dolly_width = d * math.tan(math.radians(self.lens.get_fov()[0] / 2))

    def _update(self, task):
        if self.dolly and self.lens is not None and self.dolly_width:
            d = 10 + 8 * math.sin(task.time)
            fov = math.degrees(2 * math.atan(self.dolly_width / d))
            self.place_camera((0, -d, 2), (0, 0, 1))
            self.lens.set_fov(fov)
            self.state["fov"] = round(fov, 1)
        sp = self.project_to_screen(self.target)
        if sp is not None:
            # 胶片坐标 x∈[-1,1] 需乘以宽高比才是 aspect2d 坐标
            aspect = self.base.get_aspect_ratio() if self.has_window else 1.0
            # OnscreenText.setPos(x, y) 是 2D 版本（注意不是 NodePath.set_pos）
            self.label.setPos(sp.x * aspect, sp.y + 0.12)
            self.label.setText(f"target ({sp.x:+.2f},{sp.y:+.2f})")
            self.state["target_screen"] = (round(sp.x, 3), round(sp.y, 3))
        return task.cont
