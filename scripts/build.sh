#!/usr/bin/env bash
# =============================================================================
# build.sh —— 构建产物
#
#   scripts/build.sh check   # 静态检查：字节码编译全部源码 + GLSL 文件存在 + 文档最新
#   scripts/build.sh wheel   # 构建 wheel → dist/*.whl（纯 Python 包，依赖 panda3d）
#   scripts/build.sh bam     # 把自带 .egg 模型预转成 .bam（演示 egg2bam 工具链）
#   scripts/build.sh app     # Panda3D build_apps：冻结成独立应用（需联网下载各平台 wheel）
#   scripts/build.sh clean   # 清理 build/ dist/ out/ 缓存
# =============================================================================
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
cd "$ROOT"

case "${1:-check}" in
  check)
    log "compileall（语法/字节码检查）"
    "$PY" -m compileall -q src tests tools
    log "资源检查"
    for f in src/panda3d_demo01/assets/shaders/wobble.vert.glsl src/panda3d_demo01/assets/shaders/wobble.frag.glsl \
             src/panda3d_demo01/assets/prc/demo01.prc; do
      [[ -f "$f" ]] || die "缺少资源 $f"
    done
    "$PY" tools/gen_api_coverage.py --check
    log "check OK"
    ;;
  wheel)
    log "构建 wheel"
    rm -rf dist && mkdir -p dist
    "$PY" -m pip wheel --no-deps -w dist . -q
    ls -lh dist
    ;;
  bam)
    # egg2bam 随 panda3d wheel 一起安装在 venv/bin 下
    EGG2BAM="$VENV/bin/egg2bam"
    [[ -x "$EGG2BAM" ]] || die "未找到 egg2bam"
    mkdir -p build/bam
    "$PY" - <<'EOF'
from panda3d_demo01.lessons.l19_files_serialization import build_pyramid_egg
from panda3d.core import Filename
build_pyramid_egg().write_egg(Filename.from_os_specific("build/bam/pyramid.egg"))
EOF
    "$EGG2BAM" -o build/bam/pyramid.bam build/bam/pyramid.egg
    ls -lh build/bam
    ;;
  app)
    log "Panda3D build_apps（首次会下载各平台 panda3d wheel，耗时较长）"
    "$PY" setup.py build_apps
    ;;
  clean)
    rm -rf build dist out .pytest_cache .coverage htmlcov src/*.egg-info
    find . -name __pycache__ -type d -prune -not -path "./.venv/*" -exec rm -rf {} +
    log "clean done"
    ;;
  *) die "未知目标: $1" ;;
esac
