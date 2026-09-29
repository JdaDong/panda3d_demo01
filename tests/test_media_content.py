"""L12 GUI / L13 音频 / L14 粒子 / L17 Actor / L19 文件与序列化 / L21 地形 / L22 网络。"""

from __future__ import annotations

import time
import wave

import pytest
from panda3d.core import Filename, RenderModeAttrib, VirtualFileSystem

from panda3d_demo01.lessons.l19_files_serialization import MF_MOUNT, RAM_MOUNT, FilesSerializationLesson
from panda3d_demo01.lessons.l21_terrain import HEIGHT, SIZE, make_heightmap
from panda3d_demo01.lessons.l22_networking import EchoNet


# --------------------------------------------------------------------------- L12
class TestGui:
    def test_button_updates_text(self, lesson):
        g = lesson("gui_text")
        g.on_click()
        g.on_click()
        assert g.button["text"] == "clicked 2"

    def test_check_radio_slider_entry_menu(self, lesson):
        g = lesson("gui_text")
        g.on_check(1)
        assert g.model.get_attrib(RenderModeAttrib).get_mode() == RenderModeAttrib.M_wireframe
        g.on_check(0)
        assert not g.model.has_render_mode()
        g.radio_value[0] = 2
        g.on_radio()
        assert g.state["radio"] == 2
        g.slider["value"] = 90
        g.on_slider()
        assert g.model.get_h() == pytest.approx(90)
        g.on_entry("hello")
        assert g.text3d.node().get_text() == "hello"
        g.on_menu("large")
        assert g.model.get_scale().x == pytest.approx(1.5)

    def test_waitbar_advances(self, lesson, step):
        g = lesson("gui_text")
        step(30)
        assert g.bar["value"] > 0

    def test_textnode_configuration(self, lesson):
        g = lesson("gui_text")
        tn = g.text3d.node()
        assert tn.has_shadow() and tn.has_card() and tn.has_frame()

    def test_gui_destroyed_on_stop(self, lesson, base):
        g = lesson("gui_text")
        anchor_children = base.a2dTopRight.get_num_children()
        g.stop()
        assert base.a2dTopRight.get_num_children() == anchor_children - 1


# --------------------------------------------------------------------------- L13
def _is_null(base) -> bool:
    """null 音频后端：所有 setter 都是空操作，getter 恒返回 0 —— 断言数值前要先判断。"""
    return base.sfxManagerList[0].get_type().get_name().startswith("Null")


class TestAudio:
    def test_generated_wavs(self, lesson):
        a = lesson("audio")
        for p in a.files.values():
            with wave.open(str(p)) as w:
                assert w.getnchannels() == 1 and w.getnframes() > 0

    def test_sound_api(self, lesson, base):
        a = lesson("audio")
        s = a.play_beep()
        chirp = a.play_chirp_fast()
        assert isinstance(a.status_name(s), str)
        assert a.state["last"] == "chirp x1.5"
        if not _is_null(base):  # 真实后端才会保存参数
            assert s.get_volume() == pytest.approx(0.8)
            assert chirp.get_play_rate() == pytest.approx(1.5)
            assert a.music.get_loop() is True

    def test_mute_toggle(self, lesson, base):
        a = lesson("audio")
        assert a.toggle_mute() is True
        assert a.state["muted"] is True
        assert base.sfxManagerList[0].get_volume() == 0.0
        assert a.toggle_mute() is False
        if not _is_null(base):
            assert base.sfxManagerList[0].get_volume() == 1.0

    def test_audio3d_attached(self, lesson):
        a = lesson("audio")
        assert a.pos_sound in a.audio3d.getSoundsOnObject(a.speaker)

    def test_melody_interval(self, lesson, step):
        a = lesson("audio")
        assert a.melody.getDuration() == pytest.approx(0.85)
        a.melody.start()
        step(30)
        assert a.state["melody_played"] == 1


# --------------------------------------------------------------------------- L14
class TestParticles:
    def test_particles_spawn(self, lesson, step):
        p = lesson("particles")
        step(30)
        assert p.living_particles() > 50

    def test_ptf_roundtrip(self, lesson, step):
        p = lesson("particles")
        text = p.ptf_path.read_text()
        assert "setPoolSize(600)" in text and "ForceGroup" in text
        fx = p.reload_fire()
        step(20)
        assert fx.getParticlesList()[0].getPoolSize() == 600
        assert p.state["reloaded"] == 1

    def test_soft_stop(self, lesson, step):
        p = lesson("particles")
        step(20)
        assert p.toggle_fountain() is False
        step(90)  # 寿命 ~2.6s 内逐渐消亡
        fountain = p.fountain.getParticlesList()[0]
        assert fountain.getLivingParticles() < 800


