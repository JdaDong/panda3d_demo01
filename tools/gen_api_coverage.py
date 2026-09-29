"""根据每个 Lesson.apis 自动生成 docs/API_COVERAGE.md。

用法::

    python tools/gen_api_coverage.py          # 写文件
    python tools/gen_api_coverage.py --check  # 只检查是否最新（CI 用，过期返回 1）

“文档即代码”：API 清单只在课程类里维护一份，文档永远不会与代码脱节。
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "docs" / "API_COVERAGE.md"


def module_of(api: str) -> str:
    """粗分类：按 API 名推断所属 Panda3D 模块。"""
    head = api.split(".")[0].split(" ")[0]
    if head.startswith("Bullet") or api.startswith("panda3d.bullet"):
        return "panda3d.bullet"
    if head.startswith("Ode"):
        return "panda3d.ode"
    if head.startswith(("AI", "panda3d.ai")):
        return "panda3d.ai"
    if head.startswith("Egg") or head in ("load_egg_data", "panda3d.egg"):
        return "panda3d.egg"
    if head in {"PointParticleFactory", "SpriteParticleRenderer", "PointParticleRenderer", "SphereVolumeEmitter",
                "DiscEmitter", "BaseParticleEmitter", "ColorInterpolationManager", "LinearVectorForce",
                "LinearNoiseForce", "LinearCylinderVortexForce"}:
        return "panda3d.physics"
    if head in {"Actor", "AnimControl"} or api.startswith(("direct.", "DirectObject", "messenger", "Messenger",
                                                         "TaskManager", "Task", "Interval", "Loader", "ShowBase",
                                                         "base.", "Audio3DManager", "FilterManager", "FSM",
                                                         "Particle", "ForceGroup", "OnscreenText", "OnscreenImage",
                                                         "Direct", "Lerp", "Sequence", "Parallel", "Wait", "Func",
                                                         "ProjectileInterval", "SoundInterval", "PyDatagram",
                                                         "uponDeath", "extraArgs", "blendType", "filterXxx",
                                                         "enterXxx", "widget", "loader.", "NodePath.posInterval",
                                                         "NodePath.hprInterval")):
        return "direct (Python 层)"
    return "panda3d.core"


def render() -> str:
    from panda3d_demo01.core import all_lessons

    lessons = all_lessons()
    total = sum(len(c.apis) for c in lessons)
    per_module: Counter[str] = Counter()
    for c in lessons:
        for a in c.apis:
            per_module[module_of(a)] += 1

    out = [
        "# API 覆盖清单（自动生成，请勿手改）",
        "",
        "> 由 `python tools/gen_api_coverage.py` 从各课程的 `Lesson.apis` 生成。",
        f"> 共 **{len(lessons)}** 课，登记 **{total}** 个 API 条目。",
        "",
        "## 按模块统计",
        "",
        "| 模块 | 条目数 |",
        "|------|-------:|",
    ]
    for mod, n in per_module.most_common():
        out.append(f"| `{mod}` | {n} |")
    out += ["", "## 按课程", ""]
    for c in lessons:
        out.append(f"### L{c.order:02d} {c.title} · `{c.key}`")
        out.append("")
        out.append(f"{c.summary}")
        out.append("")
        if c.controls:
            out.append("**按键**：" + "；".join(c.controls))
            out.append("")
        out.append("| API | 所属 |")
        out.append("|-----|------|")
        for a in c.apis:
            out.append(f"| `{a}` | {module_of(a)} |")
        out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text = render()
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("docs/API_COVERAGE.md is stale; run: python tools/gen_api_coverage.py")
            return 1
        print("API_COVERAGE.md up to date")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
