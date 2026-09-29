"""L14 粒子系统（panda3d.physics + direct.particles）。

一个 ParticleEffect 由三件套 + 力场组成::

    ParticleEffect
      ├── Particles (= ParticleSystem)
      │     ├── Factory   产生粒子：寿命、质量、初速度扰动     PointParticleFactory ...
      │     ├── Emitter   从哪/往哪发射：                    SphereVolumeEmitter / DiscEmitter / RingEmitter ...
      │     └── Renderer  怎么画：                           SpriteParticleRenderer / PointParticleRenderer / LineParticleRenderer
      └── ForceGroup      作用力：LinearVectorForce(重力) / LinearNoiseForce(扰动) / LinearCylinderVortexForce(漩涡) / LinearSinkForce ...

使用前必须 ``base.enable_particles()`` —— 它启动 ParticleSystemManager 与 PhysicsManager 的每帧任务。
粒子配置可以保存为 ``.ptf``（其实就是一段 Python 代码）并用 ``loadConfig`` 读回。
"""

from __future__ import annotations

from direct.particles.ForceGroup import ForceGroup
from direct.particles.ParticleEffect import ParticleEffect
from direct.particles.Particles import Particles
from panda3d.core import LPoint3, LVector3, LVector4
from panda3d.physics import (
    BaseParticleEmitter,
    BaseParticleRenderer,
    LinearNoiseForce,
    LinearVectorForce,
    LinearCylinderVortexForce,
    PointParticleRenderer,
)

from ..core import Lesson, register
from ..core.paths import cache_dir, to_panda
from ..core.procedural import make_grid, make_radial_sprite


