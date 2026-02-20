import threading
from abc import abstractmethod
from typing import Any, cast

from py_tic_tac_toe.board import Board, Move, PlayerSymbol
from py_tic_tac_toe.exception import InvalidMoveError, LogicError, NetworkError
from py_tic_tac_toe.player import Player
from py_tic_tac_toe.player_local import LocalPlayer
from py_tic_tac_toe.tcp_transport import TcpTransport


class NetworkPlayer(Player):
    def __init__(self, transport: TcpTransport, symbol: PlayerSymbol | None = None) -> None:
        self._transport = transport

        if symbol is not None:
            super().__init__(symbol)
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
            super().__init__(self._symbol)

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
    def _get_opposite_class_name(self) -> str:
        return RemoteNetworkPlayer.__name__

    def queue_move(self, row: int, col: int) -> None:
        """Queue a move and wait for remote validation before returning.

        Raises NetworkError if validation fails or connection is lost.
        """
        try:
            # Send move to remote player
            self._transport.send({"type": "move_request", "row": row, "col": col})
        except OSError as e:
            msg = f"Failed to send move: connection lost - {e}"
            raise NetworkError(msg) from e

        # Wait for acknowledgement from remote player (hardcoded 5 second timeout)
        timeout = 5.0
        ack_msg = self._transport.recv(block=True, timeout=timeout)

        if ack_msg is None:
            raise NetworkError("No acknowledgement received from remote player (timeout)")

        if ack_msg.get("type") != "move_ack":
            raise NetworkError("Received unexpected message instead of acknowledgement")

        if not ack_msg.get("ok", False):
            error_text = ack_msg.get("error", "Unknown error")
            msg = f"Remote player rejected move: {error_text}"
            raise NetworkError(msg)

        # Move was accepted, queue it locally
        super().queue_move(row, col)


class RemoteNetworkPlayer(NetworkPlayer):
    def _get_opposite_class_name(self) -> str:
        return LocalNetworkPlayer.__name__

    def __init__(self, transport: TcpTransport, board: Board, symbol: PlayerSymbol | None = None) -> None:
        self._board = board
        super().__init__(transport, symbol)
        self._transport.add_recv_handler("move_request", self._handle_move_request)

    def _handle_move_request(self, msg: dict[str, Any]) -> None:
        """Handle incoming move request from remote player, validate it, and send acknowledgement."""
        if msg.get("type") != "move_request":
            raise LogicError("Invalid message type received")

        if not isinstance(msg.get("row"), int) or not isinstance(msg.get("col"), int):
            raise LogicError("Invalid move data received")

        row: int = msg["row"]
        col: int = msg["col"]

        # Validate the move
        ok = True
        error_msg = ""

        try:
            move = Move(self.symbol, row, col)
            self._board.validate_move(move)
        except (IndexError, InvalidMoveError) as e:
            ok = False
            error_msg = str(e)

        # Send acknowledgement back
        self._transport.send({"type": "move_ack", "ok": ok, "error": error_msg})

        # If move was valid, queue it
        if ok:
            self.queue_move(row, col)

    def start_turn(self) -> None:
        pass