# --------------------------------------------------------------------------- L17
class TestActor:
    def test_joints_and_anim(self, lesson):
        a = lesson("actor_animation")
        assert a.state["joints"] > 30
        assert a.panda.getAnimNames() == ["walk"]
        assert a.panda.getNumFrames("walk") == 61

    def test_walk_toggle_and_rate(self, lesson):
        a = lesson("actor_animation")
        assert a.toggle_walk() is False
        assert a.toggle_walk() is True
        assert a.change_rate(1.0) == 2.0
        assert a.panda.getPlayRate("walk") == 2.0

    def test_pose_frame(self, lesson):
        a = lesson("actor_animation")
        assert a.pose_at(10) == 10

    def test_expose_joint_follows_animation(self, lesson, step):
        a = lesson("actor_animation")
        step(2)
        p0 = a.hat.get_pos(a.base.render)
        step(15)
        # exposeJoint 节点的世界坐标随骨骼动画变化（脚在走路中前后摆动）
        assert (a.hat.get_pos(a.base.render) - p0).length() > 1e-3

    def test_control_joint_drives_head(self, lesson, step):
        a = lesson("actor_animation")
        step(10)
        assert a.head is not None and abs(a.head_angle) > 0.1
        assert a.head.get_mat() != a.head_rest       # 程序在驱动骨骼矩阵
        assert a.head.get_mat().get_row3(0).length() > 0  # 非奇异
        assert a.toggle_head() is False
        assert a.head is None

    def test_blend_and_actor_interval(self, lesson, step):
        a = lesson("actor_animation")
        assert a.toggle_blend() == pytest.approx(0.2)
        a.seq.start()
        step(40)  # 30 帧 @30fps = 1s 后 Func 触发
        assert a.state.get("seq_half") == 1


# --------------------------------------------------------------------------- L19
class TestFiles:
    def test_egg_bam_multifile(self, lesson):
        f = lesson("files_serialization")
        assert "<Polygon>" in f.egg_path.read_text()
        assert f.state["bam_written"] and f.bam_path.stat().st_size > 100
        assert f.state["mf_subfiles"] == 2

    def test_vfs_mounts_and_unmount(self, lesson):
        vfs = VirtualFileSystem.get_global_ptr()
        f = lesson("files_serialization")
        assert vfs.exists(Filename(f"{RAM_MOUNT}/pyramid.egg"))
        assert vfs.exists(Filename(f"{MF_MOUNT}/models/pyramid.bam"))
        assert f.vfs_read(f"{RAM_MOUNT}/pyramid.egg").startswith(b"<CoordinateSystem>")
        f.stop()
        assert not vfs.exists(Filename(f"{RAM_MOUNT}/pyramid.egg"))
        assert not vfs.exists(Filename(f"{MF_MOUNT}/models/pyramid.bam"))

    def test_datagram_roundtrip(self):
        blob = FilesSerializationLesson.save_game({"name": "熊猫", "level": 42, "pos": (1.0, 2.5, -3.0)})
        out = FilesSerializationLesson.load_game(blob)
        assert out == {"version": 1, "name": "熊猫", "level": 42, "pos": (1.0, 2.5, -3.0)}

    def test_loaded_models_in_scene(self, lesson):
        f = lesson("files_serialization")
        assert f.root.find_all_matches("**/+GeomNode").get_num_paths() >= 5


# --------------------------------------------------------------------------- L21
class TestTerrain:
    def test_heightmap_shape(self):
        img = make_heightmap(33, seed=1)
        assert (img.get_x_size(), img.get_y_size()) == (33, 33)
        assert img.get_maxval() == 65535
        values = [img.get_gray(x, y) for x in range(0, 33, 4) for y in range(0, 33, 4)]
        assert 0 <= min(values) < max(values) <= 1

    def test_rover_follows_ground(self, lesson, step):
        t = lesson("terrain")
        step(3)
        x, y = t.rover.get_x(), t.rover.get_y()
        assert t.rover.get_z() == pytest.approx(t.ground_z(x, y) + 1.0, abs=1e-4)
        assert 0 <= t.ground_z(SIZE / 2, SIZE / 2) <= HEIGHT

    def test_bruteforce_toggle(self, lesson):
        t = lesson("terrain")
        assert t.toggle_bruteforce() is True
        assert t.terrain.get_bruteforce()


# --------------------------------------------------------------------------- L22
class TestNetworking:
    def test_echo_roundtrip(self):
        net = EchoNet()
        try:
            for seq in range(1, 4):
                assert net.send_ping(seq)
            deadline = time.time() + 5
            while len(net.pongs) < 3 and time.time() < deadline:
                net.pump()
                time.sleep(0.005)
            assert [s for s, _ in net.pongs] == [1, 2, 3]   # TCP 保序
            assert net.pings_received == 3
            assert all(rtt >= 0 for _, rtt in net.pongs)
            assert len(net.server_clients) == 1
        finally:
            net.close()

    def test_datagram_encoding(self):
        from direct.distributed.PyDatagramIterator import PyDatagramIterator

        dg = EchoNet.make_ping(7)
        it = PyDatagramIterator(dg)
        assert it.getUint8() == 1 and it.getUint32() == 7

    def test_lesson_pings(self, lesson, step):
        n = lesson("networking")
        n.burst(5)
        deadline = time.time() + 5
        while n.state.get("pongs", 0) < 5 and time.time() < deadline:
            step(1)
            time.sleep(0.005)
        assert n.state["pongs"] >= 5
