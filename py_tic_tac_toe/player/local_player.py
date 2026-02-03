from py_tic_tac_toe.game_engine.event import EnableInput, StartTurn
from py_tic_tac_toe.player.player import Player


class LocalPlayer(Player):
    def _on_start_turn(self, event: StartTurn) -> None:
        if self.symbol != event.current_player:
            return

        self.event_bus.publish(EnableInput(self.symbol))
