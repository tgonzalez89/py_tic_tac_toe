from typing import Final

import pygame

from py_tic_tac_toe.board import BOARD_SIZE
from py_tic_tac_toe.game_engine import GameEngine
from py_tic_tac_toe.ui import Ui


class PygameUi(Ui):
    TITLE: Final = "Tic-Tac-Toe (Pygame)"
    WINDOW_SIZE: Final = 480
    CELL_SIZE: Final = WINDOW_SIZE // BOARD_SIZE
    LINE_WIDTH: Final = 4

    BG_COLOR: Final = (0, 0, 0)
    LINE_COLOR: Final = (127, 127, 127)
    X_COLOR: Final = (191, 63, 63)
    O_COLOR: Final = (63, 63, 191)
    TEXT_COLOR: Final = (255, 255, 255)

    def __init__(self, game_engine: GameEngine) -> None:
        super().__init__(game_engine)
        self._board = self._game_engine.game.board.board.copy()
        self._title = self.TITLE
        self._title_changed = False
        self._end_message = ""

    def run(self) -> None:
        pygame.init()
        self._screen = pygame.display.set_mode((self.WINDOW_SIZE, self.WINDOW_SIZE))
        pygame.display.set_caption(self.TITLE)

        self._font = pygame.font.SysFont(None, 96)
        self._small_font = pygame.font.SysFont(None, 48)
        self._click_font = pygame.font.SysFont(None, 24)

        super().run()
        self._main_loop()

    def enable_input(self) -> None:
        super().enable_input()
        if not self._running:
            return
        self._title = f"{self.TITLE} - Player {self._game_engine.game.current_player_symbol}"
        self._title_changed = True

    def _disable_input(self) -> None:
        super()._disable_input()
        self._title = self.TITLE
        self._title_changed = True

    def _main_loop(self) -> None:
        clock = pygame.time.Clock()
        while self._running:
            clock.tick(30)
            self._handle_events()
            self._render()
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
                    self._stop()
                case pygame.MOUSEBUTTONDOWN:
                    if self._end_message:
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    elif self._input_enabled:
                        self._on_click(event.pos)

    def _render(self) -> None:
        if self._title_changed:
            self._title_changed = False
        pygame.display.set_caption(self._title)
        self._screen.fill(self.BG_COLOR)
        self._draw_grid()
        self._draw_marks()
        self._draw_end_message()
        pygame.display.flip()

    def _on_click(self, pos: tuple[int, int]) -> None:
        x, y = pos
        col = x // self.CELL_SIZE
        row = y // self.CELL_SIZE
        if not (0 <= row < BOARD_SIZE) or not (0 <= col < BOARD_SIZE):
            return
        self._apply_move(row, col)

    def _render_board(self) -> None:
        self._board = self._game_engine.game.board.board.copy()

    def _show_end_message(self, msg: str) -> None:
        self._end_message = msg

    def _on_input_error(self, _exception: Exception) -> None:
        pass

    def _draw_grid(self) -> None:
        for i in range(1, BOARD_SIZE):
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
        for row in range(len(self._board)):
            for col in range(len(self._board[0])):
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
