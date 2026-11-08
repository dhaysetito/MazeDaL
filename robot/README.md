# MazeDaL — Robô

Código do robô em MicroPython para ESP32-WROOM-32, com três sensores de
distância VL53L0X e controle dos motores pelo driver L298N.
As conexões estão em [PINAGEM.md](PINAGEM.md).

## Arquivos

| Arquivo | Função |
| --- | --- |
| [main.py](main.py) | Programa principal: avança com a frente livre, para diante de uma parede, gira à direita e realiza uma nova leitura antes de avançar. |
| [test_wall.py](test_wall.py) | Teste do sensor frontal com os motores: avança com a frente livre e permanece parado enquanto houver uma parede. Os sensores laterais ficam em standby. |
| [tests/test_sensors_esp32.py](tests/test_sensors_esp32.py) | Teste de um, dois ou três sensores no ESP32. Exibe as distâncias em milímetros, sem acionar os motores. A seleção é definida em `SENSORES_ATIVOS`. |
| [tests/test_sensors_esp8266.py](tests/test_sensors_esp8266.py) | Teste da montagem anterior com ESP8266: um sensor, LED indicador e habilitação conjunta dos motores, com limite de 150 mm. Usa pinagem própria definida no arquivo. |
| [lib/vl53l0x.py](lib/vl53l0x.py) | Driver MicroPython dos sensores VL53L0X. |
| [tests/vl53l0x.mpy](tests/vl53l0x.mpy) | Driver em formato compilado MicroPython, armazenado junto aos testes. |
| [PINAGEM.md](PINAGEM.md) | Tabelas de conexão dos sensores e do driver dos motores ao ESP32. |

## Funcionamento

O `main.py` inicializa os três sensores com endereços I²C individuais.
A leitura frontal determina o movimento; as leituras laterais são exibidas
no console. Com distância frontal acima de 200 mm, o robô avança.
Com distância de 200 mm ou menos, para e gira à direita sobre o próprio eixo,
com o motor esquerdo para frente e o direito para trás.

O giro é controlado por tempo: dura 500 ms, com pausas de 150 ms antes e
depois da manobra. Ao concluir, o programa mede novamente a frente e repete
o giro enquanto o caminho estiver bloqueado.

O `test_wall.py` utiliza o mesmo limite de 200 mm e retoma o avanço quando
o obstáculo deixa de bloquear a frente. Esse teste executa apenas avanço e parada.

| Configuração | `main.py` | `test_wall.py` |
| --- | --- | --- |
| PWM esquerdo | 50% | 40% |
| PWM direito | 50% | 49% |
| Frequência do PWM | 1 kHz | 1 kHz |
| Limite frontal | 200 mm | 200 mm |
| Pausa entre ciclos de avanço | 200 ms | 200 ms |
| Timeout dos sensores | 500 ms | 500 ms |

Nos dois programas, erros de leitura interrompem o movimento. O contador
`cont` registra comandos de avanço; na `main.py`, `giros` registra manobras
temporizadas concluídas.

## Execução no ESP32

1. Conecte os componentes conforme [PINAGEM.md](PINAGEM.md).
2. No Thonny, selecione o interpretador MicroPython para ESP32 e a porta da placa.
3. Copie [lib/vl53l0x.py](lib/vl53l0x.py) para `/lib/vl53l0x.py` no ESP32.
4. Execute [tests/test_sensors_esp32.py](tests/test_sensors_esp32.py) para acompanhar as leituras dos sensores.
5. Execute [test_wall.py](test_wall.py) para testar o avanço e a parada diante de uma parede.
6. Salve [main.py](main.py) como `/main.py` no ESP32 para iniciar o programa principal ao ligar a placa.

Interrompa o programa em execução antes de iniciar outro. Na `main.py` e no
`test_wall.py`, envie `p` + Enter ou pressione `Ctrl+C` no console para encerrar
e desligar os motores. No teste de sensores do ESP32, `Ctrl+C` encerra as leituras.
