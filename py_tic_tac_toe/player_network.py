import threading
from abc import abstractmethod
from collections.abc import Callable
from typing import Any, cast

from py_tic_tac_toe.board import Move, PlayerSymbol
from py_tic_tac_toe.exception import LogicError
from py_tic_tac_toe.game import Game
from py_tic_tac_toe.player import Player
from py_tic_tac_toe.player_local import LocalPlayer
from py_tic_tac_toe.tcp_transport import TcpTransport


class NetworkPlayer(Player):
    def __init__(self, game: Game, transport: TcpTransport, symbol: PlayerSymbol | None = None) -> None:
        self._transport = transport

        if symbol is not None:
            super().__init__(symbol, game)
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
            super().__init__(self._symbol, game)

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

    def apply_move(self, row: int, col: int) -> bool:
        if super().apply_move(row, col):
            self._transport.send({"type": "move", "row": row, "col": col})
            return True
        return False


class RemoteNetworkPlayer(NetworkPlayer):
    def _get_opposite_class_name(self) -> str:
        return LocalNetworkPlayer.__name__

    def __init__(self, game: Game, transport: TcpTransport, symbol: PlayerSymbol | None = None) -> None:
        super().__init__(game, transport, symbol)
        self._apply_move_cb: Callable[[int, int], bool]
        self._transport.add_recv_handler("move", self._handle_move)

    def set_apply_move_cb(self, callback: Callable[[int, int], bool]) -> None:
        self._apply_move_cb = callback

    def _handle_move(self, msg: dict[str, Any]) -> None:
        if msg.get("type") != "move":
            raise LogicError("Invalid message type received")
        if not isinstance(msg.get("row"), int) or not isinstance(msg.get("col"), int):
            raise LogicError("Invalid move data received")

        row: int = msg["row"]
        col: int = msg["col"]
        self._apply_move_cb(row, col)

    def start_turn(self) -> None:
        pass

    def apply_move(self, row: int, col: int) -> bool:
        self._game.apply_move(Move(self._symbol, row, col))
        return True
