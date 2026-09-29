# 踩坑记录（全部在本项目中真实遇到并修复）

每一条都给出：**现象 → 根因 → 解法 → 代码位置**。建议把它当作 Panda3D 1.10 的“避坑速查表”。

| # | 现象 | 根因 | 解法 | 位置 |
|---|---|---|---|---|
| 1 | `DatagramIterator` 读数据时断言 `_current_index < length` | `DatagramIterator(Datagram(blob))` 中临时 Datagram 被立即回收，迭代器只持有引用 | 先 `dg = Datagram(blob)` 再 `DatagramIterator(dg)`，保持 dg 存活 | l19 `load_game` |
| 2 | 加了小地图后主画面整帧不刷新（全黑） | 新 DisplayRegion 的 sort=20 与 ShowBase 的 `render2dp` DR 重复；在**多重采样离屏缓冲**上触发驱动问题 | 默认 DR：3D=0 / render2d=10 / render2dp=20，选 5 这类不冲突的值 | l06 `_make_minimap` |
| 3 | 协程任务 stop 后仍残留在 TaskManager | 正在 `await Task.pause()` 的任务 `remove()` 返回 False；1.10 上 `cancel()` 还会断言 | 协作式取消：循环里检查 `self.active` 自行退出 | l08 `_coroutine` |
| 4 | `Tried to invert singular LMatrix4` | controlJoint 返回节点的矩阵含镜像/剪切，`set_h()` 先分解再重组导致奇异 | 保存原矩阵，`set_mat(rotate_mat(a, axis) * rest)` | l17 `_update` |
| 5 | `LerpFunc` 没有 `get_duration` | Interval 系列是 **Python 类**，只有 camelCase；C++ 类才有 snake_case 别名 | Interval 一律用 `getDuration/setT/isPlaying` | l09 |
| 6 | 粒子精灵大到满屏 | `SpriteParticleRenderer.setTexture(tex, texels_per_unit=1)`：64px 贴图 = 64 单位 | 传第二个参数，如 `setTexture(tex, 128)` | l14 |
| 7 | `Multifile.add_subfile` 断言 `is_binary_or_text()` | 源 Filename 没声明读取模式 | `fn.set_binary()` / `fn.set_text()` | l19 `build_multifile` |
| 8 | `GraphicsBuffer` 没有 `get_properties` | WindowProperties 只属于 `GraphicsWindow`；离屏缓冲没有 | `isinstance(win, GraphicsWindow)` 判断 | l06 |
| 9 | `CommonFilters.setBloom()` 返回 False | 1.10 的 CommonFilters 生成 **Cg** 着色器；Apple Silicon 无 Cg 基础着色器 | FilterManager + 自写 GLSL 1.20 | l16 |
| 10 | 自写 GLSL 编译失败 | macOS 默认 legacy GL 2.1 context，只支持 GLSL 1.20 | `#version 120` + `attribute/varying/gl_FragColor` | assets/shaders |
| 11 | `from panda3d.physics import LinearVortexForce` 失败 | 该类名不存在 | 使用 `LinearCylinderVortexForce` | l14 |
| 12 | `ProjectileInterval(peakHeight=...)` 报错 | 无此参数 | 用 `duration=` / `startVel=` / `wayPoint=` | l09 |
| 13 | null 音频后端下 `get_volume()` 恒为 0 | NullAudioManager/NullAudioSound 的 setter 都是空操作 | 测试里先判断后端类型再断言数值 | tests `_is_null` |
| 14 | `ShaderInput.get_vector()` 读到垃圾值 | 传 `LVector4` 被存为 `M_numeric`(PTA)，`get_vector` 只对 `M_vector` 有效 | 用 `get_value_type()` 判断，或读 net state | tests/test_rendering |
| 15 | Pusher 让球被金币“挡住” | from 掩码同时包含墙与金币，Pusher 对所有 into 都做推离 | Pusher 只用 WALL_MASK，金币用独立 traverser + Event | l10 |
| 16 | `OnscreenText.set_pos(x, y)` 报参数错误 | snake_case 调到了 C++ `NodePath.set_pos`（需要 3 个分量） | 用 OnscreenText 自己的 `setPos(x, y)` | l06 |
| 17 | `DirectEntry(text_font=...)` 无效/报错 | Entry 的字体参数叫 `entryFont` | `entryFont=font` | l12 |
| 18 | HUD 中文变成方块、`▲` 无字形警告 | 默认字体仅 ASCII；PingFang 也没有部分符号 | 加载 CJK 字体；符号改用 ASCII | core/fonts.py、l12 |
| 19 | OrbitCamera 斜向摆位时朝向反了 | heading 推导符号错误：局部 (0,-d,0) 经 H 旋转为 (d·sinH, -d·cosH) | `H = atan2(dx, -dy)`，由 UT `test_orbit_camera_math` 发现 | core/camera_rig.py |
| 20 | 课程 setup 中途异常后，报错却是 `AttributeError` | stop() 调用了 teardown()，而 teardown 依赖 setup 尚未创建的属性，二次异常掩盖了原始错误 | `_setup_failed` 标记：失败时跳过 teardown，只做通用回收，再重新抛出原异常 | core/lesson.py |

## 设计层面的经验

1. **一个进程一个 ShowBase**：UT 共享 session 级 `base`；需要完整 App 的测试放进子进程。
2. **确定性时钟**：`ClockObject.set_mode(M_non_real_time)` + `set_frame_rate(30)`，Interval/物理/任务的测试不再依赖机器速度。
3. **渲染与逻辑解耦**：课程把可观测结果写入 `self.state`，HUD 与 UT 读同一份数据。
4. **能力探测优先于假设**：`capabilities.detect(base)` 决定是否启用 ShaderGenerator/滤镜，同一份代码在 GPU/无 GPU/无 Cg 下都能跑。
5. **资源自动回收**：`add_task / track / on_cleanup` 登记，`stop()` 统一释放；生命周期 UT 保证零泄漏。
