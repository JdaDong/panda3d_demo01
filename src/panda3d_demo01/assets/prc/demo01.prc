# =============================================================================
# demo01.prc —— 文件形式的 PRC 配置示例（由 config.apply() 通过 loadPrcFile 加载）
# 语法：每行 "变量名 值"，# 开头为注释；布尔值用 #t / #f
# 完整变量列表：运行 `python -c "from panda3d.core import ConfigVariableManager as M; M.get_global_ptr().list_variables()"`
# =============================================================================

# 背景清屏颜色（R G B A）
background-color 0.12 0.13 0.16 1

# 默认使用 OpenGL 渲染管线（macOS 上为 legacy 2.1 context，GLSL 1.20）
load-display pandagl

# 模型缓存：加载 .egg 后会缓存成 .bam，第二次加载更快
model-cache-dir $HOME/.panda3d/cache

# 想用 PStats 性能分析器时打开（需要先运行 pstats 服务器）
want-pstats #f

# 同步垂直刷新
sync-video #t
