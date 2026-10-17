from exceptions import MazeError
from parser import Parser


class Cell:
    """Maze cell structure."""

    def __init__(self) -> None:
        """
        Initialize closed maze cell.

        Creates a cell with all walls closed and
        default traversal state disabled.
        """
        self.north = True
        self.east = True
        self.south = True
        self.west = True
        self.visited = False

    def has_wall(self, direction: str) -> bool:
        """
        Check if a wall exists in given direction.

        Args:
            direction: Cardinal wall direction.

        Returns:
            True if wall exists.
        """
        mapping = {
            "N": self.north,
            "E": self.east,
            "S": self.south,
            "W": self.west,
        }

        if direction not in mapping:
            raise ValueError(
                f"Invalid direction: {direction}"
            )

        return mapping[direction]

    def close_all_walls(self) -> None:
        """Close all cell walls."""
        self.north = True
        self.east = True
        self.south = True
        self.west = True


class Maze:
    """Maze grid representation."""

    def __init__(self, config: Parser) -> None:
        """
        Initialize maze grid structure.

        Args:
            config: Maze configuration parser.
        """
        assert config.width is not None
        assert config.height is not None

        self.width = config.width
        self.height = config.height

        self.grid = [
            [Cell() for _ in range(self.width)]
            for _ in range(self.height)
        ]

    def get_cell(self, x: int, y: int) -> Cell:
        """Return cell at given coordinates."""
        return self.grid[y][x]

    def in_bounds(self, x: int, y: int) -> bool:
        """Check if coordinates are inside maze bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def neighbors(self, x: int, y: int) -> list[tuple[str, int, int]]:
        """
        Return valid neighboring cells.

        Filters adjacent coordinates that remain
        inside maze boundaries.

        Args:
            x: Current cell x coordinate.
            y: Current cell y coordinate.

        Returns:
            List of valid neighboring coordinates.
        """
        directions = [
            ("N", x, y - 1),
            ("E", x + 1, y),
            ("S", x, y + 1),
            ("W", x - 1, y)
        ]

        return [
            (direction, nx, ny)
            for direction, nx, ny in directions
            if self.in_bounds(nx, ny)
        ]

    def reachable_neighbors(self,
                            x: int,
                            y: int
                            ) -> list[tuple[int, int]]:
        """
        Return reachable neighboring cells.

        Filters adjacent cells without blocking
        walls from the current position.

        Args:
            x: Current cell x coordinate.
            y: Current cell y coordinate.

        Returns:
            List of reachable neighbor coordinates.
        """
        neighbors = []

        cell = self.get_cell(x, y)

        for direction, nx, ny in self.neighbors(x, y):
            if not cell.has_wall(direction):
                neighbors.append((nx, ny))

        return neighbors

    def remove_wall(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
    ) -> None:
        """
        Remove walls between adjacent cells.

        Updates both cells to preserve wall
        consistency across the maze.

        Args:
            x1: First cell x coordinate.
            y1: First cell y coordinate.
            x2: Second cell x coordinate.
            y2: Second cell y coordinate.
        """
        c1 = self.get_cell(x1, y1)
        c2 = self.get_cell(x2, y2)

        if x1 == x2:

            if y1 > y2:
                c1.north = False
                c2.south = False

            else:
                c1.south = False
                c2.north = False

        elif y1 == y2:

            if x1 < x2:
                c1.east = False
                c2.west = False

            else:
                c1.west = False
                c2.east = False

        else:
            raise ValueError(
                f"Cells ({x1}, {y1}) and ({x2}, {y2}) "
                "are not orthogonal neighbors."
            )

    def cell_to_hex(self, cell: Cell) -> str:
        """
        Convert cell walls into hexadecimal encoding.

        Args:
            cell: Maze cell structure.

        Returns:
            Hexadecimal wall representation.
        """
        value = 0

        if cell.north:
            value |= 1

        if cell.east:
            value |= 2

        if cell.south:
            value |= 4

        if cell.west:
            value |= 8

        return format(value, "X")

    def to_hex_grid(self) -> list[list[str]]:
        """
        Return hexadecimal maze representation.

        Returns:
            Hexadecimal encoded maze grid.
        """
        return [
            [self.cell_to_hex(cell) for cell in row]
            for row in self.grid
        ]

    @classmethod
    def from_file(
        cls, file_name: str
    ) -> tuple["Maze", tuple[int, int], tuple[int, int]]:
        """
        Load a maze, entry and exit from a saved maze file.

        Parses the hexadecimal wall grid produced by
        MazeGenerator.save_maze, ignoring the trailing
        solution line.

        Args:
            file_name: Path to the saved maze file.

        Returns:
            Tuple of (maze, entry, exit).
        """
        try:
            with open(file_name, "r") as file:
                content = file.read()
        except OSError as e:
            raise MazeError(f"Can't read maze file `{file_name}`.") from e

        blocks = content.split("\n\n", 1)
        if len(blocks) != 2:
            raise MazeError(
                f"Malformed maze file `{file_name}`: missing separator."
            )

        grid_lines = [line for line in blocks[0].splitlines() if line]
        meta_lines = [line for line in blocks[1].splitlines() if line]

        if not grid_lines:
            raise MazeError(
                f"Malformed maze file `{file_name}`: empty grid."
            )

        if len(meta_lines) < 2:
            raise MazeError(
                f"Malformed maze file `{file_name}`: missing entry/exit."
            )

        width = len(grid_lines[0])

        maze = cls.__new__(cls)
        maze.width = width
        maze.height = len(grid_lines)
        maze.grid = []

        for y, line in enumerate(grid_lines):
            if len(line) != width:
                raise MazeError(
                    f"Malformed maze file `{file_name}`: "
                    f"inconsistent row width at row {y}."
                )

            row: list[Cell] = []
            for hex_digit in line:
                try:
                    value = int(hex_digit, 16)
                except ValueError as e:
                    raise MazeError(
                        f"Malformed maze file `{file_name}`: "
                        f"invalid hex digit `{hex_digit}`."
                    ) from e

                cell = Cell()
                cell.north = bool(value & 1)
                cell.east = bool(value & 2)
                cell.south = bool(value & 4)
                cell.west = bool(value & 8)
                row.append(cell)

            maze.grid.append(row)

        entry = maze._parse_coordinates(meta_lines[0], "entry", file_name)
        exit_ = maze._parse_coordinates(meta_lines[1], "exit", file_name)

        if entry == exit_:
            raise MazeError(
                f"Malformed maze file `{file_name}`: "
                "entry and exit are the same."
            )

        return maze, entry, exit_

    def _parse_coordinates(
        self, line: str, label: str, file_name: str
    ) -> tuple[int, int]:
        """
        Parse and validate a coordinates line.

        Args:
            line: Raw `x,y` coordinates line.
            label: Coordinate field name for error messages.
            file_name: Source maze file name.

        Returns:
            Parsed and validated coordinates.
        """
        try:
            x_str, y_str = line.split(",")
            x, y = int(x_str.strip()), int(y_str.strip())
        except Exception as e:
            raise MazeError(
                f"Malformed maze file `{file_name}`: "
                f"invalid {label} `{line}`."
            ) from e

        if not self.in_bounds(x, y):
            raise MazeError(
                f"Malformed maze file `{file_name}`: "
                f"{label} out of bounds."
            )

        return (x, y)
