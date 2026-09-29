#!/usr/bin/env bash
# =============================================================================
# run.sh —— 启动交互式 Demo（参数原样透传给 python -m panda3d_demo01）
#
#   scripts/run.sh                         # 从第 1 课开始
#   scripts/run.sh --lesson collision      # 直接进入某课（key 或序号）
#   scripts/run.sh --list                  # 列出课程
#   scripts/run.sh --size 1920x1080 --mute
# =============================================================================
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
cd "$ROOT"
exec "$PY" -m panda3d_demo01 "$@"
