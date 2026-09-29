# 架构说明

## 1. 模块关系

```mermaid
flowchart LR
    CLI["__main__.py<br/>argparse CLI"] --> CFG["config.py<br/>RuntimeConfig → PRC"]
    CLI --> APP["app.py<br/>DemoApp(ShowBase)"]
    APP --> HUD["hud.py<br/>OnscreenText"]
    APP --> ORBIT["core/camera_rig.py<br/>OrbitCamera"]
    APP --> REG["core/registry.py<br/>all_lessons()"]
    REG --> LES["lessons/l01..l24<br/>@register"]
    LES --> BASE["core/lesson.py<br/>Lesson(DirectObject)"]
    LES --> PROC["core/procedural.py<br/>几何/贴图/音频工厂"]
    LES --> CAPS["core/capabilities.py<br/>GSG 能力探测"]
    TOOLS["tools/gen_api_coverage.py"] -. 读取 Lesson.apis .-> LES
    TOOLS --> DOC["docs/API_COVERAGE.md"]
    TESTS["tests/*"] --> LES
    TESTS -. 子进程 .-> CLI
```

## 2. ShowBase 一帧的执行顺序

`taskMgr.step()` 就是一帧；`base.run()` 只是不停地调用它。

```mermaid
sequenceDiagram
    participant TM as TaskManager
    participant DG as dataLoop(-50)<br/>键鼠→事件
    participant EV as eventManager(0)<br/>messenger 派发
    participant L as 课程任务(sort 自定义)
    participant IV as ivalLoop(20)<br/>Interval 推进
    participant CO as collisionLoop(30)<br/>base.cTrav
    participant IG as igLoop(50)<br/>renderFrame
    participant AU as audioLoop(60)
    TM->>DG: 读取输入设备
    TM->>EV: 分发事件 → accept 回调
    TM->>L: 你的 task(cont/done/again)
    TM->>IV: 更新所有正在播放的 Interval
    TM->>CO: 碰撞遍历
    TM->>IG: cull + draw 所有 GraphicsOutput
    TM->>AU: 更新 3D 音频
```

> 课程里自建的 Traverser/物理世界都在自己的任务中推进（sort 25~30），与默认顺序对齐。

## 3. Lesson 生命周期（RAII）

```mermaid
stateDiagram-v2
    [*] --> Created: Lesson(base)
    Created --> Active: start()<br/>创建 root / gui_root → setup()
    Active --> Active: 每帧任务 / 事件回调 / Interval
    Active --> Stopped: stop()
    Created --> Stopped: setup() 抛异常<br/>(跳过 teardown，只做通用回收)
    Stopped --> [*]
    note right of Stopped
      1. teardown()（子类：缓冲区/物理世界/网络…）
      2. Interval.pause()
      3. taskMgr.remove(登记的任务)
      4. ignoreAll()（解除全部事件）
      5. on_cleanup 回调（LIFO）
      6. root / gui_root.removeNode()
    end note
```

测试 `test_lesson_lifecycle_no_leaks` 对 24 课逐一断言：stop 后**节点、任务、事件订阅**全部清零，且能重复 start。

## 4. 场景图布局

```mermaid
flowchart TB
    R[render] --> CAM[camera → cam(Lens)]
    R --> PIV[orbit-pivot] --> CAM2[camera 被 OrbitCamera 接管]
    R --> LR["lesson:&lt;key&gt;  ← Lesson.root"]
    LR --> A[课程自己的 3D 内容]
    R2[render2d] --> A2[aspect2d]
    A2 --> GR["gui:&lt;key&gt;  ← Lesson.gui_root"]
    A2 --> ANC[a2dTopLeft / a2dTopRight ...] --> HUDN[HUD OnscreenText]
```

## 5. 渲染输出（L06 / L16）

```mermaid
flowchart LR
    subgraph WIN[GraphicsWindow / GraphicsBuffer]
      DR0["DR sort=0<br/>主 3D 相机"]
      DR5["DR sort=5<br/>小地图(L06)"]
      DR10["DR sort=10<br/>render2d HUD"]
      DR20["DR sort=20<br/>render2dp"]
    end
    RTT["make_texture_buffer (sort=-100)<br/>RTT 监视器(L16)"] -->|get_texture| CARD[场景中的屏幕 Card]
    FM["FilterManager.renderSceneInto"] -->|colortex| QUAD["全屏 Quad + GLSL 滤镜"]
    QUAD --> DR0
```

## 6. 测试架构

```mermaid
flowchart TB
    subgraph P1[pytest 进程]
      SB["session 级 ShowBase<br/>(offscreen 或 headless)"]
      CLK["ClockObject M_non_real_time 30fps"]
      FX["lesson 工厂夹具<br/>start → 断言 → stop"]
      SB --> FX
      CLK --> FX
    end
    subgraph P2[子进程]
      E2E["python -m panda3d_demo01 --autopilot<br/>--offscreen / --headless"]
    end
    P1 -. subprocess .-> P2
    E2E --> SHOTS[out/shots/*.png + report.json]
```

**为什么 App 测试要用子进程？** Panda3D 一个进程只允许一个 ShowBase；UT 共享的那个 `base` 与 `DemoApp` 无法共存。
子进程恰好也是用户真实的使用方式，所以 e2e 同时验证了 CLI、PRC、autopilot 与截图。
