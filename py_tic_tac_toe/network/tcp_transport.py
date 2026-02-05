import atexit
import contextlib
import json
import socket
import threading
import time
from collections.abc import Callable
from queue import Queue, ShutDown


class TcpTransport:
    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self._handlers: dict[str, list[Callable[[dict[str, object]], None]]] = {}
        self._handlers_lock = threading.Lock()
        self._running = False
        self._msg_queue: Queue[dict[str, object]] = Queue()
        self._close_lock = threading.Lock()  # Prevent race conditions on close
        atexit.register(self._close)  # Ensure cleanup on exit
        self._start()

    def _start(self) -> None:
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def send(self, msg: dict[str, object]) -> None:  # noqa: D102
        if not self._running:
            return
        try:
            self._send_impl(msg)
        except (OSError, TypeError, ValueError):
            # Connection was closed abruptly or something went really bad.
            self._close()
            raise

    def _send_impl(self, msg: dict[str, object]) -> None:
        data = json.dumps(msg).encode("utf-8") + b"\n"
        self._sock.sendall(data)

    def recv(self) -> dict[str, object] | None:  # noqa: D102
        try:
            return self._msg_queue.get()
        except ShutDown:
            return None

    def add_recv_handler(self, msg_type: str, handler: Callable[[dict[str, object]], None]) -> None:  # noqa: D102
        with self._handlers_lock:
            self._handlers.setdefault(msg_type, []).append(handler)

    def remove_recv_handler(self, msg_type: str, handler: Callable[[dict[str, object]], None]) -> None:  # noqa: D102
        with self._handlers_lock:
            handlers = self._handlers.get(msg_type)
            if not handlers:
                return
            try:
                handlers.remove(handler)
            except ValueError:
                return
            if not handlers:
                self._handlers.pop(msg_type, None)

    def _recv_loop(self) -> None:
        buffer = b""
        self._running = True
        while self._running:
            try:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break  # peer disconnected cleanly
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    msg = json.loads(line.decode("utf-8"))
                    if not isinstance(msg, dict):
                        raise TypeError("Unexpected msg type")  # noqa: TRY301
                    if msg.get("__control__") == "close":
                        self._running = False
                        break
                    self._dispatch(msg)
            except (OSError, TypeError, ValueError):
                # If we're already closing, don't re-raise - just exit cleanly
                if not self._running:
                    break
                # Connection was closed abruptly or something went really bad.
                self._close()
                raise
        self._close()

    def _dispatch(self, msg: dict[str, object]) -> None:
        msg_type = msg.get("type")
        if not isinstance(msg_type, str):
            return
        with self._handlers_lock:
            handlers = self._handlers.get(msg_type, []).copy()
        for handler in handlers:
            try:
                handler(msg)
            except Exception:
                # This shouldn't happen. This is either a logic error or something went really bad.
                self._close()
                raise
        self._msg_queue.put(msg)

    def _close(self) -> None:
        with self._close_lock:
            already_closed = not self._running
            self._running = False
            self._msg_queue.shutdown(immediate=True)
            with self._handlers_lock:
                self._handlers.clear()
            if not already_closed:
                with contextlib.suppress(OSError, TypeError, ValueError):
                    self._send_impl({"__control__": "close"})
                with contextlib.suppress(OSError):
                    self._sock.shutdown(socket.SHUT_WR)
            with contextlib.suppress(OSError):
                self._sock.close()
            self._thread.join(timeout=1.0)


def create_host_transport(port: int, timeout: float = 30.0) -> TcpTransport:  # noqa: D103
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", port))
    sock.listen(1)
    sock.settimeout(0.1)  # Short timeout per attempt for responsiveness

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            conn, _ = sock.accept()
            sock.close()
            return TcpTransport(conn)
        except TimeoutError:
            continue

    sock.close()
    msg = f"No client connected within {timeout} seconds"
    raise TimeoutError(msg)


def create_client_transport(host: str, port: int) -> TcpTransport:  # noqa: D103
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    return TcpTransport(sock)
