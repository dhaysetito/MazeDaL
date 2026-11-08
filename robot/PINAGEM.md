# Pinagem do MazeDaL Robot — ESP32-WROOM-32

Pinagem configurada em `main.py` para uma placa com ESP32-WROOM-32 e três
VL53L0X. O `test.py` foi validado no robô com os três sensores juntos,
usando os XSHUT e endereços da tabela. Antes disso, também foi validado um
teste com apenas um sensor, sem ligar XSHUT ao ESP32.
Para os motores, considera-se um módulo tipo L298N com ENA, ENB e
IN1–IN4; o modelo do driver foi inferido pela descrição e deve ser conferido
nos nomes impressos no módulo.

Os números abaixo são **GPIOs**, não posições físicas no conector.
As identificações D1/D2/D6 do teste antigo não se aplicam a esta ligação.

## Sensores VL53L0X

| Ligação | Sensor frontal | Sensor esquerdo | Sensor direito |
| --- | --- | --- | --- |
| SDA | GPIO21 | GPIO21 | GPIO21 |
| SCL | GPIO22 | GPIO22 | GPIO22 |
| XSHUT | GPIO32 | GPIO33 | GPIO13 |
| Endereço I²C atribuído pelo programa (7 bits) | `0x30` | `0x31` | `0x32` |
| GND | GND comum | GND comum | GND comum |

SDA e SCL são compartilhados entre os três módulos. O código mantém a
frequência de 100 kHz, o timeout de 500 ms e a leitura `sensor.range` do
teste funcional.

