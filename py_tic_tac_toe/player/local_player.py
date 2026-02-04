from py_tic_tac_toe.event_bus.event_bus import EnableInput, StartTurn
from py_tic_tac_toe.player.player import Player


class LocalPlayer(Player):
    def _on_start_turn(self, event: StartTurn) -> None:
        if self._symbol != event.player:
            return

        self._event_bus.publish(EnableInput(self._symbol))
