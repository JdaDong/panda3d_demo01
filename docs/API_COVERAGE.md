# API 覆盖清单（自动生成，请勿手改）

> 由 `python tools/gen_api_coverage.py` 从各课程的 `Lesson.apis` 生成。
> 共 **24** 课，登记 **426** 个 API 条目。

## 按模块统计

| 模块 | 条目数 |
|------|-------:|
| `panda3d.core` | 249 |
| `direct (Python 层)` | 108 |
| `panda3d.ode` | 21 |
| `panda3d.bullet` | 18 |
| `panda3d.ai` | 14 |
| `panda3d.physics` | 10 |
| `panda3d.egg` | 6 |

## 按课程

### L01 场景图与 NodePath · `scene_graph`

父子变换、实例化、查找、标签、wrtReparent、flatten

**按键**：SPACE 隐藏/显示月亮；T 把月亮 wrtReparent 到根（脱离公转）；F 对方块阵 flatten_strong

| API | 所属 |
|-----|------|
| `NodePath.attach_new_node` | panda3d.core |
| `NodePath.reparent_to` | panda3d.core |
| `NodePath.wrt_reparent_to` | panda3d.core |
| `NodePath.set_pos/set_hpr/set_scale` | panda3d.core |
| `NodePath.get_pos(other)` | panda3d.core |
| `NodePath.get_relative_point` | panda3d.core |
| `NodePath.instance_to` | panda3d.core |
| `NodePath.copy_to` | panda3d.core |
| `NodePath.find` | panda3d.core |
| `NodePath.find_all_matches` | panda3d.core |
| `NodePath.set_tag/get_tag` | panda3d.core |
| `NodePath.set_python_tag` | panda3d.core |
| `NodePath.hide/show` | panda3d.core |
| `NodePath.stash/unstash` | panda3d.core |
| `NodePath.flatten_strong` | panda3d.core |
| `NodePath.get_children` | panda3d.core |
| `NodePath.set_color` | panda3d.core |
| `NodePath.get_tight_bounds` | panda3d.core |
| `PandaNode` | panda3d.core |

### L02 程序化几何 · `procedural_geom`

自定义顶点格式、动态网格、线/点图元、CardMaker、LineSegs、Rope

**按键**：SPACE 暂停/继续波浪；N 显示/隐藏法线

| API | 所属 |
|-----|------|
| `GeomVertexArrayFormat.add_column` | panda3d.core |
| `GeomVertexFormat.register_format` | panda3d.core |
| `GeomVertexData` | panda3d.core |
| `GeomVertexWriter` | panda3d.core |
| `GeomVertexReader` | panda3d.core |
| `GeomVertexRewriter` | panda3d.core |
| `Geom.UH_dynamic` | panda3d.core |
| `GeomTriangles` | panda3d.core |
| `GeomLines` | panda3d.core |
| `GeomPoints` | panda3d.core |
| `Geom.add_primitive` | panda3d.core |
| `GeomNode.add_geom` | panda3d.core |
| `GeomNode.modify_geom` | panda3d.core |
| `Geom.modify_vertex_data` | panda3d.core |
| `CardMaker.set_frame/generate` | panda3d.core |
| `LineSegs` | panda3d.core |
| `direct.showutil.Rope` | direct (Python 层) |
| `NodePath.set_render_mode_thickness` | panda3d.core |
| `NodePath.set_render_mode_perspective` | panda3d.core |
| `InternalName` | panda3d.core |

### L03 纹理与纹理层 · `textures`

PNMImage 程序化贴图、过滤/环绕、多层混合、UV 动画、TexGen、动态 RAM 纹理

**按键**：M 切换细节层混合模式（modulate/add/decal）

