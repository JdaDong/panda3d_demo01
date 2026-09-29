"""L04 光照 / L05 着色器 / L06 相机镜头 / L15 渲染状态 / L16 后处理。"""

from __future__ import annotations

import pytest
from panda3d.core import (
    ClipPlaneAttrib,
    Fog,
    PNMImage,
    RenderModeAttrib,
    Shader,
    ShaderAttrib,
    TransparencyAttrib,
)

from panda3d_demo01.core import capabilities


# --------------------------------------------------------------------------- L04
class TestLighting:
    def test_four_lights_on_then_toggle(self, lesson):
        lt = lesson("lighting")
        assert lt.light_count() == 4
        assert lt.toggle("1") is False
        assert lt.light_count() == 3
        assert lt.state["lights_on"] == ["2", "3", "4"]
        assert lt.toggle("1") is True

    def test_point_light_attenuation_and_orbit(self, lesson, step):
        lt = lesson("lighting")
        assert tuple(lt.point.node().get_attenuation()) == pytest.approx((1, 0, 0.02))
        p0 = lt.point.get_pos()
        step(10)
        assert (lt.point.get_pos() - p0).length() > 0.1

    def test_materials(self, lesson):
        lt = lesson("lighting")
        shininess = [s.get_material().get_shininess() for s in lt.objects]
        assert shininess == [5, 40, 120]

    def test_spotlight_lens(self, lesson):
        lt = lesson("lighting")
        assert lt.spot.node().get_lens().get_fov()[0] == pytest.approx(35)

    def test_shader_auto_matches_caps(self, lesson, base):
        lt = lesson("lighting")
        assert lt.state["shader_auto"] == capabilities.detect(base).glsl


# --------------------------------------------------------------------------- L05
class TestShaders:
    def test_shaders_created(self, lesson):
        sh = lesson("shaders")
        assert sh.state["shader_ok"]
        assert sh.holo.get_language() == Shader.SL_GLSL
        assert sh.wobble.get_language() == Shader.SL_GLSL

    def test_amplitude_clamped(self, lesson):
        sh = lesson("shaders")
        for _ in range(20):
            sh.change_amplitude(0.05)
        assert sh.amplitude == pytest.approx(0.6)
        for _ in range(20):
            sh.change_amplitude(-0.05)
        assert sh.amplitude == 0.0

    @pytest.mark.window
    def test_shader_inheritance_and_override(self, lesson):
        sh = lesson("shaders")
        assert sh.group.get_shader() == sh.wobble
        # 子节点没有自己的 ShaderAttrib，但 net state 继承父节点
        net = sh.spheres[0].get_net_state().get_attrib(ShaderAttrib)
        assert net.get_shader() == sh.wobble
        # 覆盖：spheres[1] 自己持有 tint 输入；spheres[0] 没有（M_invalid=0），完全靠继承
        # 注：传 LVector4 会以 M_numeric(PTA) 存储，get_vector() 只对 M_vector 有效
        assert sh.spheres[1].get_shader_input("tint").get_value_type() != 0
        assert sh.spheres[0].get_shader_input("tint").get_value_type() == 0
        assert sh.toggle_shader_off() is True
        assert sh.spheres[1].get_attrib(ShaderAttrib).auto_shader() is False
        assert sh.toggle_shader_off() is False

    @pytest.mark.window
    def test_shader_renders_without_error(self, lesson, step):
        sh = lesson("shaders")
        step(3)
        assert not sh.wobble.get_error_flag()
        assert not sh.holo.get_error_flag()


# --------------------------------------------------------------------------- L06
@pytest.mark.window
class TestCameraLens:
    def test_projection_center(self, lesson, step):
        cl = lesson("camera_lens")
        step(1)
        sp = cl.project_to_screen(cl.target)
        assert sp is not None
        assert abs(sp.x) < 0.2 and -1 < sp.y < 1  # 目标在画面中部

    def test_extrude_ray(self, lesson):
        cl = lesson("camera_lens")
        near, far = cl.screen_ray(0, 0)
        cam_pos = cl.base.cam.get_pos(cl.base.render)
        assert (far - cam_pos).length() > (near - cam_pos).length()

    def test_fov_clamp_and_restore(self, lesson, base):
        lens = base.cam.node().get_lens()
        original = lens.get_fov()[0]
        cl = lesson("camera_lens")
        assert cl.change_fov(500) == 120
        assert cl.change_fov(-500) == 10
        cl.stop()
        assert lens.get_fov()[0] == pytest.approx(original)

    def test_minimap_region_added_and_removed(self, lesson, base):
        before = base.win.get_num_display_regions()
        cl = lesson("camera_lens")
        assert base.win.get_num_display_regions() == before + 1
        assert cl.minimap_region.get_sort() == 5
        cl.stop()
        assert base.win.get_num_display_regions() == before

    def test_dolly_zoom_keeps_width(self, lesson, step):
        cl = lesson("camera_lens")
        cl.toggle_dolly()
        step(20)
        assert 10 <= cl.state["fov"] <= 120


