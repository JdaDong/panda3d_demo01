"""L17 Actor 骨骼动画。

``Actor`` = 带骨架（Character/PartBundle）的模型 + 若干动画（AnimBundle）。
* ``Actor(model, {"名字": 动画文件})``
* 播放：``loop / play / stop / pose(name, frame)``；速率：``setPlayRate``
* 混合：``enableBlend()`` + ``setControlEffect(anim, weight)`` 多动画按权重叠加
* 骨骼：
    - ``exposeJoint(None, "modelRoot", joint)``  拿到一个“跟随骨骼”的 NodePath（挂武器/帽子）
    - ``controlJoint(None, "modelRoot", joint)`` 接管骨骼，由代码驱动（程序化看向/IK）
* ``actorInterval``：把动画片段变成 Interval，可放进 Sequence

模型用 panda3d 自带的 ``models/panda-model`` + ``models/panda-walk4``。
"""

from __future__ import annotations

import math

from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Func, Sequence
from panda3d.core import AmbientLight, DirectionalLight, LMatrix4, LVector3, NodePath

from ..core import Lesson, register
from ..core.procedural import make_cube, make_grid

HEAD_JOINT = "Bone_neck"
HAND_JOINT = "Bone_rf_foot_nub"


@register
class ActorAnimationLesson(Lesson):
    key = "actor_animation"
    order = 17
    title = "Actor 骨骼动画"
    title_en = "Actor & Skeletal Animation"
    summary = "loop/play/pose、PlayRate、AnimControl、exposeJoint 挂件、controlJoint 程序化骨骼、动画混合、actorInterval"
    apis = (
        "Actor", "Actor.loop", "Actor.play", "Actor.stop", "Actor.pose", "Actor.setPlayRate",
        "Actor.getNumFrames", "Actor.getCurrentFrame", "Actor.getAnimNames", "Actor.getAnimControl",
        "AnimControl.isPlaying", "Actor.getJoints", "Actor.exposeJoint", "Actor.controlJoint",
        "Actor.releaseJoint", "Actor.enableBlend", "Actor.setControlEffect", "Actor.actorInterval",
        "Actor.cleanup", "LMatrix4.rotate_mat (驱动 controlJoint)",
    )
    controls = ("SPACE 走/停", "+/- 速度", "B 调整混合权重", "H 头部程序控制开/关", "I 播放 actorInterval 序列")

    def setup(self) -> None:
        self.place_camera((0, -22, 9), (0, 0, 3))
        self.root.attach_new_node(make_grid(16).node())
        amb = self.root.attach_new_node(AmbientLight("amb"))
        amb.node().set_color((0.4, 0.4, 0.45, 1))
        sun = self.root.attach_new_node(DirectionalLight("sun"))
        sun.set_hpr(20, -40, 0)
        self.root.set_light(amb)
        self.root.set_light(sun)

        # --- 主角：正常播放 + 挂件
        self.panda = Actor("models/panda-model", {"walk": "models/panda-walk4"})
        self.panda.reparent_to(self.root)
        self.panda.set_scale(0.005)  # 原模型单位很大
        self.panda.set_pos(-4, 0, 0)
        self.panda.loop("walk")
        self.play_rate = 1.0
        self.hat = self.panda.exposeJoint(None, "modelRoot", HAND_JOINT)
        cube = make_cube(120, color=(1, 0.8, 0.2, 1))  # Actor 缩放 0.005 → 120 ≈ 0.6 世界单位
        cube.reparent_to(self.hat)

        # --- 第二只：controlJoint 让头部左右摆
        self.panda2 = Actor("models/panda-model", {"walk": "models/panda-walk4"})
        self.panda2.reparent_to(self.root)
        self.panda2.set_scale(0.005)
        self.panda2.set_pos(4, 0, 0)
        self.panda2.set_h(180)
        self.head: NodePath | None = self.panda2.controlJoint(None, "modelRoot", HEAD_JOINT)
        # 坑：骨骼的默认矩阵常含镜像(负缩放)/剪切，无法分解成 pos/hpr/scale。
        # 直接 head.set_h() 会先分解再重组 → 得到奇异矩阵（“Tried to invert singular LMatrix4”）。
        # 正确做法：保存原始矩阵，每帧用“旋转矩阵 × 原矩阵”组合。
        self.head_rest = LMatrix4(self.head.get_mat())
        self.head_controlled = True

        # 混合：walk 与 “第 0 帧静止姿势” 按权重叠加
        self.panda2.enableBlend()
        self.panda2.setControlEffect("walk", 1.0)
        self.panda2.loop("walk")
        self.blend = 1.0

        # actorInterval：播放 0~30 帧后回调，再播 30~60 帧
        self.cycles = 0
        self.seq = self.track(Sequence(
            self.panda2.actorInterval("walk", startFrame=0, endFrame=30),
            Func(self._on_half),
            self.panda2.actorInterval("walk", startFrame=30, endFrame=60, playRate=2.0),
            name="panda2-seq",
        ))

        self.accept("space", self.toggle_walk)
        self.accept("+", self.change_rate, [0.25])
        self.accept("=", self.change_rate, [0.25])
        self.accept("-", self.change_rate, [-0.25])
        self.accept("b", self.toggle_blend)
        self.accept("h", self.toggle_head)
        self.accept("i", self.seq.start)  # 播放 actorInterval 序列
        self.add_task(self._update, "update")
        self.state["joints"] = len(self.panda.getJoints())
        self.status(f"骨骼数 {self.state['joints']}；左：exposeJoint 挂件；右：controlJoint 摆头")

    def teardown(self) -> None:
        # Actor 持有 C++ Character 资源，必须 cleanup，否则动画控制器泄漏
        for a in (self.panda, self.panda2):
            a.cleanup()
            a.remove_node()

    # ------------------------------------------------------------ 行为
    def toggle_walk(self) -> bool:
        ctrl = self.panda.getAnimControl("walk")
        if ctrl.isPlaying():
            self.panda.stop("walk")
        else:
            self.panda.loop("walk", restart=False)
        playing = self.panda.getAnimControl("walk").isPlaying()
        self.state["walking"] = playing
        return playing

    def change_rate(self, delta: float) -> float:
        self.play_rate = max(-2.0, min(4.0, self.play_rate + delta))
        self.panda.setPlayRate(self.play_rate, "walk")  # 负值 = 倒放
        self.state["rate"] = self.play_rate
        return self.play_rate

    def toggle_blend(self) -> float:
        self.blend = 0.2 if self.blend > 0.5 else 1.0
        self.panda2.setControlEffect("walk", self.blend)
        self.state["blend"] = self.blend
        return self.blend

    def toggle_head(self) -> bool:
        if self.head_controlled:
            self.panda2.releaseJoint("modelRoot", HEAD_JOINT)  # 交还给动画
            self.head = None
        else:
            self.head = self.panda2.controlJoint(None, "modelRoot", HEAD_JOINT)
            self.head_rest = LMatrix4(self.head.get_mat())
        self.head_controlled = not self.head_controlled
        return self.head_controlled

    def pose_at(self, frame: int) -> int:
        """pose：停在某一帧（常用于“定格”或 UI 预览）。"""
        self.panda.pose("walk", frame)
        return self.panda.getCurrentFrame("walk")

    def _on_half(self) -> None:
        self.cycles += 1
        self.state["seq_half"] = self.cycles

    def _update(self, task):
        if self.head is not None:
            self.head_angle = math.sin(task.time * 2) * 40
            self.head.set_mat(LMatrix4.rotate_mat(self.head_angle, LVector3(0, 0, 1)) * self.head_rest)
        self.state["frame"] = self.panda.getCurrentFrame("walk")
        # exposeJoint 返回的节点每帧自动同步骨骼世界位置
        p = self.hat.get_pos(self.base.render)
        self.state["hand_z"] = round(p.z, 2)
        return task.cont
