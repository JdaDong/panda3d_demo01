"""L01 场景图（Scene Graph）与 NodePath —— Panda3D 的地基。

核心概念（大白话）
------------------
* **PandaNode** 是“东西”本身（几何、灯、相机、空节点……）。
* **NodePath** 是“从根到这个东西的路径”的句柄。你 99% 的时间操作的是 NodePath。
  同一个 PandaNode 可以出现在多个位置（instancing），此时它有多条 NodePath。
* **变换继承**：子节点的世界变换 = 父变换 × 自身局部变换。
  所以“地球绕太阳转”只需让一个空的 pivot 节点自转，地球挂在 pivot 下偏移即可。

    lesson root
      └── sun
      └── earth-orbit (pivot, 每帧 set_h)
            └── earth  (x = 8)
                  └── moon-orbit (pivot)
                        └── moon (x = 2)
      └── moons-ring (instance_to 出来的 6 个实例，共享同一个 GeomNode)
"""

from __future__ import annotations

from panda3d.core import LPoint3, NodePath, PandaNode

from ..core import Lesson, register
from ..core.procedural import count_geom_nodes, make_axes, make_cube, make_uv_sphere, scene_tree


@register
class SceneGraphLesson(Lesson):
    key = "scene_graph"
    order = 1
    title = "场景图与 NodePath"
    title_en = "Scene Graph & NodePath"
    summary = "父子变换、实例化、查找、标签、wrtReparent、flatten"
    apis = (
        "NodePath.attach_new_node", "NodePath.reparent_to", "NodePath.wrt_reparent_to",
        "NodePath.set_pos/set_hpr/set_scale", "NodePath.get_pos(other)", "NodePath.get_relative_point",
        "NodePath.instance_to", "NodePath.copy_to", "NodePath.find", "NodePath.find_all_matches",
        "NodePath.set_tag/get_tag", "NodePath.set_python_tag", "NodePath.hide/show",
        "NodePath.stash/unstash", "NodePath.flatten_strong", "NodePath.get_children",
        "NodePath.set_color", "NodePath.get_tight_bounds", "PandaNode",
    )
    controls = ("SPACE 隐藏/显示月亮", "T 把月亮 wrtReparent 到根（脱离公转）", "F 对方块阵 flatten_strong")

    EARTH_SPEED = 30.0  # 度/秒
    MOON_SPEED = 120.0

    def setup(self) -> None:
        self.place_camera((0, -28, 16))
        self.root.attach_new_node(make_axes(3).node())

        # 1) 太阳：直接 reparent 到 lesson 根
        self.sun = make_uv_sphere(2.0, color=(1.0, 0.8, 0.2, 1), name="sun")
        self.sun.reparent_to(self.root)
        self.sun.set_tag("body", "star")  # 字符串标签，可被 find 搜索

        # 2) 地球：空 pivot + 偏移。attach_new_node(str) 创建一个空 PandaNode
        self.earth_orbit = self.root.attach_new_node("earth-orbit")
        self.earth = make_uv_sphere(0.8, color=(0.2, 0.5, 1.0, 1), name="earth")
        self.earth.reparent_to(self.earth_orbit)
        self.earth.set_x(8)
        self.earth.set_tag("body", "planet")
        # python tag：可挂任意 Python 对象（不会被 bam 序列化）
        self.earth.set_python_tag("meta", {"mass_kg": 5.97e24, "moons": 1})

        # 3) 月亮：嵌套 pivot（层级越深，继承的变换越多）
        self.moon_orbit = self.earth.attach_new_node("moon-orbit")
        self.moon = make_uv_sphere(0.25, color=(0.8, 0.8, 0.85, 1), name="moon")
        self.moon.reparent_to(self.moon_orbit)
        self.moon.set_x(2)
        self.moon.set_tag("body", "moon")

        # 4) instancing：同一个节点被 6 个父节点引用 —— 修改一次，全部生效
        ring = self.root.attach_new_node("moons-ring")
        self.instance_template = make_cube(0.5, name="instanced-cube")
        self.instances: list[NodePath] = []
        for i in range(6):
            holder = ring.attach_new_node(f"holder-{i}")
            holder.set_pos(-7.5 + i * 3, 10, 0)
            holder.set_h(i * 15)
            self.instances.append(self.instance_template.instance_to(holder))

        # 5) copy_to：深拷贝（新节点，互不影响）
        self.copy = self.instance_template.copy_to(self.root)
        self.copy.set_pos(0, -6, 3)
        self.copy.set_color(1, 0.3, 0.3, 1)  # 只影响拷贝，不影响实例

        # 6) 大量静态小方块：flatten 前后 GeomNode 数对比
        self.grid = self.root.attach_new_node("static-grid")
        for x in range(8):
            for y in range(8):
                c = make_cube(0.3, name=f"g{x}{y}")
                c.reparent_to(self.grid)
                c.set_pos(-12 + x * 0.5, -12 + y * 0.5, 0)
        self.state["geomnodes_before_flatten"] = count_geom_nodes(self.grid)

        self.accept("space", self.toggle_moon)
        self.accept("t", self.detach_moon)
        self.accept("f", self.flatten_grid)
        self.add_task(self._spin, "spin")
        self.state["tree"] = scene_tree(self.root, max_depth=4)
        self.status("行星在转；SPACE/T/F 试试")

    # ------------------------------------------------------------ 行为
    def _spin(self, task):
        dt = self.clock.get_dt()
        self.earth_orbit.set_h(self.earth_orbit.get_h() + self.EARTH_SPEED * dt)
        self.moon_orbit.set_h(self.moon_orbit.get_h() + self.MOON_SPEED * dt)
        # get_pos(other)：相对 other 坐标系的位置；传 render 即世界坐标
        wp = self.moon.get_pos(self.base.render)
        self.state["moon_world"] = (round(wp.x, 2), round(wp.y, 2), round(wp.z, 2))
        return task.cont

    def toggle_moon(self) -> None:
        # hide 只是不渲染（仍参与碰撞/包围盒）；stash 则连遍历都跳过
        if self.moon.is_hidden():
            self.moon.show()
        else:
            self.moon.hide()
        self.state["moon_hidden"] = self.moon.is_hidden()

    def detach_moon(self) -> None:
        """reparent_to 保持局部变换（会“跳”）；wrt_reparent_to 保持世界变换（原地不动）。"""
        before = self.moon.get_pos(self.base.render)
        self.moon.wrt_reparent_to(self.root)
        after = self.moon.get_pos(self.base.render)
        self.state["detach_delta"] = (after - before).length()
        self.status("月亮脱离了地球（世界位置不变）")

    def flatten_grid(self) -> int:
        """flatten_strong：把变换烘焙进顶点并合并 Geom，减少 draw call（静态物体优化）。"""
        self.grid.flatten_strong()
        n = count_geom_nodes(self.grid)
        self.state["geomnodes_after_flatten"] = n
        self.status(f"flatten: {self.state['geomnodes_before_flatten']} → {n} GeomNode")
        return n

    # ------------------------------------------------------------ 查询示例（UT 使用）
    def find_bodies(self, kind: str) -> list[str]:
        """``**/=key=value`` 语法按标签匹配；``**`` 表示任意层级。"""
        return [np.get_name() for np in self.root.find_all_matches(f"**/=body={kind}")]

    def moon_in_sun_space(self) -> LPoint3:
        """get_relative_point(other, p)：把 other 坐标系下的点 p 转换到本节点坐标系。"""
        return self.sun.get_relative_point(self.moon, LPoint3(0, 0, 0))

    def stash_demo(self) -> tuple[int, int]:
        """stash 后 find 找不到（除非用 ;+s 修饰符），unstash 恢复。"""
        self.copy.stash()
        hidden = self.root.find_all_matches("instanced-cube").get_num_paths()
        with_stashed = self.root.find_all_matches("instanced-cube;+s").get_num_paths()
        self.copy.unstash()
        return hidden, with_stashed

    @staticmethod
    def make_empty(name: str) -> NodePath:
        """直接 new 一个 PandaNode，再包成 NodePath（不在任何场景图中 = 游离节点）。"""
        return NodePath(PandaNode(name))
