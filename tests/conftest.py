"""pytest 公共夹具。

关键约束：**一个进程只能有一个 ShowBase**。因此：
* ``base`` 为 session 级夹具，所有测试共享；
* 每个课程测试通过 ``lesson`` 工厂夹具启动，测试结束自动 ``stop()``，保证互不污染；
* 时钟切到非实时模式（每次 ``step`` 固定前进 1/30 秒），测试结果与机器快慢无关。

运行模式由环境变量 ``PANDA3D_DEMO01_TEST_MODE`` 控制：
* ``offscreen``（默认）：离屏缓冲，可测渲染相关 API
* ``headless``：window-type none，无 GPU 的 CI 用；标记 ``@pytest.mark.window`` 的用例自动 skip
"""

from __future__ import annotations

import os
from typing import Callable

import pytest

from panda3d_demo01 import config

FPS = 30


def _mode() -> config.RunMode:
    return config.RunMode(os.environ.get("PANDA3D_DEMO01_TEST_MODE", "offscreen"))


@pytest.fixture(scope="session")
def base():
    from direct.showbase.ShowBase import ShowBase
    from panda3d.core import ClockObject

    config.apply(config.RuntimeConfig(mode=_mode(), width=640, height=360, mute=True))
    sb = ShowBase()
    sb.disable_mouse()
    clock = ClockObject.get_global_clock()
    clock.set_mode(ClockObject.M_non_real_time)
    clock.set_frame_rate(FPS)
    yield sb
    sb.destroy()


@pytest.fixture
def step(base) -> Callable[[int], None]:
    """推进 n 帧（执行所有任务：事件、interval、碰撞、渲染……）。"""

    def _step(n: int = 1) -> None:
        for _ in range(n):
            base.task_mgr.step()

    return _step


@pytest.fixture
def lesson(base):
    """工厂：lesson("scene_graph") → 已 start 的课程实例；测试结束自动 stop。"""
    from panda3d_demo01.core import get_lesson

    started = []

    def _make(key: str):
        inst = get_lesson(key)(base)
        inst.start()
        started.append(inst)
        return inst

    yield _make
    for inst in reversed(started):
        inst.stop()


@pytest.fixture
def workdir(request):
    """每个用例独立的临时目录（放在 cache_dir 下，避免依赖系统 tmp 权限）。"""
    import shutil
    import uuid

    from panda3d_demo01.core.paths import cache_dir

    d = cache_dir() / "pytest" / f"{request.node.name[:40]}-{uuid.uuid4().hex[:8]}"
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def has_window(base) -> bool:
    return base.win is not None


def pytest_runtest_setup(item):
    if "window" in item.keywords and _mode() is config.RunMode.HEADLESS:
        pytest.skip("需要窗口/离屏缓冲（当前为 headless 模式）")
