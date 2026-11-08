"""Anda com a frente livre; se houver parede, gira 90 graus a direita e rele.

Os tres VL53L0X usam a inicializacao validada em test.py.
O giro e temporizado: TEMPO_GIRO_90_MS precisa ser calibrado no robo.
Envie p + Enter no console ou Ctrl+C para encerrar.
"""

from machine import Pin, SoftI2C, PWM
import select
import sys
import time
import vl53l0x


SDA_PIN = 21
SCL_PIN = 22
SENSORES = {
    "frente": (32, 0x30),
    "esquerda": (33, 0x31),
    "direita": (13, 0x32),
}

ENA_PIN = 25
ENB_PIN = 26
IN1_PIN = 18
IN2_PIN = 19
IN3_PIN = 23
IN4_PIN = 27
ESQUERDO_INVERTIDO = False
DIREITO_INVERTIDO = False

VELOCIDADE_ESQUERDA = 50  # Percentual de PWM, nao velocidade medida.
VELOCIDADE_DIREITA = 50
PWM_FREQ = 1000
LIMITE_MM = 200
SENSOR_TIMEOUT_MS = 500
INTERVALO_LEITURA_MS = 200

# Valor inicial para experimentar. Nao corresponde a um angulo medido.
# Se girar menos de 90 graus, aumente; se girar mais, diminua.
TEMPO_GIRO_90_MS = 500
PAUSA_ANTES_GIRO_MS = 150
PAUSA_APOS_GIRO_MS = 150
TECLA_PARAR = "p"


def inicializar_motores():
    motores = {
        "ena": Pin(ENA_PIN, Pin.OUT, value=0),
        "enb": Pin(ENB_PIN, Pin.OUT, value=0),
    }
    for nome, gpio in (
        ("in1", IN1_PIN), ("in2", IN2_PIN),
        ("in3", IN3_PIN), ("in4", IN4_PIN),
    ):
        motores[nome] = Pin(gpio, Pin.OUT, value=0)
    try:
        if not (0 < VELOCIDADE_ESQUERDA <= 100 and 0 < VELOCIDADE_DIREITA <= 100):
            raise ValueError("As velocidades devem estar acima de 0 e ate 100")
        if TEMPO_GIRO_90_MS <= 0:
            raise ValueError("TEMPO_GIRO_90_MS deve ser positivo")
        motores["pwm_esquerdo"] = PWM(motores["ena"], freq=PWM_FREQ, duty_u16=0)
        motores["pwm_direito"] = PWM(motores["enb"], freq=PWM_FREQ, duty_u16=0)
    except BaseException:
        finalizar_motores(motores)
        raise
    return motores


def mover(motores, esquerda_frente, direita_frente):
    if ESQUERDO_INVERTIDO:
        esquerda_frente = not esquerda_frente
    if DIREITO_INVERTIDO:
        direita_frente = not direita_frente
    motores["in1"].value(1 if esquerda_frente else 0)
    motores["in2"].value(0 if esquerda_frente else 1)
    motores["in3"].value(1 if direita_frente else 0)
    motores["in4"].value(0 if direita_frente else 1)
    motores["pwm_esquerdo"].duty_u16(int(VELOCIDADE_ESQUERDA * 65535 / 100))
    motores["pwm_direito"].duty_u16(int(VELOCIDADE_DIREITA * 65535 / 100))


def andar(motores):
    mover(motores, True, True)


def parar(motores):
    for pwm, pino in (("pwm_esquerdo", "ena"), ("pwm_direito", "enb")):
        if pwm in motores:
            motores[pwm].duty_u16(0)
        else:
            motores[pino].value(0)


def finalizar_motores(motores):
    parar(motores)
    for nome in ("pwm_esquerdo", "pwm_direito"):
        if nome in motores:
            motores[nome].deinit()
    motores["ena"].init(Pin.OUT, value=0)
    motores["enb"].init(Pin.OUT, value=0)


def inicializar_sensores(xshut):
    # Primeiro coloca TODOS em zero, igual ao test.py validado.
    for nome, (gpio, _) in SENSORES.items():
        xshut[nome] = Pin(gpio, Pin.OPEN_DRAIN, value=0)
    time.sleep_ms(100)
    print("Todos os XSHUT configurados em 0")

    i2c = SoftI2C(sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=100000)
    sensores = {}
    for nome, (_, endereco) in SENSORES.items():
        xshut[nome].value(1)
        time.sleep_ms(100)
        encontrados = i2c.scan()
        print(nome, "I2C:", [hex(a) for a in encontrados])
        if 0x29 not in encontrados or endereco in encontrados:
            raise RuntimeError(nome + ": sensor ausente ou endereco em conflito")
        sensor = vl53l0x.VL53L0X(i2c, address=0x29, io_timeout_ms=SENSOR_TIMEOUT_MS)
        sensor.set_address(endereco)
        sensores[nome] = sensor

    encontrados = i2c.scan()
    print("Sensores prontos:", [hex(a) for a in encontrados])
    for nome, (_, endereco) in SENSORES.items():
        if endereco not in encontrados:
            raise RuntimeError(nome + ": ausente apos mudar endereco")
    return sensores