| API | 所属 |
|-----|------|
| `PNMImage` | panda3d.core |
| `PNMImage.set_xel/get_xel` | panda3d.core |
| `PNMImage.gaussian_filter` | panda3d.core |
| `Texture.load` | panda3d.core |
| `Texture.setup_2d_texture` | panda3d.core |
| `Texture.set_ram_image_as` | panda3d.core |
| `Texture.set_minfilter/set_magfilter` | panda3d.core |
| `Texture.set_anisotropic_degree` | panda3d.core |
| `Texture.set_wrap_u/v` | panda3d.core |
| `SamplerState` | panda3d.core |
| `loader.load_texture` | direct (Python 层) |
| `TextureStage` | panda3d.core |
| `TextureStage.set_mode` | panda3d.core |
| `TextureStage.set_sort` | panda3d.core |
| `NodePath.set_texture` | panda3d.core |
| `NodePath.set_tex_scale` | panda3d.core |
| `NodePath.set_tex_offset` | panda3d.core |
| `NodePath.set_tex_rotate` | panda3d.core |
| `NodePath.set_tex_gen` | panda3d.core |
| `TexGenAttrib` | panda3d.core |
| `PerlinNoise2` | panda3d.core |

### L04 光照与材质 · `lighting`

四种灯、衰减、聚光锥、Material、ShaderGenerator、阴影

**按键**：1 环境光；2 平行光；3 点光；4 聚光灯 开/关

| API | 所属 |
|-----|------|
| `AmbientLight` | panda3d.core |
| `DirectionalLight` | direct (Python 层) |
| `PointLight` | panda3d.core |
| `Spotlight` | panda3d.core |
| `PerspectiveLens` | panda3d.core |
| `PointLight.set_attenuation` | panda3d.core |
| `Spotlight.set_exponent` | panda3d.core |
| `LightLensNode.set_shadow_caster` | panda3d.core |
| `NodePath.set_light` | panda3d.core |
| `NodePath.clear_light` | panda3d.core |
| `NodePath.set_light_off` | panda3d.core |
| `Material` | panda3d.core |
| `Material.set_shininess` | panda3d.core |
| `Material.set_emission` | panda3d.core |
| `NodePath.set_material` | panda3d.core |
| `NodePath.set_shader_auto` | panda3d.core |
| `Light.set_color` | panda3d.core |
| `loader.load_model(models/misc/*light)` | direct (Python 层) |

### L05 GLSL 着色器 · `shaders`

Shader.load/make、内置 p3d_* 输入、set_shader_input、shader 继承与覆盖

**按键**：+ / - 调节振幅；O 在中间球上 set_shader_off 对比

| API | 所属 |
|-----|------|
| `Shader.load` | panda3d.core |
| `Shader.make` | panda3d.core |
| `Shader.SL_GLSL` | panda3d.core |
| `NodePath.set_shader` | panda3d.core |
| `NodePath.set_shader_input` | panda3d.core |
| `NodePath.clear_shader` | panda3d.core |
| `NodePath.set_shader_off` | panda3d.core |
| `p3d_ModelViewProjectionMatrix` | panda3d.core |
| `p3d_NormalMatrix` | panda3d.core |
| `p3d_ModelMatrix` | panda3d.core |
| `osg_FrameTime` | panda3d.core |
| `p3d_Texture0` | panda3d.core |
| `Shader.get_error_flag` | panda3d.core |
| `GraphicsStateGuardian.get_supports_glsl` | panda3d.core |

### L06 相机、镜头与多视口 · `camera_lens`

FOV/近远面、正交镜头、多 DisplayRegion 小地图、project/extrude

**按键**：Z 开始/停止 dolly zoom；[ / ] 调 FOV

| API | 所属 |
|-----|------|
| `PerspectiveLens.set_fov` | panda3d.core |
| `Lens.set_near_far` | panda3d.core |
| `Lens.get_fov` | panda3d.core |
| `OrthographicLens.set_film_size` | panda3d.core |
| `Lens.project` | panda3d.core |
| `Lens.extrude` | panda3d.core |
| `Camera` | panda3d.core |
| `Camera.show_frustum` | panda3d.core |
| `Camera.set_lens` | panda3d.core |
| `GraphicsOutput.make_display_region` | panda3d.core |
| `DisplayRegion.set_camera` | panda3d.core |
| `DisplayRegion.set_sort` | panda3d.core |
| `DisplayRegion.set_clear_color_active` | panda3d.core |
| `DisplayRegion.set_clear_depth_active` | panda3d.core |
| `GraphicsOutput.remove_display_region` | panda3d.core |
| `base.camLens` | direct (Python 层) |
| `NodePath.get_relative_point` | panda3d.core |
| `WindowProperties` | panda3d.core |
| `GraphicsWindow.get_properties` | panda3d.core |

