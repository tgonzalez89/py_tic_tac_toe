# Code Review: py_tic_tac_toe

## Executive Summary
**Overall Assessment:** Good architecture with event-driven design, but several critical bugs and error handling issues need attention. Type safety is strict and code style is enforced well.

---

## 🔴 Critical Issues

### 1. **GameEngine: Missing error handling in `_on_move_requested`**
**File:** [game_engine/game_engine.py](game_engine/game_engine.py)
**Severity:** Critical
**Issue:** When `TicTacToe.apply_move()` raises `ValueError`, the exception propagates unhandled and crashes the game loop.

```python
def _on_move_requested(self, event: MoveRequested) -> None:
    self.game.apply_move(Move(event.player, event.row, event.col))  # Exception not caught!
    self._request_state_updated()
    if not self.game.winner:
        self._request_start_turn()
```

**Expected:** Invalid moves should trigger `InvalidMove` event so UIs can provide feedback.

**Fix:** Wrap in try-except and publish `InvalidMove` event:
```python
from py_tic_tac_toe.event_bus.event_bus import InvalidMove

def _on_move_requested(self, event: MoveRequested) -> None:
    try:
        self.game.apply_move(Move(event.player, event.row, event.col))
    except ValueError as e:
        self.event_bus.publish(InvalidMove(str(e)))
        return

    self._request_state_updated()
    if not self.game.winner:
        self._request_start_turn()
```

---

### 2. **EventBus: Thread-unsafe event dispatch**
**File:** [event_bus/event_bus.py](event_bus/event_bus.py)
**Severity:** Critical
**Issue:** `_handlers` dict is accessed from multiple threads without synchronization (main thread publishes, UI/network threads consume). Concurrent modification can occur if a handler subscribes during dispatch.

**Fix:** Add thread lock:
```python
import threading

class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[Callable[[Event], None]]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        with self._lock:
            self._handlers.setdefault(event_type, []).append(cast("Callable[[Event], None]", handler))

    def publish(self, event: Event) -> None:
        with self._lock:
            handlers = self._handlers.get(type(event), []).copy()
        for handler in handlers:
            handler(event)
```

---

### 3. **TerminalUi: Uncaught exception in event handler**
**File:** [ui/terminal.py](ui/terminal.py) line 62
**Severity:** Critical
**Issue:** `_get_input()` catches all exceptions with bare `except BaseException`, which is dangerous for resource cleanup and prevents proper logging.

```python
try:
    input_str = input()
except BaseException:  # noqa: BLE001 - Too broad!
    sys.exit()
```

**Fix:** Catch only `EOFError` and `KeyboardInterrupt`:
```python
try:
    input_str = input()
except (EOFError, KeyboardInterrupt):
    sys.exit()
```

---

### 4. **TcpTransport: Connection not properly closed**
**File:** [network/tcp_transport.py](network/tcp_transport.py)
**Severity:** High
**Issue:** `_sock` is never explicitly closed. The socket resource is leaked when transport stops.

**Fix:** Add close method:
```python
def close(self) -> None:
    """Close the transport and underlying socket."""
    self._running = False
    try:
        self._sock.close()
    except OSError:
        pass  # Already closed
```

And set `_running = False` in `_recv_loop` when EOF is reached.

---

### 5. **TcpTransport: Race condition in `recv()`**
**File:** [network/tcp_transport.py](network/tcp_transport.py) lines 21-31
**Severity:** High
**Issue:** Between checking `self._running` and calling `_inbox.get()`, the transport can close, causing a hung call.

```python
def recv(self, timeout: float | None = None) -> dict[str, object]:
    while self._running:  # Thread A checks this
        try:
            return self._inbox.get(timeout=timeout)  # Thread B sets _running=False here
        except Empty:
            if not self._running:
                break
    raise RuntimeError("Transport closed")
```

**Fix:** Use a sentinel value or event to signal closure cleanly.

---

## 🟡 High-Priority Issues

### 6. **RemoteNetworkPlayer: Uncaught exception in handler**
**File:** [player/network_players.py](player/network_players.py) lines 37-42
**Severity:** High
**Issue:** `_on_network_message` catches `ValueError` but swallows unexpected network errors. If `msg` is malformed (missing keys), KeyError will crash the handler.

