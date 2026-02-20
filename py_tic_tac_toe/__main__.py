import argparse
import random
import threading
import time
from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal

from py_tic_tac_toe.factories import (
    config_game_engine,
    create_local_players,
    create_network_client_players,
    create_network_host_players,
)
from py_tic_tac_toe.game_engine import GameEngine
from py_tic_tac_toe.ui_pygame import PygameUi
from py_tic_tac_toe.ui_terminal import TerminalUi
from py_tic_tac_toe.ui_tk import TkUi

if TYPE_CHECKING:
    from py_tic_tac_toe.ui import Ui


def main() -> None:
    ui_choices: dict[str, type[Ui]] = {"terminal": TerminalUi, "pygame": PygameUi, "tk": TkUi}

    parser, args = _parse_args(ui_choices.keys())

    # Create game engine and UIs.
    game_engine = GameEngine()
    uis: list[Ui] = [ui_choices[ui](game_engine) for ui in args.ui]

    # Create players based on mode.
    match args.mode:
        case "local":
            if not args.player_x or not args.player_o:
                parser.error("Local mode requires both --player-x and --player-o to be specified.")
            player1, player2 = create_local_players(args.player_x, args.player_o, game_engine.game.board, uis)
        case "network":
            match args.role:
                case "host":
                    # Randomly choose which player is X and which is O.
                    player_types: list[Literal["local", "remote"]] = ["local", "remote"]
                    random.shuffle(player_types)
                    player1, player2 = create_network_host_players(
                        player_types[0],
                        player_types[1],
                        game_engine.game.board,
                        uis,
                        args.port,
                    )
                case "client":
                    player1, player2 = create_network_client_players(game_engine.game.board, uis, args.host, args.port)
                case _:
                    parser.error("Invalid role. Choose 'host' or 'client'.")
        case _:
            parser.error("Invalid mode. Choose 'local' or 'network'.")

    # Set players and connect UI callbacks.
    config_game_engine(game_engine, (player1, player2), uis)

    # Start UI threads and run game.
    ui_threads = [threading.Thread(target=ui.run, daemon=True) for ui in uis]

    for ui_thread in ui_threads:
        ui_thread.start()

    while not all(ui.running for ui in uis):
        time.sleep(0.1)

    game_engine.start_game_loop()

    for ui_thread in ui_threads:
        ui_thread.join()


def _parse_args(ui_type_choices: Iterable[str]) -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    parser = argparse.ArgumentParser()

    parser.add_argument("--mode", choices=("local", "network"), required=True)

    # Local mode.
    parser.add_argument("--player-x", choices=("human", "easy-ai", "hard-ai"))
    parser.add_argument("--player-o", choices=("human", "easy-ai", "hard-ai"))

    # Network mode.
    parser.add_argument("--role", choices=("host", "client"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)

    parser.add_argument("--ui", nargs="+", choices=ui_type_choices, required=True)

    args = parser.parse_args()
    return parser, args


if __name__ == "__main__":
    main()
