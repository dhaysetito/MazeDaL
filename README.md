# MazeDaL

Robô autônomo que encontra a saída de um labirinto desconhecido, usando sensores de distância para perceber as paredes e decidir por onde seguir. Trabalho desenvolvido para a disciplina Projeto Integrado - 2026.2 - UFRJ.

**Autoras:** Dhayse Tito, Luiza Pacheco e Marina Sangineto.

## Visão geral

O robô é feito com:
- 3 rodas
- 3 sensores de distância a laser (VL53L0X)
- Controlado por um NodeMCU ESP8266 programado em MicroPython
- Motores são acionados por uma ponte H L298N


## Estrutura do repositório

| Pasta | Conteúdo |
|---|---|
| [`simulation/`](simulation) | Aplicação de terminal em Python 3 que gera, resolve, salva e exibe labirintos (DFS com backtracking para gerar; DFS ou BFS para resolver). |
| [`robot/`](robot) | Código do robô em MicroPython: pinagem, leitura dos sensores, controle dos motores e navegação. |

Cada pasta tem seu próprio README com instruções de uso, ligações e testes.
