from collections.abc import Callable
from dataclasses import dataclass

from py_tic_tac_toe.domain.game import Move, TicTacToe


@dataclass
class StateUpdated:
    board: list[list[str | None]]
    current_player: str
    winner: str | None


@dataclass
class MoveRequested:
    player: str
    row: int
    col: int


class GameEngine:
    def __init__(self) -> None:
        self.game = TicTacToe()
        self.subscribers: dict[type, list[Callable[[object], None]]] = {}
        self.running = False

    def subscribe(self, event_type: type, handler: Callable[[object], None]) -> None:  # noqa: D102
        self.subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: object) -> None:  # noqa: D102
        for handler in self.subscribers.get(type(event), []):
            handler(event)

    def on_move_requested(self, event: MoveRequested) -> None:  # noqa: D102
        try:
            self.game.apply_move(Move(event.player, event.row, event.col))
        except ValueError as e:
            self.publish(e)
            return

        self.publish(
            StateUpdated(
                board=self.game.board,
                current_player=self.game.current_player,
                winner=self.game.winner,
            ),
        )
