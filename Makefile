# =============================================================================
# Makefile —— 常用命令的快捷入口（真正逻辑在 scripts/*.sh）
# =============================================================================
.PHONY: help setup run list test unit headless smoke check wheel bam app docs clean

LESSON ?=

help:            ## 显示帮助
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup:           ## 创建 .venv 并安装依赖
	scripts/setup.sh

run:             ## 运行 Demo（make run LESSON=collision）
	scripts/run.sh $(if $(LESSON),--lesson $(LESSON),)

list:            ## 列出所有课程
	scripts/run.sh --list

test:            ## 全量测试 + 覆盖率 + 文档检查
	scripts/test.sh all

unit:            ## 只跑单元测试
	scripts/test.sh unit

headless:        ## 无 GPU 模式跑单元测试
	scripts/test.sh headless

smoke:           ## 离屏跑完 24 课并截图
	scripts/test.sh smoke

check:           ## 静态检查
	scripts/build.sh check

wheel:           ## 构建 wheel
	scripts/build.sh wheel

bam:             ## egg → bam 转换演示
	scripts/build.sh bam

app:             ## build_apps 打包独立应用
	scripts/build.sh app

docs:            ## 重新生成 docs/API_COVERAGE.md
	.venv/bin/python tools/gen_api_coverage.py

clean:           ## 清理产物
	scripts/build.sh clean
