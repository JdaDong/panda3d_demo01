"""L07 输入事件 / L08 任务时钟 / L09 Interval / L18 FSM —— 纯逻辑，headless 也能跑。"""

from __future__ import annotations

import time

import pytest
from direct.fsm.FSM import RequestDenied
from direct.showbase.MessengerGlobal import messenger
from panda3d.core import LPoint3

from panda3d_demo01.lessons.l08_tasks_clock import count_primes


# --------------------------------------------------------------------------- L07
class TestInputEvents:
    def test_key_down_up_moves_player(self, lesson):
        ie = lesson("input_events")
        messenger.send("w")                      # 模拟按下 W（与真实键盘走同一条路径）
        assert ie.keys["w"] is True
        ie.step(1.0)
        assert ie.state["player"] == (0.0, pytest.approx(ie.SPEED))
        messenger.send("w-up")
        assert ie.keys["w"] is False

    def test_diagonal_is_normalized(self, lesson):
        ie = lesson("input_events")
        messenger.send("w")
        messenger.send("d")
        assert ie.direction().length() == pytest.approx(1.0)

    def test_custom_event_with_args(self, lesson):
        ie = lesson("input_events")
        messenger.send("space")                  # space → 转发 demo01-jump [1.5]
        assert ie.jumps == 1
        assert ie.state["jump_source"] == "from-space"
        assert ie.player.get_z() == pytest.approx(2.0)

    def test_accept_once(self, lesson):
        ie = lesson("input_events")
        messenger.send("j")
        messenger.send("j")
        assert ie.state["once_fired"] == 1

    def test_repeat_and_click(self, lesson):
        ie = lesson("input_events")
        for _ in range(3):
            messenger.send("w-repeat")
        messenger.send("mouse1")
        assert ie.state["repeat"] == 3
        assert ie.state["clicked"] is True

    def test_gravity_brings_back(self, lesson):
        ie = lesson("input_events")
        messenger.send("space")
        for _ in range(30):
            ie.step(0.1)
        assert ie.player.get_z() == pytest.approx(0.5)

    def test_events_ignored_after_stop(self, lesson):
        ie = lesson("input_events")
        ie.stop()
        messenger.send("space")
        assert ie.jumps == 0


# --------------------------------------------------------------------------- L08
class TestTasksClock:
    def test_count_primes(self):
        assert count_primes(100) == 25
        assert count_primes(1000) == 168

    def test_periodic_oneshot_uponDeath(self, lesson, step):
        tc = lesson("tasks_clock")
        step(40)  # ≈ 1.33 秒（非实时时钟，每帧 1/30s）
        assert tc.counters["every-frame"] == 40
        # task.again 从“本次执行时刻”起重新计时，所以 1.33s 内恰好 2 次（0.5s、1.0s 附近）
        assert tc.counters["every-0.5s"] == 2
        assert any(e.startswith("one-shot:hello") for e in tc.events)
        assert "one-shot died" in tc.events
        assert tc.counters["coroutine"] >= 3

    def test_task_frame_and_dt(self, lesson, step):
        tc = lesson("tasks_clock")
        step(5)
        assert tc.state["dt_ms"] == pytest.approx(1000 / 30, abs=0.1)

    def test_worker_chain_computes_off_thread(self, lesson, step):
        tc = lesson("tasks_clock")
        tc.start_worker_job(10_000)
        deadline = time.time() + 10
        while "primes" not in tc.state and time.time() < deadline:
            step(1)
            time.sleep(0.005)
        assert tc.state["primes"] == 1229

    def test_async_loader_callback(self, lesson, step):
        tc = lesson("tasks_clock")
        tc.load_teapot_async()
        deadline = time.time() + 15
        while not tc.state.get("teapot_loaded") and time.time() < deadline:
            step(1)
            time.sleep(0.01)
        assert tc.state.get("teapot_loaded")
        assert tc.teapot.get_parent() == tc.root


# --------------------------------------------------------------------------- L09
class TestIntervals:
    def test_durations(self, lesson):
        iv = lesson("intervals")
        assert iv.square.getDuration() == pytest.approx(4.0)   # Func 时长为 0
        assert iv.pulse.getDuration() == pytest.approx(0.6 + 0.6 + 0.5 + 0.3 + 0.5)
        assert iv.counter.getDuration() == pytest.approx(4.0)

    def test_seek_sets_state_deterministically(self, lesson):
        iv = lesson("intervals")
        iv.seek(0.5)
        assert iv.cube.get_pos() == LPoint3(5, 5, 0.5)       # 第 3 个角
        assert iv.state["progress"] == 50
        assert iv.spinner.get_h() == pytest.approx(180)

    def test_func_intervals_fire(self, lesson, step):
        iv = lesson("intervals")
        step(40)  # 1.33 秒 → 至少经过 corner-0
        assert iv.state["last_func"].startswith("corner-")

    def test_pause_resume(self, lesson, step):
        iv = lesson("intervals")
        step(3)
        iv.toggle_pause()
        assert not any(x.isPlaying() for x in iv.all)
        pos = iv.cube.get_pos()
        step(10)
        assert iv.cube.get_pos() == pos
        iv.toggle_pause()
        assert all(x.isPlaying() for x in iv.all)

    def test_projectile_lands_at_end(self, lesson):
        iv = lesson("intervals")
        iv.throw.setT(iv.throw.getDuration())
        assert tuple(iv.projectile.get_pos()) == pytest.approx((6, 6, 0.3), abs=1e-3)


# --------------------------------------------------------------------------- L18
class TestFsm:
    def test_traffic_cycle(self, lesson):
        f = lesson("fsm")
        assert f.light.state == "Red"
        assert [f.light.advance() for _ in range(3)] == ["Green", "Yellow", "Red"]
        assert f.light.history[-4:] == ["Red", "Green", "Yellow", "Red"]

    def test_default_transitions_reject(self, lesson):
        f = lesson("fsm")
        with pytest.raises(RequestDenied):
            f.light.request("Yellow")                       # Red 不能直接到 Yellow
        assert f.toggle_power() == "Off"                    # 任何状态都能 Off
        assert f.toggle_power() == "Red"

    def test_filter_guard_and_redirect(self, lesson):
        f = lesson("fsm")
        assert f.try_request("Jump") is True
        assert f.character.state == "Jump"
        assert f.try_request("Walk") is False               # 空中拒绝
        assert f.try_request("Land") is True                # 重定向为 Idle
        assert f.character.state == "Idle"
        assert f.state["char_denied"] == 1

    def test_enter_args_and_exit(self, lesson):
        f = lesson("fsm")
        f.try_request("Walk", 3.0)
        assert f.character.speed == 3.0
        f.try_request("Idle")
        assert f.character.speed == 0.0                     # exitWalk 被调用

    def test_demand_and_force(self, lesson):
        f = lesson("fsm")
        assert f.demand_or_error("Land").startswith("denied")
        f.try_request("Jump")
        f.character.forceTransition("Walk")                 # 无视 filterJump
        assert f.character.state == "Walk"

    def test_auto_cycle_task(self, lesson, step):
        f = lesson("fsm")
        step(40)  # 1.33 秒 > 1.2 秒
        assert f.light.state == "Green"
