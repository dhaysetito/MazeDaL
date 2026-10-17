import themes

from maze_structure import Maze
from parser import Parser


class MazeRenderer:
    """ANSI terminal maze renderer."""

    DIRECTION_OFFSETS: dict[str, tuple[int, int]] = {
        "N": (0, -1),
        "S": (0, 1),
        "E": (1, 0),
        "W": (-1, 0),
    }

    def __init__(
        self,
        maze: Maze,
        config: Parser,
        path: list[tuple[int, int]] | None = None,
        theme: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize maze renderer.

        Args:
            maze: Maze structure.
            config: Maze configuration parser.
            path: Optional solution path.
            theme: Optional renderer theme.
        """
        self.maze = maze
        self.config = config
        self.path = path
        self.path_progress: int | None = None
        self.current_path_point: tuple[int, int] | None = None

        if theme is None:
            self.theme = themes.DEFAULT_THEME

        else:
            self.theme = theme

        self.real_width = (self.maze.width * 2) + 1
        self.real_height = (self.maze.height * 2) + 1

        self._update_theme()

        self.canvas: list[list[str]] = []

    def _update_theme(self) -> None:
        """
        Update renderer theme attributes.

        Loads colors and blocks from the
        active theme configuration.
        """
        self.wall_block = self.theme["wall_block"]
        self.path_block = self.theme["path_block"]
        self.entry_block = self.theme["entry_block"]
        self.exit_block = self.theme["exit_block"]
        self.solve_block = self.theme["solve_block"]
        self.point_block = self.theme.get("point_block", self.solve_block)

        self.wall_color = self.theme["wall"]
        self.bg_color = self.theme["bg"]
        self.path_color = self.theme["path"]
        self.entry_color = self.theme["entry"]
        self.exit_color = self.theme["exit"]

        self.reset = self.theme["reset"]

    def _create_canvas(self) -> None:
        """
        Create fresh renderer canvas.

        Initializes the terminal grid using
        wall blocks and active theme colors.
        """
        self.canvas = [
            [
                (
                    f"{self.wall_color}"
                    f"{self.wall_block}"
                    f"{self.reset}"
                )
                for _ in range(self.real_width)
            ]
            for _ in range(self.real_height)
        ]

    def _paint(self, x: int, y: int, color: str, block: str) -> None:
        """
        Paint a single canvas block.

        Args:
            x: Canvas x coordinate.
            y: Canvas y coordinate.
            color: ANSI color sequence.
            block: Render block character.
        """
        self.canvas[y][x] = f"{color}{block}{self.reset}"

    def _draw_cells(self) -> None:
        """
        Draw maze cells and corridors.

        Renders walkable areas using the active
        visual theme.
        """
        for y in range(self.maze.height):

            for x in range(self.maze.width):

                cx = (x * 2) + 1
                cy = (y * 2) + 1

                cell = self.maze.grid[y][x]
                self._paint(
                    cx,
                    cy,
                    self.bg_color,
                    self.path_block,
                )

                for direction, (dx, dy) in (
                    self.DIRECTION_OFFSETS.items()
                ):
                    if not cell.has_wall(direction):
                        nx = cx + dx
                        ny = cy + dy
                        if (
                            0 <= nx < self.real_width and
                            0 <= ny < self.real_height
                        ):
                            self._paint(
                                nx,
                                ny,
                                self.bg_color,
                                self.path_block,
                            )

    def _draw_path(self) -> None:
        """
        Draw shortest solution path.

        Paints path cells and connectors
        between adjacent solution positions.
        """
        if not self.path:
            self.current_path_point = None
            return

        visual_path: list[tuple[int, int]] = []
        first_x, first_y = self.path[0]
        visual_path.append(((first_x * 2) + 1, (first_y * 2) + 1))

        for i in range(len(self.path) - 1):
            px, py = self.path[i]
            nx, ny = self.path[i + 1]
            cell_x = (px * 2) + 1
            cell_y = (py * 2) + 1
            visual_path.append((cell_x + (nx - px), cell_y + (ny - py)))
            visual_path.append(((nx * 2) + 1, (ny * 2) + 1))

        if self.path_progress is not None:
            visual_path = visual_path[:self.path_progress]
            self.current_path_point = visual_path[-1] if visual_path else None
        else:
            self.current_path_point = None

        for x, y in visual_path:
            self._paint(x, y, self.path_color, self.solve_block)

    def _draw_current_path_point(self) -> None:
        """Highlight the current step of an in-progress path animation."""
        if self.current_path_point is None:
            return

        x, y = self.current_path_point
        self._paint(x, y, self.path_color, self.point_block)

    def _draw_entry_exit(self) -> None:
        """
        Draw maze entry and exit points.

        Highlights start and destination
        cells using dedicated theme blocks.
        """
        assert self.config.entry is not None
        assert self.config.exit is not None
        entry_x, entry_y = self.config.entry
        exit_x, exit_y = self.config.exit

        self._paint(
            (entry_x * 2) + 1,
            (entry_y * 2) + 1,
            self.entry_color,
            self.entry_block,
        )

        self._paint(
            (exit_x * 2) + 1,
            (exit_y * 2) + 1,
            self.exit_color,
            self.exit_block,
        )

    def render(self) -> None:
        """
        Render complete maze visualization.

        Updates the canvas and prints the
        final ANSI-rendered maze.
        """
        self._update_theme()
        self.real_width = (self.maze.width * 2) + 1
        self.real_height = (self.maze.height * 2) + 1
        self._create_canvas()
        self._draw_cells()
        self._draw_path()
        self._draw_entry_exit()
        self._draw_current_path_point()

        for line in self.canvas:
            print("".join(line))
