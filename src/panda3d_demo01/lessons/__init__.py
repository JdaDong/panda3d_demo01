"""24 个课程。显式导入 = 确定的注册顺序，也方便 IDE 跳转。

| #  | 模块                     | 主题                              |
|----|--------------------------|-----------------------------------|
| 01 | l01_scene_graph          | 场景图 / NodePath                 |
| 02 | l02_procedural_geom      | 程序化几何                        |
| 03 | l03_textures             | 纹理 / TextureStage / TexGen      |
| 04 | l04_lighting             | 灯光 / 材质 / 阴影                |
| 05 | l05_shaders              | GLSL 着色器                       |
| 06 | l06_camera_lens          | 相机 / 镜头 / DisplayRegion       |
| 07 | l07_input_events         | 输入 / 事件                       |
| 08 | l08_tasks_clock          | 任务 / 时钟 / 协程 / 线程         |
| 09 | l09_intervals            | Interval 动画                     |
| 10 | l10_collision            | 碰撞系统                          |
| 11 | l11_bullet_physics       | Bullet 物理                       |
| 12 | l12_gui_text             | DirectGUI / 文本                  |
| 13 | l13_audio                | 音频 / 3D 音效                    |
| 14 | l14_particles            | 粒子                              |
| 15 | l15_render_states        | 渲染状态 / 特效 / LOD             |
| 16 | l16_postprocess          | RTT / 后处理                      |
| 17 | l17_actor_animation      | Actor 骨骼动画                    |
| 18 | l18_fsm                  | 有限状态机                        |
| 19 | l19_files_serialization  | Egg / BAM / VFS / Multifile       |
| 20 | l20_math                 | 数学库                            |
| 21 | l21_terrain              | GeoMipTerrain                     |
| 22 | l22_networking           | 原生 TCP 网络                     |
| 23 | l23_ai_steering          | PandaAI                           |
| 24 | l24_ode_physics          | ODE 物理                          |
"""

from . import (  # noqa: F401
    l01_scene_graph,
    l02_procedural_geom,
    l03_textures,
    l04_lighting,
    l05_shaders,
    l06_camera_lens,
    l07_input_events,
    l08_tasks_clock,
    l09_intervals,
    l10_collision,
    l11_bullet_physics,
    l12_gui_text,
    l13_audio,
    l14_particles,
    l15_render_states,
    l16_postprocess,
    l17_actor_animation,
    l18_fsm,
    l19_files_serialization,
    l20_math,
    l21_terrain,
    l22_networking,
    l23_ai_steering,
    l24_ode_physics,
)
