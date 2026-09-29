"""L16 离屏渲染（RTT）与后处理。

两个技巧
--------
1. **Render-To-Texture**：``win.make_texture_buffer(name, w, h)`` 创建离屏缓冲，
   ``base.make_camera(buffer)`` 给它一个相机，渲染结果自动写进 ``buffer.get_texture()``，
   然后这张纹理可以贴到任何物体上（监视器、镜子、传送门）。
2. **全屏后处理**：``FilterManager(win, cam).renderSceneInto(colortex=tex)``
   把主场景渲染到纹理，返回一个全屏 quad；给 quad 挂 shader 即可做灰度/描边/暗角……

CommonFilters（bloom/cartoon/ssao…）是 FilterManager 的高级封装，但 1.10 版本依赖 Cg。
Apple Silicon 上没有 Cg 基础着色器，所以本课自己写 GLSL 1.20 滤镜——原理更透明。
"""

from __future__ import annotations

from direct.filter.FilterManager import FilterManager
from panda3d.core import CardMaker, LVector4, NodePath, Shader, Texture

from ..core import Lesson, capabilities, register
from ..core.procedural import make_cube, make_grid, make_uv_sphere

QUAD_VERT = """#version 120
uniform mat4 p3d_ModelViewProjectionMatrix;
attribute vec4 p3d_Vertex;
attribute vec2 p3d_MultiTexCoord0;
varying vec2 uv;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    uv = p3d_MultiTexCoord0;
}
"""
# 一个着色器里用 mode 分支实现 4 种滤镜：0 原图 1 灰度 2 边缘检测 3 暗角+色差
QUAD_FRAG = """#version 120
uniform sampler2D scene;
uniform float mode;
uniform vec2 texel;
varying vec2 uv;
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
void main() {
    vec3 c = texture2D(scene, uv).rgb;
    if (mode < 0.5) {
        gl_FragColor = vec4(c, 1.0);
    } else if (mode < 1.5) {
        gl_FragColor = vec4(vec3(luma(c)), 1.0);
    } else if (mode < 2.5) {
        // Sobel 边缘检测
        float tl = luma(texture2D(scene, uv + texel * vec2(-1, 1)).rgb);
        float t  = luma(texture2D(scene, uv + texel * vec2( 0, 1)).rgb);
        float tr = luma(texture2D(scene, uv + texel * vec2( 1, 1)).rgb);
        float l  = luma(texture2D(scene, uv + texel * vec2(-1, 0)).rgb);
        float r  = luma(texture2D(scene, uv + texel * vec2( 1, 0)).rgb);
        float bl = luma(texture2D(scene, uv + texel * vec2(-1,-1)).rgb);
        float b  = luma(texture2D(scene, uv + texel * vec2( 0,-1)).rgb);
        float br = luma(texture2D(scene, uv + texel * vec2( 1,-1)).rgb);
        float gx = -tl - 2.0*l - bl + tr + 2.0*r + br;
        float gy = -tl - 2.0*t - tr + bl + 2.0*b + br;
        float e = clamp(length(vec2(gx, gy)) * 2.0, 0.0, 1.0);
        gl_FragColor = vec4(mix(c, vec3(0.05), e), 1.0);
    } else {
        vec2 d = uv - 0.5;
        float vig = smoothstep(0.8, 0.2, length(d));
        float rr = texture2D(scene, uv + d * 0.01).r;
        float bb = texture2D(scene, uv - d * 0.01).b;
        gl_FragColor = vec4(vec3(rr, c.g, bb) * vig, 1.0);
    }
}
"""
MODES = ["none", "grayscale", "sobel-edges", "vignette+chromatic"]


