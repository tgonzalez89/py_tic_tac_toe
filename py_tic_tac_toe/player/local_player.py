from py_tic_tac_toe.event_bus.event_bus import EnableInput, EventBus, InputError, InvalidMove, StartTurn
from py_tic_tac_toe.game.board_utils import PlayerSymbol
from py_tic_tac_toe.player.player import Player


class LocalPlayer(Player):
    def __init__(self, event_bus: EventBus, symbol: PlayerSymbol) -> None:
        super().__init__(event_bus, symbol)
        self._event_bus.subscribe(InvalidMove, self._on_invalid_move)

    def _on_start_turn(self, event: StartTurn) -> None:
        if self._symbol != event.player:
            return

        self._event_bus.publish(EnableInput(self._symbol))

    def _on_invalid_move(self, event: InvalidMove) -> None:
        if self._symbol != event.player:
            return

        self._event_bus.publish(InputError(event.player, event.error_msg))
