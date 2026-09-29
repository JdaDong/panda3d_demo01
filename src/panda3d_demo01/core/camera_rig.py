"""轨道相机：pivot(目标点) → 相机，典型的“父子变换”应用。

    render
      └── orbit-pivot   (位置 = 目标点，H/P = 水平/俯仰角)
            └── camera  (Y = -distance，永远看向 pivot)

旋转 pivot 就能让相机绕目标转——不需要任何三角函数，这就是场景图的威力。
"""

from __future__ import annotations

import math

from direct.showbase.DirectObject import DirectObject
from panda3d.core import ClockObject, KeyboardButton, LPoint3, LVector3


class OrbitCamera(DirectObject):
    SPEED_DEG = 90.0  # 每秒旋转角度
    ZOOM_STEP = 1.15

    def __init__(self, base) -> None:
        super().__init__()
        self.base = base
        self.pivot = base.render.attach_new_node("orbit-pivot")
        base.camera.reparent_to(self.pivot)
        self.distance = 20.0
        self.heading = 0.0
        self.pitch = -20.0
        self._apply()
        # 滚轮缩放（事件驱动）
        self.accept("wheel_up", self.zoom, [1 / self.ZOOM_STEP])
        self.accept("wheel_down", self.zoom, [self.ZOOM_STEP])
        # 方向键旋转（轮询驱动，按住连续旋转）
        base.task_mgr.add(self._poll, "orbit-camera", sort=-10)

    # ------------------------------------------------------------ 公共 API
    def look_from(self, pos, target=(0, 0, 0)) -> None:
        """根据“相机位置 + 目标点”反算 heading/pitch/distance。"""
        p, t = LPoint3(*pos), LPoint3(*target)
        d = p - t
        self.distance = max(d.length(), 0.01)
        # Panda3D 约定：Y 轴向前，H 绕 Z 轴逆时针，P 绕 X 轴（单位：度）
        # 相机局部偏移 (0,-dist,0) 经 H 旋转后 = (dist·sinH, -dist·cosH) → H = atan2(dx, -dy)
        # 经 P 旋转后 z = -dist·sinP → P = -asin(dz/dist)
        self.heading = math.degrees(math.atan2(d.x, -d.y)) if (d.x or d.y) else 0.0
        self.pitch = -math.degrees(math.asin(max(-1.0, min(1.0, d.z / self.distance))))
        self.pivot.set_pos(t)
        self._apply()

    def zoom(self, factor: float) -> None:
        self.distance = min(max(self.distance * factor, 1.0), 500.0)
        self._apply()

    def rotate(self, dh: float, dp: float) -> None:
        self.heading += dh
        self.pitch = min(max(self.pitch + dp, -89.0), 89.0)
        self._apply()

    def destroy(self) -> None:
        self.ignoreAll()
        self.base.task_mgr.remove("orbit-camera")

    # ------------------------------------------------------------ 内部
    def _apply(self) -> None:
        self.pivot.set_hpr(self.heading, self.pitch, 0)
        self.base.camera.set_pos(0, -self.distance, 0)
        self.base.camera.set_hpr(0, 0, 0)

    def _poll(self, task):
        mw = getattr(self.base, "mouseWatcherNode", None)
        if mw is None:
            return task.cont
        dt = ClockObject.get_global_clock().get_dt()
        is_down = mw.is_button_down
        dh = (is_down(KeyboardButton.left()) - is_down(KeyboardButton.right())) * self.SPEED_DEG * dt
        dp = (is_down(KeyboardButton.down()) - is_down(KeyboardButton.up())) * self.SPEED_DEG * dt
        if dh or dp:
            self.rotate(dh, dp)
        return task.cont

    @property
    def forward(self) -> LVector3:
        return self.base.render.get_relative_vector(self.base.camera, LVector3(0, 1, 0))
