"""L07 输入与事件系统。

两种读输入的方式
----------------
1. **事件驱动**：``accept("w", fn)`` / ``accept("w-up", fn)`` / ``accept("w-repeat", fn)``
   ButtonThrower 把按键变成事件名丢给 messenger，messenger 再分发给订阅者。
2. **轮询**：每帧 ``mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("w"))``
   适合“按住持续移动”。

事件系统本身与输入无关：``messenger.send("任意名字", [参数])`` 就是一个进程内 pub/sub。
修饰键组合事件名：``shift-a``、``control-s``；鼠标：``mouse1``、``mouse3-up``、``wheel_up``。
"""

from __future__ import annotations

from direct.showbase.MessengerGlobal import messenger
from panda3d.core import KeyboardButton, LVector3, MouseButton, WindowProperties

from ..core import Lesson, register
from ..core.procedural import make_cube, make_grid, make_uv_sphere

MOVE_KEYS = {"w": (0, 1), "s": (0, -1), "a": (-1, 0), "d": (1, 0)}


@register
class InputEventsLesson(Lesson):
    key = "input_events"
    order = 7
    title = "输入与事件"
    title_en = "Input & Events"
    summary = "accept/-up/-repeat、轮询 is_button_down、鼠标、messenger 自定义事件、accept_once"
    apis = (
        "DirectObject.accept", "DirectObject.accept_once", "DirectObject.ignore", "DirectObject.ignoreAll",
        "messenger.send", "Messenger.is_accepting", "KeyboardButton.ascii_key", "MouseButton.one",
        "MouseWatcher.is_button_down", "MouseWatcher.has_mouse", "MouseWatcher.get_mouse",
        "ButtonThrower.set_button_down_event", "ButtonThrower.set_modifier_buttons",
        "WindowProperties.set_cursor_hidden", "GraphicsWindow.request_properties",
        "事件名: key / key-up / key-repeat / shift-key / mouse1 / wheel_up",
    )
    controls = ("WASD 移动方块", "SPACE 跳（自定义事件）", "鼠标左键 染色", "C 隐藏光标", "J 一次性事件")

    SPEED = 6.0

    def setup(self) -> None:
        self.place_camera((0, -18, 12))
        self.root.attach_new_node(make_grid(16).node())
        self.player = make_cube(1)
        self.player.reparent_to(self.root)
        self.player.set_z(0.5)
        self.cursor_ball = make_uv_sphere(0.2, color=(1, 1, 0, 1))
        self.cursor_ball.reparent_to(self.root)

        # 方式一：事件驱动 —— 维护一个按键状态表（离屏/测试也能用 messenger.send 驱动）
        self.keys = {k: False for k in MOVE_KEYS}
        for k in MOVE_KEYS:
            self.accept(k, self._set_key, [k, True])
            self.accept(f"{k}-up", self._set_key, [k, False])
        self.accept("w-repeat", self._count_repeat)       # 按住时系统自动重复
        self.accept("shift-w", self._set_key, ["w", True])  # 按着 shift 时事件名带前缀

        # 自定义事件：参数通过 sentArgs 追加到 extraArgs 之后
        self.jumps = 0
        self.accept("space", messenger.send, ["demo01-jump", [1.5]])
        self.accept("demo01-jump", self.on_jump, ["from-space"])
        self.accept_once("j", self.on_once)             # 只触发一次后自动 ignore
        self.accept("mouse1", self.on_click)
        self.accept("c", self.toggle_cursor)

        # 原始按键流：ButtonThrower 的 button_down_event 会对“任意键”额外发一个事件
        self.raw_keys: list[str] = []
        self._button_thrower = None
        if getattr(self.base, "buttonThrowers", None):
            self._button_thrower = self.base.buttonThrowers[0].node()
            self._prev_down_event = self._button_thrower.get_button_down_event()
            self._button_thrower.set_button_down_event("demo01-raw-key")
            self.accept("demo01-raw-key", self._on_raw_key)
            self.on_cleanup(lambda: self._button_thrower.set_button_down_event(self._prev_down_event))

        self.cursor_hidden = False
        self.repeat_count = 0
        self.add_task(self._move, "move")
        self.status("WASD 移动；试试按住 W 看 repeat 计数")

    # ------------------------------------------------------------ 事件处理
    def _set_key(self, key: str, down: bool) -> None:
        self.keys[key] = down

    def _count_repeat(self) -> None:
        self.repeat_count += 1
        self.state["repeat"] = self.repeat_count

    def _on_raw_key(self, key_name: str) -> None:
        self.raw_keys = (self.raw_keys + [key_name])[-8:]
        self.state["raw_keys"] = " ".join(self.raw_keys)

    def on_jump(self, source: str, height: float) -> None:
        """extraArgs(source) 在前，messenger.send 的 sentArgs(height) 在后。"""
        self.jumps += 1
        self.player.set_z(0.5 + height)
        self.state["jumps"] = self.jumps
        self.state["jump_source"] = source

    def on_once(self) -> None:
        self.state["once_fired"] = self.state.get("once_fired", 0) + 1

    def on_click(self) -> None:
        self.player.set_color_scale(1, 0.3, 0.3, 1)
        self.state["clicked"] = True

    def toggle_cursor(self) -> None:
        """WindowProperties 是“请求”：request_properties 之后由窗口系统异步生效。"""
        self.cursor_hidden = not self.cursor_hidden
        if self.has_mouse_watcher:
            props = WindowProperties()
            props.set_cursor_hidden(self.cursor_hidden)
            self.base.win.request_properties(props)

    # ------------------------------------------------------------ 每帧
    def direction(self) -> LVector3:
        """合并事件表 + 轮询结果得到移动方向。"""
        v = LVector3(0, 0, 0)
        mw = self.base.mouseWatcherNode if self.has_mouse_watcher else None
        for k, (dx, dy) in MOVE_KEYS.items():
            polled = mw is not None and mw.is_button_down(KeyboardButton.ascii_key(k))
            if self.keys[k] or polled:
                v += LVector3(dx, dy, 0)
        if v.length_squared() > 0:
            v.normalize()
        return v

    def step(self, dt: float) -> None:
        self.player.set_pos(self.player.get_pos() + self.direction() * self.SPEED * dt)
        # 重力回落
        if self.player.get_z() > 0.5:
            self.player.set_z(max(0.5, self.player.get_z() - 4 * dt))
        p = self.player.get_pos()
        self.state["player"] = (round(p.x, 2), round(p.y, 2))

    def _move(self, task):
        self.step(self.clock.get_dt())
        if self.has_mouse_watcher and self.base.mouseWatcherNode.has_mouse():
            m = self.base.mouseWatcherNode.get_mouse()  # [-1,1] 归一化鼠标坐标
            self.cursor_ball.set_pos(m.x * 8, m.y * 8, 0.2)
            self.state["mouse"] = (round(m.x, 2), round(m.y, 2))
            if self.base.mouseWatcherNode.is_button_down(MouseButton.one()):
                self.cursor_ball.set_scale(1.8)
            else:
                self.cursor_ball.set_scale(1.0)
        return task.cont