Com os fios XSHUT conectados conforme a tabela, na inicialização o programa
mantém todos os XSHUT baixos, libera um sensor por vez e usa `set_address()`
para atribuir seu endereço. Esse procedimento
é repetido a cada inicialização; os endereços não são permanentes.
[Referência da ST sobre múltiplos sensores](https://www.st.com/resource/en/application_note/an4846-using-multiple-vl53l0x-in-a-single-design-stmicroelectronics.pdf).

Os XSHUT são configurados como `Pin.OPEN_DRAIN`: zero força nível baixo e
um libera o sinal para o pull-up do módulo. Confira se os seus módulos têm
esse pull-up; caso não tenham, ele deve ser adicionado para a tensão lógica
especificada pelo fabricante do módulo. Não ligue XSHUT a 5 V.
[Descrição do modo open-drain](https://docs.micropython.org/en/latest/library/machine.Pin.html)
e [exemplo de módulo com XSHUT ligado por pull-up à alimentação do sensor](https://www.pololu.com/product/2490).

### Um sensor sem XSHUT conectado ao ESP32

O `test.py` funcionou no robô com apenas um sensor e sem o fio XSHUT.
Isso é possível quando o módulo mantém XSHUT em nível alto por seu próprio
circuito. Não significa que todo módulo possa operar com essa entrada flutuando;
o comportamento depende do módulo utilizado.

Sem o fio, escrever zero no GPIO32 **não desliga nem reseta o sensor**.
O sensor pode manter o endereço atribuído anteriormente enquanto continuar
alimentado e não sofrer reset. Foi observado `0x30`, e o teste passou a aceitar
esse endereço além do padrão `0x29`.

### Três sensores no mesmo barramento

Para a inicialização implementada no projeto, conecte fisicamente:

- XSHUT do frontal → GPIO32.
- XSHUT do esquerdo → GPIO33.
- XSHUT do direito → GPIO13.

O XSHUT é distinto do pino GPIO1 de interrupção do módulo VL53L0X.
Somente com essas ligações o programa consegue manter os sensores inativos
em standby e habilitar um por vez para atribuir endereços diferentes.
Standby por XSHUT não corta a alimentação VIN/VCC.

Selecionar apenas um sensor no código não desliga fisicamente os outros
se os fios XSHUT deles não estiverem conectados. Sem esse controle, sensores
no mesmo endereço podem causar conflito no I²C.
[Conexões e endereçamento do VL53L0X](https://www.pololu.com/product/2490).

A alimentação VIN/VCC depende do módulo VL53L0X utilizado. Confira sua
especificação e garanta que as linhas conectadas ao ESP32 usem níveis
compatíveis com 3,3 V, sem pull-ups de SDA/SCL para 5 V. No módulo Pololu,
por exemplo, o nível alto de SDA/SCL acompanha VIN; isso não identifica
necessariamente o módulo instalado no robô.
[Alimentação e níveis do módulo Pololu](https://www.pololu.com/product/2490).

## Driver dos motores

| Entrada do driver | GPIO do ESP32 | Função adotada |
| --- | --- | --- |
| ENA | 25 | Habilitar o motor esquerdo |
| ENB | 26 | Habilitar o motor direito |
| IN1 | 18 | Direção do motor esquerdo |
| IN2 | 19 | Direção do motor esquerdo |
| IN3 | 23 | Direção do motor direito |
| IN4 | 27 | Direção do motor direito |
| GND | GND comum | Referência dos sinais |

Ligue o motor esquerdo às saídas do canal A (geralmente OUT1/OUT2) e o direito
às saídas do canal B (geralmente OUT3/OUT4).

Em módulos L298N que tenham jumpers de habilitação ENA/ENB, retire esses
jumpers antes de conectar os GPIO25/26. ENA e ENB agora são sinais separados.
Esses são os jumpers dos canais dos motores, distintos do jumper do regulador
de 5 V; a alimentação e o regulador devem seguir a especificação do módulo.

Para avançar, o programa coloca IN1/IN3 em 1 e IN2/IN4 em 0 antes de
habilitar os motores. Para girar à direita sobre o próprio eixo, mantém
o esquerdo para frente e inverte o direito: IN3=0, IN4=1. Essas combinações
consideram `ESQUERDO_INVERTIDO = False` e `DIREITO_INVERTIDO = False`.
Se um motor girar para trás por causa da montagem, ajuste
`ESQUERDO_INVERTIDO` ou `DIREITO_INVERTIDO` em `main.py`.

ENA e ENB em zero desabilitam os dois canais. A `main.py` e o
`teste_parede.py` usam PWM de 1 kHz nos GPIO25/26, inicialmente
com 50% em cada motor. Ajuste `VELOCIDADE_ESQUERDA` e `VELOCIDADE_DIREITA`
acima de 0 até 100 na main (o teste também permite zero) para alterar o
comando de cada lado. O percentual é o tempo
ligado do PWM, não uma medição da velocidade real da roda.
[PWM no ESP32 com MicroPython](https://docs.micropython.org/en/latest/esp32/quickref.html#pwm-pulse-width-modulation).

A alimentação dos motores deve vir da fonte adequada ao conjunto
motor/driver, com GND comum ao ESP32 e aos sensores. Os motores não são
alimentados pelos GPIOs ou pela saída 3V3 do ESP32.
[Referência do circuito L298](https://www.st.com/resource/en/datasheet/l298.pdf).

Para manter ENA/ENB baixos também enquanto o ESP32 está em reset ou antes
de o MicroPython iniciar, use pull-downs externos, por exemplo de 10 kΩ,
em cada entrada de habilitação se o módulo não os tiver. O código só controla
essas entradas depois de começar a executar.

## LED e escolha dos GPIOs

`LED_PIN = None` desativa o LED por padrão. A identificação WROOM descreve
o módulo e não determina o GPIO ou a polaridade de um LED na placa de
desenvolvimento. Se houver um LED controlável, configure `LED_PIN` e
`LED_ATIVO_BAIXO` conforme o esquema da placa.

A distribuição evita GPIO0/2/5/12/15, que afetam configurações de
inicialização, GPIO6–11, usados pela memória, GPIO34–39, que são apenas
entradas, e GPIO1/3, normalmente usados pela serial. GPIO13 é utilizado
para XSHUT, considerando que não há depuração JTAG em uso.
[Restrições dos GPIOs do ESP32](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/gpio.html).

## Comportamento atual e arquivos

- `main.py`: inicializa os três sensores como no `test.py` validado, com
  todos os XSHUT em zero e esperas de 100 ms. Anda se a distância frontal
  for maior que 200 mm. Ao detectar parede, para, gira à direita, para e
  mede novamente. Repete o giro enquanto a frente estiver bloqueada;
  só avança após uma nova leitura livre. Os laterais são lidos para
  diagnóstico, sem decidir o sentido do giro. Erros de qualquer sensor
  desabilitam os motores e aguardam uma nova leitura válida. `p` + Enter
  ou `Ctrl+C` encerra, inclusive durante o giro. `cont` registra comandos
  de avanço e `giros` registra manobras temporizadas concluídas.
- `navegacao.py`: contém a estratégia alternativa da mão direita. A main
  implementa diretamente a regra de avançar até uma parede e girar à direita.
- `test.py`: teste **somente dos sensores** no ESP32-WROOM, sem acessar
  motores ou LED. Escolha os nomes na linha `SENSORES_ATIVOS`:
  `("frente",)` para um, `("frente", "esquerda")` para dois ou
  `("frente", "esquerda", "direita")` para três. A configuração atual
  seleciona os três e foi validada na montagem. Todos os XSHUT são colocados em zero antes
  de inicializar o I²C; cada sensor selecionado é liberado e recebe seu
  endereço antes de liberar o seguinte.
- `teste_parede.py`: programa independente com um sensor frontal e motores.
  Anda com leitura maior que 200 mm; para com leitura menor ou igual a 200 mm
  e retoma quando o caminho fica livre. Usa a mesma pinagem desta tabela e
  aceita o sensor em `0x29` ou já em `0x30`, como no teste validado.
  A inicialização segue o `test.py`: todos os XSHUT em zero, espera de
  100 ms, configuração do I²C, liberação somente do frontal e nova espera
  de 100 ms. Os laterais permanecem em standby durante este programa.
  No console do Thonny, envie `p` + Enter para encerrar definitivamente;
  `Ctrl+C` também encerra. Leituras inválidas e erros desligam os motores.
  O contador `cont` aumenta a cada comando de avanço e o console mostra
  o PWM configurado de cada lado. Ele não confirma giro físico, pois o robô
  não dispõe de leitura de encoders. Ao encerrar, o programa zera e desativa
  o PWM e mantém ENA/ENB em nível baixo.

O teclado de `teste_parede.py` é consultado sem bloquear, inclusive durante
a pausa entre leituras. Uma leitura I²C em andamento precisa terminar ou
atingir seu timeout antes de o programa processar `p`. Não é uma parada
instantânea de hardware. Antes de executar esse arquivo pelo editor do
Thonny, interrompa qualquer programa que já esteja rodando na placa.
[Consulta não bloqueante com select.poll](https://docs.micropython.org/en/latest/library/select.html).

Para executar o teste no Thonny, salve `vl53l0x.py` no ESP32 e execute
`test.py` pelo editor. O teste funciona com apenas o módulo frontal conectado;
se os laterais também estiverem conectados ao I²C, seus XSHUT devem estar
ligados aos GPIOs indicados para que permaneçam em standby. Com apenas um
sensor conectado, o teste também funciona sem o fio XSHUT, desde que o módulo
mantenha essa entrada em nível alto. Para testar vários sensores juntos,
conecte todos os XSHUT conforme a tabela. O teste encontra
cada sensor em `0x29` e atribui os mesmos endereços da main: frontal `0x30`,
esquerdo `0x31` e direito `0x32`. Com só o frontal ativo, a lista final deve
conter `0x30`, e as leituras aparecem como `frente: ... mm`.

Se apenas um sensor estiver ativo e a lista contiver somente seu endereço
atribuído (por exemplo, `0x30` para o frontal), o teste também permite ler
nesse endereço, com um aviso. Isso permite continuar um teste após um soft
reboot em que o sensor permaneceu energizado e não foi resetado por XSHUT.
Esse caso não confirma que XSHUT esteja funcionando: confira GPIO32 → XSHUT
do frontal antes de integrar os três sensores. O XSHUT é distinto do pino
GPIO1 de interrupção do módulo VL53L0X.
[Endereço volátil e conexões do sensor](https://www.pololu.com/product/2490).

## Calibração do giro na main

`TEMPO_GIRO_90_MS = 500` é um valor inicial para teste, não um ângulo
medido. Sem encoders ou outro sensor de orientação, o programa não consegue
confirmar que girou exatamente 90°. Aumente esse tempo se o giro for menor
que 90° e diminua se for maior. Recalibre ao mudar o PWM ou as condições
de alimentação. O giro depende de ambos os motores funcionando e de suas
direções estarem configuradas corretamente.

`PAUSA_ANTES_GIRO_MS` e `PAUSA_APOS_GIRO_MS`, inicialmente 150 ms, mantêm os
canais desabilitados antes da inversão e após o giro, antes da próxima leitura.
A tecla de parada é consultada a cada 10 ms nessas esperas e durante o giro.
Durante uma leitura de sensor, a consulta ao teclado aguarda a leitura
terminar ou atingir seu timeout.

O intervalo de 200 ms é uma pausa entre ciclos de avanço ou novas tentativas
após erro, além do tempo gasto nas leituras. A leitura frontal é feita primeiro;
ao detectar parede, o programa desabilita os motores antes de ler os laterais.
A regra atual não faz mapa nem reconhece a saída e pode repetir trajetos em
labirintos com ciclos. Antes do primeiro teste no chão, confira com as rodas
suspensas se ambos os motores avançam e se o comando de giro inverte o direito.