### L07 输入与事件 · `input_events`

accept/-up/-repeat、轮询 is_button_down、鼠标、messenger 自定义事件、accept_once

**按键**：WASD 移动方块；SPACE 跳（自定义事件）；鼠标左键 染色；C 隐藏光标；J 一次性事件

| API | 所属 |
|-----|------|
| `DirectObject.accept` | direct (Python 层) |
| `DirectObject.accept_once` | direct (Python 层) |
| `DirectObject.ignore` | direct (Python 层) |
| `DirectObject.ignoreAll` | direct (Python 层) |
| `messenger.send` | direct (Python 层) |
| `Messenger.is_accepting` | direct (Python 层) |
| `KeyboardButton.ascii_key` | panda3d.core |
| `MouseButton.one` | panda3d.core |
| `MouseWatcher.is_button_down` | panda3d.core |
| `MouseWatcher.has_mouse` | panda3d.core |
| `MouseWatcher.get_mouse` | panda3d.core |
| `ButtonThrower.set_button_down_event` | panda3d.core |
| `ButtonThrower.set_modifier_buttons` | panda3d.core |
| `WindowProperties.set_cursor_hidden` | panda3d.core |
| `GraphicsWindow.request_properties` | panda3d.core |
| `事件名: key / key-up / key-repeat / shift-key / mouse1 / wheel_up` | panda3d.core |

### L08 任务、时钟与协程 · `tasks_clock`

task.cont/done/again、doMethodLater、sort、uponDeath、async 协程、线程任务链、异步加载

**按键**：SPACE 启动一次后台质数计算；L 异步加载茶壶

| API | 所属 |
|-----|------|
| `TaskManager.add` | direct (Python 层) |
| `TaskManager.do_method_later` | direct (Python 层) |
| `TaskManager.remove` | direct (Python 层) |
| `TaskManager.hasTaskNamed` | direct (Python 层) |
| `TaskManager.setupTaskChain` | direct (Python 层) |
| `Task.cont/done/again` | direct (Python 层) |
| `Task.pause (await)` | direct (Python 层) |
| `task.time/task.frame` | panda3d.core |
| `uponDeath` | direct (Python 层) |
| `extraArgs/appendTask` | direct (Python 层) |
| `ClockObject.get_dt` | panda3d.core |
| `ClockObject.get_frame_time` | panda3d.core |
| `ClockObject.get_average_frame_rate` | panda3d.core |
| `Thread.is_threading_supported` | panda3d.core |
| `Loader.load_model(callback=)` | direct (Python 层) |
| `PStatCollector.start/stop` | panda3d.core |

### L09 Interval 动画时间轴 · `intervals`

Lerp*Interval、Sequence/Parallel/Wait/Func、LerpFunc、ProjectileInterval、blendType、seek

**按键**：SPACE 暂停/继续；K 从头播放；G 跳到 50% (set_t)

| API | 所属 |
|-----|------|
| `LerpPosInterval` | direct (Python 层) |
| `LerpHprInterval` | direct (Python 层) |
| `LerpScaleInterval` | direct (Python 层) |
| `LerpColorScaleInterval` | direct (Python 层) |
| `LerpFunc` | direct (Python 层) |
| `ProjectileInterval` | direct (Python 层) |
| `Sequence` | direct (Python 层) |
| `Parallel` | direct (Python 层) |
| `Wait` | direct (Python 层) |
| `Func` | direct (Python 层) |
| `NodePath.posInterval` | direct (Python 层) |
| `NodePath.hprInterval` | direct (Python 层) |
| `Interval.loop/start/pause/resume/finish` | direct (Python 层) |
| `Interval.setT/getT` | direct (Python 层) |
| `Interval.getDuration` | direct (Python 层) |
| `Interval.isPlaying` | direct (Python 层) |
| `blendType` | direct (Python 层) |

