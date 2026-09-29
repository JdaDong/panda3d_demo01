"""L12 DirectGUI 与文本。

2D 场景图
---------
* ``render2d``：坐标 x,y ∈ [-1, 1]，会随窗口宽高比拉伸
* ``aspect2d``：x ∈ [-aspect, aspect]，y ∈ [-1, 1]，**不变形**（GUI 默认父节点）
* ``base.a2dTopLeft / a2dBottomRight ...``：贴角锚点，窗口缩放时自动跟随

DirectGUI 控件都是 NodePath 子类，构造参数统一用关键字（``text=``、``scale=``、
``command=``、``frameColor=`` …），构造后可以 ``widget["text"] = "..."`` 修改属性。

文本
----
* ``OnscreenText``：2D 文本便捷类
* ``TextNode``：真正的文本节点，可以放进 3D 场景（set_align / set_shadow / set_card_color…）
"""

from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import (
    DirectButton,
    DirectCheckButton,
    DirectEntry,
    DirectFrame,
    DirectLabel,
    DirectOptionMenu,
    DirectRadioButton,
    DirectScrolledList,
    DirectSlider,
    DirectWaitBar,
)
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode, TransparencyAttrib

from ..core import Lesson, register
from ..core.procedural import make_cube


@register
class GuiTextLesson(Lesson):
    key = "gui_text"
    order = 12
    title = "DirectGUI 与文本"
    title_en = "DirectGUI & Text"
    summary = "Frame/Label/Button/Check/Radio/Slider/Entry/OptionMenu/ScrolledList/WaitBar、3D TextNode"
    apis = (
        "OnscreenText", "OnscreenImage", "DirectFrame", "DirectLabel", "DirectButton",
        "DirectCheckButton", "DirectRadioButton", "DirectSlider", "DirectEntry", "DirectOptionMenu",
        "DirectScrolledList", "DirectWaitBar", "DirectGuiGlobals (DGG)", "widget['prop'] = value",
        "TextNode", "TextNode.set_align", "TextNode.set_shadow", "TextNode.set_card_color",
        "TextNode.set_frame_color", "base.a2dTopRight", "aspect2d",
    )
    controls = ("用鼠标操作右侧面板",)

    def setup(self) -> None:
        self.place_camera((0, -10, 3), (0, 0, 1))
        font = getattr(self.base, "ui_font", None)
        cjk = getattr(self.base, "ui_font_cjk", False)
        fkw = {"text_font": font} if font is not None else {}

        # 3D 物体 —— 被 GUI 控制
        self.model = make_cube(1.6)
        self.model.reparent_to(self.root)
        self.model.set_z(1)

        # 3D 文本：TextNode 直接进 render
        tn = TextNode("title3d")
        tn.set_text("Panda3D 1.10" if not cjk else "你好，Panda3D")
        if font is not None:
            tn.set_font(font)
        tn.set_align(TextNode.A_center)
        tn.set_text_color(1, 0.9, 0.4, 1)
        tn.set_shadow(0.05, 0.05)
        tn.set_shadow_color(0, 0, 0, 1)
        tn.set_card_color(0.1, 0.1, 0.2, 0.7)
        tn.set_card_as_margin(0.3, 0.3, 0.1, 0.1)
        tn.set_frame_color(1, 0.9, 0.4, 1)
        tn.set_frame_as_margin(0.3, 0.3, 0.1, 0.1)
        self.text3d = self.root.attach_new_node(tn)
        self.text3d.set_pos(0, 0, 2.8)
        self.text3d.set_scale(0.6)
        self.text3d.set_billboard_point_eye()  # 始终面向相机
        self.text3d.set_transparency(TransparencyAttrib.M_alpha)

        # 右上角锚点：子节点坐标相对窗口右上角
        anchor = self.base.a2dTopRight.attach_new_node("gui-anchor")
        self.on_cleanup(anchor.remove_node)
        self.panel = DirectFrame(parent=anchor, frameColor=(0.1, 0.12, 0.16, 0.85),
                                 frameSize=(-0.78, 0, -1.72, 0), pos=(-0.02, 0, -0.02))
        # destroy() 会递归销毁子控件并解除它们的鼠标事件绑定（LIFO：先于 anchor.remove_node 执行）
        self.on_cleanup(self.panel.destroy)
        DirectLabel(parent=self.panel, text="Controls" if not cjk else "控制面板", scale=0.06,
                    pos=(-0.39, 0, -0.09), frameColor=(0, 0, 0, 0), text_fg=(1, 1, 1, 1), **fkw)

        self.clicks = 0
        self.button = DirectButton(parent=self.panel, text="Click me", scale=0.055, pos=(-0.39, 0, -0.2),
                                   command=self.on_click, pad=(0.3, 0.2), **fkw)
        self.check = DirectCheckButton(parent=self.panel, text="wireframe", scale=0.05, pos=(-0.39, 0, -0.32),
                                       command=self.on_check, **fkw)
        self.radio_value = [0]
        self.radios = []
        for i, label in enumerate(["R", "G", "B"]):
            rb = DirectRadioButton(parent=self.panel, text=label, variable=self.radio_value, value=[i],
                                   scale=0.05, pos=(-0.6 + i * 0.2, 0, -0.44), command=self.on_radio, **fkw)
            self.radios.append(rb)
        for rb in self.radios:
            rb.setOthers(self.radios)  # 互斥分组

        self.slider = DirectSlider(parent=self.panel, range=(0, 360), value=0, pageSize=30,
                                   scale=0.3, pos=(-0.39, 0, -0.56), command=self.on_slider)
        self.entry = DirectEntry(parent=self.panel, initialText="type & Enter", scale=0.045, width=14,
                                 pos=(-0.72, 0, -0.68), command=self.on_entry, numLines=1, focus=0,
                                 **({"entryFont": font} if font is not None else {}))  # Entry 用 entryFont
        self.menu = DirectOptionMenu(parent=self.panel, items=["small", "medium", "large"], initialitem=1,
                                     scale=0.05, pos=(-0.6, 0, -0.8), command=self.on_menu, **fkw)
        self.bar = DirectWaitBar(parent=self.panel, range=100, value=0, scale=(0.33, 1, 0.3),
                                 pos=(-0.39, 0, -0.9), barColor=(0.3, 0.8, 0.4, 1))
        items = [DirectLabel(text=f"item {i}", scale=0.045, frameColor=(0, 0, 0, 0), text_fg=(1, 1, 1, 1)) for i in range(12)]
        self.scrolled = DirectScrolledList(
            parent=self.panel, pos=(-0.39, 0, -1.28), items=items, numItemsVisible=4, itemFrame_frameSize=(-0.3, 0.3, -0.2, 0.05),
            itemFrame_pos=(0, 0, 0.1), decButton_text="up", decButton_scale=0.05,
            decButton_pos=(0.34, 0, 0.12), incButton_text="dn", incButton_scale=0.05,
            incButton_pos=(0.34, 0, -0.2), forceHeight=0.06,
        )

        # OnscreenImage：用 panda 自带的笑脸贴图，左下角
        self.image = OnscreenImage(image="maps/smiley.rgb", pos=(-1.1, 0, -0.75), scale=0.12, parent=self.gui_root)
        self.hint = OnscreenText(text="DirectGUI demo", pos=(-1.1, -0.92), scale=0.045, fg=(1, 1, 1, 1),
                                 parent=self.gui_root, font=font, mayChange=True)

        self.add_task(self._tick, "tick")
        self.status("所有控件都在右侧面板；3D 标题是 TextNode + billboard")

    # ------------------------------------------------------------ 回调
    def on_click(self) -> None:
        self.clicks += 1
        self.button["text"] = f"clicked {self.clicks}"  # DirectGUI 属性以 dict 方式读写
        self.state["clicks"] = self.clicks

    def on_check(self, checked) -> None:
        if checked:
            self.model.set_render_mode_wireframe()
        else:
            self.model.clear_render_mode()
        self.state["wireframe"] = bool(checked)

    def on_radio(self) -> None:
        c = [(1, 0.4, 0.4, 1), (0.4, 1, 0.4, 1), (0.4, 0.6, 1, 1)][self.radio_value[0]]
        self.model.set_color_scale(*c)
        self.state["radio"] = self.radio_value[0]

    def on_slider(self) -> None:
        v = self.slider["value"]
        self.model.set_h(v)
        self.state["slider"] = round(v, 1)

    def on_entry(self, text: str) -> None:
        self.text3d.node().set_text(text)
        self.state["entry"] = text

    def on_menu(self, item: str) -> None:
        self.model.set_scale({"small": 0.6, "medium": 1.0, "large": 1.5}[item])
        self.state["menu"] = item

    def _tick(self, task):
        self.bar["value"] = (task.time * 20) % 100
        return task.cont

    @staticmethod
    def gui_state_names() -> tuple[str, str, str]:
        """DirectGUI 状态常量：NORMAL / DISABLED / 以及 frameStyle 常量。"""
        return DGG.NORMAL, DGG.DISABLED, str(DGG.FLAT)
