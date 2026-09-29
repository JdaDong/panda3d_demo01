"""L10 碰撞系统（非物理引擎的“几何查询”）。

角色划分
--------
* **from 物体**：主动去撞的（加入 traverser 的 CollisionNode）
* **into 物体**：被撞的（场景里所有 CollisionNode 默认都可被撞）
* **CollisionTraverser**：遍历一次 = 所有 from × into 做相交测试
* **Handler**：决定碰撞结果怎么处理
    - CollisionHandlerQueue   把结果存成列表（拾取/射线检测）
    - CollisionHandlerPusher  自动把 from 物体推出墙（角色碰墙）
    - CollisionHandlerEvent   抛事件 ``%fn-into-%in``（触发器/拾取金币）
    - CollisionHandlerFloor   贴地（高度跟随）
* **BitMask32**：from_collide_mask & into_collide_mask ≠ 0 才测试 —— 碰撞分层

固体（CollisionSolid）：Sphere / Box / Plane / Ray / Segment / Capsule / Polygon …
"""

from __future__ import annotations

import math
import random

from panda3d.core import (
    BitMask32,
    CollisionBox,
    CollisionCapsule,
    CollisionHandlerEvent,
    CollisionHandlerFloor,
    CollisionHandlerPusher,
    CollisionHandlerQueue,
    CollisionNode,
    CollisionPlane,
    CollisionRay,
    CollisionSegment,
    CollisionSphere,
    CollisionTraverser,
    LPoint3,
    LVector3,
    NodePath,
    Plane,
)

from ..core import Lesson, register
from ..core.procedural import make_cube, make_plane, make_uv_sphere

WALL_MASK = BitMask32.bit(1)
COIN_MASK = BitMask32.bit(2)
PICK_MASK = BitMask32.bit(3)
FLOOR_MASK = BitMask32.bit(4)