### L10 碰撞检测 · `collision`

Traverser + Queue/Pusher/Event/Floor 四种 Handler、BitMask 分层、鼠标射线拾取

**按键**：鼠标左键 拾取方块（变红）；V 显示/隐藏碰撞体

| API | 所属 |
|-----|------|
| `CollisionTraverser` | panda3d.core |
| `CollisionTraverser.traverse` | panda3d.core |
| `CollisionTraverser.show_collisions` | panda3d.core |
| `CollisionHandlerQueue` | panda3d.core |
| `CollisionHandlerQueue.sort_entries` | panda3d.core |
| `CollisionHandlerPusher` | panda3d.core |
| `CollisionHandlerEvent.add_in_pattern` | panda3d.core |
| `CollisionHandlerFloor` | panda3d.core |
| `CollisionNode` | panda3d.core |
| `CollisionSphere` | panda3d.core |
| `CollisionBox` | panda3d.core |
| `CollisionPlane` | panda3d.core |
| `CollisionRay.set_from_lens` | panda3d.core |
| `CollisionSegment` | panda3d.core |
| `CollisionCapsule` | panda3d.core |
| `CollisionEntry.get_surface_point` | panda3d.core |
| `CollisionEntry.get_into_node_path` | panda3d.core |
| `BitMask32` | panda3d.core |
| `CollisionNode.set_from_collide_mask` | panda3d.core |
| `CollisionNode.set_into_collide_mask` | panda3d.core |

### L11 Bullet 刚体物理 · `bullet_physics`

BulletWorld、刚体/形状、冲量、铰链约束、射线查询、接触测试、调试线框

**按键**：SPACE 发射炮弹；B 显示/隐藏调试线框；K 重建方块塔

| API | 所属 |
|-----|------|
| `BulletWorld` | panda3d.bullet |
| `BulletWorld.set_gravity` | panda3d.bullet |
| `BulletWorld.do_physics` | panda3d.bullet |
| `BulletWorld.attach` | panda3d.bullet |
| `BulletWorld.remove` | panda3d.bullet |
| `BulletWorld.ray_test_closest` | panda3d.bullet |
| `BulletWorld.contact_test` | panda3d.bullet |
| `BulletWorld.set_debug_node` | panda3d.bullet |
| `BulletRigidBodyNode` | panda3d.bullet |
| `BulletRigidBodyNode.set_mass` | panda3d.bullet |
| `BulletRigidBodyNode.apply_central_impulse` | panda3d.bullet |
| `BulletRigidBodyNode.set_linear_velocity` | panda3d.bullet |
| `BulletBoxShape` | panda3d.bullet |
| `BulletSphereShape` | panda3d.bullet |
| `BulletPlaneShape` | panda3d.bullet |
| `BulletCapsuleShape` | panda3d.bullet |
| `BulletHingeConstraint` | panda3d.bullet |
| `BulletDebugNode` | panda3d.bullet |
| `set_friction/set_restitution` | panda3d.core |

### L12 DirectGUI 与文本 · `gui_text`

Frame/Label/Button/Check/Radio/Slider/Entry/OptionMenu/ScrolledList/WaitBar、3D TextNode

**按键**：用鼠标操作右侧面板

| API | 所属 |
|-----|------|
| `OnscreenText` | direct (Python 层) |
| `OnscreenImage` | direct (Python 层) |
| `DirectFrame` | direct (Python 层) |
| `DirectLabel` | direct (Python 层) |
| `DirectButton` | direct (Python 层) |
| `DirectCheckButton` | direct (Python 层) |
| `DirectRadioButton` | direct (Python 层) |
| `DirectSlider` | direct (Python 层) |
| `DirectEntry` | direct (Python 层) |
| `DirectOptionMenu` | direct (Python 层) |
| `DirectScrolledList` | direct (Python 层) |
| `DirectWaitBar` | direct (Python 层) |
| `DirectGuiGlobals (DGG)` | direct (Python 层) |
| `widget['prop'] = value` | direct (Python 层) |
| `TextNode` | panda3d.core |
| `TextNode.set_align` | panda3d.core |
| `TextNode.set_shadow` | panda3d.core |
| `TextNode.set_card_color` | panda3d.core |
| `TextNode.set_frame_color` | panda3d.core |
| `base.a2dTopRight` | direct (Python 层) |
| `aspect2d` | panda3d.core |

