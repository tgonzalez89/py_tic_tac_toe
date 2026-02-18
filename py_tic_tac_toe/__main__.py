# ruff: noqa: ERA001

import argparse
import random
import threading
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from py_tic_tac_toe.game_engine import GameEngine
from py_tic_tac_toe.player_ai import HardAiPlayer, RandomAiPlayer
from py_tic_tac_toe.player_local import LocalPlayer
from py_tic_tac_toe.player_network import LocalNetworkPlayer, RemoteNetworkPlayer
from py_tic_tac_toe.tcp_transport import TcpTransport, create_client_transport, create_host_transport
from py_tic_tac_toe.ui_pygame import PygameUi
from py_tic_tac_toe.ui_terminal import TerminalUi
from py_tic_tac_toe.ui_tk import TkUi

if TYPE_CHECKING:
    from py_tic_tac_toe.board import PlayerSymbol
    from py_tic_tac_toe.player import Player
    from py_tic_tac_toe.ui import Ui


def main() -> None:  # noqa: C901, PLR0912, PLR0915
    ui_choices: dict[str, type[Ui]] = {"terminal": TerminalUi, "pygame": PygameUi, "tk": TkUi}

    parser, args = _parse_args(ui_choices.keys())

    # Build game components

    game_engine = GameEngine()
    player1: Player
    player2: Player
    uis: list[Ui] = [ui_choices[ui](game_engine) for ui in args.ui]

    # -----------------------------
    # MODE: LOCAL
    # -----------------------------
    if args.mode == "local":
        if not args.player_x or not args.player_o:
            parser.error("local mode requires --player-x and --player-o")

        match args.player_x:
            case "human":
                player1 = LocalPlayer("X", game_engine.game)
                for ui in uis:
                    player1.add_enable_input_cb(ui.enable_input)
                    player1.add_input_error_cb(ui.on_input_error)
            case "easy-ai":
                player1 = RandomAiPlayer("X", game_engine.game)
                player1.set_apply_move_cb(game_engine.apply_move)
            case "hard-ai":
                player1 = HardAiPlayer("X", game_engine.game)
                player1.set_apply_move_cb(game_engine.apply_move)
            case _:
                parser.error(f"Invalid choice for --player-x: {args.player_x}")

        match args.player_o:
            case "human":
                player2 = LocalPlayer("O", game_engine.game)
                for ui in uis:
                    player2.add_enable_input_cb(ui.enable_input)
                    player2.add_input_error_cb(ui.on_input_error)
            case "easy-ai":
                player2 = RandomAiPlayer("O", game_engine.game)
                player2.set_apply_move_cb(game_engine.apply_move)
            case "hard-ai":
                player2 = HardAiPlayer("O", game_engine.game)
                player2.set_apply_move_cb(game_engine.apply_move)
            case _:
                parser.error(f"Invalid choice for --player-o: {args.player_o}")

    # -----------------------------
    # MODE: NETWORK
    # -----------------------------
    else:
        if not args.role:
            parser.error("network mode requires --role")

        match args.role:
            case "host":
                executor = ThreadPoolExecutor()
                future = executor.submit(create_host_transport, args.port)
                while not future.done():
                    time.sleep(1)
                    print("Waiting for client to connect...")  # noqa: T201
                transport: TcpTransport = future.result()
                host_symbol: PlayerSymbol = random.choice(("X", "O"))
                client_symbol: PlayerSymbol = "O" if host_symbol == "X" else "X"
                player1 = LocalNetworkPlayer(game_engine.game, transport, host_symbol)
                player2 = RemoteNetworkPlayer(game_engine.game, transport, client_symbol)
                for ui in uis:
                    player1.add_enable_input_cb(ui.enable_input)
                    player1.add_input_error_cb(ui.on_input_error)
                player2.set_apply_move_cb(game_engine.apply_move)
            case "client":
                transport = create_client_transport(args.host, args.port)
                player1 = RemoteNetworkPlayer(game_engine.game, transport)
                player2 = LocalNetworkPlayer(game_engine.game, transport)
                player1.set_apply_move_cb(game_engine.apply_move)
                for ui in uis:
                    player2.add_enable_input_cb(ui.enable_input)
                    player2.add_input_error_cb(ui.on_input_error)
            case _:
                parser.error(f"Invalid choice for --role: {args.role}")

    game_engine.set_players(player1, player2)
    for ui in uis:
        game_engine.add_board_updated_cb(ui.on_board_updated)

    # -----------------------------
    # UI
    # -----------------------------
    ui_threads = [threading.Thread(target=ui.run, daemon=True) for ui in uis]

    for ui_thread in ui_threads:
        ui_thread.start()

    while not all(ui.running for ui in uis):
        time.sleep(0.1)

    game_engine.start()

    for ui_thread in ui_threads:
        ui_thread.join()


def _parse_args(ui_choices: Iterable[str]) -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    parser = argparse.ArgumentParser()

    parser.add_argument("--mode", choices=("local", "network"), required=True)

    # local mode
    parser.add_argument("--player-x", choices=("human", "easy-ai", "hard-ai"))
    parser.add_argument("--player-o", choices=("human", "easy-ai", "hard-ai"))

    # network mode
    parser.add_argument("--role", choices=("host", "client"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)

    parser.add_argument("--ui", nargs="+", choices=ui_choices, required=True)

    args = parser.parse_args()
    return parser, args
