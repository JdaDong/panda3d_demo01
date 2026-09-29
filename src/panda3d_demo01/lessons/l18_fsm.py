"""L18 有限状态机 direct.fsm.FSM。

约定大于配置：
* 状态 ``Foo`` 对应方法 ``enterFoo(*args)`` / ``exitFoo()``（都可省略）
* ``request("Foo", *args)``：请求切换；合法性由 ``defaultTransitions`` 或 ``filterXxx`` 决定
* ``filterXxx(request, args)``：当前处于 Xxx 时收到 request 的“守卫”，
  返回新状态名（可重定向）、tuple(状态, 参数…) 或 None（拒绝）
* ``demand`` 不允许失败（非法则抛 RequestDenied）；``forceTransition`` 无视规则强制切换
* 状态名首字母必须大写；``Off`` 是初始状态
"""

from __future__ import annotations

from direct.fsm.FSM import FSM, RequestDenied

from ..core import Lesson, register
from ..core.procedural import make_cube, make_uv_sphere

COLORS = {"Red": (1, 0.15, 0.1, 1), "Yellow": (1, 0.85, 0.1, 1), "Green": (0.2, 1, 0.3, 1)}
DIM = (0.15, 0.15, 0.15, 1)


class TrafficLight(FSM):
    """交通灯：Off → Red → Green → Yellow → Red …，Off 可随时进入。"""

    # defaultTransitions：{当前状态: [允许去往的状态]}；未列出的切换一律拒绝
    defaultTransitions = {
        "Off": ["Red"],
        "Red": ["Green", "Off"],
        "Green": ["Yellow", "Off"],
        "Yellow": ["Red", "Off"],
    }

    def __init__(self, lamps) -> None:
        FSM.__init__(self, "TrafficLight")
        self.lamps = lamps
        self.history: list[str] = []

    def _light(self, name: str | None) -> None:
        for k, np in self.lamps.items():
            np.set_color(COLORS[k] if k == name else DIM)

    def enterRed(self) -> None:
        self._light("Red")
        self.history.append("Red")

    def enterGreen(self) -> None:
        self._light("Green")
        self.history.append("Green")

    def enterYellow(self) -> None:
        self._light("Yellow")
        self.history.append("Yellow")

    def enterOff(self) -> None:
        self._light(None)

    NEXT = {"Red": "Green", "Green": "Yellow", "Yellow": "Red", "Off": "Red"}

    def advance(self) -> str:
        self.request(self.NEXT[self.state])
        return self.state


class Character(FSM):
    """角色：用 filter 方法实现更灵活的规则（例如 Jump 中禁止再跳，但允许 Land）。"""

    def __init__(self, body) -> None:
        FSM.__init__(self, "Character")
        self.body = body
        self.denied = 0

    def enterIdle(self) -> None:
        self.body.set_z(0.5)
        self.body.set_color_scale(1, 1, 1, 1)

    def enterWalk(self, speed: float = 1.0) -> None:
        self.body.set_color_scale(0.6, 1, 0.6, 1)
        self.speed = speed

    def exitWalk(self) -> None:
        self.speed = 0.0

    def enterJump(self) -> None:
        self.body.set_z(2.0)

    def filterJump(self, request: str, args):
        # 空中只接受 Land，并把 Land 重定向为 Idle
        if request == "Land":
            return "Idle"
        return None  # 其它一律拒绝

    def defaultFilter(self, request: str, args):
        # 地面上：Land 无意义（拒绝），其它交给默认规则（首字母大写 → 直接切换）
        if request == "Land":
            return None
        return FSM.defaultFilter(self, request, args)


@register
class FsmLesson(Lesson):
    key = "fsm"
    order = 18
    title = "有限状态机 FSM"
    title_en = "Finite State Machine"
    summary = "enter/exit 约定、defaultTransitions、filterXxx 守卫、request/demand/forceTransition"
    apis = (
        "direct.fsm.FSM", "FSM.request", "FSM.demand", "FSM.forceTransition", "FSM.state",
        "FSM.defaultTransitions", "FSM.defaultFilter", "filterXxx", "enterXxx/exitXxx",
        "FSM.RequestDenied", "FSM.cleanup",
    )
    controls = ("SPACE 手动切下一灯", "O 关灯/开灯", "W 走 / J 跳 / L 落地 / X 强制 Idle")

    def setup(self) -> None:
        self.place_camera((0, -14, 5), (0, 0, 2))
        pole = make_cube(0.3, color=(0.3, 0.3, 0.3, 1))
        pole.reparent_to(self.root)
        pole.set_scale(1, 1, 16)
        pole.set_pos(-3, 0, 2.4)
        lamps = {}
        for i, name in enumerate(["Red", "Yellow", "Green"]):
            s = make_uv_sphere(0.45)
            s.reparent_to(self.root)
            s.set_pos(-3, -0.3, 4.2 - i * 1.0)
            lamps[name] = s
        self.light = TrafficLight(lamps)
        self.light.request("Red")
        self.character = Character(make_cube(1))
        self.character.body.reparent_to(self.root)
        self.character.body.set_pos(2, 0, 0.5)
        self.character.request("Idle")

        self.accept("space", self.light.advance)
        self.accept("o", self.toggle_power)
        self.accept("w", self.try_request, ["Walk", 2.0])
        self.accept("j", self.try_request, ["Jump"])
        self.accept("l", self.try_request, ["Land"])
        self.accept("x", self.character.forceTransition, ["Idle"])
        self.add_task(self._auto_cycle, "auto", delay=1.2)
        self.add_task(self._report, "report")
        self.status("交通灯自动循环；角色状态机试试 W/J/L")

    def teardown(self) -> None:
        # FSM.cleanup：退出当前状态并进入 Off
        self.light.cleanup()
        self.character.cleanup()

    def _auto_cycle(self, task):
        if self.light.state != "Off":
            self.light.advance()
        return task.again

    def toggle_power(self) -> str:
        self.light.request("Red" if self.light.state == "Off" else "Off")
        return self.light.state

    def try_request(self, state: str, *args) -> bool:
        """request 被拒绝时返回 None（不抛异常）；demand 被拒绝则抛 RequestDenied。"""
        result = self.character.request(state, *args)
        if result is None:
            self.character.denied += 1
        self.state["char_denied"] = self.character.denied
        return result is not None

    def demand_or_error(self, state: str) -> str:
        try:
            self.character.demand(state)
            return "ok"
        except RequestDenied as exc:
            return f"denied: {exc}"

    def _report(self, task):
        self.state["light"] = self.light.state
        self.state["character"] = self.character.state
        return task.cont