@register
class ParticleLesson(Lesson):
    key = "particles"
    order = 14
    title = "粒子系统"
    title_en = "Particle Systems"
    summary = "ParticleEffect/Particles、Factory/Emitter/Renderer、ForceGroup、颜色插值、.ptf 存取"
    apis = (
        "ShowBase.enable_particles", "ParticleEffect", "ParticleEffect.start/cleanup", "Particles",
        "Particles.setFactory/setRenderer/setEmitter", "PointParticleFactory", "SpriteParticleRenderer",
        "PointParticleRenderer", "SphereVolumeEmitter", "DiscEmitter", "BaseParticleEmitter.ETRADIATE",
        "ColorInterpolationManager.addLinear", "ForceGroup", "LinearVectorForce", "LinearNoiseForce",
        "LinearCylinderVortexForce", "ParticleEffect.saveConfig", "ParticleEffect.loadConfig",
    )
    controls = ("SPACE 暂停/恢复喷泉", "R 从 .ptf 重载火焰")

    def setup(self) -> None:
        self.place_camera((0, -22, 8), (0, 0, 3))
        self.root.attach_new_node(make_grid(16).node())
        self.base.enable_particles()
        self.on_cleanup(self.base.disable_particles)
        self.sprite = make_radial_sprite(64)

        self.fountain = self.make_fountain()
        self.fountain.start(parent=self.root, renderParent=self.root)
        self.fountain.set_pos(-4, 0, 0)

        self.fire = self.make_fire()
        self.fire.start(parent=self.root, renderParent=self.root)
        self.fire.set_pos(4, 0, 0)

        self.ptf_path = cache_dir() / "fire.ptf"
        self.fire.saveConfig(to_panda(self.ptf_path))  # 把整套参数写成 .ptf
        self.running = True
        self.accept("space", self.toggle_fountain)
        self.accept("r", self.reload_fire)
        self.status(f"左：Sprite 喷泉+重力+噪声；右：点精灵火焰+漩涡力；ptf → {self.ptf_path.name}")

    def teardown(self) -> None:
        for fx in (self.fountain, self.fire):
            fx.cleanup()

    # ------------------------------------------------------------ 构建
    def make_fountain(self) -> ParticleEffect:
        p = Particles("fountain")
        p.setFactory("PointParticleFactory")
        p.setRenderer("SpriteParticleRenderer")
        p.setEmitter("DiscEmitter")
        p.setPoolSize(800)          # 同时存在的最大粒子数
        p.setBirthRate(0.02)        # 每 0.02s 出生一批
        p.setLitterSize(8)          # 每批 8 个
        p.setLitterSpread(2)
        p.setLocalVelocityFlag(True)
        p.setSystemGrowsOlderFlag(False)  # 系统本身永生

        p.factory.setLifespanBase(2.2)
        p.factory.setLifespanSpread(0.4)
        p.factory.setMassBase(1.0)
        p.factory.setTerminalVelocityBase(400)

        r = p.renderer
        # 第二个参数 texels_per_unit：精灵基础尺寸 = 纹理像素 / texels_per_unit（64/128 = 0.5 单位）
        # 坑：默认值 1.0 会让 64px 贴图变成 64 单位大的精灵，满屏一片。
        r.setTexture(self.sprite, 128)
        r.setAlphaMode(BaseParticleRenderer.PRALPHAOUT)  # 随寿命淡出
        r.setUserAlpha(1.0)
        r.setXScaleFlag(True)
        r.setYScaleFlag(True)
        r.setInitialXScale(0.3)
        r.setFinalXScale(0.9)
        r.setInitialYScale(0.3)
        r.setFinalYScale(0.9)
        r.setColor(LVector4(0.4, 0.7, 1.0, 1))
        cim = r.getColorInterpolationManager()
        cim.addLinear(0.0, 1.0, LVector4(0.5, 0.8, 1, 1), LVector4(0.1, 0.2, 0.9, 0.2), True)

        e = p.emitter
        e.setEmissionType(BaseParticleEmitter.ETEXPLICIT)
        e.setExplicitLaunchVector(LVector3(0, 0, 1))
        e.setAmplitude(1.0)
        e.setAmplitudeSpread(0.2)
        e.setOffsetForce(LVector3(0, 0, 9))  # 发射初速度
        e.setRadius(0.3)

        fg = ForceGroup("fountain-forces")
        fg.addForce(LinearVectorForce(LVector3(0, 0, -6.0), 1.0, False))  # 重力
        noise = LinearNoiseForce(0.6, False)
        fg.addForce(noise)

        fx = ParticleEffect("fountain-fx")
        fx.addParticles(p)
        fx.addForceGroup(fg)
        return fx

    def make_fire(self) -> ParticleEffect:
        p = Particles("fire")
        p.setFactory("PointParticleFactory")
        p.setRenderer("PointParticleRenderer")
        p.setEmitter("SphereVolumeEmitter")
        p.setPoolSize(600)
        p.setBirthRate(0.01)
        p.setLitterSize(6)
        p.factory.setLifespanBase(1.2)
        p.factory.setLifespanSpread(0.3)
        r = p.renderer
        r.setPointSize(6)
        r.setStartColor(LVector4(1.0, 0.8, 0.2, 1))
        r.setEndColor(LVector4(0.9, 0.1, 0.0, 0.0))
        r.setBlendType(1)  # PP_BLEND_LIFE：按寿命在 start/end 颜色间插值
        r.setAlphaMode(BaseParticleRenderer.PRALPHAOUT)
        e = p.emitter
        e.setEmissionType(BaseParticleEmitter.ETRADIATE)  # 从中心向外辐射
        e.setRadiateOrigin(LPoint3(0, 0, -0.5))
        e.setAmplitude(0.8)
        e.setOffsetForce(LVector3(0, 0, 2.5))
        e.setRadius(0.6)
        fg = ForceGroup("fire-forces")
        vortex = LinearCylinderVortexForce(1.0, 2.0, 1.0, 2.0, False)  # 半径, 长度, 系数, 振幅, 是否与质量相关
        fg.addForce(vortex)
        fx = ParticleEffect("fire-fx")
        fx.addParticles(p)
        fx.addForceGroup(fg)
        return fx

    # ------------------------------------------------------------ 行为
    def toggle_fountain(self) -> bool:
        self.running = not self.running
        if self.running:
            self.fountain.softStart()
        else:
            self.fountain.softStop()  # 不再生新粒子，已有粒子自然消亡
        self.state["fountain_running"] = self.running
        return self.running

    def reload_fire(self) -> ParticleEffect:
        """从 .ptf 文件还原：loadConfig 会清空并按文件重建 Particles/ForceGroup。"""
        pos = self.fire.get_pos()
        self.fire.cleanup()
        self.fire = ParticleEffect("fire-fx-reloaded")
        self.fire.loadConfig(to_panda(self.ptf_path))
        self.fire.start(parent=self.root, renderParent=self.root)
        self.fire.set_pos(pos)
        self.state["reloaded"] = self.state.get("reloaded", 0) + 1
        return self.fire

    def living_particles(self) -> int:
        total = 0
        for fx in (self.fountain, self.fire):
            for p in fx.getParticlesList():
                total += p.getLivingParticles()
        return total
