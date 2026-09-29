"""CLI 与端到端测试。

DemoApp 本身继承 ShowBase，不能和 session 级 ``base`` 共存于同一进程，
所以 App 级测试全部以 **子进程** 方式运行真实命令行（这也正是用户使用它的方式）。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from panda3d.core import Filename, PNMImage

from panda3d_demo01.__main__ import build_parser, list_lessons

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, timeout: int = 240) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    return subprocess.run([sys.executable, "-m", "panda3d_demo01", *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=timeout)


# --------------------------------------------------------------------------- 参数解析（进程内）
def test_parser_defaults():
    ns = build_parser().parse_args([])
    assert ns.frames == 30 and ns.size == "1280x720" and not ns.autopilot


def test_parser_mutually_exclusive_modes():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--offscreen", "--headless"])


def test_list_lessons_text():
    lines = list_lessons()
    assert len(lines) == 24 and lines[0].startswith("01  scene_graph")


# --------------------------------------------------------------------------- 子进程
@pytest.mark.e2e
def test_cli_list():
    r = run_cli("--list")
    assert r.returncode == 0
    assert "ode_physics" in r.stdout


@pytest.mark.e2e
def test_cli_headless_autopilot_all_lessons(workdir):
    report = workdir / "report.json"
    r = run_cli("--headless", "--autopilot", "--frames", "5", "--report", str(report))
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(report.read_text())
    assert len(data) == 24 and all(item["ok"] for item in data)


@pytest.mark.e2e
@pytest.mark.window
def test_cli_offscreen_screenshots_not_blank(workdir):
    shots = workdir / "shots"
    keys = "scene_graph,lighting,postprocess,particles"
    r = run_cli("--offscreen", "--size", "480x270", "--autopilot", "--frames", "15", "--only", keys,
                "--shots", str(shots))
    assert r.returncode == 0, r.stdout + r.stderr
    files = sorted(shots.glob("*.png"))
    assert len(files) == 4
    for f in files:
        img = PNMImage()
        assert img.read(Filename.from_os_specific(str(f)))
        # 非空白：采样像素的颜色种类要足够多
        colors = {tuple(round(c, 2) for c in img.get_xel(x, y))
                  for x in range(0, img.get_x_size(), 24) for y in range(0, img.get_y_size(), 24)}
        assert len(colors) > 5, f"{f.name} looks blank"


@pytest.mark.e2e
def test_api_coverage_doc_is_fresh():
    """docs/API_COVERAGE.md 必须与各课程 Lesson.apis 保持一致。"""
    r = subprocess.run([sys.executable, "tools/gen_api_coverage.py", "--check"], cwd=ROOT,
                       capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=str(ROOT / "src")))
    assert r.returncode == 0, r.stdout
