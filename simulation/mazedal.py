import sys

from exceptions import ConfigError, MazeError
from maze_generator import MazeGenerator
from maze_structure import Maze
from menu import MazeMenu
from parser import Parser
from solver import MazeSolver


def main() -> None:
    """
    Run the maze generation program.

    Parses the configuration file, generates
    the maze, solves the shortest path and
    launches the interactive terminal menu.
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) > 1:
        print("Usage: python mazedal.py")
        sys.exit(1)

    try:
        config_path = "configs/config_load.txt"
        config = Parser(config_path)

        if config.load_file is not None:
            maze, entry, exit_ = Maze.from_file(config.load_file)
            config.entry = entry
            config.exit = exit_
            config.width = maze.width
            config.height = maze.height

            gen = MazeGenerator(maze, config)
        else:
            maze = Maze(config)

            gen = MazeGenerator(maze, config)
            gen.generate()

        solver = MazeSolver(maze, config)
        solver.solve()
        if config.output_file is not None:
            solution = solver.path_to_directions()
            gen.save_maze(maze, config, solution)

        MazeMenu(maze, gen, config).run()

    except ConfigError as e:
        print(f"Config error: {e}")

    except MazeError as e:
        print(f"Maze error: {e}")

    except KeyboardInterrupt:
        print("\nExiting...")

    except Exception as e:
        print(f"Error found: {e}")


if __name__ == "__main__":
    main()
