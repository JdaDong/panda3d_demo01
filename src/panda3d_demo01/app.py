"""DemoApp —— 继承 ShowBase 的主程序。

ShowBase 帮你做了什么？
----------------------
``ShowBase.__init__`` 会：读取 PRC → 打开窗口(GraphicsPipe/GraphicsEngine) →
创建 render/render2d/aspect2d 场景图 → 创建默认相机 → 启动 TaskManager 的默认任务
（数据图、事件、interval、渲染、音频）→ 把 base/render/loader/taskMgr/messenger
等注入 builtins。``run()`` 进入主循环（本质是不停地 ``taskMgr.step()``）。

本 App 额外提供：
* 课程切换（N/P/F5）与 HUD
* OrbitCamera
* **autopilot**：无需人工，依次跑完所有课程并截图（CI / 冒烟测试用）
"""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from direct.showbase.ShowBase import ShowBase
from panda3d.core import ClockObject, Filename

from . import config
from .core import Lesson, all_lessons
from .core import capabilities
from .core.camera_rig import OrbitCamera
from .core.fonts import load_ui_font
from .hud import Hud


@dataclass
class LessonReport:
    key: str
    ok: bool
    frames: int
    seconds: float
    screenshot: str | None = None
    error: str | None = None
    state: dict = field(default_factory=dict)


class DemoApp(ShowBase):
    def __init__(self, runtime: config.RuntimeConfig | None = None, start: str | None = None) -> None:
        self.runtime = runtime or config.RuntimeConfig()
        config.apply(self.runtime)                 # 必须在 ShowBase.__init__ 之前
        super().__init__()
        self.disable_mouse()                       # 关闭默认的“鼠标轨迹球”相机控制
        self.set_background_color(0.12, 0.13, 0.16, 1)
        self.caps = capabilities.detect(self)
        self.ui_font, self.ui_font_cjk = load_ui_font(self.loader)
        self.orbit = OrbitCamera(self) if getattr(self, "camera", None) is not None else None
        self.hud = Hud(self, self.ui_font, self.ui_font_cjk) if self.win is not None else None

        self.lesson_classes: list[type[Lesson]] = all_lessons()
        self.current: Lesson | None = None
        self.index = 0
        if start:
            keys = [c.key for c in self.lesson_classes]
            self.index = keys.index(start) if start in keys else int(start) - 1

        self.accept("escape", self.userExit)
        self.accept("n", self.next_lesson)
        self.accept("page_down", self.next_lesson)
        self.accept("p", self.prev_lesson)
        self.accept("page_up", self.prev_lesson)
        self.accept("f5", self.reload_lesson)
        self.accept("h", self._toggle_hud)
        self.accept("f12", self.save_screenshot)
        self.task_mgr.add(self._hud_task, "hud-refresh", sort=100)
        self.show_lesson(self.index)

    # ------------------------------------------------------------ 课程切换
    def show_lesson(self, index: int) -> Lesson:
        if self.current is not None:
            self.current.stop()
        self.index = index % len(self.lesson_classes)
        cls = self.lesson_classes[self.index]
        self.current = cls(self)
        self.current.start()
        if self.hud is not None:
            self.hud.show_lesson(self.index, len(self.lesson_classes), self.current)
        return self.current

    def next_lesson(self) -> Lesson:
        return self.show_lesson(self.index + 1)

    def prev_lesson(self) -> Lesson:
        return self.show_lesson(self.index - 1)

    def reload_lesson(self) -> Lesson:
        return self.show_lesson(self.index)

    def _toggle_hud(self) -> None:
        if self.hud is not None:
            self.hud.toggle()

    def _hud_task(self, task):
        if self.hud is not None and self.current is not None:
            self.hud.update_status(self.current)
        return task.cont

    # ------------------------------------------------------------ 截图
    def save_screenshot(self, path: str | Path | None = None) -> str | None:
        """GraphicsOutput.save_screenshot：把当前帧缓冲写成图片（格式由扩展名决定）。"""
        if self.win is None:
            return None
        if path is None:
            return str(self.screenshot(namePrefix=f"demo01-{self.current.key if self.current else 'x'}"))
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        ok = self.win.save_screenshot(Filename.from_os_specific(str(p)))
        return str(p) if ok else None

    # ------------------------------------------------------------ autopilot
    def run_autopilot(self, frames_per_lesson: int = 30, screenshot_dir: Path | None = None,
                      only: list[str] | None = None) -> list[LessonReport]:
        """确定性地逐课运行：非实时时钟（固定 dt=1/30），每课跑 N 帧并截图。"""
        clock = ClockObject.get_global_clock()
        clock.set_mode(ClockObject.M_non_real_time)
        clock.set_frame_rate(30)
        reports: list[LessonReport] = []
        for i, cls in enumerate(self.lesson_classes):
            if only and cls.key not in only:
                continue
            t0 = time.perf_counter()
            try:
                lesson = self.show_lesson(i)
                for _ in range(frames_per_lesson):
                    self.task_mgr.step()           # 一帧：执行所有任务（包括渲染）
                shot = None
                if screenshot_dir is not None and self.win is not None:
                    shot = self.save_screenshot(Path(screenshot_dir) / f"{i + 1:02d}_{cls.key}.png")
                reports.append(LessonReport(cls.key, True, frames_per_lesson, time.perf_counter() - t0, shot,
                                            state=_jsonable(lesson.state)))
            except Exception as exc:  # noqa: BLE001 - 汇总报告而不是中断
                reports.append(LessonReport(cls.key, False, 0, time.perf_counter() - t0,
                                            error=f"{exc!r}\n{traceback.format_exc()}"))
        if self.current is not None:
            self.current.stop()
            self.current = None
        clock.set_mode(ClockObject.M_normal)
        return reports


def _jsonable(state: dict) -> dict:
    out = {}
    for k, v in state.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        elif isinstance(v, (list, tuple)):
            out[k] = [x if isinstance(x, (str, int, float, bool)) else str(x) for x in v][:20]
        else:
            out[k] = str(v)
    return out
