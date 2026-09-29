"""L01 场景图 / L02 程序化几何 / L03 纹理 / L20 数学库。"""

from __future__ import annotations

import pytest
from panda3d.core import (
    GeomEnums,
    LPoint3,
    LQuaternion,
    LVector3,
    TexGenAttrib,
    TextureStage,
)

from panda3d_demo01.lessons.l02_procedural_geom import make_custom_format
from panda3d_demo01.lessons.l20_math import MathLesson, compose, nlerp, slerp


# --------------------------------------------------------------------------- L01
class TestSceneGraph:
    def test_tag_search(self, lesson):
        sg = lesson("scene_graph")
        assert sg.find_bodies("planet") == ["earth"]
        assert sg.find_bodies("moon") == ["moon"]
        assert sg.find_bodies("star") == ["sun"]

    def test_python_tag(self, lesson):
        sg = lesson("scene_graph")
        assert sg.earth.get_python_tag("meta")["moons"] == 1

    def test_hierarchy_propagates_transform(self, lesson, step):
        sg = lesson("scene_graph")
        before = sg.moon.get_pos(sg.base.render)
        step(15)  # 0.5 秒
        after = sg.moon.get_pos(sg.base.render)
        assert (after - before).length() > 0.5
        # 局部坐标没变：只是父节点在转
        assert sg.moon.get_pos() == LPoint3(2, 0, 0)
        # 太阳坐标系下月亮到太阳距离 ∈ [8-2, 8+2]
        d = sg.moon_in_sun_space().length()
        assert 6 - 1e-3 <= d <= 10 + 1e-3

    def test_instances_share_node(self, lesson):
        sg = lesson("scene_graph")
        nodes = {inst.node().this for inst in sg.instances}
        assert len(nodes) == 1  # 同一个 PandaNode
        assert sg.instance_template.node().get_num_parents() == 6
        # copy_to 是深拷贝：不同节点
        assert sg.copy.node().this != sg.instance_template.node().this

    def test_hide_and_wrt_reparent(self, lesson):
        sg = lesson("scene_graph")
        sg.toggle_moon()
        assert sg.state["moon_hidden"] is True
        sg.toggle_moon()
        assert sg.state["moon_hidden"] is False
        sg.detach_moon()
        assert sg.state["detach_delta"] == pytest.approx(0, abs=1e-4)
        assert sg.moon.get_parent() == sg.root

    def test_flatten_strong_reduces_geomnodes(self, lesson):
        sg = lesson("scene_graph")
        assert sg.state["geomnodes_before_flatten"] == 64
        assert sg.flatten_grid() < 64

    def test_stash_hides_from_find(self, lesson):
        sg = lesson("scene_graph")
        assert sg.stash_demo() == (0, 1)
        assert not sg.copy.is_stashed()

    def test_free_node(self):
        from panda3d_demo01.lessons.l01_scene_graph import SceneGraphLesson

        np = SceneGraphLesson.make_empty("free")
        assert not np.has_parent() and np.get_name() == "free"


# --------------------------------------------------------------------------- L02
class TestProceduralGeom:
    def test_custom_format_columns(self):
        fmt = make_custom_format()
        arr = fmt.get_array(0)
        assert arr.get_num_columns() == 3
        color = fmt.get_column("color")
        assert color.get_numeric_type() == GeomEnums.NT_uint8
        assert fmt.is_registered()

    def test_wave_mesh_vertex_count_and_update(self, lesson):
        pg = lesson("procedural_geom")
        n = pg.GRID + 1
        assert pg.state["vertex_count"] == n * n
        pg.update_wave(0.0)
        h0 = pg.max_height()
        pg.update_wave(0.7)
        assert pg.max_height() > 0.1
        assert h0 != pg.max_height()

    def test_normals_lines(self, lesson):
        pg = lesson("procedural_geom")
        np = pg.toggle_normals()
        prim = np.node().get_geom(0).get_primitive(0)
        assert prim.get_num_primitives() == pg.state["vertex_count"]  # 每个顶点一条线
        assert pg.toggle_normals().is_empty()

    def test_point_cloud_and_render_mode(self, lesson):
        pg = lesson("procedural_geom")
        assert pg.points.get_render_mode_thickness() == 4
        assert pg.vertex_count(pg.points) == 200

    def test_pause(self, lesson, step):
        pg = lesson("procedural_geom")
        pg.toggle_pause()
        step(1)
        t = pg.state.get("wave_t")
        step(5)
        assert pg.state.get("wave_t") == t


