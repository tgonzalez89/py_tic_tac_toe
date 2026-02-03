import os

import pygame

from py_tic_tac_toe.game_engine.event import EnableInput, EventBus, InvalidMove, MoveRequested, StateUpdated
from py_tic_tac_toe.ui.ui import Ui


class PygameUi(Ui):
    TITLE = "Tic-Tac-Toe (Pygame)"
    WINDOW_SIZE = 480
    GRID_SIZE = 3
    CELL_SIZE = WINDOW_SIZE // GRID_SIZE
    LINE_WIDTH = 4

    BG_COLOR = (0, 0, 0)
    LINE_COLOR = (127, 127, 127)
    X_COLOR = (191, 63, 63)
    O_COLOR = (63, 63, 191)
    TEXT_COLOR = (255, 255, 255)

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__(event_bus)

        self.board: list[list[str | None]]
        self.current_player: str
        self.input_enabled = False
        self.game_running = False
        self.title = self.TITLE
        self.title_changed = False
        self.end_message = ""

    def start(self) -> None:  # noqa: D102
        pygame.init()
        self.screen = pygame.display.set_mode((self.WINDOW_SIZE, self.WINDOW_SIZE))
        pygame.display.set_caption(self.TITLE)

        self.font = pygame.font.SysFont(None, 96)
        self.small_font = pygame.font.SysFont(None, 48)
        self.click_font = pygame.font.SysFont(None, 24)

        self.game_running = True
        self._started = True
        self._main_loop()

    def _enable_input(self, event: EnableInput) -> None:
        self.current_player = event.player
        self.input_enabled = True
        self.title = f"{self.TITLE} - Player {self.current_player}"
        self.title_changed = True

    def _disable_input(self) -> None:
        self.input_enabled = False
        self.title = self.TITLE
        self.title_changed = True

    # -----------------------------
    # Main loop
    # -----------------------------

    def _main_loop(self) -> None:
        clock = pygame.time.Clock()

        while True:
            clock.tick(60)
            if self.title_changed:
                self.title_changed = False
            pygame.display.set_caption(self.title)
            self._handle_events()
            self._render()

    # -----------------------------
    # Rendering
    # -----------------------------

    def _render(self) -> None:
        self.screen.fill(self.BG_COLOR)
        self._draw_grid()
        self._draw_marks()
        self._draw_end_message()
        pygame.display.flip()

    def _draw_grid(self) -> None:
        for i in range(1, self.GRID_SIZE):
            pygame.draw.line(
                self.screen,
                self.LINE_COLOR,
                (0, i * self.CELL_SIZE),
                (self.WINDOW_SIZE, i * self.CELL_SIZE),
                self.LINE_WIDTH,
            )
            pygame.draw.line(
                self.screen,
                self.LINE_COLOR,
                (i * self.CELL_SIZE, 0),
                (i * self.CELL_SIZE, self.WINDOW_SIZE),
                self.LINE_WIDTH,
            )

    def _draw_marks(self) -> None:
        for row in range(3):
            for col in range(3):
                value = self.board[row][col]

                text = self.font.render(value, True, self.X_COLOR if value == "X" else self.O_COLOR)  # noqa: FBT003
                rect = text.get_rect(
                    center=(col * self.CELL_SIZE + self.CELL_SIZE // 2, row * self.CELL_SIZE + self.CELL_SIZE // 2),
                )
                self.screen.blit(text, rect)

    def _draw_end_message(self) -> None:
        if not self.end_message:
            return

        main_text = self.small_font.render(self.end_message, True, self.TEXT_COLOR)  # noqa: FBT003
        click_text = self.click_font.render("Click anywhere to exit", True, self.TEXT_COLOR)  # noqa: FBT003
        main_rect = main_text.get_rect(center=(self.WINDOW_SIZE // 2, self.WINDOW_SIZE // 2 - 20))
        click_rect = click_text.get_rect(center=(self.WINDOW_SIZE // 2, self.WINDOW_SIZE // 2 + 20))
        self.screen.blit(main_text, main_rect)
        self.screen.blit(click_text, click_rect)

    # -----------------------------
    # Event handling
    # -----------------------------

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                os._exit(0)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if not self.game_running:
                    pygame.quit()
                    os._exit(0)
                self._on_click(event.pos)

    def _on_click(self, pos: tuple[int, int]) -> None:
        if not self.input_enabled:
            return

        x, y = pos
        col = x // self.CELL_SIZE
        row = y // self.CELL_SIZE

        if row > 2 or col > 2:  # noqa: PLR2004
            return

        self._disable_input()

        try:
            self.event_bus.publish(MoveRequested(self.current_player, row, col))
        except ValueError:
            self._enable_input(EnableInput(self.current_player))

    def _on_state_updated(self, event: StateUpdated) -> None:
        self.current_player = event.current_player

        self.board = event.board

        if event.winner:
            self._show_end_message(f"Winner: {event.winner}")
        elif all(all(cell is not None for cell in row) for row in event.board):
            self._show_end_message("It's a draw")

    def _show_end_message(self, msg: str) -> None:
        self.game_running = False
        self.end_message = msg

    def _on_error(self, event: InvalidMove) -> None:
        pass
