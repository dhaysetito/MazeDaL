"""Configuracao do robo: algoritmo e parametros de movimento.

Espelha ALGORITHM, ENTRY e EXIT do config.txt da simulacao.
"""

# "left_hand" (regra da mao esquerda) ou "dfs" (DFS da simulacao)
ALGORITHM = "left_hand"

# So usados pelo "dfs": celula inicial/final (x, y) e direcao inicial do robo
# (N, E, S ou W; mesma convencao da simulacao: N diminui y, E aumenta x).
ENTRY = (2, 2)
EXIT = (0, 0)
START_HEADING = "N"

# Calibrar no robo: duracao de um giro de 90 graus e de um passo de uma celula.
TURN_90_MS = 450
STEP_MS = 800

# Distancia (mm) abaixo da qual o sensor enxerga uma parede.
WALL_MM = 150
