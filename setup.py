"""Panda3D 官方部署工具 build_apps 的配置入口。

普通安装请用 pyproject.toml（pip install -e .）；本文件只服务于打包成独立应用::

    python setup.py build_apps   # → build/<platform>/panda3d_demo01(.app/.exe)
    python setup.py bdist_apps   # → dist/ 下的 zip / dmg / installer

build_apps 会：
  1. 冻结 Python 字节码（不需要用户装 Python）
  2. 把 include_patterns 匹配的资源打进包，.egg 自动转换为 .bam
  3. 下载目标平台的 panda3d wheel（需要联网），拷贝 plugins 指定的原生插件
"""

from setuptools import setup

# 注意：name/version 等元数据由 pyproject.toml [project] 提供，这里不能重复声明
setup(
    options={
        "build_apps": {
            # gui_apps：带窗口的应用；console_apps 则保留控制台
            "gui_apps": {"panda3d_demo01": "run_demo.py"},  # 入口必须是独立脚本（不能用相对导入）
            "include_patterns": ["src/panda3d_demo01/assets/**/*"],
            # 运行时动态加载的原生插件必须显式声明
            "plugins": ["pandagl", "p3openal_audio", "p3ptloader"],
            "include_modules": {"*": ["panda3d_demo01.lessons.*", "panda3d.bullet", "panda3d.ode",
                                      "panda3d.physics", "panda3d.ai", "panda3d.egg"]},
            "platforms": ["macosx_11_0_arm64", "manylinux2014_x86_64", "win_amd64"],
            "log_filename": "$USER_APPDATA/panda3d_demo01/output.log",
            "log_append": False,
        }
    },
)