### L13 音频与 3D 音效 · `audio`

load_sfx/load_music、音量/音调/循环、Audio3DManager 定位与多普勒、SoundInterval

**按键**：1 播放提示音；2 升调播放；M 静音/取消；SPACE 播放旋律(SoundInterval)

| API | 所属 |
|-----|------|
| `Loader.load_sfx` | direct (Python 层) |
| `Loader.load_music` | direct (Python 层) |
| `AudioSound.play/stop` | panda3d.core |
| `AudioSound.set_volume` | panda3d.core |
| `AudioSound.set_play_rate` | panda3d.core |
| `AudioSound.set_loop` | panda3d.core |
| `AudioSound.status` | panda3d.core |
| `AudioSound.length` | panda3d.core |
| `AudioManager.set_volume` | panda3d.core |
| `AudioManager.set_active` | panda3d.core |
| `Audio3DManager` | direct (Python 层) |
| `Audio3DManager.attachSoundToObject` | direct (Python 层) |
| `Audio3DManager.setDropOffFactor` | direct (Python 层) |
| `Audio3DManager.setSoundVelocityAuto` | direct (Python 层) |
| `SoundInterval` | direct (Python 层) |
| `base.sfxManagerList` | direct (Python 层) |
| `base.musicManager` | direct (Python 层) |

### L14 粒子系统 · `particles`

ParticleEffect/Particles、Factory/Emitter/Renderer、ForceGroup、颜色插值、.ptf 存取

**按键**：SPACE 暂停/恢复喷泉；R 从 .ptf 重载火焰

| API | 所属 |
|-----|------|
| `ShowBase.enable_particles` | direct (Python 层) |
| `ParticleEffect` | direct (Python 层) |
| `ParticleEffect.start/cleanup` | direct (Python 层) |
| `Particles` | direct (Python 层) |
| `Particles.setFactory/setRenderer/setEmitter` | direct (Python 层) |
| `PointParticleFactory` | panda3d.physics |
| `SpriteParticleRenderer` | panda3d.physics |
| `PointParticleRenderer` | panda3d.physics |
| `SphereVolumeEmitter` | panda3d.physics |
| `DiscEmitter` | panda3d.physics |
| `BaseParticleEmitter.ETRADIATE` | panda3d.physics |
| `ColorInterpolationManager.addLinear` | panda3d.physics |
| `ForceGroup` | direct (Python 层) |
| `LinearVectorForce` | panda3d.physics |
| `LinearNoiseForce` | panda3d.physics |
| `LinearCylinderVortexForce` | panda3d.physics |
| `ParticleEffect.saveConfig` | direct (Python 层) |
| `ParticleEffect.loadConfig` | direct (Python 层) |

### L15 渲染状态与特效 · `render_states`

Fog、透明/排序 bin、加法混合、线框、双面、深度偏移、裁剪平面、Billboard/Compass、LOD

**按键**：F 切换雾(off/linear/exp)；W 线框；C 裁剪平面；D 拉远/拉近看 LOD

