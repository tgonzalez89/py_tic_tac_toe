import json
import socket
import threading
from collections.abc import Callable
from queue import Empty, Queue


class TcpTransport:
    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self._handlers: dict[str, list[Callable[[dict[str, object]], None]]] = {}
        self._running = False
        self._inbox: Queue[dict[str, object]] = Queue()
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def send(self, msg: dict[str, object]) -> None:  # noqa: D102
        data = json.dumps(msg).encode("utf-8") + b"\n"
        try:
            self._sock.sendall(data)
        except ConnectionResetError:
            self._running = False

    def recv(self, timeout: float | None = None) -> dict[str, object]:
        """Blocking receive of the next unhandled message.
        Raises RuntimeError if the transport is closed.
        """
        while self._running:
            try:
                return self._inbox.get(timeout=timeout)
            except Empty:
                if not self._running:
                    break
        raise RuntimeError("Transport closed")

    def add_recv_handler(self, msg_type: str, handler: Callable[[dict[str, object]], None]) -> None:  # noqa: D102
        self._handlers.setdefault(msg_type, []).append(handler)

    def _recv_loop(self) -> None:
        buffer = b""
        self._running = True
        while self._running:
            try:
                chunk = self._sock.recv(4096)
            except ConnectionResetError:
                break  # peer disconnected abruptly
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                msg = json.loads(line.decode("utf-8"))
                self._dispatch(msg)

    def _dispatch(self, msg: dict[str, object]) -> None:
        msg_type = msg.get("type")
        handlers = self._handlers.get(msg_type) if isinstance(msg_type, str) else None
        if handlers:
            for handler in handlers:
                handler(msg)
        else:
            self._inbox.put(msg)


def create_host_transport(port: int) -> TcpTransport:  # noqa: D103
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", port))
    sock.listen(1)
    conn, _ = sock.accept()
    return TcpTransport(conn)


def create_client_transport(host: str, port: int) -> TcpTransport:  # noqa: D103
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    return TcpTransport(sock)
