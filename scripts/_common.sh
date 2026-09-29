#!/usr/bin/env bash
# =============================================================================
# 公共函数：被其它脚本 source。定位项目根目录、venv 里的 python、彩色日志。
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${VENV:-$ROOT/.venv}"
PY="$VENV/bin/python"

log()  { printf '\033[1;36m[demo01]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[demo01]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[demo01]\033[0m %s\n' "$*" >&2; exit 1; }

require_venv() {
  [[ -x "$PY" ]] || die "未找到 $PY，请先运行 scripts/setup.sh"
}