| API | 所属 |
|-----|------|
| `Fog` | panda3d.core |
| `Fog.set_exp_density` | panda3d.core |
| `Fog.set_linear_range` | panda3d.core |
| `NodePath.set_fog` | panda3d.core |
| `TransparencyAttrib` | panda3d.core |
| `NodePath.set_transparency` | panda3d.core |
| `NodePath.set_alpha_scale` | panda3d.core |
| `NodePath.set_bin` | panda3d.core |
| `NodePath.set_depth_write` | panda3d.core |
| `NodePath.set_depth_test` | panda3d.core |
| `ColorBlendAttrib` | panda3d.core |
| `NodePath.set_attrib` | panda3d.core |
| `RenderModeAttrib` | panda3d.core |
| `NodePath.set_render_mode_wireframe` | panda3d.core |
| `NodePath.set_render_mode_filled_wireframe` | panda3d.core |
| `NodePath.set_two_sided` | panda3d.core |
| `CullFaceAttrib` | panda3d.core |
| `NodePath.set_depth_offset` | panda3d.core |
| `PlaneNode` | panda3d.core |
| `NodePath.set_clip_plane` | panda3d.core |
| `NodePath.set_billboard_point_eye` | panda3d.core |
| `CompassEffect` | panda3d.core |
| `LODNode` | panda3d.core |
| `LODNode.add_switch` | panda3d.core |
| `AntialiasAttrib` | panda3d.core |
| `NodePath.get_attrib` | panda3d.core |
| `NodePath.get_net_state` | panda3d.core |

### L16 渲染到纹理与后处理 · `postprocess`

make_texture_buffer + make_camera 监视器、FilterManager 全屏 GLSL 滤镜（灰度/Sobel/暗角）

**按键**：SPACE 切换滤镜

| API | 所属 |
|-----|------|
| `GraphicsOutput.make_texture_buffer` | panda3d.core |
| `GraphicsOutput.get_texture` | panda3d.core |
| `GraphicsOutput.set_clear_color` | panda3d.core |
| `ShowBase.make_camera` | direct (Python 层) |
| `GraphicsEngine.remove_window` | panda3d.core |
| `FilterManager` | direct (Python 层) |
| `FilterManager.renderSceneInto` | direct (Python 层) |
| `FilterManager.cleanup` | direct (Python 层) |
| `Texture` | panda3d.core |
| `Shader.make` | panda3d.core |
| `CardMaker` | panda3d.core |
| `direct.filter.CommonFilters (Cg 环境)` | direct (Python 层) |

### L17 Actor 骨骼动画 · `actor_animation`

loop/play/pose、PlayRate、AnimControl、exposeJoint 挂件、controlJoint 程序化骨骼、动画混合、actorInterval

**按键**：SPACE 走/停；+/- 速度；B 调整混合权重；H 头部程序控制开/关；I 播放 actorInterval 序列

| API | 所属 |
|-----|------|
| `Actor` | direct (Python 层) |
| `Actor.loop` | direct (Python 层) |
| `Actor.play` | direct (Python 层) |
| `Actor.stop` | direct (Python 层) |
| `Actor.pose` | direct (Python 层) |
| `Actor.setPlayRate` | direct (Python 层) |
| `Actor.getNumFrames` | direct (Python 层) |
| `Actor.getCurrentFrame` | direct (Python 层) |
| `Actor.getAnimNames` | direct (Python 层) |
| `Actor.getAnimControl` | direct (Python 层) |
| `AnimControl.isPlaying` | direct (Python 层) |
| `Actor.getJoints` | direct (Python 层) |
| `Actor.exposeJoint` | direct (Python 层) |
| `Actor.controlJoint` | direct (Python 层) |
| `Actor.releaseJoint` | direct (Python 层) |
| `Actor.enableBlend` | direct (Python 层) |
| `Actor.setControlEffect` | direct (Python 层) |
| `Actor.actorInterval` | direct (Python 层) |
| `Actor.cleanup` | direct (Python 层) |
| `LMatrix4.rotate_mat (驱动 controlJoint)` | panda3d.core |

### L18 有限状态机 FSM · `fsm`

enter/exit 约定、defaultTransitions、filterXxx 守卫、request/demand/forceTransition

**按键**：SPACE 手动切下一灯；O 关灯/开灯；W 走 / J 跳 / L 落地 / X 强制 Idle