def ler_distancias(sensores, motores):
    distancias = {}
    # Le a frente primeiro e para imediatamente se detectar parede.
    for nome in ("frente", "esquerda", "direita"):
        distancia = sensores[nome].range
        if (
            not isinstance(distancia, (int, float))
            or isinstance(distancia, bool)
            or not 0 < distancia < float("inf")
        ):
            raise ValueError("Leitura invalida em {}: {}".format(nome, distancia))
        if nome == "frente" and distancia <= LIMITE_MM:
            parar(motores)
        distancias[nome] = distancia
    return distancias


def parada_solicitada(teclado):
    for _ in range(32):
        eventos = teclado.poll(0)
        if not eventos:
            return False
        flags = eventos[0][1]
        if flags & (select.POLLERR | select.POLLHUP):
            raise OSError("Console desconectado")
        if not flags & select.POLLIN:
            return False
        tecla = sys.stdin.read(1)
        if not tecla or tecla.lower() == TECLA_PARAR:
            return True
    return False


def aguardar_ou_parar(teclado, duracao_ms):
    inicio = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), inicio) < duracao_ms:
        if parada_solicitada(teclado):
            return True
        time.sleep_ms(10)
    return parada_solicitada(teclado)


def girar_90_direita(motores, teclado):
    parar(motores)
    if aguardar_ou_parar(teclado, PAUSA_ANTES_GIRO_MS):
        return False

    print("Giro a direita por {} ms (calibrar para 90 graus)".format(TEMPO_GIRO_90_MS))
    try:
        # Esquerdo para frente, direito para tras: giro sobre o proprio eixo.
        mover(motores, True, False)
        if aguardar_ou_parar(teclado, TEMPO_GIRO_90_MS):
            return False
    finally:
        parar(motores)

    return not aguardar_ou_parar(teclado, PAUSA_APOS_GIRO_MS)


def executar():
    motores = inicializar_motores()
    xshut = {}
    cont = 0
    giros = 0
    try:
        teclado = select.poll()
        teclado.register(sys.stdin, select.POLLIN)
        sensores = inicializar_sensores(xshut)
        print("Envie p + Enter ou Ctrl+C para encerrar.")
        print("PWM esquerdo={}%, direito={}% | parede ate {} mm".format(
            VELOCIDADE_ESQUERDA, VELOCIDADE_DIREITA, LIMITE_MM
        ))
        print("cont conta comandos de avanco; giros conta manobras temporizadas.")

        while True:
            if parada_solicitada(teclado):
                break
            try:
                distancias = ler_distancias(sensores, motores)
            except Exception as erro:
                parar(motores)
                print("Erro de sensor -> PARADO:", erro)
                if aguardar_ou_parar(teclado, INTERVALO_LEITURA_MS):
                    break
                continue

            if parada_solicitada(teclado):
                break
            print("Distancias (mm):", distancias)
            if distancias["frente"] <= LIMITE_MM:
                parar(motores)
                print("PAREDE -> PARAR E GIRAR")
                if not girar_90_direita(motores, teclado):
                    break
                giros += 1
                print("Giro {} concluido. Vou medir a frente novamente.".format(giros))
                # Nunca avanca com a leitura feita antes do giro.
                continue

            andar(motores)
            cont += 1
            print("cont={} | giros={} | AVANCO | PWM E={:.0f}% D={:.0f}%".format(
                cont, giros,
                motores["pwm_esquerdo"].duty_u16() * 100 / 65535,
                motores["pwm_direito"].duty_u16() * 100 / 65535,
            ))
            if aguardar_ou_parar(teclado, INTERVALO_LEITURA_MS):
                break

    except KeyboardInterrupt:
        print("Interrompido por Ctrl+C")
    finally:
        try:
            finalizar_motores(motores)
        finally:
            for pino in xshut.values():
                pino.value(0)
        print("Programa encerrado. Motores desligados. cont={} giros={}".format(cont, giros))


if __name__ == "__main__":
    executar()
