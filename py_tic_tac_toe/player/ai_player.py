import random

from py_tic_tac_toe.game_engine.event import MoveRequested, StartTurn
from py_tic_tac_toe.player.player import Player


class RandomAIPlayer(Player):
    def _on_start_turn(self, event: StartTurn) -> None:
        if self.symbol != event.current_player:
            return

        choices = [(r, c) for r in range(3) for c in range(3) if event.board[r][c] is None]
        if not choices:
            return
        row, col = random.choice(choices)  # noqa: S311

        self.event_bus.publish(MoveRequested(self.symbol, row, col))
