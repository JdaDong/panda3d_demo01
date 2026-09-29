"""panda3d_demo01 —— 通过 24 个可运行课程学习 Panda3D 几乎全部公开 API。

包结构::

    panda3d_demo01/
    ├── config.py        PRC 配置系统（loadPrcFileData / ConfigVariable）
    ├── app.py           DemoApp(ShowBase)：课程切换、HUD、自动驾驶截图
    ├── core/            课程基类、注册表、程序化资源、相机控制、能力探测
    └── lessons/         l01 ~ l24，每个文件 = 一个 API 主题

注意：Panda3D 一个进程只能存在一个 ShowBase，所以这里不在 import 时创建任何
Panda3D 全局对象，全部延迟到 DemoApp / 测试 fixture 里。
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