# --------------------------------------------------------------------------- L03
class TestTextures:
    def test_multitexture_stages(self, lesson):
        tx = lesson("textures")
        stages = tx.cube.find_all_texture_stages()
        assert stages.get_num_texture_stages() == 2
        assert tx.cube.get_tex_scale(tx.detail_stage) == (3, 3)

    def test_cycle_modes(self, lesson):
        tx = lesson("textures")
        assert [tx.cycle_mode() for _ in range(3)] == ["add", "decal", "modulate"]
        assert tx.detail_stage.get_mode() == TextureStage.M_modulate

    def test_texgen(self, lesson):
        tx = lesson("textures")
        assert tx.sphere.get_tex_gen(TextureStage.get_default()) == TexGenAttrib.M_eye_sphere_map

    def test_dynamic_ram_image(self, lesson):
        tx = lesson("textures")
        data = tx.update_plasma(1.0)
        assert len(data) == tx.DYN * tx.DYN * 4
        assert tx.dyn_tex.has_ram_image()
        assert tx.update_plasma(2.0) != data

    def test_noise_texture(self):
        from panda3d_demo01.lessons.l03_textures import TextureLesson

        tex = TextureLesson.make_noise_texture(16)
        assert (tex.get_x_size(), tex.get_y_size()) == (16, 16)

    def test_uv_scroll(self, lesson, step):
        tx = lesson("textures")
        step(10)
        assert tx.ground.get_tex_offset(TextureStage.get_default()).length() > 0


# --------------------------------------------------------------------------- L20
class TestMath:
    def test_vector_basics(self):
        v = MathLesson.vector_basics()
        assert v["cross"] == pytest.approx((0, 0, 1))
        assert v["dot"] == 0
        assert v["len"] == 5
        assert v["normalized"] == pytest.approx((0, 0, 1))
        assert v["angle_deg"] == pytest.approx(90)

    def test_point_vs_vector(self):
        p, v = MathLesson.point_vs_vector()
        assert tuple(p) == pytest.approx((10, 1, 0), abs=1e-5)   # 点：旋转 + 平移
        assert tuple(v) == pytest.approx((0, 1, 0), abs=1e-5)    # 向量：只旋转

    def test_inverse_roundtrip(self):
        assert tuple(MathLesson.inverse_roundtrip()) == pytest.approx((5, 6, 7), abs=1e-4)

    def test_transform_compose_order(self):
        assert tuple(MathLesson.compose_transforms()) == pytest.approx((0, 1, 10), abs=1e-5)

    def test_plane_and_box(self):
        dist, hit = MathLesson.plane_queries()
        assert dist == pytest.approx(5)
        assert tuple(hit) == pytest.approx((0, 0, 0), abs=1e-5)
        assert MathLesson.box_contains()

    def test_slerp_endpoints_and_unit(self):
        a, b = LQuaternion(), LQuaternion()
        a.set_hpr(LVector3(0, 0, 0))
        b.set_hpr(LVector3(90, 0, 0))
        assert slerp(a, b, 0).almost_same_direction(a, 1e-4)
        assert slerp(a, b, 1).almost_same_direction(b, 1e-4)
        mid = slerp(a, b, 0.5)
        assert mid.length() == pytest.approx(1)
        assert mid.get_hpr()[0] == pytest.approx(45, abs=1e-3)
        assert nlerp(a, -b, 0.5).get_hpr()[0] == pytest.approx(45, abs=1e-3)  # 最短弧

    def test_compose_matrix(self):
        m = compose((1, 2, 3), (0, 0, 0), (2, 2, 2))
        assert tuple(m.xform_point(LPoint3(1, 1, 1))) == pytest.approx((3, 4, 5))

    def test_lesson_random_points(self, lesson, step):
        ml = lesson("math")
        assert 0 < ml.state["inside_sphere"] < 60
        step(5)
        assert ml.slerp_obj.get_quat().length() == pytest.approx(1, abs=1e-4)
