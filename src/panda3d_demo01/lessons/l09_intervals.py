"""L09 Interval —— 声明式动画 / 时间轴。

Interval 是“有时长、可随意 seek 的动作”。组合子：
* ``Sequence(a, b, c)``   串行
* ``Parallel(a, b)``      并行（时长 = 最长的那个）
* ``Wait(t)``             空等
* ``Func(fn, *args)``     瞬时回调
* ``LerpFunc(fn, fromData, toData, duration)``  对任意数值插值（驱动非 NodePath 属性）

常用 Lerp：Pos / Hpr / Quat / Scale / Color / ColorScale / PosHprScale
``blendType``：``noBlend`` / ``easeIn`` / ``easeOut`` / ``easeInOut``
控制：``start() loop() pause() resume() finish() setT(t) getDuration()``（Interval 是 Python 类，只有 camelCase）
便捷方法：``np.posInterval(...)`` 等价于 ``LerpPosInterval(np, ...)``
"""

from __future__ import annotations

from direct.interval.IntervalGlobal import (
    Func,
    LerpColorScaleInterval,
    LerpFunc,
    LerpHprInterval,
    LerpPosInterval,
    LerpScaleInterval,
    Parallel,
    ProjectileInterval,
    Sequence,
    Wait,
)
from panda3d.core import LPoint3

from ..core import Lesson, register
from ..core.procedural import make_cube, make_grid, make_uv_sphere


@register
class IntervalLesson(Lesson):
    key = "intervals"
    order = 9
    title = "Interval 动画时间轴"
    title_en = "Intervals"
    summary = "Lerp*Interval、Sequence/Parallel/Wait/Func、LerpFunc、ProjectileInterval、blendType、seek"
    apis = (
        "LerpPosInterval", "LerpHprInterval", "LerpScaleInterval", "LerpColorScaleInterval",
        "LerpFunc", "ProjectileInterval", "Sequence", "Parallel", "Wait", "Func",
        "NodePath.posInterval", "NodePath.hprInterval", "Interval.loop/start/pause/resume/finish",
        "Interval.setT/getT", "Interval.getDuration", "Interval.isPlaying", "blendType",
    )
    controls = ("SPACE 暂停/继续", "K 从头播放", "G 跳到 50% (set_t)")

    def setup(self) -> None:
        self.place_camera((0, -22, 10), (0, 0, 2))
        self.root.attach_new_node(make_grid(16).node())
        self.log: list[str] = []

        # --- 方块：沿正方形路径走，每条边带不同缓动
        self.cube = make_cube(1)
        self.cube.reparent_to(self.root)
        corners = [LPoint3(-5, -5, 0.5), LPoint3(5, -5, 0.5), LPoint3(5, 5, 0.5), LPoint3(-5, 5, 0.5)]
        blends = ["noBlend", "easeIn", "easeOut", "easeInOut"]
        legs = []
        for i, (b, c) in enumerate(zip(blends, corners[1:] + corners[:1])):
            legs.append(Parallel(
                LerpPosInterval(self.cube, 1.0, c, startPos=corners[i], blendType=b),
                LerpHprInterval(self.cube, 1.0, (90 * (i + 1), 0, 0), startHpr=(90 * i, 0, 0)),
            ))
            legs.append(Func(self._note, f"corner-{i}"))
        self.square = self.track(Sequence(*legs, name="square-walk"))

        # --- 球：缩放脉冲 + 颜色渐变
        self.ball = make_uv_sphere(0.8)
        self.ball.reparent_to(self.root)
        self.ball.set_z(3)
        self.pulse = self.track(Sequence(
            LerpScaleInterval(self.ball, 0.6, 1.6, startScale=1.0, blendType="easeOut"),
            LerpScaleInterval(self.ball, 0.6, 1.0, blendType="easeIn"),
            LerpColorScaleInterval(self.ball, 0.5, (1, 0.3, 0.3, 1)),
            Wait(0.3),
            LerpColorScaleInterval(self.ball, 0.5, (1, 1, 1, 1)),
            name="pulse",
        ))

        # --- 抛物线：ProjectileInterval（给起点、终点、时长 → 按重力自动算初速度与轨迹）
        self.projectile = make_uv_sphere(0.3, color=(1, 0.8, 0.2, 1))
        self.projectile.reparent_to(self.root)
        self.throw = self.track(Sequence(
            ProjectileInterval(self.projectile, startPos=LPoint3(-6, 6, 0.3), endPos=LPoint3(6, 6, 0.3), duration=1.6),
            Wait(0.4),
            name="throw",
        ))

        # --- LerpFunc：驱动任意值（这里驱动 HUD 数字 & 背景亮度）
        self.progress = 0.0
        self.counter = self.track(LerpFunc(self._set_progress, fromData=0, toData=100, duration=4.0, name="counter"))

        # --- 便捷写法：NodePath.hprInterval
        self.spinner = make_cube(0.8, color=(0.6, 0.9, 0.5, 1))
        self.spinner.reparent_to(self.root)
        self.spinner.set_pos(0, 0, 0.4)
        self.spin = self.track(self.spinner.hprInterval(2.0, (360, 0, 0), startHpr=(0, 0, 0)))

        self.all = [self.square, self.pulse, self.throw, self.counter, self.spin]
        for iv in self.all:
            iv.loop()
        self.paused = False
        self.accept("space", self.toggle_pause)
        self.accept("k", self.restart)
        self.accept("g", self.seek, [0.5])
        self.status(f"square-walk 时长 {self.square.getDuration():.1f}s")

    def _note(self, tag: str) -> None:
        self.log = (self.log + [tag])[-6:]
        self.state["last_func"] = tag

    def _set_progress(self, v: float) -> None:
        self.progress = v
        self.state["progress"] = int(v)

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        for iv in self.all:
            iv.pause() if self.paused else iv.resume()

    def restart(self) -> None:
        for iv in self.all:
            iv.loop()  # loop() 会从 t=0 重新开始
        self.paused = False

    def seek(self, fraction: float) -> None:
        """setT：把时间轴拨到某一时刻（NodePath 状态立即更新）。"""
        for iv in self.all:
            iv.setT(iv.getDuration() * fraction)
        self.state["seek"] = fraction
