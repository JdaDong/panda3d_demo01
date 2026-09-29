"""框架层 UT：PRC 配置、注册表、程序化资源、能力探测、课程生命周期（无泄漏）。"""

from __future__ import annotations

import wave

import pytest
from direct.showbase.MessengerGlobal import messenger
from panda3d.core import GeomVertexReader

from panda3d_demo01 import config
from panda3d_demo01.core import Lesson, all_lessons, get_lesson, register
from panda3d_demo01.core import capabilities, procedural
from panda3d_demo01.core.paths import cache_dir, panda_str, to_panda

ALL_KEYS = [c.key for c in all_lessons()]


# --------------------------------------------------------------------------- config
class TestConfig:
    def test_prc_text_per_mode(self):
        prc = config.RuntimeConfig(mode=config.RunMode.HEADLESS, width=320, height=200).to_prc()
        assert "window-type none" in prc
        assert "win-size 320 200" in prc
        assert "audio-library-name null" in prc  # 非窗口模式强制静音

    def test_window_mode_uses_openal_unless_muted(self):
        assert "p3openal_audio" in config.RuntimeConfig(mode=config.RunMode.WINDOW).to_prc()
        assert "audio-library-name null" in config.RuntimeConfig(mode=config.RunMode.WINDOW, mute=True).to_prc()

    def test_extra_lines_appended(self):
        prc = config.RuntimeConfig(extra=("sync-video #f",)).to_prc()
        assert prc.strip().endswith("sync-video #f")

    def test_custom_variable_readable_after_apply(self, base):
        # base 夹具已调用 config.apply → 自定义变量生效
        assert config.read_custom_flag() == "你好-Panda3D"
        assert config.is_true("textures-power-2-nonexistent", True) is True

    def test_loaded_pages_contains_runtime_page(self, base):
        assert any("panda3d_demo01-runtime" in n for n in config.list_loaded_pages())


# --------------------------------------------------------------------------- registry
class TestRegistry:
    def test_24_lessons_ordered_unique(self):
        lessons = all_lessons()
        assert len(lessons) == 24
        assert [c.order for c in lessons] == list(range(1, 25))
        assert len(set(ALL_KEYS)) == 24

    def test_every_lesson_documents_apis(self):
        for cls in all_lessons():
            assert cls.apis, cls.key
            assert cls.title and cls.title_en and cls.summary, cls.key

    def test_total_api_coverage_is_large(self):
        assert sum(len(c.apis) for c in all_lessons()) >= 350

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError):
            get_lesson("no-such-lesson")

    def test_register_validation(self):
        class NoKey(Lesson):
            apis = ("x",)

            def setup(self):
                pass

        class NoApis(Lesson):
            key = "tmp-no-apis"

            def setup(self):
                pass

        class Dup(Lesson):
            key = "scene_graph"
            apis = ("x",)

            def setup(self):
                pass

        for cls in (NoKey, NoApis, Dup):
            with pytest.raises(ValueError):
                register(cls)


# --------------------------------------------------------------------------- procedural
class TestProcedural:
    def test_cube_has_24_vertices_12_triangles(self):
        cube = procedural.make_cube(2)
        geom = cube.node().get_geom(0)
        assert geom.get_vertex_data().get_num_rows() == 24
        assert geom.get_primitive(0).get_num_primitives() == 12

    def test_cube_bounds_match_size(self):
        lo, hi = procedural.make_cube(2).get_tight_bounds()
        assert tuple(lo) == pytest.approx((-1, -1, -1))
        assert tuple(hi) == pytest.approx((1, 1, 1))

    def test_sphere_vertices_on_radius(self):
        s = procedural.make_uv_sphere(3.0, 8, 12)
        reader = GeomVertexReader(s.node().get_geom(0).get_vertex_data(), "vertex")
        while not reader.is_at_end():
            assert reader.get_data3().length() == pytest.approx(3.0, abs=1e-4)

    def test_checker_image_alternates(self):
        img = procedural.make_checker_image(16, 2)
        assert img.get_xel(0, 0) != img.get_xel(8, 0)
        assert img.get_xel(0, 0) == img.get_xel(8, 8)

    def test_radial_sprite_alpha_falloff(self):
        tex = procedural.make_radial_sprite(32)
        assert tex.get_x_size() == 32 and tex.get_num_components() == 4

    def test_wav_writer(self, workdir):
        p = procedural.write_tone_wav(workdir / "t.wav", (440, 880), 0.1, rate=8000)
        with wave.open(str(p)) as w:
            assert w.getframerate() == 8000
            assert w.getnframes() == 800

    def test_scene_tree_and_count(self):
        root = procedural.make_cube(1)
        procedural.make_cube(1).reparent_to(root)
        tree = procedural.scene_tree(root)
        assert len(tree) == 2 and tree[1].startswith("  GeomNode")
        assert procedural.count_geom_nodes(root) == 1  # ** 不含自身

    def test_paths_roundtrip(self, workdir):
        assert to_panda(workdir).to_os_specific() == str(workdir)
        assert panda_str(workdir).startswith("/")
        assert cache_dir().exists()


