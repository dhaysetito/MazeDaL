
"""MazeDaL - Calibracao dos motores.

1. Anda para frente por 2 segundos.
2. Para por 1 segundo.
3. Gira para a direita pelo tempo configurado.
4. Para definitivamente.

Nao utiliza sensores nem comandos do computador.
"""

from machine import Pin, PWM
import time


# =====================================
# PINAGEM VALIDADA - CODIGO BASE
# =====================================

ENA_PIN = 25
ENB_PIN = 27

IN1_PIN = 18
IN2_PIN = 19
IN3_PIN = 23
IN4_PIN = 14

ESQUERDO_INVERTIDO = False
DIREITO_INVERTIDO = False


# =====================================
# VELOCIDADES
# =====================================

VELOCIDADE_ESQUERDA = 40
VELOCIDADE_DIREITA = 49

PWM_FREQ = 1000


# =====================================
# TEMPOS DE CALIBRACAO
# =====================================

TEMPO_FRENTE_MS = 2000

# ALTERE ESTE VALOR PARA CALIBRAR 90 GRAUS
TEMPO_GIRO_90_MS = 500

PAUSA_MS = 1000


# =====================================
# INICIALIZACAO
# =====================================

ena = Pin(ENA_PIN, Pin.OUT, value=0)
enb = Pin(ENB_PIN, Pin.OUT, value=0)

in1 = Pin(IN1_PIN, Pin.OUT, value=0)
in2 = Pin(IN2_PIN, Pin.OUT, value=0)
in3 = Pin(IN3_PIN, Pin.OUT, value=0)
in4 = Pin(IN4_PIN, Pin.OUT, value=0)

pwm_esquerdo = PWM(
    ena, freq=PWM_FREQ, duty_u16=0
)

pwm_direito = PWM(
    enb, freq=PWM_FREQ, duty_u16=0
)


# =====================================
# FUNCOES DOS MOTORES
# =====================================

def mover(esquerda_frente, direita_frente):

    if ESQUERDO_INVERTIDO:
        esquerda_frente = not esquerda_frente

    if DIREITO_INVERTIDO:
        direita_frente = not direita_frente

    in1.value(1 if esquerda_frente else 0)
    in2.value(0 if esquerda_frente else 1)

    in3.value(1 if direita_frente else 0)
    in4.value(0 if direita_frente else 1)

    pwm_esquerdo.duty_u16(
        int(VELOCIDADE_ESQUERDA * 65535 / 100)
    )

    pwm_direito.duty_u16(
        int(VELOCIDADE_DIREITA * 65535 / 100)
    )


def parar():

    pwm_esquerdo.duty_u16(0)
    pwm_direito.duty_u16(0)

    in1.value(0)
    in2.value(0)
    in3.value(0)
    in4.value(0)


def andar_frente():

    mover(True, True)


def girar_direita():

    # Motor esquerdo avanca.
    # Motor direito recua.
    mover(True, False)


# =====================================
# TESTE DE CALIBRACAO
# =====================================

try:

    print("Iniciando teste MazeDaL")

    # 1 - Avancar por 2 segundos
    print("Avancando por 2 segundos")

    andar_frente()
    time.sleep_ms(TEMPO_FRENTE_MS)

    parar()

    # 2 - Pausa antes do giro
    time.sleep_ms(PAUSA_MS)

    # 3 - Giro para direita
    print(
        "Girando por {} ms".format(
            TEMPO_GIRO_90_MS
        )
    )

    girar_direita()
    time.sleep_ms(TEMPO_GIRO_90_MS)

    parar()

    print("Teste concluido")


finally:

    parar()

    pwm_esquerdo.deinit()
    pwm_direito.deinit()

    ena.init(Pin.OUT, value=0)
    enb.init(Pin.OUT, value=0)

    print("Motores desligados")