# --------------------------------------------------------------------------- L15
class TestRenderStates:
    def test_fog_cycle(self, lesson):
        rs = lesson("render_states")
        assert rs.cycle_fog() == "linear"
        assert rs.root.get_fog().get_mode() == Fog.M_linear
        assert rs.cycle_fog() == "exp"
        assert rs.root.get_fog().get_mode() == Fog.M_exponential
        assert rs.cycle_fog() == "off"
        assert not rs.root.has_fog()

    def test_transparency_and_bins(self, lesson):
        rs = lesson("render_states")
        assert rs.net_transparency(rs.glass) == TransparencyAttrib.M_alpha
        assert rs.glass.get_bin_name() == "transparent"
        assert rs.glow.get_bin_name() == "fixed"
        assert rs.glass.get_depth_write() is False

    def test_wireframe_toggle(self, lesson):
        rs = lesson("render_states")
        assert rs.toggle_wireframe() is True
        assert rs.root.get_attrib(RenderModeAttrib).get_mode() == RenderModeAttrib.M_wireframe
        assert rs.toggle_wireframe() is False

    def test_clip_plane(self, lesson):
        rs = lesson("render_states")
        rs.toggle_clip()
        attrib = rs.root.get_attrib(ClipPlaneAttrib)
        assert attrib is not None and attrib.get_num_on_planes() == 1
        rs.toggle_clip()
        assert not rs.root.has_clip_plane(rs.clip_np)

    def test_lod_switch_levels(self, lesson):
        rs = lesson("render_states")
        assert [rs.lod_level_for(d) for d in (5, 20, 100, 500)] == [0, 1, 2, -1]

    def test_compass_effect_locks_rotation(self, lesson, step):
        rs = lesson("render_states")
        step(15)
        assert abs(rs.spinner.get_h()) > 1
        # CompassEffect(P_rot)：子节点相对 render 的朝向不随父节点旋转
        assert rs.compass_child.get_h(rs.base.render) == pytest.approx(0, abs=1e-3)


# --------------------------------------------------------------------------- L16
@pytest.mark.window
class TestPostProcess:
    def test_rtt_buffer_and_filter(self, lesson, step):
        pp = lesson("postprocess")
        assert pp.state["rtt_size"] == (256, 256)
        assert pp.state["filter"] == "sobel-edges"
        step(3)
        assert pp.buffer.get_texture().get_x_size() == 256

    def test_filter_cycle(self, lesson):
        pp = lesson("postprocess")
        assert [pp.cycle_filter() for _ in range(4)] == ["vignette+chromatic", "none", "grayscale", "sobel-edges"]
        assert pp.set_filter(1) == "grayscale"

    def test_grayscale_output_is_gray(self, lesson, step, base, workdir):
        pp = lesson("postprocess")
        pp.set_filter(1)
        step(3)
        shot = workdir / "gray.png"
        from panda3d.core import Filename

        assert base.win.save_screenshot(Filename.from_os_specific(str(shot)))
        img = PNMImage()
        img.read(Filename.from_os_specific(str(shot)))
        # 抽样 3D 区域（避开 HUD）：灰度滤镜下 R≈G≈B
        for x, y in [(img.get_x_size() // 2, img.get_y_size() // 2), (img.get_x_size() // 3, img.get_y_size() * 2 // 3)]:
            r, g, b = img.get_xel(x, y)
            assert abs(r - g) < 0.02 and abs(g - b) < 0.02

    def test_cleanup_restores_windows(self, lesson, base):
        n = base.graphicsEngine.get_num_windows()
        pp = lesson("postprocess")
        assert base.graphicsEngine.get_num_windows() > n
        pp.stop()
        assert base.graphicsEngine.get_num_windows() == n