@register
class CollisionLesson(Lesson):
    key = "collision"
    order = 10
    title = "碰撞检测"
    title_en = "Collision System"
    summary = "Traverser + Queue/Pusher/Event/Floor 四种 Handler、BitMask 分层、鼠标射线拾取"
    apis = (
        "CollisionTraverser", "CollisionTraverser.traverse", "CollisionTraverser.show_collisions",
        "CollisionHandlerQueue", "CollisionHandlerQueue.sort_entries", "CollisionHandlerPusher",
        "CollisionHandlerEvent.add_in_pattern", "CollisionHandlerFloor", "CollisionNode",
        "CollisionSphere", "CollisionBox", "CollisionPlane", "CollisionRay.set_from_lens",
        "CollisionSegment", "CollisionCapsule", "CollisionEntry.get_surface_point",
        "CollisionEntry.get_into_node_path", "BitMask32", "CollisionNode.set_from_collide_mask",
        "CollisionNode.set_into_collide_mask",
    )
    controls = ("鼠标左键 拾取方块（变红）", "V 显示/隐藏碰撞体")

    ARENA = 8.0

    def setup(self) -> None:
        self.place_camera((0, -20, 18))
        self.trav = CollisionTraverser("lesson-trav")
        rng = random.Random(7)

        ground = make_plane(self.ARENA * 2, color=(0.35, 0.4, 0.35, 1))
        ground.reparent_to(self.root)
        floor_c = self.root.attach_new_node(CollisionNode("floor"))
        floor_c.node().add_solid(CollisionPlane(Plane(LVector3(0, 0, 1), LPoint3(0, 0, 0))))
        floor_c.node().set_into_collide_mask(FLOOR_MASK)

        # 四面墙：CollisionBox（into-only）
        self.walls: list[NodePath] = []
        for name, pos, half in [
            ("wall-n", (0, self.ARENA, 0.5), (self.ARENA, 0.2, 0.5)),
            ("wall-s", (0, -self.ARENA, 0.5), (self.ARENA, 0.2, 0.5)),
            ("wall-e", (self.ARENA, 0, 0.5), (0.2, self.ARENA, 0.5)),
            ("wall-w", (-self.ARENA, 0, 0.5), (0.2, self.ARENA, 0.5)),
        ]:
            vis = make_cube(1, color=(0.6, 0.6, 0.65, 1))
            vis.reparent_to(self.root)
            vis.set_pos(*pos)
            vis.set_scale(half[0] * 2, half[1] * 2, half[2] * 2)
            cn = CollisionNode(name)
            cn.add_solid(CollisionBox(LPoint3(*pos), *half))
            cn.set_into_collide_mask(WALL_MASK)
            self.walls.append(self.root.attach_new_node(cn))

        # 金币：into=COIN_MASK 的球体
        self.coins: list[NodePath] = []
        for i in range(8):
            coin = make_uv_sphere(0.35, color=(1, 0.85, 0.2, 1), name=f"coin-{i}")
            coin.reparent_to(self.root)
            coin.set_pos(rng.uniform(-6, 6), rng.uniform(-6, 6), 0.4)
            cn = CollisionNode(f"coin-{i}")
            cn.add_solid(CollisionSphere(0, 0, 0, 0.35))
            cn.set_into_collide_mask(COIN_MASK)
            coin.attach_new_node(cn)
            self.coins.append(coin)

        # 可拾取的方块：into=PICK_MASK，另外演示 Capsule 固体
        self.pickables: list[NodePath] = []
        for i in range(4):
            box = make_cube(1, name=f"pick-{i}")
            box.reparent_to(self.root)
            box.set_pos(-4.5 + i * 3, 4, 0.5)
            cn = CollisionNode(f"pick-{i}")
            cn.add_solid(CollisionCapsule(0, 0, -0.5, 0, 0, 0.5, 0.6))
            cn.set_into_collide_mask(PICK_MASK)
            cn.set_python_tag("owner", box)
            box.attach_new_node(cn)
            self.pickables.append(box)

        # ---- 玩家球：一个 from 球同时挂 Pusher（墙）与 Event（金币）
        self.ball = make_uv_sphere(0.5, color=(0.3, 0.7, 1, 1), name="ball")
        self.ball.reparent_to(self.root)
        self.ball.set_pos(0, -3, 0.5)
        ball_c = CollisionNode("ball")
        ball_c.add_solid(CollisionSphere(0, 0, 0, 0.5))
        # 只和墙做 Pusher（若包含 COIN_MASK，金币也会像墙一样把球挡住）
        ball_c.set_from_collide_mask(WALL_MASK)
        ball_c.set_into_collide_mask(BitMask32.all_off())  # 自己不当 into
        self.ball_c = self.ball.attach_new_node(ball_c)
        self.pusher = CollisionHandlerPusher()
        self.pusher.add_collider(self.ball_c, self.ball)
        self.trav.add_collider(self.ball_c, self.pusher)
        # Event handler 也可以复用 Pusher（Pusher 继承自 Event），这里单独建一个以演示
        self.coin_events = CollisionHandlerEvent()
        self.coin_events.add_in_pattern("%fn-into-%in")  # 生成事件名 ball-into-coin-3
        self.coin_trav = CollisionTraverser("coin-trav")
        coin_from = self.ball.attach_new_node(CollisionNode("ball-coin"))
        coin_from.node().add_solid(CollisionSphere(0, 0, 0, 0.5))
        coin_from.node().set_from_collide_mask(COIN_MASK)
        coin_from.node().set_into_collide_mask(BitMask32.all_off())
        self.coin_trav.add_collider(coin_from, self.coin_events)
        for i in range(len(self.coins)):
            self.accept(f"ball-coin-into-coin-{i}", self.collect, [i])
        self.score = 0

        # ---- Floor handler：从高处往下的射线，让“无人机”贴地飞
        self.drone = make_cube(0.4, color=(1, 0.4, 0.8, 1), name="drone")
        self.drone.reparent_to(self.root)
        self.drone.set_pos(3, -3, 5)
        ray_np = self.drone.attach_new_node(CollisionNode("drone-ray"))
        ray_np.node().add_solid(CollisionRay(0, 0, 0, 0, 0, -1))
        ray_np.node().set_from_collide_mask(FLOOR_MASK)
        ray_np.node().set_into_collide_mask(BitMask32.all_off())
        self.floor = CollisionHandlerFloor()
        self.floor.add_collider(ray_np, self.drone)
        self.floor.set_offset(1.5)  # 离地高度
        self.trav.add_collider(ray_np, self.floor)

        # ---- 拾取：射线 + Queue
        self.pick_queue = CollisionHandlerQueue()
        self.pick_trav = CollisionTraverser("pick-trav")
        self.pick_ray = CollisionRay()
        pick_node = CollisionNode("mouse-ray")
        pick_node.add_solid(self.pick_ray)
        pick_node.set_from_collide_mask(PICK_MASK)
        pick_node.set_into_collide_mask(BitMask32.all_off())
        if getattr(self.base, "cam", None) is not None:
            self.pick_np = self.base.cam.attach_new_node(pick_node)
            self.on_cleanup(self.pick_np.remove_node)
            self.pick_trav.add_collider(self.pick_np, self.pick_queue)
        else:
            self.pick_np = None

        self.velocity = LVector3(4.0, 3.0, 0)
        self.shown = False
        self.accept("mouse1", self.pick_from_mouse)
        self.accept("v", self.toggle_show)
        self.add_task(self._update, "update", sort=25)
        self.status("球被墙推回、吃金币会抛事件；点击方块做拾取")

    # ------------------------------------------------------------ 逻辑
    def step(self, dt: float) -> None:
        # 随意移动，碰墙后 Pusher 会把位置修正回来；检测到修正就反弹
        before = self.ball.get_pos()
        target = before + self.velocity * dt
        self.ball.set_pos(target)
        self.trav.traverse(self.root)
        self.coin_trav.traverse(self.root)
        after = self.ball.get_pos()
        if (after - target).length() > 1e-4:
            push = after - target
            if abs(push.x) > abs(push.y):
                self.velocity.x *= -1
            else:
                self.velocity.y *= -1
        # 无人机水平绕圈，高度交给 Floor handler
        t = self.clock.get_frame_time()
        self.drone.set_x(3 * math.cos(t))
        self.drone.set_y(-3 + 3 * math.sin(t))
        self.state["ball"] = (round(after.x, 2), round(after.y, 2))
        self.state["drone_z"] = round(self.drone.get_z(), 2)

    def _update(self, task):
        self.step(min(self.clock.get_dt(), 0.05))
        return task.cont

    def collect(self, index: int, entry) -> None:
        """事件回调的最后一个参数是 CollisionEntry。"""
        coin = self.coins[index]
        if coin.is_stashed():
            return
        coin.stash()  # stash 后不再参与碰撞遍历
        self.score += 1
        self.state["score"] = self.score
        self.state["last_hit_point"] = tuple(round(v, 2) for v in entry.get_surface_point(self.base.render))

    def pick(self, film_x: float, film_y: float) -> NodePath | None:
        """set_from_lens：根据镜头与胶片坐标自动设置射线起点和方向。"""
        if self.pick_np is None:
            return None
        self.pick_ray.set_from_lens(self.base.cam.node(), film_x, film_y)
        self.pick_trav.traverse(self.root)
        if self.pick_queue.get_num_entries() == 0:
            return None
        self.pick_queue.sort_entries()  # 按距离从近到远
        entry = self.pick_queue.get_entry(0)
        owner = entry.get_into_node().get_python_tag("owner")
        for p in self.pickables:
            p.clear_color_scale()
        owner.set_color_scale(1, 0.3, 0.3, 1)
        self.state["picked"] = owner.get_name()
        return owner

    def pick_from_mouse(self) -> None:
        if self.has_mouse_watcher and self.base.mouseWatcherNode.has_mouse():
            m = self.base.mouseWatcherNode.get_mouse()
            self.pick(m.x, m.y)

    def segment_hits(self, a: LPoint3, b: LPoint3) -> int:
        """CollisionSegment：一次性线段检测（例如视线遮挡判断）。"""
        q = CollisionHandlerQueue()
        t = CollisionTraverser("segment")
        node = CollisionNode("seg")
        node.add_solid(CollisionSegment(a, b))
        node.set_from_collide_mask(WALL_MASK)
        node.set_into_collide_mask(BitMask32.all_off())
        np = self.root.attach_new_node(node)
        t.add_collider(np, q)
        t.traverse(self.root)
        n = q.get_num_entries()
        np.remove_node()
        return n

    def toggle_show(self) -> None:
        """show_collisions：可视化本 traverser 检测到的碰撞；CollisionNode.show() 显示碰撞体。"""
        self.shown = not self.shown
        for np in self.root.find_all_matches("**/+CollisionNode"):
            np.show() if self.shown else np.hide()
        if self.shown:
            self.trav.show_collisions(self.root)
        else:
            self.trav.hide_collisions()