# --------------------------------------------------------------------------- capabilities
def test_capabilities_detect(base):
    caps = capabilities.detect(base)
    assert caps.has_window == (base.win is not None)
    assert isinstance(caps.summary, str)
    if caps.has_window:
        assert caps.max_texture_size >= 1024


# --------------------------------------------------------------------------- lifecycle
@pytest.mark.parametrize("key", ALL_KEYS)
def test_lesson_lifecycle_no_leaks(base, step, key):
    """每一课：start → 跑 10 帧 → stop，然后断言节点/任务/事件全部回收，且可重复启动。"""
    cls = get_lesson(key)
    for round_ in range(2):
        inst = cls(base)
        inst.start()
        assert inst.active
        assert not base.render.find(f"lesson:{key}").is_empty()
        step(10)
        assert isinstance(inst.state.get("status", ""), str)
        inst.stop()
        assert not inst.active
        step(10)  # 让协作式取消的协程任务有机会醒来并退出
        assert base.render.find(f"lesson:{key}").is_empty(), "3D 根节点未移除"
        assert base.aspect2d.find(f"gui:{key}").is_empty(), "GUI 根节点未移除"
        assert base.task_mgr.getTasksMatching(f"{key}:*") == [], "任务未移除"
        assert messenger.getAllAccepting(inst) == [], "事件订阅未解除"
        inst.stop()  # 幂等


def test_start_twice_raises(base):
    inst = get_lesson("math")(base)
    inst.start()
    try:
        with pytest.raises(RuntimeError):
            inst.start()
    finally:
        inst.stop()


def test_failed_setup_is_cleaned(base):
    class Broken(Lesson):
        key = "broken-tmp"
        apis = ("x",)

        def setup(self):
            self.add_task(lambda task: task.cont, "t")
            self.accept("broken-event", lambda: None)
            raise RuntimeError("boom")

        def teardown(self):  # 不应被调用
            raise AssertionError("teardown should be skipped")

    inst = Broken(base)
    with pytest.raises(RuntimeError, match="boom"):
        inst.start()
    assert not inst.active
    assert base.task_mgr.getTasksMatching("broken-tmp:*") == []
    assert messenger.getAllAccepting(inst) == []


# --------------------------------------------------------------------------- fonts / camera rig
def test_ui_font_loads(base):
    from panda3d_demo01.core.fonts import find_cjk_font, load_ui_font

    font, cjk = load_ui_font(base.loader)
    assert font is not None
    assert cjk == (find_cjk_font() is not None)


@pytest.mark.window
def test_orbit_camera_math(base):
    from panda3d.core import LPoint3

    from panda3d_demo01.core.camera_rig import OrbitCamera

    orbit = OrbitCamera(base)
    try:
        orbit.look_from((0, -10, 0), (0, 0, 0))
        assert orbit.distance == pytest.approx(10)
        assert orbit.heading == pytest.approx(0) and orbit.pitch == pytest.approx(0)
        assert tuple(base.camera.get_pos(base.render)) == pytest.approx((0, -10, 0), abs=1e-4)
        orbit.look_from((10, 0, 10), (0, 0, 0))
        assert orbit.pitch == pytest.approx(-45, abs=1e-4)          # 俯视 45°
        assert tuple(orbit.forward) == pytest.approx(tuple((LPoint3(0, 0, 0) - LPoint3(10, 0, 10)).normalized()), abs=1e-4)
        orbit.rotate(0, -200)
        assert orbit.pitch == -89.0                                   # 俯仰角被钳制
        orbit.zoom(1000)
        assert orbit.distance == 500.0
    finally:
        orbit.destroy()
        base.camera.reparent_to(base.render)
        orbit.pivot.remove_node()
