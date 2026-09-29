"""独立启动脚本（不依赖 pip 安装；也是 build_apps 的入口）。

    python run_demo.py --lesson bullet_physics
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from panda3d_demo01.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
