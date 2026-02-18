import atexit
import contextlib
import json
import socket
import threading
from collections.abc import Callable
from queue import Empty, Queue, ShutDown


class TcpTransport:
    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self._handlers: dict[str, list[Callable[[dict[str, object]], None]]] = {}
        self._msg_queue: Queue[dict[str, object]] = Queue()
        self._handlers_lock = threading.Lock()  # Prevents race conditions when accessing handlers.
        self._close_lock = threading.Lock()  # Prevents closing the transport multiple times concurrently.
        self._running = False
        self._sock.settimeout(0.25)  # Set a timeout for recv to allow periodic checks for shutdown.
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()
        atexit.register(self._close)  # Ensure cleanup on exit.

    def send(self, msg: dict[str, object]) -> None:
        if not self._running:
            return
        try:
            self._send_impl(msg)
        except (OSError, TypeError, ValueError):
            # Connection was closed unexpectedly.
            self._close()
            raise

    def _send_impl(self, msg: dict[str, object]) -> None:
        data = json.dumps(msg).encode("utf-8") + b"\n"
        self._sock.sendall(data)

    def recv(self, *, block: bool = True, timeout: float | None = None) -> dict[str, object] | None:
        try:
            return self._msg_queue.get(block=block, timeout=timeout)
        except (Empty, ShutDown):
            return None

    def add_recv_handler(self, msg_type: str, handler: Callable[[dict[str, object]], None]) -> None:
        with self._handlers_lock:
            self._handlers.setdefault(msg_type, []).append(handler)
        # Drain the queue to trigger any handlers for messages that arrived before the handler was registered.
        messages = []
        while True:
            try:
                msg = self._msg_queue.get_nowait()
            except (Empty, ShutDown):
                break
            messages.append(msg)

        # Process matching messages and collect non-matching ones to put them back.
        for msg in messages:
            if msg.get("type") == msg_type:
                handler(msg)
            else:
                try:
                    self._msg_queue.put(msg)
                except ShutDown:
                    break

    def remove_recv_handler(self, msg_type: str, handler: Callable[[dict[str, object]], None]) -> None:
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
        try:
            while self._running:
                try:
                    chunk = self._sock.recv(4096)
                except TimeoutError:
                    continue  # Socket timeout is normal, continue waiting for data.
                except (OSError, TypeError, ValueError):
                    break  # Connection was closed unexpectedly.
                if not chunk:
                    return  # Peer disconnected cleanly.
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    msg = json.loads(line.decode("utf-8"))
                    if not isinstance(msg, dict):
                        break  # Invalid message format.
                    self._dispatch(msg)
        finally:
            if self._running:
                self._close()

    def _dispatch(self, msg: dict[str, object]) -> None:
        msg_type = msg.get("type")
        if not isinstance(msg_type, str):
            raise TypeError("Invalid type for 'type' field")
        with self._handlers_lock:
            handlers = self._handlers.get(msg_type, []).copy()
        # If there are handlers, call them. Otherwise, put the message in the queue for recv() to handle.
        if handlers:
            for handler in handlers:
                handler(msg)
        else:
            self._msg_queue.put(msg)

    def _close(self) -> None:
        if not self._close_lock.acquire(blocking=False):
            return
        if not self._running:
            self._close_lock.release()
            return
        try:
            self._running = False
            if self._thread != threading.current_thread():
                self._thread.join(timeout=5.0)
            with contextlib.suppress(OSError):
                self._sock.close()
            with self._handlers_lock:
                self._handlers.clear()
            with contextlib.suppress(RuntimeError, ValueError):
                self._msg_queue.shutdown(immediate=True)
        finally:
            self._close_lock.release()


def create_host_transport(port: int, timeout: float | None = None) -> TcpTransport:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", port))
    sock.listen(1)
    sock.settimeout(timeout)
    conn_sock, _ = sock.accept()
    return TcpTransport(conn_sock)


def create_client_transport(host: str, port: int, timeout: float | None = None) -> TcpTransport:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((host, port))
    return TcpTransport(sock)