| API | 所属 |
|-----|------|
| `direct.fsm.FSM` | direct (Python 层) |
| `FSM.request` | direct (Python 层) |
| `FSM.demand` | direct (Python 层) |
| `FSM.forceTransition` | direct (Python 层) |
| `FSM.state` | direct (Python 层) |
| `FSM.defaultTransitions` | direct (Python 层) |
| `FSM.defaultFilter` | direct (Python 层) |
| `filterXxx` | direct (Python 层) |
| `enterXxx/exitXxx` | direct (Python 层) |
| `FSM.RequestDenied` | direct (Python 层) |
| `FSM.cleanup` | direct (Python 层) |

### L19 文件、VFS 与序列化 · `files_serialization`

EggData 建模、write_bam_file、VFS 挂载 RAM 盘/Multifile、Datagram 二进制

| API | 所属 |
|-----|------|
| `panda3d.egg.EggData` | panda3d.core |
| `EggVertexPool` | panda3d.egg |
| `EggVertex` | panda3d.egg |
| `EggPolygon` | panda3d.egg |
| `EggGroup` | panda3d.egg |
| `EggData.write_egg` | panda3d.egg |
| `load_egg_data` | panda3d.egg |
| `NodePath.write_bam_file` | panda3d.core |
| `Loader.load_model(bam)` | direct (Python 层) |
| `VirtualFileSystem.get_global_ptr` | panda3d.core |
| `VirtualFileSystem.mount` | panda3d.core |
| `VirtualFileSystem.unmount_point` | panda3d.core |
| `VirtualFileMountRamdisk` | panda3d.core |
| `VirtualFileSystem.write_file` | panda3d.core |
| `VirtualFileSystem.read_file` | panda3d.core |
| `VirtualFileSystem.exists` | panda3d.core |
| `Multifile.open_write/add_subfile/flush` | panda3d.core |
| `Filename.from_os_specific` | panda3d.core |
| `Datagram` | panda3d.core |
| `DatagramIterator` | panda3d.core |

### L20 数学库 · `math`

LVector/LPoint、叉积点积、LMatrix4、TransformState、四元数 slerp、包围体、平面、噪声、随机数

| API | 所属 |
|-----|------|
| `LVector3.cross/dot/normalized/length` | panda3d.core |
| `LPoint3` | panda3d.core |
| `LMatrix4` | panda3d.core |
| `LMatrix4.xform_point/xform_vec` | panda3d.core |
| `LMatrix4.invert_from` | panda3d.core |
| `TransformState.make_pos_hpr_scale` | panda3d.core |
| `TransformState.compose` | panda3d.core |
| `LQuaternion.set_hpr/get_hpr` | panda3d.core |
| `LQuaternion.xform` | panda3d.core |
| `look_at()` | panda3d.core |
| `BoundingSphere.contains` | panda3d.core |
| `BoundingBox` | panda3d.core |
| `LPlane.dist_to_plane` | panda3d.core |
| `LPlane.intersects_line` | panda3d.core |
| `PerlinNoise3` | panda3d.core |
| `Randomizer` | panda3d.core |
| `NodePath.set_quat` | panda3d.core |
| `NodePath.get_mat` | panda3d.core |

### L21 GeoMipTerrain 地形 · `terrain`

高度图地形、分块 LOD、focal point、get_elevation 贴地、color map、StackedPerlinNoise2

**按键**：B 切换 bruteforce(无 LOD)

| API | 所属 |
|-----|------|
| `GeoMipTerrain` | panda3d.core |
| `GeoMipTerrain.set_heightfield` | panda3d.core |
| `GeoMipTerrain.set_color_map` | panda3d.core |
| `GeoMipTerrain.set_block_size` | panda3d.core |
| `GeoMipTerrain.set_near/set_far` | panda3d.core |
| `GeoMipTerrain.set_focal_point` | panda3d.core |
| `GeoMipTerrain.set_bruteforce` | panda3d.core |
| `GeoMipTerrain.generate` | panda3d.core |
| `GeoMipTerrain.update` | panda3d.core |
| `GeoMipTerrain.get_elevation` | panda3d.core |
| `GeoMipTerrain.get_root` | panda3d.core |
| `StackedPerlinNoise2` | panda3d.core |
| `PNMImage(16-bit)` | panda3d.core |

