# MazeDaL

Aplicação de terminal para gerar, resolver, salvar e visualizar labirintos.
O gerador usa busca em profundidade (DFS) com backtracking. A resolução pode
usar DFS ou busca em largura (BFS), definida no arquivo de configuração.

## Requisitos e execução

É necessário ter Python 3 instalado. A partir da raiz do projeto, execute:

```powershell
python mazedal.py
```

O programa não recebe argumentos. Ele inicia carregando a configuração fixa
em `configs/config_load.txt`.

## Estrutura

```text
MazeDaL_simulation/
├── configs/
│   ├── config.txt          # configuração para geração automática
│   └── config_load.txt     # configuração do labirinto fixo
├── mazes/
│   ├── maze_5x5.txt        # labirinto fixo atual
│   ├── maze.txt            # exemplo/saída de labirinto salvo
│   └── maze_trivial.txt    # exemplo de labirinto pequeno
├── mazedal.py              # ponto de entrada
├── menu.py                 # interface do terminal
├── maze_generator.py       # geração DFS
├── solver.py               # resolução BFS/DFS
├── renderer.py             # desenho ANSI no terminal
├── maze_structure.py       # células, paredes e grade
├── parser.py               # leitura e validação de configurações
├── themes.py               # cores e ícones do terminal
└── exceptions.py           # exceções da aplicação
```

## Fontes de labirinto

O menu inicia com o labirinto fixo configurado em `config_load.txt`:

```text
LOAD_FILE=maze_5x5.txt
ALGORITHM=DFS
```

Na opção `[1] Choose maze source`, escolha uma das fontes:

- `[1] Load fixed maze`: recarrega `configs/config_load.txt` e abre o arquivo
  informado por `LOAD_FILE`.
- `[2] Generate maze automatically`: recarrega `configs/config.txt` e gera
  uma nova grade.

Arquivos referenciados por `LOAD_FILE` podem ser caminhos explícitos. Para um
nome simples, como `maze_5x5.txt`, o programa procura o arquivo em `mazes/`.

## Configuração de geração

`configs/config.txt` controla o modo automático. Exemplo atual:

```text
WIDTH=5
HEIGHT=5
ENTRY=2,2
EXIT=0,0
OUTPUT_FILE=maze.txt
PERFECT=True
SEED=None
ALGORITHM=DFS
```

| Chave | Descrição |
|---|---|
| `WIDTH`, `HEIGHT` | Largura e altura da grade, entre 1 e 50. |
| `ENTRY`, `EXIT` | Coordenadas `x,y`, dentro da grade e diferentes entre si. |
| `OUTPUT_FILE` | Nome do arquivo usado ao salvar; o resultado fica em `mazes/`. |
| `PERFECT` | `True` cria um labirinto sem loops; `False` cria caminhos extras. |
| `SEED` | `None` usa aleatoriedade nova a cada geração; um inteiro torna a geração reproduzível. |
| `ALGORITHM` | Algoritmo do resolvedor: `DFS` ou `BFS`. O padrão é `BFS`. |
| `LOAD_FILE` | Arquivo do labirinto fixo; usado apenas em `config_load.txt`. |

`WIDTH` e `HEIGHT` devem aparecer antes de `ENTRY` e `EXIT` no arquivo.

## Menu

| Opção | Ação |
|---|---|
| `[1]` | Escolhe entre carregar o labirinto fixo e gerar um labirinto automático. |
| `[2]` | Mostra ou oculta o caminho final até a saída. |
| `[3]` | Salva o labirinto atual em `mazes/`. |
| `[4]` | Mostra a solução final passo a passo. |
| `[5]` | Mostra passo a passo o percurso completo feito pelo DFS. |
| `[6]` | Reproduz automaticamente o percurso completo do DFS. |
| `[7]` | Exibe estatísticas da geração e resolução. |
| `[0]` | Encerra o programa. |

Nas opções `[4]` e `[5]`, pressione Espaço para revelar o próximo bloco do
trajeto. Pressione `0` para voltar ao menu com o caminho exibido; qualquer
outra tecla encerra a aplicação. Em terminais sem captura direta de teclas,
pressione Espaço e depois Enter.

A opção `[6]` avança automaticamente a cada 0,12 segundo. Durante as
visualizações, a ponta atual do caminho usa o `point_block` azul; o trecho já
revelado usa o ícone amarelo da solução. A entrada e a saída permanecem,
respectivamente, vermelha e verde.

## Algoritmos

### Geração

`MazeGenerator` constrói a grade com DFS e backtracking. A cada célula, escolhe
aleatoriamente um vizinho ainda não visitado, remove a parede entre as duas
células e volta quando encontra um beco sem saída. Com `PERFECT=False`, remove
paredes adicionais para criar loops.

### Resolução

`MazeSolver` usa o algoritmo definido por `ALGORITHM`:

- `BFS` encontra o caminho com menor número de movimentos.
- `DFS` segue a prioridade: cima, direita, baixo e esquerda.

A opção `[4]` mostra somente a solução reconstruída entre entrada e saída. As
opções `[5]` e `[6]` mostram o percurso real do DFS, incluindo as voltas após
becos sem saída.

## Salvamento e formato dos labirintos

Ao salvar, apenas o nome do arquivo é usado e o resultado é escrito em
`mazes/`. Por exemplo, salvar como `meu_labirinto.txt` cria:

```text
mazes/meu_labirinto.txt
```

O arquivo contém, nesta ordem:

1. Uma grade de caracteres hexadecimais que codifica as paredes de cada célula.
2. Uma linha em branco.
3. A entrada no formato `x,y`.
4. A saída no formato `x,y`.
5. A solução final com movimentos `N`, `E`, `S` e `W`.

Na codificação hexadecimal, as paredes valem: norte = `1`, leste = `2`, sul =
`4` e oeste = `8`. O dígito salvo é a combinação dessas paredes.

## Encerramento

Use `[0]` no menu ou `Ctrl+C` para sair. O programa limpa a tela e exibe
`Exiting...`.
