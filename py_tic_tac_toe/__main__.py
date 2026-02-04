# ruff: noqa: ERA001

import argparse
import random
import threading
from typing import TYPE_CHECKING

from py_tic_tac_toe.event_bus.event_bus import EventBus
from py_tic_tac_toe.game_engine.game_engine import GameEngine
from py_tic_tac_toe.network.tcp_transport import create_client_transport, create_host_transport
from py_tic_tac_toe.player.ai_player import RandomAIPlayer
from py_tic_tac_toe.player.local_player import LocalPlayer
from py_tic_tac_toe.player.network_players import LocalNetworkPlayer, RemoteNetworkPlayer
from py_tic_tac_toe.ui.pygame import PygameUi
from py_tic_tac_toe.ui.terminal import TerminalUi
from py_tic_tac_toe.ui.tk import TkUi

if TYPE_CHECKING:
    from py_tic_tac_toe.ui.ui import Ui


def main() -> None:  # noqa: D103
    ui_choices: dict[str, type[Ui]] = {"terminal": TerminalUi, "pygame": PygameUi, "tk": TkUi}

    parser = argparse.ArgumentParser()

    parser.add_argument("--mode", choices=("local", "network"), required=True)

    # local mode
    parser.add_argument("--player-x", choices=("human", "ai"))
    parser.add_argument("--player-o", choices=("human", "ai"))

    # network mode
    parser.add_argument("--role", choices=("host", "client"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)

    parser.add_argument("--ui", nargs="+", choices=ui_choices.keys(), required=True)

    args = parser.parse_args()

    event_bus = EventBus()

    # -----------------------------
    # UI
    # -----------------------------
    uis: list[Ui] = [ui_choices[ui](event_bus) for ui in args.ui]
    ui_threads = [threading.Thread(target=ui.start, daemon=True) for ui in uis]

    for ui_thread in ui_threads:
        ui_thread.start()

    while not all(ui.started for ui in uis):
        pass

    # -----------------------------
    # MODE: LOCAL
    # -----------------------------
    if args.mode == "local":
        if not args.player_x or not args.player_o:
            parser.error("local mode requires --player-x and --player-o")

        if args.player_x == "human":
            LocalPlayer(event_bus, "X")
        else:
            RandomAIPlayer(event_bus, "X")

        if args.player_o == "human":
            LocalPlayer(event_bus, "O")
        else:
            RandomAIPlayer(event_bus, "O")

        engine = GameEngine(event_bus)
        engine.start()

    # -----------------------------
    # MODE: NETWORK
    # -----------------------------
    elif args.role == "host":
        transport = create_host_transport(args.port)

        host_symbol = random.choice(("X", "O"))
        remote_symbol = "O" if host_symbol == "X" else "X"

        LocalPlayer(event_bus, host_symbol)
        RemoteNetworkPlayer(event_bus, remote_symbol, transport)

        engine = GameEngine(event_bus)
        engine.start()

    else:
        transport = create_client_transport(args.host, args.port)
        LocalNetworkPlayer(event_bus, transport)

    for ui_thread in ui_threads:
        ui_thread.join()