### L22 原生网络 TCP · `networking`

QueuedConnectionManager/Listener/Reader、ConnectionWriter、PyDatagram 编解码、同进程 echo

**按键**：SPACE 立刻发 5 个 ping

| API | 所属 |
|-----|------|
| `QueuedConnectionManager` | panda3d.core |
| `QueuedConnectionManager.open_TCP_server_rendezvous` | panda3d.core |
| `QueuedConnectionManager.open_TCP_client_connection` | panda3d.core |
| `QueuedConnectionManager.close_connection` | panda3d.core |
| `QueuedConnectionListener.new_connection_available` | panda3d.core |
| `QueuedConnectionListener.get_new_connection` | panda3d.core |
| `QueuedConnectionReader.data_available` | panda3d.core |
| `QueuedConnectionReader.get_data` | panda3d.core |
| `ConnectionWriter.send` | panda3d.core |
| `NetDatagram.get_connection` | panda3d.core |
| `PointerToConnection` | panda3d.core |
| `NetAddress` | panda3d.core |
| `PyDatagram` | direct (Python 层) |
| `PyDatagramIterator` | direct (Python 层) |

### L23 PandaAI 转向行为 · `ai_steering`

AIWorld、AICharacter、seek/flee/pursue/evade/wander/arrival 行为叠加与状态查询

**按键**：SPACE 暂停/恢复猎人

| API | 所属 |
|-----|------|
| `panda3d.ai.AIWorld` | panda3d.core |
| `AIWorld.add_ai_char` | panda3d.ai |
| `AIWorld.remove_ai_char` | panda3d.ai |
| `AIWorld.update` | panda3d.ai |
| `AICharacter` | panda3d.ai |
| `AICharacter.get_ai_behaviors` | panda3d.ai |
| `AICharacter.get_velocity` | panda3d.ai |
| `AIBehaviors.seek` | panda3d.ai |
| `AIBehaviors.flee` | panda3d.ai |
| `AIBehaviors.pursue` | panda3d.ai |
| `AIBehaviors.evade` | panda3d.ai |
| `AIBehaviors.wander` | panda3d.ai |
| `AIBehaviors.arrival` | panda3d.ai |
| `AIBehaviors.behavior_status` | panda3d.ai |
| `AIBehaviors.pause_ai/resume_ai` | panda3d.ai |

### L24 ODE 物理引擎 · `ode_physics`

OdeWorld/OdeBody/OdeMass、Space+Geom 碰撞、auto_collide 接触组、表面表、球关节链

**按键**：SPACE 撒一把方块

| API | 所属 |
|-----|------|
| `OdeWorld` | panda3d.ode |
| `OdeWorld.set_gravity` | panda3d.ode |
| `OdeWorld.quick_step` | panda3d.ode |
| `OdeWorld.init_surface_table` | panda3d.ode |
| `OdeWorld.set_surface_entry` | panda3d.ode |
| `OdeBody` | panda3d.ode |
| `OdeMass.set_box/set_sphere` | panda3d.ode |
| `OdeBody.set_mass` | panda3d.ode |
| `OdeBody.set_position/get_position` | panda3d.ode |
| `OdeBody.get_quaternion` | panda3d.ode |
| `OdeBody.add_force` | panda3d.ode |
| `OdeSimpleSpace` | panda3d.ode |
| `OdeSimpleSpace.set_auto_collide_world` | panda3d.ode |
| `OdeSimpleSpace.auto_collide` | panda3d.ode |
| `OdeSimpleSpace.set_auto_collide_joint_group` | panda3d.ode |
| `OdeBoxGeom` | panda3d.ode |
| `OdeSphereGeom` | panda3d.ode |
| `OdePlaneGeom` | panda3d.ode |
| `OdeGeom.set_body` | panda3d.ode |
| `OdeJointGroup.empty` | panda3d.ode |
| `OdeBallJoint` | panda3d.ode |

