"""L11 Bullet 物理引擎（panda3d.bullet）。

与 L10 碰撞系统的区别：L10 只回答“碰没碰到”，Bullet 还负责“碰到之后怎么动”
（质量、速度、摩擦、弹性、约束、休眠……）。

用法三板斧
----------
1. ``BulletWorld``：物理世界，设重力，每帧 ``do_physics(dt, max_substeps, fixed_step)``
2. ``BulletRigidBodyNode``：刚体节点（也是场景图节点！）+ ``add_shape(shape)``
   → Bullet 每步把模拟结果写回这个节点的变换，挂在它下面的模型自动跟着动
3. ``world.attach(node)``：加入模拟

mass = 0 表示静态物体（地面/墙）。
"""

from __future__ import annotations

from panda3d.bullet import (
    BulletBoxShape,
    BulletCapsuleShape,
    BulletDebugNode,
    BulletHingeConstraint,
    BulletPlaneShape,
    BulletRigidBodyNode,
    BulletSphereShape,
    BulletWorld,
    ZUp,
)
from panda3d.core import LPoint3, LVector3, NodePath

from ..core import Lesson, register
from ..core.procedural import make_cube, make_plane, make_uv_sphere


@register
class BulletPhysicsLesson(Lesson):
    key = "bullet_physics"
    order = 11
    title = "Bullet 刚体物理"
    title_en = "Bullet Physics"
    summary = "BulletWorld、刚体/形状、冲量、铰链约束、射线查询、接触测试、调试线框"
    apis = (
        "BulletWorld", "BulletWorld.set_gravity", "BulletWorld.do_physics", "BulletWorld.attach",
        "BulletWorld.remove", "BulletWorld.ray_test_closest", "BulletWorld.contact_test",
        "BulletWorld.set_debug_node", "BulletRigidBodyNode", "BulletRigidBodyNode.set_mass",
        "BulletRigidBodyNode.apply_central_impulse", "BulletRigidBodyNode.set_linear_velocity",
        "BulletBoxShape", "BulletSphereShape", "BulletPlaneShape", "BulletCapsuleShape",
        "BulletHingeConstraint", "BulletDebugNode", "set_friction/set_restitution",
    )
    controls = ("SPACE 发射炮弹", "B 显示/隐藏调试线框", "K 重建方块塔")

    def setup(self) -> None:
        self.place_camera((0, -26, 12), (0, 0, 3))
        self.world = BulletWorld()
        self.world.set_gravity(LVector3(0, 0, -9.81))

        # 调试渲染：把碰撞形状画成线框
        dbg = BulletDebugNode("bullet-debug")
        dbg.show_wireframe(True)
        dbg.show_constraints(True)
        dbg.show_bounding_boxes(False)
        self.debug_np = self.root.attach_new_node(dbg)
        self.debug_np.hide()
        self.world.set_debug_node(dbg)

        # 地面：静态刚体 + 无限平面形状
        ground = BulletRigidBodyNode("ground")
        ground.add_shape(BulletPlaneShape(LVector3(0, 0, 1), 0))
        ground.set_friction(0.8)
        self.ground_np = self.root.attach_new_node(ground)
        make_plane(40, color=(0.45, 0.45, 0.5, 1)).reparent_to(self.ground_np)
        self.world.attach(ground)

        self.bodies: list[NodePath] = []
        self.build_tower()
        self._build_pendulum()

        self.accept("space", self.fire)
        self.accept("b", self.toggle_debug)
        self.accept("k", self.build_tower)
        self.add_task(self._simulate, "simulate", sort=30)
        self.status("SPACE 开炮；B 看碰撞形状")

    def teardown(self) -> None:
        # 先移除约束再移除刚体，BulletWorld 随 Python 引用释放
        for c in list(self.world.get_constraints()):
            self.world.remove(c)
        for body in list(self.world.get_rigid_bodies()):
            self.world.remove(body)

    # ------------------------------------------------------------ 构建
    def make_box(self, pos, half=0.5, mass=1.0, color=None) -> NodePath:
        node = BulletRigidBodyNode("box")
        node.set_mass(mass)
        node.add_shape(BulletBoxShape(LVector3(half, half, half)))
        node.set_friction(0.7)
        node.set_restitution(0.1)
        np = self.root.attach_new_node(node)
        np.set_pos(*pos)
        make_cube(half * 2, color=color).reparent_to(np)  # 视觉模型挂在刚体下
        self.world.attach(node)
        self.bodies.append(np)
        return np

    def build_tower(self) -> None:
        for np in self.bodies:
            self.world.remove(np.node())
            np.remove_node()
        self.bodies.clear()
        for level in range(6):
            for i in range(3):
                off = (i - 1) * 1.02
                pos = (off, 4, 0.5 + level * 1.0) if level % 2 == 0 else (0, 4 + off, 0.5 + level * 1.0)
                self.make_box(pos, color=(0.9 - level * 0.1, 0.5, 0.3 + level * 0.1, 1))
        self.shots = 0
        self.state["bodies"] = len(self.bodies)

    def _build_pendulum(self) -> None:
        """铰链约束：把一个胶囊体挂在静态锚点上，形成钟摆。"""
        anchor = BulletRigidBodyNode("anchor")  # mass=0 → 静态
        anchor.add_shape(BulletSphereShape(0.2))
        anchor_np = self.root.attach_new_node(anchor)
        anchor_np.set_pos(-6, 4, 8)
        self.world.attach(anchor)

        bob = BulletRigidBodyNode("bob")
        bob.set_mass(2.0)
        bob.add_shape(BulletCapsuleShape(0.4, 3.0, ZUp))
        self.bob_np = self.root.attach_new_node(bob)
        self.bob_np.set_pos(-6, 4, 6)
        vis = make_uv_sphere(0.5, color=(0.4, 1, 0.6, 1))
        vis.reparent_to(self.bob_np)
        vis.set_z(-1.5)
        self.world.attach(bob)
        # 轴在各自局部坐标里：锚点中心、摆锤顶端(z=+2)，绕 Y 轴旋转
        hinge = BulletHingeConstraint(anchor, bob, LPoint3(0, 0, 0), LPoint3(0, 0, 2), LVector3(0, 1, 0), LVector3(0, 1, 0), True)
        self.world.attach(hinge)
        bob.apply_central_impulse(LVector3(6, 0, 0))

    # ------------------------------------------------------------ 交互
    def fire(self) -> NodePath:
        node = BulletRigidBodyNode(f"shot-{self.shots}")
        node.set_mass(3.0)
        node.add_shape(BulletSphereShape(0.4))
        node.set_restitution(0.5)
        np = self.root.attach_new_node(node)
        np.set_pos(0, -12, 3)
        make_uv_sphere(0.4, color=(1, 1, 0.3, 1)).reparent_to(np)
        self.world.attach(node)
        node.apply_central_impulse(LVector3(0, 60, 6))  # 冲量 = 质量 × 速度变化
        self.bodies.append(np)
        self.shots += 1
        self.state["shots"] = self.shots
        return np

    def toggle_debug(self) -> None:
        self.debug_np.hide() if not self.debug_np.is_hidden() else self.debug_np.show()

    def step(self, dt: float) -> None:
        # 固定步长 1/120，最多补 10 个子步：帧率抖动时模拟依然稳定
        self.world.do_physics(dt, 10, 1.0 / 120.0)
        hit = self.world.ray_test_closest(LPoint3(0, 4, 20), LPoint3(0, 4, -1))
        if hit.has_hit():
            self.state["tower_top_z"] = round(hit.get_hit_pos().z, 2)
            self.state["ray_hit"] = hit.get_node().get_name()
        self.state["ground_contacts"] = self.world.contact_test(self.ground_np.node()).get_num_contacts()

    def _simulate(self, task):
        self.step(self.clock.get_dt())
        return task.cont
