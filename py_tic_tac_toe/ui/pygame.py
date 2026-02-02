import os

import pygame

from py_tic_tac_toe.engine.game_engine import GameEngine, MoveRequested, StateUpdated


class PygameUI:
    WINDOW_SIZE = 480
    GRID_SIZE = 3
    CELL_SIZE = WINDOW_SIZE // GRID_SIZE
    LINE_WIDTH = 4

    BG_COLOR = (30, 30, 30)
    LINE_COLOR = (200, 200, 200)
    X_COLOR = (200, 70, 70)
    O_COLOR = (70, 70, 200)
    TEXT_COLOR = (240, 240, 240)

    def __init__(self, game_engine: GameEngine) -> None:
        self.game_engine = game_engine
        self.current_player = "X"
        self.game_over = False
        self.board = game_engine.game.board
        self.end_message = ""

        pygame.init()
        self.screen = pygame.display.set_mode((self.WINDOW_SIZE, self.WINDOW_SIZE))
        pygame.display.set_caption("Tic-Tac-Toe (Pygame)")

        self.font = pygame.font.SysFont(None, 96)
        self.small_font = pygame.font.SysFont(None, 48)
        self.click_font = pygame.font.SysFont(None, 24)

        self.game_engine.subscribe(StateUpdated, self._on_state_updated)

    def start(self) -> None:  # noqa: D102
        self._main_loop()

    # -----------------------------
    # Main loop
    # -----------------------------

    def _main_loop(self) -> None:
        clock = pygame.time.Clock()

        while True:
            clock.tick(60)
            self._handle_events()
            self._render()

    # -----------------------------
    # Event handling
    # -----------------------------

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                os._exit(0)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.game_over:
                    pygame.quit()
                    os._exit(0)
                elif self.current_player is not None:
                    self._handle_click(event.pos)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        x, y = pos
        col = x // self.CELL_SIZE
        row = y // self.CELL_SIZE

        if row > 2 or col > 2:  # noqa: PLR2004
            return

        self.game_engine.on_move_requested(
            MoveRequested(
                player=self.current_player,
                row=row,
                col=col,
            ),
        )

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

                text = self.font.render(
                    value,
                    True,  # noqa: FBT003
                    self.X_COLOR if value == "X" else self.O_COLOR,
                )
                rect = text.get_rect(
                    center=(
                        col * self.CELL_SIZE + self.CELL_SIZE // 2,
                        row * self.CELL_SIZE + self.CELL_SIZE // 2,
                    ),
                )
                self.screen.blit(text, rect)

    def _draw_end_message(self) -> None:
        if self.end_message:
            main_text = self.small_font.render(
                self.end_message,
                True,  # noqa: FBT003
                self.TEXT_COLOR,
            )
            click_text = self.click_font.render(
                "Click anywhere to exit",
                True,  # noqa: FBT003
                self.TEXT_COLOR,
            )
            main_rect = main_text.get_rect(center=(self.WINDOW_SIZE // 2, self.WINDOW_SIZE // 2 - 20))
            click_rect = click_text.get_rect(center=(self.WINDOW_SIZE // 2, self.WINDOW_SIZE // 2 + 20))
            self.screen.blit(main_text, main_rect)
            self.screen.blit(click_text, click_rect)

    # -----------------------------
    # State updates
    # -----------------------------

    def _on_state_updated(self, event: StateUpdated) -> None:
        self.board = event.board
        self.current_player = event.current_player

        if event.winner:
            self._show_end_message(f"Winner: {event.winner}")
        elif all(all(cell is not None for cell in row) for row in event.board):
            self._show_end_message("It's a draw")
        else:
            pygame.display.set_caption(f"Tic-Tac-Toe (Tk) - Player {self.current_player}")

    def _show_end_message(self, message: str) -> None:
        self.game_over = True
        self.end_message = message
