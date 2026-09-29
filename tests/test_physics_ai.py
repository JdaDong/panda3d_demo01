"""L10 碰撞 / L11 Bullet / L23 PandaAI / L24 ODE。"""

from __future__ import annotations

import pytest
from panda3d.core import LPoint2, LPoint3


# --------------------------------------------------------------------------- L10
class TestCollision:
    def test_pusher_keeps_ball_inside(self, lesson):
        c = lesson("collision")
        for _ in range(400):
            c.step(1 / 30)
        x, y = c.state["ball"]
        assert abs(x) < c.ARENA and abs(y) < c.ARENA

    def test_floor_handler(self, lesson):
        c = lesson("collision")
        for _ in range(3):
            c.step(1 / 30)
        assert c.state["drone_z"] == pytest.approx(1.5, abs=1e-3)  # 地面 z=0 + offset 1.5

    def test_event_handler_collects_coin(self, lesson, step):
        c = lesson("collision")
        coin = c.coins[0]
        c.velocity.set(0, 0, 0)
        c.ball.set_pos(coin.get_pos())
        c.coin_trav.traverse(c.root)   # 生成 ball-coin-into-coin-0 事件 → 事件队列
        step(1)                        # eventManager 任务派发事件
        assert c.score >= 1
        assert coin.is_stashed()
        assert len(c.state["last_hit_point"]) == 3

    def test_segment_query(self, lesson):
        c = lesson("collision")
        assert c.segment_hits(LPoint3(-20, 0, 0.5), LPoint3(20, 0, 0.5)) == 2   # 东西两面墙
        assert c.segment_hits(LPoint3(-1, 0, 0.5), LPoint3(1, 0, 0.5)) == 0

    @pytest.mark.window
    def test_mouse_ray_picking(self, lesson, step):
        c = lesson("collision")
        step(1)
        target = c.pickables[2]
        # 目标中心 → 相机空间 → 胶片坐标，模拟“鼠标点在它身上”
        p_cam = c.base.cam.get_relative_point(target, LPoint3(0, 0, 0))
        film = LPoint2()
        assert c.base.cam.node().get_lens().project(p_cam, film)
        assert c.pick(film.x, film.y) == target
        assert c.state["picked"] == "pick-2"
        assert c.pick(0.99, 0.99) is None  # 画面角落：什么都没点到

    def test_toggle_show(self, lesson):
        c = lesson("collision")
        c.toggle_show()
        assert not c.walls[0].is_hidden()
        c.toggle_show()
        assert c.walls[0].is_hidden()


# --------------------------------------------------------------------------- L11
class TestBullet:
    def test_bodies_settle_on_ground(self, lesson):
        b = lesson("bullet_physics")
        assert b.state["bodies"] == 18
        for _ in range(60):
            b.step(1 / 30)
        assert b.state["ground_contacts"] > 0
        assert b.state["ray_hit"] in ("box", "ground")
        assert all(np.get_z() > 0 for np in b.bodies)  # 没有穿透地面

    def test_fire_impulse(self, lesson):
        b = lesson("bullet_physics")
        shot = b.fire()
        y0 = shot.get_y()
        for _ in range(10):
            b.step(1 / 30)
        assert shot.get_y() > y0 + 3               # 冲量 60 / 质量 3 = 20 m/s
        assert b.state["shots"] == 1

    def test_pendulum_swings(self, lesson):
        b = lesson("bullet_physics")
        x0 = b.bob_np.get_x()
        for _ in range(10):
            b.step(1 / 30)
        assert b.bob_np.get_x() != pytest.approx(x0, abs=1e-3)
        assert len(list(b.world.get_constraints())) == 1

    def test_rebuild_tower(self, lesson):
        b = lesson("bullet_physics")
        b.fire()
        b.build_tower()
        assert len(b.bodies) == 18 and b.world.get_num_rigid_bodies() == 18 + 3  # + 地面/锚点/摆锤

    def test_debug_toggle(self, lesson):
        b = lesson("bullet_physics")
        b.toggle_debug()
        assert not b.debug_np.is_hidden()


# --------------------------------------------------------------------------- L23
class TestAi:
    def test_hunter_pursues(self, lesson, step):
        ai = lesson("ai_steering")
        ai.step(0)
        d0 = ai.state["hunter_to_target"]
        step(90)
        assert ai.state["hunter_to_target"] < d0
        # 进入 arrival 半径后，PandaAI 会把 pursue 置为 paused、由 arrival 接管减速
        assert ai.state["pursue_status"] in ("active", "done", "paused")

    def test_pause_behavior(self, lesson, step):
        ai = lesson("ai_steering")
        step(1)
        assert ai.state["pursue_status"] == "active"
        assert ai.toggle_hunter() is True
        step(1)
        assert ai.state["pursue_status"] == "paused"
        assert ai.toggle_hunter() is False

    def test_coward_moves(self, lesson, step):
        ai = lesson("ai_steering")
        p0 = ai.coward_np.get_pos()
        step(60)
        assert (ai.coward_np.get_pos() - p0).length() > 0.1


# --------------------------------------------------------------------------- L24
class TestOde:
    def test_boxes_fall_and_rest(self, lesson):
        o = lesson("ode_physics")
        assert o.state["bodies"] == 12
        start_z = min(b.get_position().z for np, b in o.objects[:12])
        for _ in range(180):          # 2 秒模拟
            o.step_fixed()
        o.sync()
        lowest = min(b.get_position().z for _, b in o.objects[:12])
        assert lowest < start_z
        assert lowest > 0.1           # 被地面接住，没有穿透

    def test_chain_hangs_from_anchor(self, lesson):
        o = lesson("ode_physics")
        for _ in range(90):
            o.step_fixed()
        first = o.objects[12][1].get_position()
        anchor = LPoint3(6 - 0.35, 0, 8)
        assert (LPoint3(first) - anchor).length() == pytest.approx(0.35, abs=0.1)

    def test_spawn_more(self, lesson):
        o = lesson("ode_physics")
        o.spawn_boxes(3)
        assert len(o.objects) == 12 + 5 + 3
        o.sync()
        np, body = o.objects[-1]
        assert tuple(np.get_pos()) == pytest.approx(tuple(body.get_position()), abs=1e-4)
