"""L08 任务系统（TaskManager）、时钟、协程、线程任务链、异步加载。

一帧里发生了什么（ShowBase 默认任务，按 sort 升序）::

    dataLoop(-50) → eventManager(0) → ivalLoop(20) → collisionLoop(30)
      → 你的任务(默认 0) → igLoop(50, 真正 renderFrame) → audioLoop(60)

任务函数返回值决定命运
--------------------
* ``task.cont``  下一帧继续
* ``task.done``  结束（触发 uponDeath）
* ``task.again`` 以 delay 重新调度（仅 doMethodLater 有意义）

进阶
----
* **协程任务**：``async def`` 直接交给 ``taskMgr.add``，用 ``await Task.pause(s)`` 让出
* **任务链(task chain)**：可配置独立线程，把耗时计算移出主线程
* **异步加载**：``loader.load_model(path, callback=fn)`` 或 ``await loader.load_model(..., blocking=False)``
* **PStatCollector**：给代码段打点，连上 PStats 服务器即可看火焰图
"""

from __future__ import annotations

import queue

from direct.task import Task
from panda3d.core import ClockObject, NodePath, PStatCollector, Thread

from ..core import Lesson, register
from ..core.procedural import make_cube

WORKER_CHAIN = "demo01-worker"
_chain_ready = False


def count_primes(limit: int) -> int:
    """故意写得朴素 —— 模拟 CPU 密集工作。"""
    sieve = bytearray([1]) * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, int(limit ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i :: i] = bytearray(len(sieve[i * i :: i]))
    return sum(sieve)


@register
class TasksClockLesson(Lesson):
    key = "tasks_clock"
    order = 8
    title = "任务、时钟与协程"
    title_en = "Tasks, Clock & Coroutines"
    summary = "task.cont/done/again、doMethodLater、sort、uponDeath、async 协程、线程任务链、异步加载"
    apis = (
        "TaskManager.add", "TaskManager.do_method_later", "TaskManager.remove", "TaskManager.hasTaskNamed",
        "TaskManager.setupTaskChain", "Task.cont/done/again", "Task.pause (await)", "task.time/task.frame",
        "uponDeath", "extraArgs/appendTask", "ClockObject.get_dt", "ClockObject.get_frame_time",
        "ClockObject.get_average_frame_rate", "Thread.is_threading_supported", "Loader.load_model(callback=)",
        "PStatCollector.start/stop",
    )
    controls = ("SPACE 启动一次后台质数计算", "L 异步加载茶壶")

    def setup(self) -> None:
        self.place_camera((0, -16, 6), (0, 0, 2))
        self.bars: dict[str, NodePath] = {}
        self.counters = {"every-frame": 0, "every-0.5s": 0, "coroutine": 0, "worker": 0}
        for i, name in enumerate(self.counters):
            bar = make_cube(1, color=(0.3 + 0.2 * i, 0.6, 1 - 0.2 * i, 1))
            bar.reparent_to(self.root)
            bar.set_x(-4.5 + i * 3)
            self.bars[name] = bar
        self.events: list[str] = []
        self.results: queue.Queue[int] = queue.Queue()
        self.pstat = PStatCollector("App:demo01:tasks")

        # 1) 每帧任务，sort 控制同帧内顺序
        self.add_task(self._every_frame, "every-frame", sort=5)
        # 2) 周期任务：do_method_later + return task.again
        self.add_task(self._every_half_second, "every-0.5s", delay=0.5)
        # 3) 一次性任务 + extraArgs + uponDeath
        once = self.add_task(self._one_shot, "one-shot", delay=0.2, extra_args=["hello"])
        once.setUponDeath(lambda task: self.events.append("one-shot died"))
        # 4) 协程任务：taskMgr.add 可以直接接收 coroutine 对象
        self.coro_task = self.base.task_mgr.add(self._coroutine(), f"{self.key}:coroutine")
        self._tasks.append(self.coro_task)
        # 5) 线程任务链（真线程）
        self.threaded = Thread.is_threading_supported()
        self._ensure_worker_chain()
        self.add_task(self._drain_results, "drain")

        self.teapot: NodePath | None = None
        self.accept("space", self.start_worker_job, [200_000])
        self.accept("l", self.load_teapot_async)
        self.status(f"真线程: {Thread.is_true_threads()}；SPACE 后台计算 / L 异步加载")

    # ------------------------------------------------------------ 任务函数
    def _every_frame(self, task):
        self.pstat.start()
        self.counters["every-frame"] += 1
        self._grow("every-frame")
        clock = ClockObject.get_global_clock()
        self.state["frame"] = task.frame
        self.state["dt_ms"] = round(clock.get_dt() * 1000, 2)
        self.state["avg_fps"] = round(clock.get_average_frame_rate(), 1)
        self.pstat.stop()
        return task.cont

    def _every_half_second(self, task):
        self.counters["every-0.5s"] += 1
        self._grow("every-0.5s")
        return task.again

    def _one_shot(self, word: str, task):
        # appendTask=True 时 task 放在 extraArgs 之后
        self.events.append(f"one-shot:{word}@{task.time:.2f}")
        return task.done

    async def _coroutine(self):
        """协程：像写同步代码一样写“等待 → 做事 → 再等待”的流程。

        坑：await 中的协程任务无法被 taskMgr.remove() 立即移除，
        所以用 self.active 做“协作式取消”：课程 stop 后，下一次醒来就自然结束。
        """
        while self.active:
            await Task.pause(0.25)
            if not self.active:
                break
            self.counters["coroutine"] += 1
            self._grow("coroutine")
        return Task.done

    def _grow(self, name: str) -> None:
        n = self.counters[name]
        self.bars[name].set_scale(1, 1, 0.2 + (n % 50) * 0.1)
        self.bars[name].set_z((0.2 + (n % 50) * 0.1) / 2)
        self.state[f"count:{name}"] = n

    # ------------------------------------------------------------ 线程
    def _ensure_worker_chain(self) -> None:
        """setupTaskChain：同名链只需创建一次；numThreads>0 表示由独立线程执行。"""
        global _chain_ready
        if not _chain_ready:
            self.base.task_mgr.setupTaskChain(
                WORKER_CHAIN, numThreads=1 if self.threaded else 0, tickClock=False, frameSync=False
            )
            _chain_ready = True

    def start_worker_job(self, limit: int) -> None:
        def job(task):
            # 运行在 worker 线程：不要碰场景图，只做纯计算，结果放队列
            self.results.put(count_primes(limit))
            return task.done

        self.add_task(job, f"prime-job-{limit}", task_chain=WORKER_CHAIN)

    def _drain_results(self, task):
        while not self.results.empty():
            n = self.results.get_nowait()
            self.counters["worker"] += 1
            self._grow("worker")
            self.state["primes"] = n
        return task.cont

    # ------------------------------------------------------------ 异步加载
    def load_teapot_async(self) -> None:
        """callback 形式：加载在后台线程完成后，在主线程回调。"""
        self.base.loader.load_model("models/teapot", callback=self._on_teapot)

    def _on_teapot(self, model: NodePath) -> None:
        if not self.active:  # 课程已切走
            return
        self.teapot = model
        model.reparent_to(self.root)
        model.set_pos(0, 4, 0)
        model.set_scale(0.8)
        self.state["teapot_loaded"] = True
