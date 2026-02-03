import json
import socket
import threading
from collections.abc import Callable


class TcpTransport:
    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self._handlers: list[Callable[[dict[str, object]], None]] = []
        self._running = False
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def send(self, msg: dict[str, object]) -> None:  # noqa: D102
        data = json.dumps(msg).encode("utf-8") + b"\n"
        try:
            self._sock.sendall(data)
        except ConnectionResetError:
            self._running = False

    def add_recv_handler(self, handler: Callable[[dict[str, object]], None]) -> None:  # noqa: D102
        self._handlers.append(handler)

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
                for handler in self._handlers:
                    handler(msg)


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