@register
class PostProcessLesson(Lesson):
    key = "postprocess"
    order = 16
    title = "渲染到纹理与后处理"
    title_en = "Render-To-Texture & Post FX"
    summary = "make_texture_buffer + make_camera 监视器、FilterManager 全屏 GLSL 滤镜（灰度/Sobel/暗角）"
    apis = (
        "GraphicsOutput.make_texture_buffer", "GraphicsOutput.get_texture", "GraphicsOutput.set_clear_color",
        "ShowBase.make_camera", "GraphicsEngine.remove_window", "FilterManager",
        "FilterManager.renderSceneInto", "FilterManager.cleanup", "Texture", "Shader.make",
        "CardMaker", "direct.filter.CommonFilters (Cg 环境)",
    )
    controls = ("SPACE 切换滤镜",)

    def setup(self) -> None:
        self.place_camera((0, -14, 5), (0, 0, 1.5))
        caps = capabilities.get(self.base)
        self.root.attach_new_node(make_grid(12).node())
        for i in range(5):
            s = make_uv_sphere(0.7, color=(0.3 + i * 0.15, 0.8 - i * 0.1, 0.4 + i * 0.1, 1))
            s.reparent_to(self.root)
            s.set_pos(-4 + i * 2, 2, 0.7)
        self.buffer = None
        self.manager: FilterManager | None = None
        self.quad: NodePath | None = None
        self.mode = 2  # 默认 Sobel 描边，进课即可看到效果
        if not caps.has_window:
            self.status("无窗口：跳过 RTT 与后处理（需要 GSG）")
            self.state["skipped"] = True
            return
        self._build_monitor()
        if caps.glsl:
            self._build_filter()
        self.accept("space", self.cycle_filter)
        self.add_task(self._spin, "spin")
        self.status("中间屏幕 = RTT 监视器；SPACE 切换全屏滤镜")

    def teardown(self) -> None:
        if self.manager is not None:
            self.manager.cleanup()  # 恢复主相机直接渲染到窗口
            self.manager = None
        if self.buffer is not None:
            # make_camera 会把相机登记进 base.camList，移除缓冲前一并注销
            if self.rtt_cam in self.base.camList:
                self.base.camList.remove(self.rtt_cam)
            self.rtt_cam.remove_node()
            self.base.graphicsEngine.remove_window(self.buffer)
            self.buffer = None

    # ------------------------------------------------------------ RTT
    def _build_monitor(self) -> None:
        """独立场景 + 独立相机 → 渲染到 256×256 的纹理 → 贴到“屏幕”上。"""
        self.buffer = self.base.win.make_texture_buffer("monitor-buffer", 256, 256)
        self.buffer.set_sort(-100)  # 先于主窗口渲染
        self.buffer.set_clear_color(LVector4(0.1, 0.05, 0.2, 1))
        self.rtt_scene = NodePath("rtt-scene")  # 游离场景图，只给 RTT 相机看
        self.rtt_cube = make_cube(1.5)
        self.rtt_cube.reparent_to(self.rtt_scene)
        self.rtt_cam = rtt_cam = self.base.make_camera(self.buffer)
        rtt_cam.reparent_to(self.rtt_scene)
        rtt_cam.set_pos(0, -5, 1.5)
        rtt_cam.look_at(0, 0, 0)
        cm = CardMaker("monitor")
        cm.set_frame(-2, 2, -1.5, 1.5)
        self.monitor = self.root.attach_new_node(cm.generate())
        self.monitor.set_pos(0, 5, 2.5)
        self.monitor.set_texture(self.buffer.get_texture())
        self.state["rtt_size"] = (self.buffer.get_x_size(), self.buffer.get_y_size())

    # ------------------------------------------------------------ 后处理
    def _build_filter(self) -> None:
        self.manager = FilterManager(self.base.win, self.base.cam)
        self.scene_tex = Texture("scene")
        self.quad = self.manager.renderSceneInto(colortex=self.scene_tex)
        shader = Shader.make(Shader.SL_GLSL, vertex=QUAD_VERT, fragment=QUAD_FRAG)
        self.quad.set_shader(shader)
        self.quad.set_shader_input("scene", self.scene_tex)
        self.quad.set_shader_input("mode", float(self.mode))
        w, h = self.base.win.get_x_size(), self.base.win.get_y_size()
        self.quad.set_shader_input("texel", (1.0 / max(w, 1), 1.0 / max(h, 1)))
        self.state["filter"] = MODES[self.mode]

    def cycle_filter(self) -> str:
        self.mode = (self.mode + 1) % len(MODES)
        if self.quad is not None:
            self.quad.set_shader_input("mode", float(self.mode))
        self.state["filter"] = MODES[self.mode]
        self.status(f"滤镜: {MODES[self.mode]}")
        return MODES[self.mode]

    def set_filter(self, index: int) -> str:
        self.mode = (index - 1) % len(MODES)
        return self.cycle_filter()

    def _spin(self, task):
        self.rtt_cube.set_hpr(task.time * 50, task.time * 30, 0)
        return task.cont
