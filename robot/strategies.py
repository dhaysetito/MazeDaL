"""Algoritmos de decisao do MazeDaL.

Uma estrategia so decide O QUE fazer; quem move o robo e o Controller
(control.py). Interface:

    decide(walls) -> acao
    on_done(acao)     (chamado quando uma acao cronometrada termina)

`walls` e um dict {"left": bool, "front": bool, "right": bool}, True = parede.

Acoes: "forward" (anda continuamente), "step" (anda uma celula), "left",
"right", "around" (giros de 90, 90 e 180 graus) e "stop".

Este modulo nao importa nada da placa, entao roda no computador.
"""

# Mesma ordem de maze_structure.Maze.neighbors da simulacao.
DIRECTIONS = "NESW"
_DELTA = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}


class LeftHand:
    """Regra da mao esquerda: esquerda livre > frente livre > direita > meia-volta.

    Depois de qualquer giro o robo da um passo de uma celula antes de decidir
    de novo. Sem isso, ao virar numa bifurcacao ele ve o corredor de onde veio
    livre a sua esquerda e vira outra vez, voltando por onde veio.
    """

    def __init__(self):
        self._plan = []

    def decide(self, walls):
        if self._plan:
            action = self._plan.pop(0)
            if action != "step" or not walls["front"]:
                return action
            # Parede a frente: descarta o passo e decide de novo.
        if not walls["left"]:
            action = "left"
        elif not walls["front"]:
            return "forward"
        elif not walls["right"]:
            action = "right"
        else:
            action = "around"
        self._plan = ["step"]
        return action

    def on_done(self, action):
        pass


class DFS:
    """DFS da simulacao (solver._solve_dfs) executado pelo robo.

    Guarda posicao, direcao, celulas visitadas e a pilha de caminho. Em cada
    celula nova le as paredes, escolhe o primeiro vizinho livre e nao visitado
    na ordem N, E, S, W e anda uma celula. Sem vizinho novo, volta pela pilha.
    Para ao chegar em `exit_`.

    A posicao e estimada por contagem de passos e giros, entao ela deriva se
    o robo patinar. O robo deve comecar centralizado na celula `entry`,
    olhando para `heading`.
    """

    def __init__(self, entry, exit_, heading="N"):
        self.entry = tuple(entry)
        self.exit = tuple(exit_)
        self.pos = self.entry
        self.heading = heading
        self.visited = {self.entry}
        self.stack = [self.entry]
        self.path = [self.entry]  # celulas na ordem em que o robo chegou nelas
        self._open = {}  # celula -> {direcao absoluta: livre?}
        self._plan = []
        self._move = None
        self._scan = None
        self.error = None

    def _turn(self, delta):
        index = DIRECTIONS.index(self.heading)
        return DIRECTIONS[(index + delta) % 4]

    def _turns_to(self, direction):
        diff = (DIRECTIONS.index(direction) - DIRECTIONS.index(self.heading)) % 4
        return [[], ["right"], ["around"], ["left"]][diff]

    def _neighbor(self, direction):
        dx, dy = _DELTA[direction]
        return (self.pos[0] + dx, self.pos[1] + dy)

    def _observe(self, walls):
        """Direcoes absolutas livres vistas pelos tres sensores."""
        return {
            self._turn(-1): not walls["left"],
            self.heading: not walls["front"],
            self._turn(1): not walls["right"],
        }

    def _sense_cell(self, walls):
        """Preenche _open para a celula atual. True quando ja da para decidir."""
        if self.pos in self._open:
            return True

        seen = self._observe(walls)
        if len(self.stack) > 1:
            # Veio da celula anterior, entao a traseira e livre.
            seen[self._turn(2)] = True
            self._open[self.pos] = seen
            return True

        # Celula de entrada: a traseira e desconhecida. Gira 180 graus uma vez
        # para os sensores olharem para tras e junta as duas leituras.
        if self._scan is None:
            self._scan = seen
            self._plan = ["around"]
            return False
        seen.update(self._scan)
        self._scan = None
        self._open[self.pos] = seen
        return True

    def decide(self, walls):
        if self._plan:
            action = self._plan.pop(0)
            if action == "step" and walls["front"]:
                # O mapa interno nao bate com o labirinto (patinagem?).
                self._plan = []
                self._move = None
                self.error = "parede a frente ao dar o passo (posicao derivou)"
                return "stop"
            return action
        if self.pos == self.exit:
            return "stop"
        if not self._sense_cell(walls):
            return self._plan.pop(0)

        open_dirs = self._open[self.pos]
        for direction in DIRECTIONS:
            target = self._neighbor(direction)
            if open_dirs.get(direction) and target not in self.visited:
                self._move = ("forward", target)
                self._plan = self._turns_to(direction) + ["step"]
                return self._plan.pop(0)

        if len(self.stack) > 1:
            parent = self.stack[-2]
            for direction in DIRECTIONS:
                if self._neighbor(direction) == parent:
                    self._move = ("back", parent)
                    self._plan = self._turns_to(direction) + ["step"]
                    return self._plan.pop(0)

        return "stop"  # sem saida alcancavel

    def on_done(self, action):
        if action == "left":
            self.heading = self._turn(-1)
        elif action == "right":
            self.heading = self._turn(1)
        elif action == "around":
            self.heading = self._turn(2)
        elif action == "step" and self._move is not None:
            kind, target = self._move
            self._move = None
            self.pos = target
            if kind == "forward":
                self.visited.add(target)
                self.stack.append(target)
            else:
                self.stack.pop()
            self.path.append(target)


def make_strategy(name, config):
    """Cria a estrategia `name` ("left_hand" ou "dfs") a partir de robot_config."""
    if name == "left_hand":
        return LeftHand()
    if name == "dfs":
        return DFS(config.ENTRY, config.EXIT, config.START_HEADING)
    raise ValueError(
        "Algoritmo desconhecido: %s (use 'left_hand' ou 'dfs')" % name
    )