```python
def _on_network_message(self, msg: dict[str, Any]) -> None:
    if msg["type"] == "MoveRequested":  # KeyError if "type" missing
        try:
            self.event_bus.publish(MoveRequested(msg["player"], msg["row"], msg["col"]))
        except ValueError:  # Only catches move validation errors
            self.event_bus.publish(self.start_turn_event_cache)
```

**Fix:** Validate message structure:
```python
def _on_network_message(self, msg: dict[str, Any]) -> None:
    if msg.get("type") != "MoveRequested":
        return
    try:
        self.event_bus.publish(
            MoveRequested(str(msg["player"]), int(msg["row"]), int(msg["col"]))
        )
    except (KeyError, ValueError, TypeError):
        # Log error or notify UI
        pass
```

---

### 7. **LocalNetworkPlayer: Unused method**
**File:** [player/network_players.py](player/network_players.py) lines 82-85
**Severity:** Medium
**Issue:** `_on_assign_role()` method is defined but never registered with event bus and never called.

```python
def _on_assign_role(self, msg: dict[str, Any]) -> None:
    if msg["type"] == "AssignRole":
        self.symbol = msg["role"]  # This is already set in __init__
```

**Fix:** Remove this unused method or integrate into initialization if needed.

---

### 8. **RandomAIPlayer: Empty board edge case not handled**
**File:** [player/ai_player.py](player/ai_player.py) lines 12-16
**Severity:** Medium
**Issue:** When no moves available (board full), silently returns. Should log warning or indicate error.

```python
choices = [(r, c) for r in range(3) for c in range(3) if event.board[r][c] is None]
if not choices:
    return  # Silent failure - should never happen in normal game
```

**Fix:** Add assertion or error logging:
```python
if not choices:
    raise RuntimeError(f"No moves available for player {self.symbol}")
```

---

## 🟠 Medium-Priority Issues

### 9. **__main__.py: Missing validation for network mode**
**File:** [__main__.py](__main__.py) lines 76-77
**Severity:** Medium
**Issue:** Network mode requires `--role` argument but there's no validation. If someone runs `--mode network --ui terminal` without `--role`, the code silently skips engine initialization.

```python
elif args.role == "host":
    # ... setup
else:
    # ... assume client, but args.role could be None
```

**Fix:** Validate arguments based on mode:
```python
if args.mode == "network" and not args.role:
    parser.error("network mode requires --role {host|client}")
```

---

### 10. **TcpTransport: JSON decode error not caught**
**File:** [network/tcp_transport.py](network/tcp_transport.py) line 51
**Severity:** Medium
**Issue:** If malformed JSON is received, `json.loads()` will raise `JSONDecodeError` and crash the receive loop.

```python
msg = json.loads(line.decode("utf-8"))  # Can crash here
```

**Fix:** Wrap with try-except:
```python
try:
    msg = json.loads(line.decode("utf-8"))
except json.JSONDecodeError:
    continue  # Skip malformed message
```

---

### 11. **TerminalUi: Busy-wait loop on startup**
**File:** [__main__.py](__main__.py) lines 53-54
**Severity:** Medium
**Issue:** Polling loop consumes CPU while waiting for UIs to start:

```python
while not all(ui.started for ui in uis):
    pass  # 100% CPU busy-wait
```

**Fix:** Use threading event or sleep:
```python
import time
while not all(ui.started for ui in uis):
    time.sleep(0.01)
```

---

### 12. **UIs: `_on_error` method is a no-op**
**File:** [ui/terminal.py](ui/terminal.py) line 117, [ui/pygame.py](ui/pygame.py) line 173, [ui/tk.py](ui/tk.py) line 106
**Severity:** Medium
**Issue:** All three UI implementations have empty `_on_error` handlers:

```python
def _on_error(self, event: InvalidMove) -> None:
    pass
```

This means invalid moves are silently ignored. Players get no feedback that their move was rejected.

**Fix:** Display error to player:
```python
# TerminalUi
def _on_error(self, event: InvalidMove) -> None:
    print(f"Error: {event.msg}")
    self._ask_for_move()

# PygameUi / TkUi
def _on_error(self, event: InvalidMove) -> None:
    # Show message box or on-screen notification
    pass
```

---

