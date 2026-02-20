from abc import ABC, abstractmethod
from queue import Empty, Full, Queue

from py_tic_tac_toe.board import PlayerSymbol
from py_tic_tac_toe.exception import LogicError


class Player(ABC):
    def __init__(self, symbol: PlayerSymbol) -> None:
        self._symbol = symbol
        self._move_queue: Queue[tuple[int, int]] = Queue(maxsize=1)

    @property
    def symbol(self) -> PlayerSymbol:
        return self._symbol

    @abstractmethod
    def start_turn(self) -> None:
        pass

    def get_pending_move(self, *, block: bool = False, timeout: float | None = None) -> tuple[int, int] | None:
        """Get the next pending move if one is available."""
        try:
            return self._move_queue.get(block=block, timeout=timeout)
        except Empty:
            return None

    def queue_move(self, row: int, col: int) -> None:
        """Queue a move to be processed by the game engine."""
        try:
            self._move_queue.put_nowait((row, col))
        except Full as e:
            raise LogicError("Pending move queue is full.") from e
