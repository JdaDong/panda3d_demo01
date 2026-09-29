"""L24 ODE 物理（panda3d.ode）—— 与 Bullet 对照学习。

ODE 把“动力学”和“碰撞”拆成两套对象，比 Bullet 更底层：
* **动力学**：``OdeWorld`` + ``OdeBody``（质量 ``OdeMass``、速度、力）
* **碰撞**：``OdeSimpleSpace`` / ``OdeHashSpace`` 里放 ``OdeGeom``（Box/Sphere/Plane…）
* 二者通过 ``geom.set_body(body)`` 绑定
* 每步：``space.auto_collide()`` 生成接触点 → 写入 ``OdeJointGroup`` 作为临时接触关节
  → ``world.quick_step(dt)`` 积分 → ``joint_group.empty()`` 清空接触
* 表面参数表：``world.init_surface_table(n)`` + ``set_surface_entry``（摩擦/弹性…）
* 与场景图不自动同步：需要自己把 ``body.get_position()/get_quaternion()`` 写回 NodePath
"""

from __future__ import annotations

import random

from panda3d.core import LQuaternion, LVecBase4, LVector3, NodePath
from panda3d.ode import (
    OdeBallJoint,
    OdeBody,
    OdeBoxGeom,
    OdeJointGroup,
    OdeMass,
    OdePlaneGeom,
    OdeSimpleSpace,
    OdeSphereGeom,
    OdeWorld,
)

from ..core import Lesson, register
from ..core.procedural import make_cube, make_plane, make_uv_sphere


@register
class OdePhysicsLesson(Lesson):
    key = "ode_physics"
    order = 24
    title = "ODE 物理引擎"
    title_en = "ODE Physics"
    summary = "OdeWorld/OdeBody/OdeMass、Space+Geom 碰撞、auto_collide 接触组、表面表、球关节链"
    apis = (
        "OdeWorld", "OdeWorld.set_gravity", "OdeWorld.quick_step", "OdeWorld.init_surface_table",
        "OdeWorld.set_surface_entry", "OdeBody", "OdeMass.set_box/set_sphere", "OdeBody.set_mass",
        "OdeBody.set_position/get_position", "OdeBody.get_quaternion", "OdeBody.add_force",
        "OdeSimpleSpace", "OdeSimpleSpace.set_auto_collide_world", "OdeSimpleSpace.auto_collide",
        "OdeSimpleSpace.set_auto_collide_joint_group", "OdeBoxGeom", "OdeSphereGeom", "OdePlaneGeom",
        "OdeGeom.set_body", "OdeJointGroup.empty", "OdeBallJoint",
    )
    controls = ("SPACE 撒一把方块",)

    STEP = 1.0 / 90.0

    def setup(self) -> None:
        self.place_camera((0, -24, 12), (0, 0, 2))
        make_plane(30, color=(0.35, 0.35, 0.4, 1)).reparent_to(self.root)
        self.rng = random.Random(11)

        self.world = OdeWorld()
        self.world.set_gravity(0, 0, -9.81)
        # 表面表：1 种表面类型，(0,0) 条目 = 摩擦 150、弹性 0.3、最小反弹速度 9.1、ERP/CFM/slip/damping
        self.world.init_surface_table(1)
        self.world.set_surface_entry(0, 0, 150, 0.3, 9.1, 0.9, 0.00001, 0.0, 0.002)

        self.space = OdeSimpleSpace()
        self.contacts = OdeJointGroup()
        self.space.set_auto_collide_world(self.world)
        self.space.set_auto_collide_joint_group(self.contacts)
        # 平面方程 ax+by+cz=d → (0,0,1,0) 即 z=0；静态几何不绑定 body
        self.ground_geom = OdePlaneGeom(self.space, LVecBase4(0, 0, 1, 0))
        self.space.set_surface_type(self.ground_geom, 0)

        self.objects: list[tuple[NodePath, OdeBody]] = []
        self.geoms: list = []
        self.joints: list[OdeBallJoint] = []
        self.spawn_boxes(12)
        self._build_chain()
        self.accumulator = 0.0
        self.accept("space", self.spawn_boxes, [8])
        self.add_task(self._simulate, "simulate", sort=30)
        self.status("ODE：方块堆 + 球关节锁链")

    def teardown(self) -> None:
        self.contacts.empty()
        for joint in self.joints:
            joint.destroy()
        for geom in self.geoms:
            geom.destroy()
        for _, body in self.objects:
            body.destroy()
        self.ground_geom.destroy()
        self.space.destroy()
        self.world.destroy()

    # ------------------------------------------------------------ 构建
    def spawn_boxes(self, n: int) -> None:
        for _ in range(n):
            size = self.rng.uniform(0.5, 1.1)
            np = make_cube(size, color=(self.rng.random(), 0.6, self.rng.random(), 1))
            np.reparent_to(self.root)
            body = OdeBody(self.world)
            mass = OdeMass()
            mass.set_box(50, size, size, size)  # 密度 50
            body.set_mass(mass)
            body.set_position(self.rng.uniform(-3, 3), self.rng.uniform(-3, 3), self.rng.uniform(4, 12))
            q = LQuaternion()
            q.set_hpr(LVector3(self.rng.uniform(0, 360), self.rng.uniform(0, 360), 0))
            body.set_quaternion(q)
            geom = OdeBoxGeom(self.space, size, size, size)
            geom.set_body(body)
            self.space.set_surface_type(geom, 0)  # 对应表面表的索引 0
            self.geoms.append(geom)
            self.objects.append((np, body))
        self.state["bodies"] = len(self.objects)

    def _build_chain(self) -> None:
        """5 个球用 OdeBallJoint 串起来，第一个用球关节固定到世界（attach 到 None=世界）。"""
        prev = None
        for i in range(5):
            np = make_uv_sphere(0.3, color=(1, 0.8, 0.3, 1))
            np.reparent_to(self.root)
            body = OdeBody(self.world)
            m = OdeMass()
            m.set_sphere(20, 0.3)
            body.set_mass(m)
            body.set_position(6 + i * 0.7, 0, 8)
            geom = OdeSphereGeom(self.space, 0.3)
            geom.set_body(body)
            self.space.set_surface_type(geom, 0)
            self.geoms.append(geom)
            joint = OdeBallJoint(self.world)
            if prev is None:
                joint.attach_body(body, 0)  # 另一端是世界
                joint.set_anchor(6 - 0.35, 0, 8)
            else:
                joint.attach_bodies(prev, body)
                joint.set_anchor(6 + i * 0.7 - 0.35, 0, 8)
            self.joints.append(joint)
            self.objects.append((np, body))
            prev = body

    # ------------------------------------------------------------ 模拟
    def step_fixed(self) -> None:
        self.space.auto_collide()      # 生成接触关节
        self.world.quick_step(self.STEP)
        self.contacts.empty()          # 接触只在本步有效

    def sync(self) -> None:
        for np, body in self.objects:
            np.set_pos_quat(self.base.render, body.get_position(), LQuaternion(body.get_quaternion()))

    def _simulate(self, task):
        # 固定步长累加器：与帧率解耦
        self.accumulator += min(self.clock.get_dt(), 0.1)
        while self.accumulator >= self.STEP:
            self.step_fixed()
            self.accumulator -= self.STEP
        self.sync()
        self.state["lowest_z"] = round(min(b.get_position().z for _, b in self.objects), 2)
        return task.cont
