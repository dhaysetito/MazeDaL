import random
import time
from pathlib import Path

from maze_structure import Maze
from parser import Parser


class MazeGenerator:
    """Procedural DFS maze generator."""
    def __init__(self, maze: Maze, config: Parser) -> None:
        """
        Initialize maze generator.

        Args:
            maze: Maze structure.
            config: Maze configuration parser.
        """
        self.maze = maze
        self.config = config
        self.random = random.Random(config.seed)
        self.generation_time = 0.0
        self.loops_added = 0

    def _unvisited_neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        """
        Return unvisited reachable neighbors.

        Filters already visited cells.

        Args:
            x: Current cell x coordinate.
            y: Current cell y coordinate.

        Returns:
            List of unvisited neighbor coordinates.
        """
        result: list[tuple[int, int]] = []

        for _, n_x, n_y in self.maze.neighbors(x, y):
            neighbor = self.maze.get_cell(n_x, n_y)

            if not neighbor.visited:
                result.append((n_x, n_y))
        return result

    def _reset_visited(self) -> None:
        """Reset visited state of all cells."""
        for row in self.maze.grid:
            for cell in row:
                cell.visited = False

    def generate(self) -> None:
        """
        Generate maze using DFS backtracking.

        Traverses random unvisited neighbors while
        removing walls between adjacent cells until
        the maze becomes fully connected.
        """
        start = time.perf_counter()
        stack: list[tuple[int, int]] = []

        x, y = 0, 0
        self.maze.get_cell(x, y).visited = True

        while True:
            neighbors = self._unvisited_neighbors(x, y)

            if neighbors:
                nx, ny = self.random.choice(neighbors)

                self.maze.remove_wall(x, y, nx, ny)

                stack.append((x, y))

                x, y = nx, ny
                self.maze.get_cell(x, y).visited = True

            elif stack:
                x, y = stack.pop()

            else:
                break

        if not self.config.perfect:
            self._add_loops()

        self.generation_time = time.perf_counter() - start
        self._reset_visited()

    def _add_loops(self) -> None:
        """
        Create additional paths in non-perfect mazes.

        Removes selected walls while preventing
        large open areas and invalid structures.
        """
        loops = (self.maze.width * self.maze.height) // 20

        created = 0
        attempts = 0
        max_attempts = loops * 20

        while created < loops and attempts < max_attempts:
            attempts += 1
            x = self.random.randint(0, self.maze.width - 1)
            y = self.random.randint(0, self.maze.height - 1)
            cell = self.maze.get_cell(x, y)
            valid_neighbors = []

            for _, nx, ny in self.maze.neighbors(x, y):
                neighbor = self.maze.get_cell(nx, ny)
                if nx == x + 1 and cell.east:
                    pass
                elif nx == x - 1 and cell.west:
                    pass
                elif ny == y + 1 and cell.south:
                    pass
                elif ny == y - 1 and cell.north:
                    pass
                else:
                    continue

                open_paths = 0
                for d, _, _ in self.maze.neighbors(x, y):
                    if not cell.has_wall(d):
                        open_paths += 1

                if open_paths >= 3:
                    continue
                open_neighbor_paths = 0

                for d, _, _ in (self.maze.neighbors(nx, ny)):
                    if not neighbor.has_wall(d):
                        open_neighbor_paths += 1

                if open_neighbor_paths >= 3:
                    continue

                valid_neighbors.append((nx, ny))

            if not valid_neighbors:
                continue

            nx, ny = self.random.choice(valid_neighbors)
            self.maze.remove_wall(x, y, nx, ny)

            created += 1
            self.loops_added += 1

    @staticmethod
    def save_maze(maze: Maze, config: Parser, solution: str) -> None:
        """
        Export maze structure to output file.

        Writes hexadecimal wall encoding, entry,
        exit and shortest solution path.

        Args:
            maze: Maze structure.
            config: Maze configuration.
            solution: NESW shortest path string.
        """
        assert config.output_file is not None
        assert config.entry is not None
        assert config.exit is not None

        try:
            maze_directory = Path(__file__).parent / "mazes"
            output_path = maze_directory / Path(config.output_file).name

            with open(output_path, "w") as file:
                for row in maze.grid:
                    line = "".join(maze.cell_to_hex(c) for c in row)
                    file.write(line + "\n")

                file.write("\n")
                file.write(f"{str(config.entry[0])},{str(config.entry[1])}")
                file.write("\n")
                file.write(f"{str(config.exit[0])},{str(config.exit[1])}")
                file.write("\n")
                file.write(f"{solution}\n")

        except OSError as e:
            raise MazeError("Can't create file.") from e
