import random

from py_tic_tac_toe.event_bus.event_bus import BoardProvided, BoardRequested, EventBus, MoveRequested, StartTurn
from py_tic_tac_toe.player.player import Player
from py_tic_tac_toe.util.errors import LogicError


class RandomAIPlayer(Player):
    def __init__(self, event_bus: EventBus, symbol: str) -> None:
        super().__init__(event_bus, symbol)
        self._event_bus.subscribe(BoardProvided, self._on_board_provided)

    def _on_start_turn(self, event: StartTurn) -> None:
        if self._symbol != event.player:
            return

        # Request board to make move decision
        self._event_bus.publish(BoardRequested(self._symbol))

    def _on_board_provided(self, event: BoardProvided) -> None:
        if self._symbol != event.player:
            return

        choices = [(r, c) for r in range(3) for c in range(3) if event.board[r][c] is None]
        if not choices:
            msg = f"No moves available for player {self._symbol}, but game not over"
            raise LogicError(msg)
        row, col = random.choice(choices)

        self._event_bus.publish(MoveRequested(self._symbol, row, col))
