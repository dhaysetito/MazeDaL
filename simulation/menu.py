import os
import sys
import time
from pathlib import Path

from maze_generator import MazeGenerator
from maze_structure import Maze
from parser import Parser
from renderer import MazeRenderer
from solver import MazeSolver


class MazeMenu:
    """Interactive maze terminal menu."""

    def __init__(
        self,
        maze: Maze,
        generator: MazeGenerator,
        config: Parser,
    ) -> None:
        """
        Initialize interactive maze menu.

        Args:
            maze: Maze structure.
            generator: Maze generator instance.
            config: Maze configuration parser.
        """
        self.maze = maze
        self.generator = generator
        self.config = config

        self.show_path = False
        self.path: (list[tuple[int, int]] | None) = None

        self.renderer = MazeRenderer(
            self.maze,
            self.config,
            self.path,
        )

        solver = MazeSolver(self.maze, self.config)
        self.path = solver.solve()
        self.save = True
        self.saved_file = (
            Path(self.config.load_file).name
            if self.config.load_file is not None
            else self.config.output_file
        )

    def _clear_screen(self) -> None:
        """Clear terminal screen."""
        command = "cls" if os.name == "nt" else "clear"
        os.system(command)

    def _exit(self) -> None:
        """Clear the maze display and show the exit message."""
        self._clear_screen()
        print("Exiting...")

    def _render(self) -> None:
        """
        Render maze using current state.

        Updates renderer attributes before
        displaying the maze.
        """
        self.renderer.maze = self.maze

        if self.show_path:
            self.renderer.path = self.path

        else:
            self.renderer.path = None


        self.renderer.render()

    def _show_menu(self) -> None:
        """
        Display available menu options.

        Shows interactive actions and current
        visualization state.
        """
        print()

        print(f"{'═'*15} Menu {'═'*15}")
        print("[1] Choose maze source")
        if not self.show_path:
            print("[2] Toggle shortest path (Disabled)")
        else:
            print("[2] Toggle shortest path (Enabled)")
        if self.save:
            print(
                "[3] Save maze "
                f"(saved to `mazes/{self.saved_file}`)"
            )
        else:
            print("[3] Save maze (not saved)")
        print("[4] Show solution (press SPACE)")
        print("[5] Show full traversal (press SPACE)")
        print("[6] Show full traversal automatically")
        print("[7] Show stats")
        print("[0] Exit")
        print(f"{'═'*36}")

        print()

    def _show_title(self) -> None:
        """
        Show project title and maze status.

        Displays the project banner.
        """
        print(
            "\033[1m"
            "\033[38;5;220m"
            r"""
             ███╗   ███╗ █████╗ ███████╗███████╗██████╗  █████╗ ██╗
             ████╗ ████║██╔══██╗╚══███╔╝██╔════╝██╔══██╗██╔══██╗██║
             ██╔████╔██║███████║  ███╔╝ █████╗  ██║  ██║███████║██║
             ██║╚██╔╝██║██╔══██║ ███╔╝  ██╔══╝  ██║  ██║██╔══██║██║
             ██║ ╚═╝ ██║██║  ██║███████╗███████╗██████╔╝██║  ██║███████╗
             ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═════╝ ╚═╝  ╚═╝╚══════╝
                """
            "\033[0m"
            )


    def _load_configuration(self, config_name: str) -> None:
        """
        Load a configured maze source and solve it.

        The automatic and fixed maze modes use
        their own configuration files.
        """
        config_path = Path(__file__).parent / "configs" / config_name
        self.config = Parser(str(config_path))

        if self.config.load_file is not None:
            self.maze, entry, exit_ = Maze.from_file(self.config.load_file)
            self.config.entry = entry
            self.config.exit = exit_
            self.config.width = self.maze.width
            self.config.height = self.maze.height
            self.generator = MazeGenerator(self.maze, self.config)
        else:
            self.maze = Maze(self.config)
            self.generator = MazeGenerator(self.maze, self.config)
            self.generator.generate()

        solver = MazeSolver(self.maze, self.config)
        self.path = solver.solve()
        self.renderer.maze = self.maze
        self.renderer.config = self.config
        self.save = self.config.load_file is not None
        self.saved_file = (
            Path(self.config.load_file).name
            if self.config.load_file is not None
            else None
        )

    def _choose_maze_source(self) -> None:
        """Choose between the bundled maze and automatic generation."""
        print("\n[1] Load fixed maze")
        print("[2] Generate maze automatically")
        choice = input("Source: ").strip()

        if choice == "1":
            self._load_configuration("config_load.txt")

        elif choice == "2":
            self._load_configuration("config.txt")

        else:
            print("\nSelect a valid source (1-2).\n")
            self._pause()
            return

    def _toggle_path(self) -> None:
        """Show or hide shortest path."""
        self.show_path = not self.show_path

    def _show_full_traversal(self) -> str:
        """Show the complete route explored by the active solver."""
        solver = MazeSolver(self.maze, self.config)
        solver.solve()
        return self._show_solution_on_space(solver.traversal)

    def _save_maze(self) -> None:
        """
        Save maze to output file.

        Exports hexadecimal maze encoding and
        shortest solution path.
        """
        try:
            default_name = self.config.output_file or "maze.txt"
            new_file = input(
                f"Enter the name of the file to save"
                f" ({default_name}): "
                )
            self.config.output_file = new_file or default_name
            solver = MazeSolver(self.maze, self.config)
            solver.solve()
            solution = solver.path_to_directions()
            self.generator.save_maze(self.maze, self.config, solution)
            self.save = True
            self.saved_file = Path(self.config.output_file).name

        except Exception:
            print("\nFailed to save maze.\n")
            self.save = False
            self._pause()

    def _show_stats(self) -> None:
        """Display maze generation statistics."""
        solver = MazeSolver(self.maze, self.config)
        path = solver.solve()

        print(f"\n{'═'*15} Stats {'═'*14}\n")

        print(f"Algorithm: {self.config.algorithm}")
        print(f"Maze Size: {self.maze.width} x {self.maze.height}")
        print(f"Perfect Maze: {self.config.perfect}")
        print(f"Visited Nodes: {solver.visited_nodes}")
        print(f"Path Length: {len(path)}")
        print(f"Solve Time: {solver.solve_time:.6f}s")
        print(f"Generation Time: {self.generator.generation_time:.6f}s")
        print(f"Loops Added: {self.generator.loops_added}")
        print(f"Seed: {self.config.seed}")
        print(f"\n{'═'*36}")

    def _handle_choice(self, choice: str) -> bool:
        """
        Handle user menu selection.

        Args:
            choice: Selected menu option.

        Returns:
            False when exiting the menu.
        """
        if choice == "1":
            self._choose_maze_source()

        elif choice == "2":
            self._toggle_path()

        elif choice == "3":
            self._save_maze()

        elif choice == "4":
            if self._show_solution_on_space() == "exit":
                return False

        elif choice == "5":
            if self._show_full_traversal() == "exit":
                return False

        elif choice == "6":
            self._show_full_traversal_automatically()

        elif choice == "7":
            self._show_stats()
            self._pause()

        elif choice == "0":
            self._exit()
            return False

        else:
            print("\nSelect a valid menu option (0-7).\n")
            self._pause()

        return True

    def _pause(self) -> None:
        """Wait for user confirmation."""
        input("Press ENTER to continue...")

    def _wait_for_solution_key(self) -> str:
        """Read the next-step, menu, or exit command."""
        if os.name == "nt" and sys.stdin.isatty():
            import msvcrt

            key = msvcrt.getwch()
        else:
            key = input("Command: ")

        if key == " ":
            return "next"
        if key == "0":
            return "menu"
        return "exit"

    def _show_solution_on_space(
        self,
        path: list[tuple[int, int]] | None = None,
    ) -> str:
        """Advance a route one step every time Space is pressed."""
        if path is None:
            solver = MazeSolver(self.maze, self.config)
            path = solver.solve()

        if not path:
            return "menu"

        total_steps = (len(path) * 2) - 1
        for progress in range(1, total_steps + 1):
            self.renderer.path = path
            self.renderer.path_progress = progress
            self._clear_screen()
            self._show_title()
            self.renderer.render()

            if progress > 1:
                move_index = (progress - 2) // 2
                x1, y1 = path[move_index]
                x2, y2 = path[move_index + 1]
                direction = {
                    (1, 0): "Direita",
                    (-1, 0): "Esquerda",
                    (0, 1): "Baixo",
                    (0, -1): "Cima",
                }[(x2 - x1, y2 - y1)]
                print(f"\nDireção: {direction}")

            if progress < total_steps:
                print("\nSPACE: próximo passo | 0: voltar ao menu")
                command = self._wait_for_solution_key()

                if command == "next":
                    continue

                self.renderer.path_progress = None
                if command == "menu":
                    self.path = path
                    self.show_path = True
                    return "menu"

                self.renderer.path_progress = None
                self._exit()
                return "exit"

        self.path = path
        self.show_path = True
        self.renderer.path_progress = None
        return "menu"

    def _show_full_traversal_automatically(self) -> None:
        """Play the complete DFS traversal with a short visual delay."""
        solver = MazeSolver(self.maze, self.config)
        solver.solve()
        path = solver.traversal

        if not path:
            return

        total_steps = (len(path) * 2) - 1
        for progress in range(1, total_steps + 1):
            self.renderer.path = path
            self.renderer.path_progress = progress
            self._clear_screen()
            self._show_title()
            self.renderer.render()

            if progress > 1:
                move_index = (progress - 2) // 2
                x1, y1 = path[move_index]
                x2, y2 = path[move_index + 1]
                direction = {
                    (1, 0): "Direita",
                    (-1, 0): "Esquerda",
                    (0, 1): "Baixo",
                    (0, -1): "Cima",
                }[(x2 - x1, y2 - y1)]
                print(f"\nDireção: {direction}")

            time.sleep(0.12)

        self.path = path
        self.show_path = True
        self.renderer.path_progress = None

    def run(self) -> None:
        """
        Start interactive terminal loop.

        Continuously renders the maze and
        handles user interactions.
        """
        while True:
            try:
                self._clear_screen()
                self._show_title()
                self._render()
                self._show_menu()

                choice = input("Option: ").strip()
                if not self._handle_choice(choice):
                    break
            except KeyboardInterrupt:
                self._exit()
                break
