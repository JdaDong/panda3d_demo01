"""L22 网络：Panda3D 原生 TCP（QueuedConnection*）+ PyDatagram。

组件
----
* ``QueuedConnectionManager``   连接工厂（开监听、连服务器、关连接）
* ``QueuedConnectionListener``  接受新连接（服务器端）
* ``QueuedConnectionReader``    读数据报（numThreads=0 表示在主线程轮询）
* ``ConnectionWriter``          发数据报
* ``PyDatagram / PyDatagramIterator``  带 Python 便捷方法的 Datagram

Panda3D 的 TCP 自带“长度前缀分帧”，每次 get_data 拿到的就是一个完整消息，
不用自己处理粘包/拆包。本课在同一进程内起一个 echo 服务器 + 客户端，
每秒发一个 ping，服务器回 pong，测往返延迟。
"""

from __future__ import annotations

import socket
import time

from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from panda3d.core import (
    ConnectionWriter,
    NetAddress,
    NetDatagram,
    PointerToConnection,
    QueuedConnectionListener,
    QueuedConnectionManager,
    QueuedConnectionReader,
)

from ..core import Lesson, register
from ..core.procedural import make_cube, make_uv_sphere

MSG_PING = 1
MSG_PONG = 2


def free_port() -> int:
    """借用 Python socket 找一个空闲端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class EchoNet:
    """把服务器与客户端封装在一起，便于 UT 手动 pump。"""

    def __init__(self, port: int | None = None) -> None:
        self.port = port or free_port()
        self.manager = QueuedConnectionManager()
        self.listener = QueuedConnectionListener(self.manager, 0)
        self.reader = QueuedConnectionReader(self.manager, 0)
        self.writer = ConnectionWriter(self.manager, 0)
        self.server_clients = []
        self.rendezvous = self.manager.open_TCP_server_rendezvous(self.port, 10)
        if self.rendezvous is None:
            raise OSError(f"cannot listen on {self.port}")
        self.listener.add_connection(self.rendezvous)
        self.client = self.manager.open_TCP_client_connection("127.0.0.1", self.port, 3000)
        if self.client is None:
            raise OSError("client connect failed")
        self.reader.add_connection(self.client)
        self.pongs: list[tuple[int, float]] = []
        self.pings_received = 0

    # ------------------------------------------------------------ 消息
    @staticmethod
    def make_ping(seq: int) -> PyDatagram:
        dg = PyDatagram()
        dg.addUint8(MSG_PING)
        dg.addUint32(seq)
        dg.addFloat64(time.perf_counter())
        return dg

    def send_ping(self, seq: int) -> bool:
        return self.writer.send(self.make_ping(seq), self.client)

    # ------------------------------------------------------------ 轮询
    def pump(self) -> None:
        # 1) 服务器：接受新连接
        if self.listener.new_connection_available():
            rendezvous, addr, new_conn = PointerToConnection(), NetAddress(), PointerToConnection()
            if self.listener.get_new_connection(rendezvous, addr, new_conn):
                conn = new_conn.p()
                self.server_clients.append(conn)
                self.reader.add_connection(conn)
        # 2) 读取所有到达的数据报（服务器端与客户端共用一个 reader）
        while self.reader.data_available():
            dg = NetDatagram()
            if not self.reader.get_data(dg):
                break
            it = PyDatagramIterator(dg)
            kind = it.getUint8()
            if kind == MSG_PING:
                self.pings_received += 1
                seq, sent = it.getUint32(), it.getFloat64()
                reply = PyDatagram()
                reply.addUint8(MSG_PONG)
                reply.addUint32(seq)
                reply.addFloat64(sent)
                self.writer.send(reply, dg.get_connection())  # 回给发送方
            elif kind == MSG_PONG:
                seq, sent = it.getUint32(), it.getFloat64()
                self.pongs.append((seq, (time.perf_counter() - sent) * 1000))

    def close(self) -> None:
        for c in self.server_clients:
            self.reader.remove_connection(c)
            self.manager.close_connection(c)
        if self.client is not None:
            self.reader.remove_connection(self.client)
            self.manager.close_connection(self.client)
        if self.rendezvous is not None:
            self.listener.remove_connection(self.rendezvous)
            self.manager.close_connection(self.rendezvous)
        self.client = self.rendezvous = None
        self.server_clients.clear()


@register
class NetworkingLesson(Lesson):
    key = "networking"
    order = 22
    title = "原生网络 TCP"
    title_en = "Native Networking"
    summary = "QueuedConnectionManager/Listener/Reader、ConnectionWriter、PyDatagram 编解码、同进程 echo"
    apis = (
        "QueuedConnectionManager", "QueuedConnectionManager.open_TCP_server_rendezvous",
        "QueuedConnectionManager.open_TCP_client_connection", "QueuedConnectionManager.close_connection",
        "QueuedConnectionListener.new_connection_available", "QueuedConnectionListener.get_new_connection",
        "QueuedConnectionReader.data_available", "QueuedConnectionReader.get_data", "ConnectionWriter.send",
        "NetDatagram.get_connection", "PointerToConnection", "NetAddress", "PyDatagram", "PyDatagramIterator",
    )
    controls = ("SPACE 立刻发 5 个 ping",)

    def setup(self) -> None:
        self.place_camera((0, -12, 4), (0, 0, 1))
        self.server_np = make_cube(1.2, color=(0.3, 0.6, 1, 1))
        self.server_np.reparent_to(self.root)
        self.server_np.set_pos(3, 0, 1)
        self.client_np = make_cube(1.2, color=(1, 0.6, 0.3, 1))
        self.client_np.reparent_to(self.root)
        self.client_np.set_pos(-3, 0, 1)
        self.packet = make_uv_sphere(0.25, color=(1, 1, 0.3, 1))
        self.packet.reparent_to(self.root)
        self.net = EchoNet()
        self.on_cleanup(self.net.close)
        self.seq = 0
        self.accept("space", self.burst, [5])
        self.add_task(self._pump, "pump")
        self.add_task(self._ping, "ping", delay=0.5)
        self.status(f"echo server @127.0.0.1:{self.net.port}")

    def burst(self, n: int) -> None:
        for _ in range(n):
            self.seq += 1
            self.net.send_ping(self.seq)

    def _ping(self, task):
        self.burst(1)
        return task.again

    def _pump(self, task):
        self.net.pump()
        if self.net.pongs:
            seq, rtt = self.net.pongs[-1]
            self.state["last_rtt_ms"] = round(rtt, 3)
            self.state["pongs"] = len(self.net.pongs)
        # 小球在客户端/服务器之间往返，纯可视化
        phase = (task.time * 2) % 2
        x = -3 + 6 * (phase if phase < 1 else 2 - phase)
        self.packet.set_pos(x, 0, 2.2)
        return task.cont
