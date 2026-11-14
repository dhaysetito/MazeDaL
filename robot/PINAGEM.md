# Pinagem — MazeDaL

Controlador: **ESP32-WROOM-32**. Driver dos motores: **L298N**.
Os números das tabelas identificam os GPIOs do ESP32.

## Sensores VL53L0X

| Conexão | Sensor frontal | Sensor esquerdo | Sensor direito |
| --- | --- | --- | --- |
| SDA | GPIO21 | GPIO21 | GPIO21 |
| SCL | GPIO22 | GPIO22 | GPIO22 |
| XSHUT | GPIO32 | GPIO33 | GPIO13 |
| GND | GND comum | GND comum | GND comum |
| Endereço I²C atribuído pelo programa | `0x30` | `0x31` | `0x32` |

SDA e SCL são compartilhados pelos três sensores. Cada XSHUT possui uma
conexão individual ao ESP32.

## Driver L298N

| Entrada do driver | Conexão no ESP32 | Função |
| --- | --- | --- |
| ENA | GPIO25 | PWM do motor esquerdo |
| ENB | GPIO26/27 | PWM do motor direito |
| IN1 | GPIO18 | Sentido do motor esquerdo |
| IN2 | GPIO19 | Sentido do motor esquerdo |
| IN3 | GPIO23 | Sentido do motor direito |
| IN4 | GPIO27/14 | Sentido do motor direito |
| GND | GND comum | Referência dos sinais |

| Saídas do driver | Motor |
| --- | --- |
| OUT1 e OUT2 — canal A | Esquerdo |
| OUT3 e OUT4 — canal B | Direito |

Os jumpers de habilitação ENA e ENB ficam removidos para o controle por PWM.
O ESP32, os sensores e o driver compartilham o GND. A alimentação dos motores
é conectada à entrada de potência do driver.
