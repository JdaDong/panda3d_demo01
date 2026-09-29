#!/usr/bin/env bash
# =============================================================================
# setup.sh —— 创建虚拟环境并以可编辑模式安装本项目 + 开发依赖
#
#   scripts/setup.sh                    # 默认用 python3
#   PYTHON=python3.12 scripts/setup.sh  # 指定解释器（需 3.10+）
#   PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple scripts/setup.sh  # 国内镜像
# =============================================================================
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null || die "找不到解释器 $PYTHON"
"$PYTHON" - <<'EOF' || die "需要 Python >= 3.10"
import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)
EOF

if [[ ! -x "$PY" ]]; then
  log "创建虚拟环境 $VENV"
  "$PYTHON" -m venv "$VENV"
fi

log "升级 pip"
"$PY" -m pip install -q --upgrade pip
log "安装 panda3d_demo01[dev]（可编辑模式）"
"$PY" -m pip install -q -e "$ROOT[dev]"

log "验证安装"
"$PY" - <<'EOF'
import panda3d, panda3d.core as core
from panda3d_demo01.core import all_lessons
print(f"  panda3d {panda3d.__version__} | lessons={len(all_lessons())}")
print(f"  bullet/ode/physics/ai 模块:", all(__import__(f"panda3d.{m}") for m in ("bullet", "ode", "physics", "ai")))
EOF
log "完成。运行: scripts/run.sh   测试: scripts/test.sh"
