"""L04 光照与材质。

Panda3D 的灯本身是场景图节点：
  1. 创建 ``XxxLight`` 节点并挂到场景图（位置/朝向由 NodePath 决定）
  2. 在要被照亮的子树上 ``set_light(light_np)``（光照作用范围 = 这棵子树）
这种“灯的位置”和“灯的作用范围”分离的设计非常灵活。

四种灯
------
* AmbientLight      环境光，无方向
* DirectionalLight  平行光（太阳），只看朝向
* PointLight        点光源，有位置和衰减 (constant, linear, quadratic)
* Spotlight         聚光灯，需要一个 Lens 定义锥体

``Material`` 决定表面如何响应光：ambient / diffuse / specular / shininess / emission。
``set_shader_auto()`` 启用 ShaderGenerator：逐像素光照 + 阴影 + 法线贴图。
"""

from __future__ import annotations

import math

from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    LVector4,
    Material,
    PerspectiveLens,
    PointLight,
    Spotlight,
)

from ..core import Lesson, register
from ..core import capabilities
from ..core.procedural import make_cube, make_plane, make_uv_sphere


@register
class LightingLesson(Lesson):
    key = "lighting"
    order = 4
    title = "光照与材质"
    title_en = "Lights & Materials"
    summary = "四种灯、衰减、聚光锥、Material、ShaderGenerator、阴影"
    apis = (
        "AmbientLight", "DirectionalLight", "PointLight", "Spotlight", "PerspectiveLens",
        "PointLight.set_attenuation", "Spotlight.set_exponent", "LightLensNode.set_shadow_caster",
        "NodePath.set_light", "NodePath.clear_light", "NodePath.set_light_off",
        "Material", "Material.set_shininess", "Material.set_emission", "NodePath.set_material",
        "NodePath.set_shader_auto", "Light.set_color", "loader.load_model(models/misc/*light)",
    )
    controls = ("1 环境光", "2 平行光", "3 点光", "4 聚光灯 开/关")

    def setup(self) -> None:
        self.place_camera((0, -20, 10), (0, 0, 1))
        caps = capabilities.get(self.base)

        # 场景：地面 + 若干不同材质的物体
        ground = make_plane(24, color=(0.8, 0.8, 0.8, 1))
        ground.reparent_to(self.root)
        self.objects = []
        for i, (shiny, color) in enumerate([(5, (0.9, 0.2, 0.2, 1)), (40, (0.2, 0.9, 0.3, 1)), (120, (0.3, 0.4, 1, 1))]):
            s = make_uv_sphere(1.2, 24, 32)
            s.reparent_to(self.root)
            s.set_pos(-4 + i * 4, 0, 1.2)
            s.set_material(self.make_material(color, shiny), 1)  # priority=1 覆盖模型自带材质
            self.objects.append(s)
        cube = make_cube(1.5)
        cube.reparent_to(self.root)
        cube.set_pos(0, 4, 0.75)
        glow = Material("glow")
        glow.set_emission((0.6, 0.4, 0.0, 1))  # 自发光：不受灯影响也有颜色
        cube.set_material(glow, 1)

        # ---- 1) 环境光
        amb = AmbientLight("ambient")
        amb.set_color((0.15, 0.15, 0.2, 1))
        self.ambient = self.root.attach_new_node(amb)

        # ---- 2) 平行光（太阳）——只有朝向有意义
        sun = DirectionalLight("sun")
        sun.set_color((0.7, 0.7, 0.65, 1))
        self.sun = self.root.attach_new_node(sun)
        self.sun.set_hpr(30, -50, 0)

        # ---- 3) 点光源 + 衰减 + 可视化灯泡模型（自身不受光照影响）
        pl = PointLight("point")
        pl.set_color((1.0, 0.5, 0.2, 1))
        pl.set_attenuation((1, 0, 0.02))  # 1/(c + l*d + q*d²)
        self.point = self.root.attach_new_node(pl)
        bulb = self.base.loader.load_model("models/misc/Pointlight")
        if not bulb.is_empty():
            bulb.reparent_to(self.point)
            bulb.set_scale(0.3)
            bulb.set_light_off(1)

        # ---- 4) 聚光灯：Lens 决定锥角
        sp = Spotlight("spot")
        sp.set_color((0.2, 0.6, 1.0, 1))
        lens = PerspectiveLens()
        lens.set_fov(35)
        lens.set_near_far(1, 40)
        sp.set_lens(lens)
        sp.set_exponent(20)  # 光斑边缘柔和程度
        self.spot = self.root.attach_new_node(sp)
        self.spot.set_pos(8, -8, 10)
        self.spot.look_at(0, 0, 0)

        # ShaderGenerator：需要 GLSL；阴影只有平行/聚光这类 LensNode 灯支持
        self.shader_auto = caps.glsl
        if self.shader_auto:
            self.root.set_shader_auto()
            sun.set_shadow_caster(True, 1024, 1024)
            sun.get_lens().set_film_size(30, 30)
            sun.get_lens().set_near_far(-30, 30)
        self.state["shader_auto"] = self.shader_auto

        self.lights = {"1": self.ambient, "2": self.sun, "3": self.point, "4": self.spot}
        self.enabled = {k: False for k in self.lights}
        for k in self.lights:
            self.toggle(k)
            self.accept(k, self.toggle, [k])
        self.add_task(self._orbit_point, "orbit-point")
        self.status("数字键 1-4 开关灯；橙色点光在绕圈")

    # ------------------------------------------------------------ API 演示
    @staticmethod
    def make_material(color, shininess: float) -> Material:
        m = Material(f"mat-{shininess}")
        m.set_ambient(color)
        m.set_diffuse(color)
        m.set_specular((1, 1, 1, 1))
        m.set_shininess(shininess)  # 越大高光越集中
        return m

    def toggle(self, key: str) -> bool:
        light_np = self.lights[key]
        on = not self.enabled[key]
        if on:
            self.root.set_light(light_np)
        else:
            self.root.clear_light(light_np)
        self.enabled[key] = on
        self.state["lights_on"] = [k for k, v in self.enabled.items() if v]
        return on

    def _orbit_point(self, task):
        t = task.time
        self.point.set_pos(math.cos(t) * 6, math.sin(t) * 6, 3)
        return task.cont

    def light_count(self) -> int:
        """查询 LightAttrib：子树上实际生效的灯数量。"""
        from panda3d.core import LightAttrib

        attrib = self.root.get_attrib(LightAttrib)
        return 0 if attrib is None else attrib.get_num_on_lights()

    @staticmethod
    def color_of(light_np) -> LVector4:
        return light_np.node().get_color()
