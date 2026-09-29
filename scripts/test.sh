#!/usr/bin/env bash
# =============================================================================
# test.sh —— 测试入口
#
#   scripts/test.sh            # 全部：UT + e2e + 覆盖率 + 文档一致性
#   scripts/test.sh unit       # 只跑单元测试（跳过子进程 e2e，最快）
#   scripts/test.sh headless   # 无 GPU 模式（window-type none），window 标记的用例自动 skip
#   scripts/test.sh smoke      # 离屏 autopilot：跑完 24 课并截图到 out/shots
#   scripts/test.sh -k bullet  # 其余参数透传给 pytest
# =============================================================================
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
cd "$ROOT"

case "${1:-all}" in
  all)
    log "API 文档一致性检查"
    "$PY" tools/gen_api_coverage.py --check
    log "pytest（含 e2e）+ 覆盖率"
    "$PY" -m pytest --cov --cov-report=term-missing:skip-covered --cov-report=html:out/htmlcov
    log "覆盖率 HTML 报告: out/htmlcov/index.html"
    ;;
  unit)
    shift
    "$PY" -m pytest -m "not e2e" -q "$@"
    ;;
  headless)
    shift
    PANDA3D_DEMO01_TEST_MODE=headless "$PY" -m pytest -m "not e2e" -q "$@"
    ;;
  smoke)
    shift
    mkdir -p out
    "$PY" -m panda3d_demo01 --offscreen --autopilot --frames "${FRAMES:-30}" \
      --shots out/shots --report out/report.json "$@"
    "$PY" tools/contact_sheet.py out/shots out/contact_sheet.png
    log "截图: out/shots/  总览: out/contact_sheet.png  报告: out/report.json"
    ;;
  *)
    "$PY" -m pytest "$@"
    ;;
esac
