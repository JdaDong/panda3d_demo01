"""L13 音频：AudioManager、AudioSound、3D 定位音效、SoundInterval。

ShowBase 默认创建：
* ``base.sfxManagerList[0]``  音效管理器（loader.load_sfx 用它）
* ``base.musicManager``       音乐管理器（loader.load_music 用它，通常只放一首）
后端由 PRC ``audio-library-name`` 决定：p3openal_audio / p3fmod_audio / null。
null 后端返回 NullAudioSound —— 所有 API 可调用但不出声，便于 CI。

Audio3DManager：把声音“挂”到 NodePath 上，根据与 listener（相机）的距离/速度
自动计算音量衰减与多普勒效应。
"""

from __future__ import annotations

import math

from direct.interval.IntervalGlobal import Func, Sequence, SoundInterval, Wait
from direct.showbase.Audio3DManager import Audio3DManager
from panda3d.core import AudioSound

from ..core import Lesson, register
from ..core.paths import cache_dir, panda_str
from ..core.procedural import make_cube, make_grid, make_uv_sphere, write_tone_wav


@register
class AudioLesson(Lesson):
    key = "audio"
    order = 13
    title = "音频与 3D 音效"
    title_en = "Audio & 3D Sound"
    summary = "load_sfx/load_music、音量/音调/循环、Audio3DManager 定位与多普勒、SoundInterval"
    apis = (
        "Loader.load_sfx", "Loader.load_music", "AudioSound.play/stop", "AudioSound.set_volume",
        "AudioSound.set_play_rate", "AudioSound.set_loop", "AudioSound.status", "AudioSound.length",
        "AudioManager.set_volume", "AudioManager.set_active", "Audio3DManager",
        "Audio3DManager.attachSoundToObject", "Audio3DManager.setDropOffFactor",
        "Audio3DManager.setSoundVelocityAuto", "SoundInterval", "base.sfxManagerList", "base.musicManager",
    )
    controls = ("1 播放提示音", "2 升调播放", "M 静音/取消", "SPACE 播放旋律(SoundInterval)")

    def setup(self) -> None:
        self.place_camera((0, -18, 8))
        self.root.attach_new_node(make_grid(16).node())
        listener = make_cube(0.6, color=(1, 1, 1, 1))
        listener.reparent_to(self.root)
        listener.set_z(0.3)

        d = cache_dir() / "audio"
        self.files = {
            "beep": write_tone_wav(d / "beep.wav", (880.0,), 0.15),
            "chirp": write_tone_wav(d / "chirp.wav", (440, 550, 660, 880), 0.5),
            "hum": write_tone_wav(d / "hum.wav", (110.0,), 1.0, volume=0.25),
            "note_c": write_tone_wav(d / "c.wav", (523.25,), 0.25),
            "note_e": write_tone_wav(d / "e.wav", (659.25,), 0.25),
            "note_g": write_tone_wav(d / "g.wav", (783.99,), 0.25),
        }
        loader = self.base.loader
        self.beep = loader.load_sfx(panda_str(self.files["beep"]))
        self.chirp = loader.load_sfx(panda_str(self.files["chirp"]))
        self.music = loader.load_music(panda_str(self.files["hum"]))
        self.music.set_loop(True)
        self.music.set_volume(0.3)
        self.music.play()
        self.on_cleanup(self.music.stop)

        # 3D 音效：listener 绑定到相机（无头模式下用 lesson 根）
        listener_np = self.base.camera if getattr(self.base, "camera", None) is not None else self.root
        self.audio3d = Audio3DManager(self.base.sfxManagerList[0], listener_np)
        self.audio3d.setDropOffFactor(0.5)
        self.speaker = make_uv_sphere(0.5, color=(1, 0.5, 0.2, 1))
        self.speaker.reparent_to(self.root)
        self.pos_sound = self.audio3d.loadSfx(panda_str(self.files["beep"]))
        self.audio3d.attachSoundToObject(self.pos_sound, self.speaker)
        self.audio3d.setSoundVelocityAuto(self.pos_sound)  # 根据位移自动算速度 → 多普勒
        self.audio3d.setSoundMinDistance(self.pos_sound, 2)
        self.on_cleanup(self._cleanup_3d)

        notes = [loader.load_sfx(panda_str(self.files[k])) for k in ("note_c", "note_e", "note_g")]
        self.melody = self.track(Sequence(
            *[SoundInterval(n, duration=0.25) for n in notes],
            Wait(0.1),
            Func(self._note_done),
            name="melody",
        ))
        self.melody_count = 0
        self.muted = False

        self.accept("1", self.play_beep)
        self.accept("2", self.play_chirp_fast)
        self.accept("m", self.toggle_mute)
        self.accept("space", self.melody.start)
        self.add_task(self._orbit, "orbit")
        self.add_task(self._ping, "ping", delay=1.0)
        self.status(f"音频后端: {type(self.base.sfxManagerList[0]).__name__}；橙球每秒发声")

    # ------------------------------------------------------------ 行为
    def play_beep(self) -> AudioSound:
        self.beep.set_volume(0.8)
        self.beep.set_play_rate(1.0)
        self.beep.play()
        self.state["last"] = "beep"
        return self.beep

    def play_chirp_fast(self) -> AudioSound:
        self.chirp.set_play_rate(1.5)  # 播放速率 >1 → 音调升高
        self.chirp.play()
        self.state["last"] = "chirp x1.5"
        return self.chirp

    def toggle_mute(self) -> bool:
        """AudioManager 级别的总音量 / 激活开关。"""
        self.muted = not self.muted
        for mgr in self.base.sfxManagerList:
            mgr.set_volume(0.0 if self.muted else 1.0)
        self.base.musicManager.set_active(not self.muted)
        self.state["muted"] = self.muted
        return self.muted

    def _note_done(self) -> None:
        self.melody_count += 1
        self.state["melody_played"] = self.melody_count

    def _orbit(self, task):
        t = task.time
        # 只需移动节点；Audio3DManager 自带的 update 任务每帧同步声源/听者位置
        self.speaker.set_pos(math.cos(t) * 7, math.sin(t) * 7, 1)
        return task.cont

    def _ping(self, task):
        self.pos_sound.play()
        self.state["pos_sound_status"] = self.status_name(self.pos_sound)
        return task.again

    def _cleanup_3d(self) -> None:
        self.audio3d.detachSound(self.pos_sound)
        self.audio3d.disable()

    @staticmethod
    def status_name(sound: AudioSound) -> str:
        return {AudioSound.READY: "READY", AudioSound.PLAYING: "PLAYING", AudioSound.BAD: "BAD"}.get(sound.status(), "?")

    @staticmethod
    def sound_length(sound: AudioSound) -> float:
        return sound.length()