## 🔵 Low-Priority Issues / Code Quality

### 13. **TicTacToe: Type inconsistency in winner checking**
**File:** [game/game.py](game/game.py) line 39
**Severity:** Low
**Issue:** Type annotation mixes list and tuple:

```python
lines: list[list[str | None] | tuple[str | None]] = []
```

The `zip()` result is a tuple, but lists are appended. This is safe but confusing.

**Fix:** Use consistent types:
```python
lines: list[Sequence[str | None]] = []
```

Or convert tuple to list:
```python
lines.extend([list(row) for row in zip(*self.board, strict=True)])
```

---

### 14. **Minimal docstrings**
**Files:** Most methods use `# noqa: D102` to suppress docstring warnings.
**Severity:** Low
**Issue:** Public methods should have docstrings explaining their behavior, especially abstract methods and complex logic.

**Examples:**
- `MoveRequested`: What does it represent?
- `TcpTransport.send()`: Is it async? Can it raise exceptions?
- `EventBus.publish()`: Does it call handlers synchronously?

---

### 15. **RemoteNetworkPlayer: Dangerous type cast**
**File:** [player/network_players.py](player/network_players.py) lines 53-56
**Severity:** Low
**Issue:** Unchecked type cast during initialization:

```python
if msg.get("type") == "AssignRole" and isinstance(msg.get("role"), str):
    super().__init__(event_bus, str(msg["role"]))
else:
    err_msg = "Error assigning role."
    raise RuntimeError(err_msg)
```

The `str()` cast is redundant since `isinstance` already verified it's a string. Also, the `"role"` field might be missing.

**Fix:** Use `.get()` with proper error handling:
```python
role = msg.get("type") == "AssignRole" and isinstance(msg.get("role"), str)
if not role:
    raise RuntimeError("Invalid AssignRole message")
super().__init__(event_bus, msg["role"])  # No cast needed
```

---

### 16. **Inconsistent error messages**
**Files:** Multiple
**Severity:** Low
**Issue:** Error messages vary in style (some use "Error", some bare messages). Example:

```python
# TicTacToe
raise ValueError("Game over")
raise ValueError("Not your turn")

# RemoteNetworkPlayer
err_msg = "Error assigning role."
raise RuntimeError(err_msg)
```

**Fix:** Establish error message convention (e.g., always include context, consistent capitalization).

---

### 17. **TkUi: Unnecessary threading.Thread for messagebox**
**File:** [ui/tk.py](ui/tk.py) lines 102-104
**Severity:** Low
**Issue:** Spawning a daemon thread to call `messagebox.showinfo()` is unnecessary. Tkinter is already in the main event loop.

```python
threading.Thread(target=self._show_end_message_internal, daemon=True, args=(msg,)).start()
```

**Fix:** Call directly:
```python
messagebox.showinfo("Game Over", msg)
self.root.destroy()
```

---

## ✅ Positive Observations

1. **Event-driven architecture is clean**: Good decoupling via EventBus pub-sub pattern.
2. **Type hints enforced**: `mypy --strict` catches type errors early.
3. **Code style consistent**: Ruff formatter applied with ALL rules.
4. **Modular player/UI system**: Easy to add new implementations.
5. **Network support is clever**: TCP transport handles JSON serialization well.
6. **Frozen dataclasses for events**: Ensures immutability of event objects.

---

## Priority Fixes (Recommended Order)

1. ✅ **GameEngine error handling** (Issue #1) - Game loop will crash otherwise
2. ✅ **EventBus thread safety** (Issue #2) - Data corruption risk
3. ✅ **TcpTransport race condition** (Issue #5) - Hangs on network close
4. ✅ **TerminalUi exception handling** (Issue #3) - Bare except is dangerous
5. ✅ **Network message validation** (Issue #6) - Crash-prone
6. ✅ **Error feedback to players** (Issue #12) - UX issue, no feedback on invalid moves
7. ✅ **Network mode validation** (Issue #9) - Silent failures in CLI

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Critical Issues | 5 |
| High-Priority Issues | 3 |
| Medium-Priority Issues | 5 |
| Low-Priority Issues | 4 |
| **Total Issues** | **17** |

**Estimated Fix Time:** 2-3 hours for critical + high-priority items.
