# Changelog

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Added
- `docs/ADDING_A_LESSON.md`：新增课程的步骤、约定和需要同步修改的写死数量
- `CHANGELOG.md`、`LICENSE`（MIT，与 `pyproject.toml` 声明一致）
- README 增加“验证状态”表，说明哪些功能已实测、哪些未实测

## [0.1.0] - 2026-09-30

### Added
- 24 节课（`lessons/l01`~`l24`），覆盖 `panda3d.core / direct / bullet / ode / physics / ai / egg`，共登记 426 个 API
- 公共框架：`Lesson` 基类（自动回收资源）、`@register` 注册表、`DemoApp` 主程序、HUD、轨道相机、GSG 能力探测、CJK 字体加载
- CLI：`--lesson / --list / --offscreen / --headless / --autopilot / --shots / --report / --prc`
- 174 个测试（单元测试 + 子进程端到端测试），行覆盖率 90%；headless 模式 157 passed / 13 skipped
- 脚本：`scripts/setup|run|test|build.sh`、`Makefile`；`setup.py` 用于 `build_apps` 打包
- 文档：README、ARCHITECTURE（Mermaid）、LEARNING_PATH、PITFALLS（20 条）、自动生成的 API_COVERAGE、截图总览
- 工具：`tools/gen_api_coverage.py [--check]`、`tools/contact_sheet.py`
- Git：`.gitignore`、`.gitattributes`（统一 LF），已推送到 `git@github.com:JdaDong/panda3d_demo01.git`
