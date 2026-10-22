# Teste dos sensores VL53L0X

O `main.py` executa um teste independente dos tres sensores no NodeMCU
ESP8266. A pinagem fica centralizada em `pinout.py`. O programa inicializa
cada VL53L0X, confirma o endereco no barramento e imprime leituras em
milimetros a cada 500 ms. Nenhum motor do L298N e acionado por este teste.

## Ligacoes

| Sinal | NodeMCU | GPIO | Destino |
|---|---|---:|---|
| I2C SCL | D2 | 4 | SCL dos tres sensores |
| I2C SDA | D1 | 5 | SDA dos tres sensores |
| XSHUT frontal | D5 | 14 | XSHUT do sensor frontal |
| XSHUT esquerdo | D7 | 13 | XSHUT do sensor esquerdo |
| XSHUT direito | D0 | 16 | XSHUT do sensor direito |
| Motor esquerdo IN1 | D3 | 0 | IN1 do L298N |
| Motor esquerdo IN2 | D4 | 2 | IN2 do L298N |
| Motor direito IN3 | D8 | 15 | IN3 do L298N |
| Motor direito IN4 | RX | 3 | IN4 do L298N |
| Enable motores | D6 | 12 | ENA e ENB do L298N |
| Alimentacao | 3V3 | — | VIN dos sensores |
| Terra comum | GND | — | GND dos sensores |

Ligacao fisica correspondente ao codigo atual:

```text
NodeMCU ESP8266            VL53L0X / L298N
----------------          -----------------
D2 / GPIO4   ------------ SCL (todos os VL53L0X)
D1 / GPIO5   ------------ SDA (todos os VL53L0X)

D5 / GPIO14  ------------ XSHUT frontal
D7 / GPIO13  ------------ XSHUT esquerdo
D0 / GPIO16  ------------ XSHUT direito

3V3           ------------ VIN/VCC dos VL53L0X
GND           ------------ GND comum

D3 / GPIO0   ------------ IN1 do L298N (motor esquerdo)
D4 / GPIO2   ------------ IN2 do L298N (motor esquerdo)
D8 / GPIO15  ------------ IN3 do L298N (motor direito)
RX / GPIO3   ------------ IN4 do L298N (motor direito)
D6 / GPIO12  ------------ ENA + ENB do L298N
```

> **Atencao:** esta configuracao usa D2/GPIO4 como SCL e D1/GPIO5 como
> SDA. Isso e o inverso da convencao mais comum do NodeMCU, que normalmente
> usa D1/GPIO5 como SCL e D2/GPIO4 como SDA. Como os pinos sao definidos por
> software no MicroPython, a configuracao atual pode funcionar, mas a ligacao
> fisica deve seguir exatamente `pinout.py`. Para adotar a convencao usual,
> troque os valores de `I2C_SCL_GPIO` e `I2C_SDA_GPIO` nesse arquivo e tambem
> inverta os dois fios na placa.

> **Atencao aos motores:** D3/GPIO0, D4/GPIO2 e D8/GPIO15 participam do
> processo de boot do ESP8266. Para iniciar corretamente, GPIO0 e GPIO2 devem
> permanecer em nivel alto e GPIO15 em nivel baixo durante o boot. O pino
> RX/GPIO3 tambem deixa de ficar livre para recepcao serial. Esta pinagem usa
> os poucos GPIOs restantes e deve ser testada com cuidado. ENA e ENB ficam
> unidos em D6/GPIO12, portanto os motores nao possuem velocidades PWM
> independentes. Remova os jumpers ENA e ENB do modulo L298N antes de conectar
> esses terminais ao ESP8266.

GPIO16/D0 e usado apenas como saida digital para XSHUT. O GPIO12/D6 esta
reservado ao sinal ENA+ENB do L298N e nao e inicializado pelo teste. Conecte
cada XSHUT ao seu GPIO individual; sem esses tres sinais nao e possivel
atribuir enderecos distintos no barramento compartilhado.

## Execucao no ESP8266

Copie `main.py`, `sensors.py`, `pinout.py` e o driver MicroPython
`vl53l0x.py` para o ESP8266 e execute `main.py` pelo Thonny. O teste espera
que o driver exporte `VL53L0X(i2c, address)`, um metodo `set_address(address)` ou
`change_address(address)`, e um metodo `read()` ou
`read_range_single_millimeters()`. Um metodo `start()` e chamado quando
disponivel. Se o driver usado tiver outra API, ajuste `_create_driver` ou os
adaptadores em `sensors.py` para a versao instalada.

Os sensores iniciam em `0x29`. O programa os mantem desligados pelo XSHUT e
liga um por vez, atribuindo `0x30` ao frontal, `0x31` ao esquerdo e `0x32` ao
direito. Em seguida, confirma cada endereco com `I2C.scan()`. `Ctrl-C`
interrompe o teste e coloca os tres pinos XSHUT em nivel baixo.

O arquivo `vl53l0x.py` nao esta incluído neste repositorio; use a copia
compativel com MicroPython que ja foi validada no projeto. Se a inicializacao
falhar, confira primeiro se apenas o sensor cujo XSHUT foi elevado esta
respondendo em `0x29`, se o driver permite mudar o endereco e se cada sensor
responde no novo endereco. Leituras iguais a zero sao reportadas como erro,
nao como distancias validas. Uma falha de leitura nao encerra o programa:
`read_all()` retorna `None` somente para o sensor afetado e disponibiliza a
mensagem correspondente em `last_errors`. Tambem e possivel ler cada direcao
com `read_front()`, `read_left()` e `read_right()`.

## Teste basico dos motores

O arquivo `main_test_control.py` testa, nesta ordem, movimento para frente,
giro para a esquerda, giro para a direita e re. Cada movimento dura um
segundo, com uma pausa de meio segundo entre eles. O teste sempre coloca os
motores em parada ao terminar ou receber `Ctrl-C`.

Esse teste pressupoe que os jumpers ENA e ENB tenham sido removidos e que os
dois pinos de sinal estejam ligados juntos a D6/GPIO12. O PWM e compartilhado,
portanto os dois motores sempre recebem a mesma velocidade. Ela pode ser
ajustada por `MOTOR_SPEED` e `TURN_SPEED` em `main_test_control.py`. Mantenha
as rodas do robo suspensas no primeiro teste e confirme se cada motor gira no
sentido esperado antes de coloca-lo no chao.

## Escolha do algoritmo

O algoritmo e escolhido em `robot_config.py` (`ALGORITHM`):

| Valor | Comportamento |
|---|---|
| `"left_hand"` | Regra da mao esquerda: reativa, sem mapa, nunca para sozinha. |
| `"dfs"` | O DFS de `simulation/solver.py`: guarda posicao, celulas visitadas e pilha; tenta vizinhos na ordem N, E, S, W, volta pela pilha e para na saida. |

O `dfs` usa `ENTRY`, `EXIT` e `START_HEADING` (o robo deve comecar centralizado
na celula de entrada, olhando para essa direcao). Ele estima a posicao
contando passos e giros por tempo, entao `STEP_MS` e `TURN_90_MS` precisam ser
calibrados; sem encoders a posicao pode derivar.

`control.Controller` so executa acoes; as decisoes ficam em `strategies.py`.
Para adicionar um algoritmo, crie uma classe com `decide(walls)` e
`on_done(action)` e registre-a em `make_strategy`. O loop principal e
`runner.run` (usado por `hardware.start()`).

Testes no computador (comparam o DFS do robo com `MazeSolver`):

    cd robot && python3 test_strategies.py
