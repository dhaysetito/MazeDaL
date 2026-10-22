"""Testes no computador (sem placa): estrategias + Controller num labirinto da
simulacao. Rodar de dentro de robot/:  python3 test_strategies.py
"""

import os
import sys
import unittest
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "simulation")
sys.path.insert(0, SIM)
sys.path.insert(0, HERE)

import control  # noqa: E402
from control import Controller  # noqa: E402
from maze_structure import Maze  # noqa: E402
from solver import MazeSolver  # noqa: E402
from strategies import DFS, LeftHand, make_strategy  # noqa: E402

TICK_MS = 10
TURN_90_MS = 450
STEP_MS = 800
DIRS = "NESW"
DELTA = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}


class World:
    """Robo simulado numa celula de um Maze real, com relogio falso."""

    def __init__(self, maze, entry, heading="N"):
        self.maze = maze
        self.pos = entry
        self.heading = heading
        self.now = 0
        self.cmd = "stop"
        self.elapsed = 0
        self.visits = []  # celulas na ordem em que o robo mudou de celula

    # --- interface de DriveBase ---
    def _set(self, cmd):
        if cmd != self.cmd:
            self.cmd = cmd
            self.elapsed = 0

    def forward(self):
        self._set("forward")

    def backward(self):
        self._set("backward")

    def turn_left(self):
        self._set("left")

    def turn_right(self):
        self._set("right")

    def stop(self):
        self._set("stop")

    # --- fisica ---
    def tick(self):
        self.now += TICK_MS
        self.elapsed += TICK_MS
        if self.cmd == "forward" and self.elapsed >= STEP_MS:
            self.elapsed -= STEP_MS
            if not self.maze.get_cell(*self.pos).has_wall(self.heading):
                dx, dy = DELTA[self.heading]
                self.pos = (self.pos[0] + dx, self.pos[1] + dy)
                self.visits.append(self.pos)
        elif self.cmd in ("left", "right") and self.elapsed >= TURN_90_MS:
            self.elapsed -= TURN_90_MS
            step = -1 if self.cmd == "left" else 1
            self.heading = DIRS[(DIRS.index(self.heading) + step) % 4]

    def readings(self):
        cell = self.maze.get_cell(*self.pos)
        index = DIRS.index(self.heading)

        def dist(direction):
            return 50 if cell.has_wall(direction) else 500

        return {
            "left": dist(DIRS[(index - 1) % 4]),
            "front": dist(self.heading),
            "right": dist(DIRS[(index + 1) % 4]),
        }


def load(name):
    return Maze.from_file(os.path.join(SIM, "mazes", name))


def add_loops(maze, count):
    """Abre `count` paredes internas para criar ciclos (labirinto nao perfeito)."""
    opened = 0
    for y in range(maze.height):
        for x in range(maze.width):
            for direction, nx, ny in maze.neighbors(x, y):
                if opened < count and maze.get_cell(x, y).has_wall(direction):
                    maze.remove_wall(x, y, nx, ny)
                    opened += 1
    return maze


def drive(maze, entry, exit_, strategy, heading="N", readings=None,
          limit=200000, stop_at_exit=False):
    """Roda Controller + estrategia ate ela parar (ou, se stop_at_exit, ate
    o robo fisicamente chegar na saida: a mao esquerda nao sabe onde e a saida)."""
    world = World(maze, entry, heading)
    control.ticks_ms = lambda: world.now
    control.ticks_diff = lambda a, b: a - b
    controller = Controller(
        world, strategy, turn_90_ms=TURN_90_MS, step_ms=STEP_MS, wall_mm=150
    )
    for _ in range(limit):
        if controller.finished or (stop_at_exit and world.pos == exit_):
            break
        controller.update(readings(world) if readings else world.readings())
        world.tick()
    return world, controller


def sim_traversal(maze, entry, exit_):
    config = SimpleNamespace(entry=entry, exit=exit_, algorithm="DFS")
    solver = MazeSolver(maze, config)
    solver.solve()
    return solver.traversal


class DFSMatchesSimulation(unittest.TestCase):
    def check(self, maze, entry, exit_, heading):
        expected = sim_traversal(maze, entry, exit_)
        strategy = DFS(entry, exit_, heading)
        world, controller = drive(maze, entry, exit_, strategy, heading)
        self.assertEqual(world.pos, exit_)
        self.assertEqual(world.visits, expected[1:])
        self.assertEqual(strategy.path, expected)

    def test_maze_5x5_all_headings(self):
        for heading in "NESW":
            maze, entry, exit_ = load("maze_5x5.txt")
            self.check(maze, entry, exit_, heading)

    def test_maze_with_loops(self):
        for loops in (3, 8):
            maze, entry, exit_ = load("maze_5x5.txt")
            self.check(add_loops(maze, loops), entry, exit_, "N")

    def test_other_saved_mazes(self):
        for name in ("maze.txt", "maze_trivial.txt"):
            maze, entry, exit_ = load(name)
            self.check(maze, entry, exit_, "N")

    def test_stops_motors_at_exit(self):
        maze, entry, exit_ = load("maze_5x5.txt")
        world, controller = drive(maze, entry, exit_, DFS(entry, exit_))
        self.assertTrue(controller.finished)
        self.assertEqual(world.cmd, "stop")


class LeftHandBehavior(unittest.TestCase):
    def test_priorities(self):
        w = lambda l, f, r: {"left": l, "front": f, "right": r}  # noqa: E731
        self.assertEqual(LeftHand().decide(w(False, False, False)), "left")
        self.assertEqual(LeftHand().decide(w(True, False, False)), "forward")
        self.assertEqual(LeftHand().decide(w(True, True, False)), "right")
        self.assertEqual(LeftHand().decide(w(True, True, True)), "around")

    def test_steps_after_turning(self):
        s = LeftHand()
        s.decide({"left": False, "front": True, "right": True})
        self.assertEqual(s.decide({"left": False, "front": True, "right": True}), "step")

    def test_reaches_exit_in_perfect_maze(self):
        maze, entry, exit_ = load("maze_5x5.txt")
        world, _ = drive(maze, entry, exit_, LeftHand(), stop_at_exit=True)
        self.assertEqual(world.pos, exit_)


class ControllerRobustness(unittest.TestCase):
    def test_none_readings_do_not_raise(self):
        maze, entry, exit_ = load("maze_5x5.txt")
        for strategy in (LeftHand(), DFS(entry, exit_)):
            drive(
                maze, entry, exit_, strategy,
                readings=lambda w: {"left": None, "front": None, "right": None},
                limit=500,
            )

    def test_default_strategy_is_left_hand(self):
        self.assertIsInstance(Controller(None).strategy, LeftHand)

    def test_make_strategy(self):
        cfg = SimpleNamespace(ENTRY=(1, 1), EXIT=(0, 0), START_HEADING="E")
        self.assertIsInstance(make_strategy("left_hand", cfg), LeftHand)
        dfs = make_strategy("dfs", cfg)
        self.assertEqual((dfs.entry, dfs.exit, dfs.heading), ((1, 1), (0, 0), "E"))
        with self.assertRaises(ValueError):
            make_strategy("bfs", cfg)


if __name__ == "__main__":
    unittest.main()
