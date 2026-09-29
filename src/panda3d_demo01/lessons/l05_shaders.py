"""L05 自定义着色器（GLSL）。

两种创建方式
------------
* ``Shader.load(Shader.SL_GLSL, vertex=path, fragment=path)``  从文件加载
* ``Shader.make(Shader.SL_GLSL, vertex=src, fragment=src)``    从字符串创建

参数传递
--------
* ``NodePath.set_shader(shader)``                    绑定到子树（子节点继承）
* ``NodePath.set_shader_input(name, value)``         传 uniform：float/vec/mat/Texture/NodePath
* 内置输入：``p3d_*``（矩阵/顶点属性/纹理/材质/灯光）、``osg_FrameTime`` 等
* 子节点可以用同名 ``set_shader_input`` 覆盖父节点的值（按 priority 与层级合成）
"""

from __future__ import annotations

from panda3d.core import LVector3, LVector4, Shader

from ..config import ASSET_DIR
from ..core import Lesson, capabilities, register
from ..core.paths import to_panda
from ..core.procedural import make_checker_texture, make_uv_sphere

# 字符串形式的着色器：程序化“扫描线全息”效果
HOLO_VERT = """#version 120
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
attribute vec4 p3d_Vertex;
varying vec3 v_world;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    v_world = (p3d_ModelMatrix * p3d_Vertex).xyz;
}
"""
HOLO_FRAG = """#version 120
uniform float osg_FrameTime;
uniform vec4 holo_color;
varying vec3 v_world;
void main() {
    float line = step(0.5, fract(v_world.z * 6.0 - osg_FrameTime * 2.0));
    gl_FragColor = vec4(holo_color.rgb * (0.4 + 0.6 * line), 0.75);
}
"""


@register
class ShaderLesson(Lesson):
    key = "shaders"
    order = 5
    title = "GLSL 着色器"
    title_en = "GLSL Shaders"
    summary = "Shader.load/make、内置 p3d_* 输入、set_shader_input、shader 继承与覆盖"
    apis = (
        "Shader.load", "Shader.make", "Shader.SL_GLSL", "NodePath.set_shader",
        "NodePath.set_shader_input", "NodePath.clear_shader", "NodePath.set_shader_off",
        "p3d_ModelViewProjectionMatrix", "p3d_NormalMatrix", "p3d_ModelMatrix", "osg_FrameTime",
        "p3d_Texture0", "Shader.get_error_flag", "GraphicsStateGuardian.get_supports_glsl",
    )
    controls = ("+ / - 调节振幅", "O 在中间球上 set_shader_off 对比")

    def setup(self) -> None:
        self.place_camera((0, -14, 4), (0, 0, 1))
        caps = capabilities.get(self.base)
        self.amplitude = 0.15
        self.spheres = []
        for i in range(3):
            s = make_uv_sphere(1.3, 32, 48)
            s.reparent_to(self.root)
            s.set_pos(-3.5 + i * 3.5, 0, 1.5)
            self.spheres.append(s)
        tex = make_checker_texture(64, 8, c1=(1, 1, 1), c2=(0.6, 0.6, 0.7))
        for s in self.spheres[:2]:
            s.set_texture(tex)

        self.supported = caps.glsl or not caps.has_window  # 无头模式也允许创建 Shader 对象
        self.wobble = self.load_wobble()
        self.holo = Shader.make(Shader.SL_GLSL, vertex=HOLO_VERT, fragment=HOLO_FRAG)
        self.state["shader_ok"] = self.wobble is not None and self.holo is not None

        # 在父节点上设置 shader + uniform，子节点全部继承
        group = self.root.attach_new_node("wobble-group")
        for s in self.spheres[:2]:
            s.wrt_reparent_to(group)
        if caps.glsl:
            group.set_shader(self.wobble)
            group.set_shader_input("amplitude", self.amplitude)
            group.set_shader_input("tint", LVector4(1.0, 0.85, 0.7, 1))
            group.set_shader_input("light_dir", LVector3(-0.4, 0.6, -0.7))
            # 子节点可以覆盖父节点的 uniform
            self.spheres[1].set_shader_input("tint", LVector4(0.6, 1.0, 0.7, 1))

            holo_np = self.spheres[2]
            holo_np.set_shader(self.holo)
            holo_np.set_shader_input("holo_color", LVector4(0.2, 0.9, 1.0, 1))
            holo_np.set_transparency(True)
            self.status("左/中：文件加载的 wobble toon；右：字符串创建的全息扫描线")
        else:
            self.status("当前 GSG 不支持 GLSL，仅创建 Shader 对象")
        self.group = group
        self.shader_off = False
        self.accept("+", self.change_amplitude, [0.05])
        self.accept("=", self.change_amplitude, [0.05])
        self.accept("-", self.change_amplitude, [-0.05])
        self.accept("o", self.toggle_shader_off)
        self.add_task(self._spin, "spin")

    @staticmethod
    def load_wobble() -> Shader | None:
        shader_dir = ASSET_DIR / "shaders"
        return Shader.load(
            Shader.SL_GLSL,
            vertex=to_panda(shader_dir / "wobble.vert.glsl"),
            fragment=to_panda(shader_dir / "wobble.frag.glsl"),
        )

    def change_amplitude(self, delta: float) -> float:
        self.amplitude = max(0.0, min(0.6, self.amplitude + delta))
        self.group.set_shader_input("amplitude", self.amplitude)
        self.state["amplitude"] = round(self.amplitude, 2)
        return self.amplitude

    def toggle_shader_off(self) -> bool:
        """set_shader_off：在子节点上屏蔽继承来的 shader，回到固定管线。"""
        self.shader_off = not self.shader_off
        if self.shader_off:
            self.spheres[1].set_shader_off(1)
        else:
            self.spheres[1].clear_shader()
        return self.shader_off

    def _spin(self, task):
        for i, s in enumerate(self.spheres):
            s.set_h(task.time * (20 + i * 10))
        return task.cont
