"""L19 文件、虚拟文件系统与序列化。

* **Egg**：Panda3D 的文本模型格式。``panda3d.egg`` 提供 EggData 对象模型，
  可以在内存里拼出一个模型，再 ``load_egg_data`` 转成场景图。
* **BAM**：二进制场景图快照（加载最快）。``NodePath.write_bam_file`` 写，
  ``loader.load_model("x.bam")`` 读。
* **VirtualFileSystem (VFS)**：所有 Panda3D 文件访问都经过它。可以挂载：
    - 真实目录 / Multifile(.mf 资源包) / RAM 盘 / HTTP
  所以资源打包后代码一行不用改。
* **Multifile**：Panda3D 的资源包格式（可压缩、可加密、可签名）。
* **Datagram / DatagramIterator**：二进制序列化基元（网络包、存档）。
"""

from __future__ import annotations

from panda3d.core import (
    CS_zup_right,
    Datagram,
    DatagramIterator,
    Filename,
    LColor,
    LPoint3,
    LPoint3d,
    Multifile,
    NodePath,
    VirtualFileMountRamdisk,
    VirtualFileSystem,
)
from panda3d.egg import (
    EggData,
    EggGroup,
    EggPolygon,
    EggVertex,
    EggVertexPool,
    load_egg_data,
)

from ..core import Lesson, register
from ..core.paths import cache_dir, to_panda
from ..core.procedural import make_cube, make_grid

RAM_MOUNT = "/demo01-ram"
MF_MOUNT = "/demo01-mf"


