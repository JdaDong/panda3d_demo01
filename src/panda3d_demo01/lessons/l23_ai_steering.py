"""L23 PandaAI 转向行为（panda3d.ai）。

* ``AIWorld(render)``：AI 世界，每帧 ``update()``
* ``AICharacter(name, nodepath, mass, movt_force, max_force)``：给 NodePath 装上“AI 大脑”
* ``getAiBehaviors()`` 返回 AIBehaviors，可叠加多种行为（按优先级混合）：
    seek(追) / flee(逃) / pursue(预判追) / evade(预判逃) / wander(闲逛) /
    arrival(到达减速) / flock(群聚) / obstacle_avoidance / path_follow / path_find_to(寻路)
* ``behavior_status(name)`` 查询行为状态：active / done / paused / disabled
"""

from __future__ import annotations

import math

from panda3d.ai import AICharacter, AIWorld

from ..core import Lesson, register
from ..core.procedural import make_cube, make_grid, make_uv_sphere


@register
class AiSteeringLesson(Lesson):
    key = "ai_steering"
    order = 23
    title = "PandaAI 转向行为"
    title_en = "PandaAI Steering"
    summary = "AIWorld、AICharacter、seek/flee/pursue/evade/wander/arrival 行为叠加与状态查询"
    apis = (
        "panda3d.ai.AIWorld", "AIWorld.add_ai_char", "AIWorld.remove_ai_char", "AIWorld.update",
        "AICharacter", "AICharacter.get_ai_behaviors", "AICharacter.get_velocity", "AIBehaviors.seek",
        "AIBehaviors.flee", "AIBehaviors.pursue", "AIBehaviors.evade", "AIBehaviors.wander",
        "AIBehaviors.arrival", "AIBehaviors.behavior_status", "AIBehaviors.pause_ai/resume_ai",
    )
    controls = ("SPACE 暂停/恢复猎人",)

    def setup(self) -> None:
        self.place_camera((0, -30, 26))
        self.root.attach_new_node(make_grid(30).node())
        self.world = AIWorld(self.root)

        # 目标：沿“8 字”轨道运动（手动驱动）
        self.target = make_uv_sphere(0.6, color=(1, 0.9, 0.2, 1), name="target")
        self.target.reparent_to(self.root)

        self.chars: dict[str, AICharacter] = {}
        # 猎人：预判追击目标 + 到达时减速
        self.hunter_np = self._spawn("hunter", (0.9, 0.2, 0.2, 1), (-10, -10, 0.5))
        hunter = self._ai("hunter", self.hunter_np, mass=60, force=12, max_force=15)
        hunter.get_ai_behaviors().pursue(self.target, 1.0)
        hunter.get_ai_behaviors().arrival(3)

        # 胆小鬼：见到猎人就逃（panic 距离 8，安全距离 14），同时闲逛
        self.coward_np = self._spawn("coward", (0.3, 1, 0.4, 1), (8, 8, 0.5))
        coward = self._ai("coward", self.coward_np, mass=40, force=10, max_force=12)
        coward.get_ai_behaviors().evade(self.hunter_np, 8, 14, 1.0)
        coward.get_ai_behaviors().wander(4, 0, 20, 0.5)

        # 跟随者：直接 seek 胆小鬼
        self.follower_np = self._spawn("follower", (0.4, 0.6, 1, 1), (-8, 8, 0.5))
        follower = self._ai("follower", self.follower_np, mass=50, force=8, max_force=10)
        follower.get_ai_behaviors().seek(self.coward_np, 1.0)

        self.paused = False
        self.accept("space", self.toggle_hunter)
        self.add_task(self._update, "ai-update")
        self.status("红=pursue 黄球；绿=evade 红+wander；蓝=seek 绿")

    def teardown(self) -> None:
        for name in list(self.chars):
            self.world.remove_ai_char(name)
        self.chars.clear()

    def _spawn(self, name: str, color, pos):
        np = make_cube(1.0, color=color, name=name)
        np.reparent_to(self.root)
        np.set_pos(*pos)
        return np

    def _ai(self, name: str, np, mass: float, force: float, max_force: float) -> AICharacter:
        char = AICharacter(name, np, mass, force, max_force)
        self.world.add_ai_char(char)
        self.chars[name] = char
        return char

    def toggle_hunter(self) -> bool:
        beh = self.chars["hunter"].get_ai_behaviors()
        self.paused = not self.paused
        if self.paused:
            beh.pause_ai("pursue")
        else:
            beh.resume_ai("pursue")
        return self.paused

    def step(self, t: float) -> None:
        self.target.set_pos(10 * math.sin(t * 0.6), 6 * math.sin(t * 1.2), 0.6)
        self.world.update()  # 所有 AICharacter 前进一步（内部使用全局时钟 dt）
        self.state["hunter_to_target"] = round((self.hunter_np.get_pos() - self.target.get_pos()).length(), 2)
        self.state["pursue_status"] = self.chars["hunter"].get_ai_behaviors().behavior_status("pursue")

    def _update(self, task):
        self.step(task.time)
        return task.cont
