import argparse
import threading
from typing import TYPE_CHECKING

from py_tic_tac_toe.game_engine.event import EventBus
from py_tic_tac_toe.game_engine.game_engine import GameEngine
from py_tic_tac_toe.player.ai_player import RandomAIPlayer
from py_tic_tac_toe.player.local_player import LocalPlayer
from py_tic_tac_toe.player.player import Player
from py_tic_tac_toe.ui.pygame import PygameUi
from py_tic_tac_toe.ui.terminal import TerminalUi
from py_tic_tac_toe.ui.tk import TkUi

if TYPE_CHECKING:
    from py_tic_tac_toe.ui.ui import Ui


def _create_player(player_type: str, player_symbol: str, event_bus: EventBus) -> Player:
    match player_type:
        case "human":
            return LocalPlayer(event_bus, player_symbol)
        case "ai":
            return RandomAIPlayer(event_bus, player_symbol)
        case unknown:
            msg = f"Invalid option for player {player_symbol}: {unknown}"
            raise ValueError(msg)


def main() -> None:  # noqa: D103
    ui_choices: dict[str, type[Ui]] = {"terminal": TerminalUi, "pygame": PygameUi, "tk": TkUi}

    parser = argparse.ArgumentParser()
    parser.add_argument("player_x", choices=("human", "ai"))
    parser.add_argument("player_o", choices=("human", "ai"))
    parser.add_argument("ui", nargs="+", choices=ui_choices.keys())
    args = parser.parse_args()
    if not (1 <= len(args.ui) <= len(ui_choices)):
        parser.error("Specify between 1 and 3 UI backends")
    if len(args.ui) != len(set(args.ui)):
        parser.error("UI arguments must be unique")

    event_bus = EventBus()

    _player_x = _create_player(args.player_x, "X", event_bus)
    _player_o = _create_player(args.player_o, "O", event_bus)

    uis: dict[str, Ui] = {ui: ui_choices[ui](event_bus) for ui in args.ui}
    ui_threads: dict[str, threading.Thread] = {ui: threading.Thread(target=uis[ui].start, daemon=True) for ui in uis}

    for ui_thread in ui_threads.values():
        ui_thread.start()

    while not all(ui.started for ui in uis.values()):
        pass

    engine = GameEngine(event_bus)
    engine.start()

    for ui_thread in ui_threads.values():
        ui_thread.join()
