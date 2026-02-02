import argparse
import threading

from py_tic_tac_toe.engine.game_engine import GameEngine
from py_tic_tac_toe.ui.pygame import PygameUI
from py_tic_tac_toe.ui.terminal import TerminalUI
from py_tic_tac_toe.ui.tk import TkUI


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", action="store_true")
    parser.add_argument("--tk", action="store_true")
    parser.add_argument("--pygame", action="store_true")
    args = parser.parse_args()

    if not args.terminal and not args.tk and not args.pygame:
        return

    engine = GameEngine()

    if args.terminal:
        if args.pygame or args.tk:
            # If Pygame or Tk are also given, Terminal should not block the main thread.
            terminal_ui = TerminalUI(engine)
            threading.Thread(target=terminal_ui.start, daemon=True).start()
        else:
            TerminalUI(engine).start()  # Blocking

    if args.pygame:
        if args.tk:
            # If Tk is also given, Pygame should not block the main thread.
            pygame_ui = PygameUI(engine)
            threading.Thread(target=pygame_ui.start, daemon=True).start()
        else:
            PygameUI(engine).start()  # Blocking

    if args.tk:
        TkUI(engine).start()  # Blocking. Tk can only run in the main thread, so it goes last.
