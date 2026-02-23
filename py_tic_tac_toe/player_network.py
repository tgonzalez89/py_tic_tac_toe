import contextlib
import threading
from abc import abstractmethod
from collections.abc import Callable
from typing import Any, cast

from py_tic_tac_toe.board import Move, PlayerSymbol
from py_tic_tac_toe.exception import InvalidMoveError, LogicError, NetworkError
from py_tic_tac_toe.game import Game
from py_tic_tac_toe.player import Player
from py_tic_tac_toe.player_local import LocalPlayer
from py_tic_tac_toe.tcp_transport import TcpTransport


class NetworkPlayer(Player):
    def __init__(self, game: Game, transport: TcpTransport, symbol: PlayerSymbol | None = None) -> None:
        self._transport = transport

        if symbol is not None:
            super().__init__(game, symbol)
            self._transport.send({"type": f"assign_symbol:{self.__class__.__name__}", "symbol": symbol})
        else:
            # Receiving class is the opposite of the sending class.
            opposite_class_name = self._get_opposite_class_name()
            self._assign_symbol_event_var = threading.Event()
            self._transport.add_recv_handler(f"assign_symbol:{opposite_class_name}", self._handle_assign_symbol)
            # Wait until the symbol is assigned before proceeding.
            if not self._assign_symbol_event_var.wait(timeout=5.0):
                raise TimeoutError("Symbol assignment timeout")
            self._transport.remove_recv_handler(f"assign_symbol:{opposite_class_name}", self._handle_assign_symbol)
            super().__init__(game, self._symbol)

    @abstractmethod
    def _get_opposite_class_name(self) -> str:
        pass

    def _handle_assign_symbol(self, msg: dict[str, Any]) -> None:
        if not msg.get("type", "").startswith("assign_symbol"):
            raise LogicError("Invalid message type received")
        if msg.get("type", "").split(":")[-1] not in (LocalNetworkPlayer.__name__, RemoteNetworkPlayer.__name__):
            raise LogicError("Invalid sending class received")
        if msg.get("symbol") not in ("X", "O"):
            raise LogicError("Invalid symbol received")

        self._symbol = cast("PlayerSymbol", msg["symbol"])
        self._assign_symbol_event_var.set()


class LocalNetworkPlayer(NetworkPlayer, LocalPlayer):
    # Timeout in seconds for waiting for move acknowledgement from remote player
    ACK_TIMEOUT = 10.0

    def __init__(self, game: Game, transport: TcpTransport, symbol: PlayerSymbol | None = None) -> None:
        NetworkPlayer.__init__(self, game, transport, symbol)
        self._on_error_cbs: list[Callable[[Exception], None]] = []
        self._transport.add_recv_handler("move_ack", self._handle_move_ack)
        self.pending_move: tuple[int, int] | None = None
        self._timeout_timer: threading.Timer | None = None

    def add_on_error_cb(self, callback: Callable[[Exception], None]) -> None:
        self._on_error_cbs.append(callback)

    def _get_opposite_class_name(self) -> str:
        return RemoteNetworkPlayer.__name__

    def queue_move(self, row: int, col: int) -> None:
        """Queue a move and send to remote player without waiting for acknowledgement.

        Starts a timer to handle timeout if acknowledgement is not received.
        """
        self._transport.send({"type": "move_request", "row": row, "col": col})
        self.pending_move = (row, col)
        # Start timeout timer for acknowledgement
        self._timeout_timer = threading.Timer(self.ACK_TIMEOUT, self._handle_ack_timeout)
        self._timeout_timer.start()

    def _handle_move_ack(self, msg: dict[str, Any]) -> None:
        """Handle move acknowledgement from remote player asynchronously."""
        # Cancel timeout timer since ack was received
        if self._timeout_timer:
            self._timeout_timer.cancel()
            self._timeout_timer = None

        if msg.get("type") != "move_ack":
            for callback in self._on_error_cbs:
                callback(NetworkError("Invalid message type received in move acknowledgement"))
            return

        if not msg.get("ok", False):
            error_text = msg.get("error", "Unknown error")
            error_msg = f"Remote player rejected move: {error_text}"
            for callback in self._on_error_cbs:
                callback(NetworkError(error_msg))
            return

        # Queue move once ack is received.
        if self.pending_move is not None:
            row, col = self.pending_move
            super().queue_move(row, col)
            self.pending_move = None

    def _handle_ack_timeout(self) -> None:
        """Handle timeout waiting for acknowledgement from remote player."""
        if self.pending_move is not None:
            error_msg = f"Timeout waiting for move acknowledgement (>{self.ACK_TIMEOUT}s)"
            for callback in self._on_error_cbs:
                callback(NetworkError(error_msg))
            self.pending_move = None
        self._timeout_timer = None


class RemoteNetworkPlayer(NetworkPlayer):
    def _get_opposite_class_name(self) -> str:
        return LocalNetworkPlayer.__name__

    def __init__(self, game: Game, transport: TcpTransport, symbol: PlayerSymbol | None = None) -> None:
        super().__init__(game, transport, symbol)
        self._on_error_cbs: list[Callable[[Exception], None]] = []
        self._transport.add_recv_handler("move_request", self._handle_move_request)

    def add_on_error_cb(self, callback: Callable[[Exception], None]) -> None:
        self._on_error_cbs.append(callback)

    def _handle_move_request(self, msg: dict[str, Any]) -> None:
        """Handle incoming move request from remote player and queue it for validation by the engine."""
        if msg.get("type") != "move_request":
            error_msg = "Invalid message type received"
            with contextlib.suppress(NetworkError):
                self._transport.send({"type": "move_ack", "ok": False, "error": error_msg})
            return

        if not isinstance(msg.get("row"), int) or not isinstance(msg.get("col"), int):
            error_msg = "Invalid move data received"
            with contextlib.suppress(NetworkError):
                self._transport.send({"type": "move_ack", "ok": False, "error": error_msg})
            return

        row: int = msg["row"]
        col: int = msg["col"]

        move = Move(self.symbol, row, col)
        try:
            # Validate the move before applying to ensure invalid moves are rejected and only valid moves are applied.
            self._game.validate_move(move)
            move_ok = True
            error_msg = ""
        except (InvalidMoveError, IndexError) as e:
            move_ok = False
            error_msg = str(e)
            # Do not re-raise the exception here since the move was rejected and the error will be communicated back
            # to the local player via ack.
        finally:
            try:
                self._transport.send({"type": "move_ack", "ok": move_ok, "error": error_msg})
            except NetworkError as e:
                error_msg = f"Failed to send move acknowledgement: {e!s}"
                for callback in self._on_error_cbs:
                    callback(NetworkError(error_msg))
                return

        if move_ok:
            # Queue the move for the engine to validate and apply
            self.queue_move(row, col)

    def start_turn(self) -> None:
        pass