def build_pyramid_egg(name: str = "pyramid") -> EggData:
    """用 EggData API 拼一个四棱锥：VertexPool 存顶点，Polygon 引用顶点。"""
    data = EggData()
    data.set_coordinate_system(CS_zup_right)  # Panda3D 默认：Z 轴向上、右手系
    group = EggGroup(name)
    data.add_child(group)
    pool = EggVertexPool(f"{name}-pool")
    group.add_child(pool)
    pts = [(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0), (0, 0, 1.6)]
    colors = [(1, 0.3, 0.3, 1), (0.3, 1, 0.3, 1), (0.3, 0.3, 1, 1), (1, 1, 0.3, 1), (1, 1, 1, 1)]
    verts = []
    for p, c in zip(pts, colors):
        v = EggVertex()
        v.set_pos(LPoint3d(*p))
        v.set_color(LColor(*c))
        verts.append(pool.add_vertex(v))
    faces = [(0, 3, 2, 1), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
    for f in faces:
        poly = EggPolygon()
        for i in f:
            poly.add_vertex(verts[i])
        group.add_child(poly)
    data.recompute_polygon_normals()
    return data


@register
class FilesSerializationLesson(Lesson):
    key = "files_serialization"
    order = 19
    title = "文件、VFS 与序列化"
    title_en = "Files, VFS & Serialization"
    summary = "EggData 建模、write_bam_file、VFS 挂载 RAM 盘/Multifile、Datagram 二进制"
    apis = (
        "panda3d.egg.EggData", "EggVertexPool", "EggVertex", "EggPolygon", "EggGroup",
        "EggData.write_egg", "load_egg_data", "NodePath.write_bam_file", "Loader.load_model(bam)",
        "VirtualFileSystem.get_global_ptr", "VirtualFileSystem.mount", "VirtualFileSystem.unmount_point",
        "VirtualFileMountRamdisk", "VirtualFileSystem.write_file", "VirtualFileSystem.read_file",
        "VirtualFileSystem.exists", "Multifile.open_write/add_subfile/flush", "Filename.from_os_specific",
        "Datagram", "DatagramIterator",
    )
    controls = ()

    def setup(self) -> None:
        self.place_camera((0, -14, 6), (0, 0, 1))
        self.root.attach_new_node(make_grid(12).node())
        self.vfs = VirtualFileSystem.get_global_ptr()
        out = cache_dir() / "serialization"
        out.mkdir(parents=True, exist_ok=True)

        # 1) EggData → 场景图 & 写 .egg 文本文件
        egg = build_pyramid_egg()
        self.egg_path = out / "pyramid.egg"
        egg.write_egg(to_panda(self.egg_path))
        pyramid = NodePath(load_egg_data(egg))
        pyramid.reparent_to(self.root)
        pyramid.set_pos(-4, 0, 0)

        # 2) 场景图 → BAM → 重新加载（noCache 避免命中模型缓存）
        self.bam_path = out / "pyramid.bam"
        ok = pyramid.write_bam_file(to_panda(self.bam_path))
        reloaded = self.base.loader.load_model(to_panda(self.bam_path), noCache=True)
        reloaded.reparent_to(self.root)
        reloaded.set_pos(0, 0, 0)
        reloaded.set_color_scale(0.6, 0.9, 1, 1)
        self.state["bam_written"] = bool(ok)

        # 3) RAM 盘：挂载 → 写 → 读 → 从 RAM 里加载 egg
        self.ram = VirtualFileMountRamdisk()
        self.vfs.mount(self.ram, RAM_MOUNT, 0)
        self.on_cleanup(lambda: self.vfs.unmount_point(RAM_MOUNT))
        egg_text = self.egg_path.read_text()
        self.vfs.write_file(Filename(f"{RAM_MOUNT}/pyramid.egg"), egg_text.encode(), False)
        from_ram = self.base.loader.load_model(f"{RAM_MOUNT}/pyramid.egg", noCache=True)
        from_ram.reparent_to(self.root)
        from_ram.set_pos(4, 0, 0)
        from_ram.set_color_scale(1, 0.7, 0.4, 1)

        # 4) Multifile 资源包：把 bam 打进 .mf 再挂载读取
        self.mf_path = out / "assets.mf"
        self.build_multifile()
        self.vfs.mount(to_panda(self.mf_path), MF_MOUNT, VirtualFileSystem.MF_read_only)
        self.on_cleanup(lambda: self.vfs.unmount_point(MF_MOUNT))
        from_mf = self.base.loader.load_model(f"{MF_MOUNT}/models/pyramid.bam", noCache=True)
        from_mf.reparent_to(self.root)
        from_mf.set_pos(0, 4, 0)
        from_mf.set_scale(0.6)

        # 5) Datagram：把一个“存档”序列化
        self.save_blob = self.save_game({"name": "panda", "level": 7, "pos": (1.5, -2.0, 0.0)})
        self.state["save_bytes"] = len(self.save_blob)
        self.state["loaded_save"] = self.load_game(self.save_blob)
        marker = make_cube(0.4, color=(1, 1, 1, 1))
        marker.reparent_to(self.root)
        marker.set_pos(LPoint3(*self.state["loaded_save"]["pos"]))
        self.status("左 EggData / 中 BAM / 右 RAM 盘 / 后 Multifile；白块=从 Datagram 存档读出的位置")

    # ------------------------------------------------------------ Multifile
    def build_multifile(self) -> int:
        mf = Multifile()
        if not mf.open_write(to_panda(self.mf_path)):
            raise IOError(f"cannot write {self.mf_path}")
        # add_subfile(包内路径, 源文件, 压缩级别 0-9)；源 Filename 必须声明是二进制还是文本
        bam = to_panda(self.bam_path)
        bam.set_binary()
        egg = to_panda(self.egg_path)
        egg.set_text()
        mf.add_subfile("models/pyramid.bam", bam, 6)
        mf.add_subfile("models/pyramid.egg", egg, 9)
        mf.flush()
        n = mf.get_num_subfiles()
        mf.close()
        self.state["mf_subfiles"] = n
        return n

    # ------------------------------------------------------------ Datagram
    @staticmethod
    def save_game(data: dict) -> bytes:
        dg = Datagram()
        dg.add_uint16(1)                    # 版本号
        dg.add_string(data["name"])
        dg.add_int32(data["level"])
        for v in data["pos"]:
            dg.add_float32(v)
        return bytes(dg.get_message())

    @staticmethod
    def load_game(blob: bytes) -> dict:
        # 坑：DatagramIterator 只保存对 Datagram 的引用，不持有所有权。
        # 写成 DatagramIterator(Datagram(blob)) 时临时对象会被立即回收 → 读到空数据/断言失败。
        dg = Datagram(blob)
        it = DatagramIterator(dg)
        version = it.get_uint16()
        name = it.get_string()
        level = it.get_int32()
        pos = tuple(round(it.get_float32(), 3) for _ in range(3))
        return {"version": version, "name": name, "level": level, "pos": pos}

    def vfs_read(self, path: str) -> bytes:
        return bytes(self.vfs.read_file(Filename(path), True))
