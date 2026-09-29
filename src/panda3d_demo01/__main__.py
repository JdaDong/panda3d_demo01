"""命令行入口。

示例::

    python -m panda3d_demo01                       # 开窗交互，从第 1 课开始
    python -m panda3d_demo01 --lesson collision    # 直接进入某一课（key 或序号）
    python -m panda3d_demo01 --list                # 列出所有课程
    python -m panda3d_demo01 --offscreen --autopilot --frames 30 --shots out/shots --report out/report.json
                                                   # 无窗口跑完所有课程并截图（CI 冒烟）
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__, config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="panda3d-demo01", description="Panda3D API learning lab")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--list", action="store_true", help="列出课程后退出")
    p.add_argument("--lesson", default=None, help="起始课程 key 或 1 起始序号")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--offscreen", action="store_true", help="离屏缓冲渲染（不弹窗）")
    mode.add_argument("--headless", action="store_true", help="window-type none（无 GSG）")
    p.add_argument("--size", default="1280x720", help="窗口/缓冲尺寸 WxH")
    p.add_argument("--mute", action="store_true", help="使用 null 音频后端")
    p.add_argument("--autopilot", action="store_true", help="自动依次运行所有课程")
    p.add_argument("--frames", type=int, default=30, help="autopilot 每课帧数")
    p.add_argument("--only", default=None, help="autopilot 只跑这些 key（逗号分隔）")
    p.add_argument("--shots", default=None, help="autopilot 截图目录")
    p.add_argument("--report", default=None, help="autopilot JSON 报告路径")
    p.add_argument("--prc", action="append", default=[], help="额外 PRC 行，可多次，如 --prc 'sync-video #f'")
    return p


def list_lessons() -> list[str]:
    from .core import all_lessons

    return [f"{c.order:02d}  {c.key:<22} {c.title}  —  {c.summary}" for c in all_lessons()]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list:
        print("\n".join(list_lessons()))
        return 0
    w, h = (int(x) for x in args.size.lower().split("x"))
    mode = config.RunMode.OFFSCREEN if args.offscreen else config.RunMode.HEADLESS if args.headless else config.RunMode.WINDOW
    runtime = config.RuntimeConfig(mode=mode, width=w, height=h, mute=args.mute, extra=tuple(args.prc))

    from .app import DemoApp  # 延迟导入：--list 不需要初始化 Panda3D

    app = DemoApp(runtime, start=args.lesson)
    if not args.autopilot:
        app.run()
        return 0
    only = [s.strip() for s in args.only.split(",")] if args.only else None
    reports = app.run_autopilot(args.frames, Path(args.shots) if args.shots else None, only)
    failed = [r for r in reports if not r.ok]
    for r in reports:
        flag = "OK " if r.ok else "ERR"
        print(f"[{flag}] {r.key:<22} {r.seconds * 1000:7.1f} ms  {r.screenshot or ''}")
        if r.error:
            print(r.error)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps([asdict(r) for r in reports], ensure_ascii=False, indent=2))
    print(f"{len(reports) - len(failed)}/{len(reports)} lessons passed")
    app.destroy()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
