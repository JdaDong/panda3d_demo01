"""HUD：左上角课程信息、左下角状态栏、右下角全局快捷键。

OnscreenText 挂在 a2d* 锚点下，窗口缩放时自动贴边。
``mayChange=True`` 表示文本会频繁修改（否则每次 setText 都会重建并 flatten）。
"""

from __future__ import annotations

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode

GLOBAL_KEYS_ZH = "N/P 下/上一课 · F5 重载 · H 帮助 · 方向键/滚轮 转相机 · F12 截图 · ESC 退出"
GLOBAL_KEYS_EN = "N/P next/prev · F5 reload · H help · arrows/wheel orbit · F12 shot · ESC quit"


class Hud:
    def __init__(self, base, font, cjk: bool) -> None:
        self.base = base
        self.cjk = cjk
        common = {"font": font, "mayChange": True, "shadow": (0, 0, 0, 0.8)}
        self.title = OnscreenText(parent=base.a2dTopLeft, pos=(0.05, -0.09), scale=0.06, fg=(1, 0.9, 0.5, 1),
                                  align=TextNode.A_left, **common)
        self.body = OnscreenText(parent=base.a2dTopLeft, pos=(0.05, -0.16), scale=0.038, fg=(0.9, 0.9, 0.95, 1),
                                 align=TextNode.A_left, wordwrap=40, **common)
        self.status = OnscreenText(parent=base.a2dBottomLeft, pos=(0.05, 0.06), scale=0.042, fg=(0.6, 1, 0.7, 1),
                                   align=TextNode.A_left, **common)
        self.keys = OnscreenText(parent=base.a2dBottomRight, pos=(-0.05, 0.06), scale=0.034, fg=(0.8, 0.8, 0.85, 1),
                                 align=TextNode.A_right, text=GLOBAL_KEYS_ZH if cjk else GLOBAL_KEYS_EN, **common)
        self.visible = True

    def show_lesson(self, index: int, total: int, lesson) -> None:
        title = lesson.title if self.cjk else lesson.title_en
        self.title.setText(f"[{index + 1:02d}/{total}] {title}")
        lines = [lesson.summary if self.cjk else lesson.key]
        if self.cjk and lesson.controls:
            lines.append("按键: " + " | ".join(lesson.controls))
        self.body.setText("\n".join(lines))
        self.update_status(lesson)

    def update_status(self, lesson) -> None:
        text = str(lesson.state.get("status", ""))
        if not self.cjk:
            text = text.encode("ascii", "ignore").decode()
        self.status.setText(text)

    def toggle(self) -> None:
        self.visible = not self.visible
        for t in (self.title, self.body, self.status, self.keys):
            t.show() if self.visible else t.hide()

    def destroy(self) -> None:
        for t in (self.title, self.body, self.status, self.keys):
            t.destroy()
