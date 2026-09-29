"""Lesson 基类 —— 每个课程的“生命周期容器”。

设计要点
--------
* 继承 ``DirectObject``：获得 ``accept/ignore/ignoreAll`` 事件订阅能力，
  这是 Panda3D 里所有“能收消息的对象”的通用基类。
* 每个课程独占两个根节点：
    - ``self.root``      挂在 ``render`` 下（3D 场景）
    - ``self.gui_root``  挂在 ``aspect2d`` 下（2D 界面）
  ``stop()`` 时整棵子树 ``removeNode()``，保证课程之间零残留。
* 通过 ``add_task / track / on_cleanup`` 登记的资源会在 ``stop()`` 时自动回收，
  ——这就是 RAII 思想在 Panda3D 里的落地：谁创建谁登记，框架统一释放。
* ``self.state`` 是一个普通 dict，课程把可观测状态写进去，HUD 展示、UT 断言
  都读它，从而把“渲染”与“逻辑验证”解耦。
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable

from direct.showbase.DirectObject import DirectObject
from direct.task import Task
from panda3d.core import NodePath

if TYPE_CHECKING:  # 仅用于类型标注，避免运行期循环依赖
    from direct.interval.Interval import Interval
    from direct.showbase.ShowBase import ShowBase


class Lesson(DirectObject, abc.ABC):
    """所有课程的抽象基类。子类只需实现 :meth:`setup`（可选 :meth:`teardown`）。"""

    #: 唯一 ID，用于命令行 ``--lesson <key>`` 与注册表
    key: ClassVar[str] = ""
    #: 排序号（决定 N/P 翻页顺序）
    order: ClassVar[int] = 0
    #: 中文标题 / 英文标题（无 CJK 字体时 HUD 退化为英文）
    title: ClassVar[str] = ""
    title_en: ClassVar[str] = ""
    #: 一句话说明
    summary: ClassVar[str] = ""
    #: 本课覆盖的 Panda3D API 列表 —— docs/API_COVERAGE.md 由它自动生成
    apis: ClassVar[tuple[str, ...]] = ()
    #: 本课的专属按键说明
    controls: ClassVar[tuple[str, ...]] = ()

    def __init__(self, base: "ShowBase") -> None:
        super().__init__()
        self.base = base
        self.root: NodePath = NodePath()  # 空 NodePath，start() 后才有效
        self.gui_root: NodePath = NodePath()
        self.state: dict[str, Any] = {}
        self.active = False
        self._tasks: list[Task.Task] = []
        self._intervals: list["Interval"] = []
        self._cleanups: list[Callable[[], None]] = []

    # ------------------------------------------------------------------ 属性
    @property
    def has_window(self) -> bool:
        """是否有可渲染的输出（onscreen 窗口或 offscreen 缓冲）。"""
        return self.base.win is not None

    @property
    def has_mouse_watcher(self) -> bool:
        """只有真实窗口才有 MouseWatcher（离屏/无头都没有键鼠输入）。"""
        return getattr(self.base, "mouseWatcherNode", None) is not None

    @property
    def clock(self):
        """全局时钟 ClockObject（ShowBase 把它注入 builtins.globalClock）。"""
        from panda3d.core import ClockObject

        return ClockObject.get_global_clock()

    # ------------------------------------------------------------ 生命周期
    def start(self) -> None:
        """创建根节点并调用子类 setup()。"""
        if self.active:
            raise RuntimeError(f"lesson {self.key} already started")
        # attachNewNode = 新建 PandaNode 并挂到父节点下，返回指向它的 NodePath
        self.root = self.base.render.attach_new_node(f"lesson:{self.key}")
        self.gui_root = self.base.aspect2d.attach_new_node(f"gui:{self.key}")
        self.active = True
        self.state.clear()
        self._setup_failed = False
        try:
            self.setup()
        except Exception:
            # setup 半途失败：跳过 teardown（它可能依赖未创建的属性），只做通用回收
            self._setup_failed = True
            self.stop()
            raise

    def stop(self) -> None:
        """逆序释放：teardown → interval → task → 事件 → 自定义清理 → 节点。"""
        if not self.active:
            return
        try:
            if not getattr(self, "_setup_failed", False):
                self.teardown()
        finally:
            for iv in reversed(self._intervals):
                iv.pause()  # pause 而不是 finish：finish 会跳到终点并触发 Func
            for task in self._tasks:
                # 坑：正在 await（如 Task.pause）的协程任务 remove() 会返回 False 且移除失败，
                # 在 1.10 上 cancel() 也会触发断言。协程应自行检查 self.active 并退出（见 l08）。
                self.base.task_mgr.remove(task)
            self.ignoreAll()  # DirectObject：取消本对象所有 accept
            for fn in reversed(self._cleanups):
                fn()
            self.root.remove_node()
            self.gui_root.remove_node()
            self._intervals.clear()
            self._tasks.clear()
            self._cleanups.clear()
            self.active = False

    @abc.abstractmethod
    def setup(self) -> None:
        """构建场景、注册任务与事件。"""

    def teardown(self) -> None:
        """可选：释放非节点资源（缓冲区、物理世界、网络连接……）。"""

    # ------------------------------------------------------------ 登记辅助
    def add_task(
        self,
        fn: Callable[..., Any],
        name: str,
        *,
        delay: float | None = None,
        sort: int = 0,
        extra_args: Iterable[Any] | None = None,
        task_chain: str | None = None,
    ) -> Task.Task:
        """包装 taskMgr.add / taskMgr.doMethodLater，并登记以便自动移除。

        - ``delay`` 为 None → 每帧调用；否则延迟 delay 秒后调用（返回 task.again 可周期执行）
        - ``sort``  越小越先执行（同一帧内的相对顺序）
        """
        full_name = f"{self.key}:{name}"
        kwargs: dict[str, Any] = {"sort": sort}
        if extra_args is not None:
            kwargs["extraArgs"] = list(extra_args)
            kwargs["appendTask"] = True
        if task_chain is not None:
            kwargs["taskChain"] = task_chain
        if delay is None:
            task = self.base.task_mgr.add(fn, full_name, **kwargs)
        else:
            task = self.base.task_mgr.do_method_later(delay, fn, full_name, **kwargs)
        self._tasks.append(task)
        return task

    def track(self, interval: "Interval") -> "Interval":
        """登记 Interval，stop() 时 pause。"""
        self._intervals.append(interval)
        return interval

    def on_cleanup(self, fn: Callable[[], None]) -> None:
        """登记任意清理回调（LIFO 执行）。"""
        self._cleanups.append(fn)

    def place_camera(self, pos: tuple[float, float, float], look_at: tuple[float, float, float] = (0, 0, 0)) -> None:
        """摆放默认相机；若 App 装了 OrbitCamera 则同步给它。无头模式下 camera 为 None。"""
        orbit = getattr(self.base, "orbit", None)
        if orbit is not None:
            orbit.look_from(pos, look_at)
        elif getattr(self.base, "camera", None) is not None:
            self.base.camera.set_pos(*pos)
            self.base.camera.look_at(*look_at)

    def status(self, text: str) -> None:
        """写入 HUD 状态栏。"""
        self.state["status"] = text

    # ------------------------------------------------------------ 描述
    def describe(self) -> str:
        return f"[{self.key}] {self.title} — {self.summary}"

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Lesson {self.key} active={self.active}>"
