import sys
from typing import Final

import pygame

from py_tic_tac_toe.event_bus.event_bus import EnableInput, EventBus, InvalidMove, MoveRequested, StateUpdated
from py_tic_tac_toe.ui.ui import Ui


class PygameUi(Ui):
    TITLE: Final = "Tic-Tac-Toe (Pygame)"
    WINDOW_SIZE: Final = 480
    GRID_SIZE: Final = 3
    CELL_SIZE: Final = WINDOW_SIZE // GRID_SIZE
    LINE_WIDTH: Final = 4

    BG_COLOR: Final = (0, 0, 0)
    LINE_COLOR: Final = (127, 127, 127)
    X_COLOR: Final = (191, 63, 63)
    O_COLOR: Final = (63, 63, 191)
    TEXT_COLOR: Final = (255, 255, 255)

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__(event_bus)

        self._board: list[list[str | None]]
        self._current_player: str
        self._input_enabled = False
        self._game_running = False
        self._title = self.TITLE
        self._title_changed = False
        self._end_message = ""

    def start(self) -> None:  # noqa: D102
        pygame.init()
        self._screen = pygame.display.set_mode((self.WINDOW_SIZE, self.WINDOW_SIZE))
        pygame.display.set_caption(self.TITLE)

        self._font = pygame.font.SysFont(None, 96)
        self._small_font = pygame.font.SysFont(None, 48)
        self._click_font = pygame.font.SysFont(None, 24)

        self._game_running = True
        self._started = True
        self._main_loop()

    def _enable_input(self, event: EnableInput) -> None:
        self._current_player = event.player
        self._input_enabled = True
        self._title = f"{self.TITLE} - Player {self._current_player}"
        self._title_changed = True

    def _disable_input(self) -> None:
        self._input_enabled = False
        self._title = self.TITLE
        self._title_changed = True

    # -----------------------------
    # Main loop
    # -----------------------------

    def _main_loop(self) -> None:
        clock = pygame.time.Clock()

        while True:
            clock.tick(60)
            if self._title_changed:
                self._title_changed = False
            pygame.display.set_caption(self._title)
            self._handle_events()
            self._render()

    # -----------------------------
    # Rendering
    # -----------------------------

    def _render(self) -> None:
        self._screen.fill(self.BG_COLOR)
        self._draw_grid()
        self._draw_marks()
        self._draw_end_message()
        pygame.display.flip()

    def _draw_grid(self) -> None:
        for i in range(1, self.GRID_SIZE):
            pygame.draw.line(
                self._screen,
                self.LINE_COLOR,
                (0, i * self.CELL_SIZE),
                (self.WINDOW_SIZE, i * self.CELL_SIZE),
                self.LINE_WIDTH,
            )
            pygame.draw.line(
                self._screen,
                self.LINE_COLOR,
                (i * self.CELL_SIZE, 0),
                (i * self.CELL_SIZE, self.WINDOW_SIZE),
                self.LINE_WIDTH,
            )

    def _draw_marks(self) -> None:
        if not hasattr(self, "_board"):
            return

        for row in range(3):
            for col in range(3):
                value = self._board[row][col]

                text = self._font.render(value, True, self.X_COLOR if value == "X" else self.O_COLOR)  # noqa: FBT003
                rect = text.get_rect(
                    center=(col * self.CELL_SIZE + self.CELL_SIZE // 2, row * self.CELL_SIZE + self.CELL_SIZE // 2),
                )
                self._screen.blit(text, rect)

    def _draw_end_message(self) -> None:
        if not self._end_message:
            return

        main_text = self._small_font.render(self._end_message, True, self.TEXT_COLOR)  # noqa: FBT003
        click_text = self._click_font.render("Click anywhere to exit", True, self.TEXT_COLOR)  # noqa: FBT003
        main_rect = main_text.get_rect(center=(self.WINDOW_SIZE // 2, self.WINDOW_SIZE // 2 - 20))
        click_rect = click_text.get_rect(center=(self.WINDOW_SIZE // 2, self.WINDOW_SIZE // 2 + 20))
        self._screen.blit(main_text, main_rect)
        self._screen.blit(click_text, click_rect)

    # -----------------------------
    # Event handling
    # -----------------------------

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if not self._game_running:
                    pygame.quit()
                    sys.exit()
                self._on_click(event.pos)

    def _on_click(self, pos: tuple[int, int]) -> None:
        if not self._input_enabled:
            return

        x, y = pos
        col = x // self.CELL_SIZE
        row = y // self.CELL_SIZE

        if row > 2 or col > 2:  # noqa: PLR2004
            return

        self._disable_input()
        self._event_bus.publish(MoveRequested(self._current_player, row, col))

    def _on_state_updated(self, event: StateUpdated) -> None:
        self._current_player = event.player

        self._board = event.board

        if event.winner:
            self._show_end_message(f"Winner: {event.winner}")
        elif all(all(cell is not None for cell in row) for row in event.board):
            self._show_end_message("It's a draw")

    def _show_end_message(self, msg: str) -> None:
        self._game_running = False
        self._end_message = msg

    def _on_invalid_move(self, event: InvalidMove) -> None:
        self._enable_input(EnableInput(event.player))
