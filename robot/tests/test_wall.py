"""Um sensor frontal: anda acima de 200 mm e para a 200 mm ou menos.

No console do Thonny, envie p + Enter para encerrar. Ctrl+C tambem encerra.
Use a pinagem ESP32-WROOM/L298N de PINAGEM.md e vl53l0x.py no ESP32.
Inicializacao do sensor baseada no test.py validado com os tres sensores.
PWM ajustavel por motor; cont conta comandos de avanco, nao giros das rodas.
"""

from machine import Pin, SoftI2C, PWM
import select
import sys
import time
import vl53l0x


SDA_PIN = 21
SCL_PIN = 22
XSHUT_FRENTE_PIN = 32
XSHUT_ESQUERDA_PIN = 33
XSHUT_DIREITA_PIN = 13

ENA_PIN = 25
ENB_PIN = 27 # era 26
IN1_PIN = 18
IN2_PIN = 19
IN3_PIN = 23
IN4_PIN = 14 # era 27
ESQUERDO_INVERTIDO = False
DIREITO_INVERTIDO = False

VELOCIDADE_ESQUERDA = 40  # Percentual de PWM, de 0 a 100.
VELOCIDADE_DIREITA = 49
PWM_FREQ = 1000

LIMITE_MM = 200
SENSOR_TIMEOUT_MS = 500
INTERVALO_LEITURA_MS = 200
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
        if not (0 <= VELOCIDADE_ESQUERDA <= 100 and 0 <= VELOCIDADE_DIREITA <= 100):
            raise ValueError("As velocidades devem estar entre 0 e 100")
        motores["pwm_esquerdo"] = PWM(motores["ena"], freq=PWM_FREQ, duty_u16=0)
        motores["pwm_direito"] = PWM(motores["enb"], freq=PWM_FREQ, duty_u16=0)
    except BaseException:
        finalizar_motores(motores)
        raise
    return motores


def andar(motores):
    motores["in1"].value(0 if ESQUERDO_INVERTIDO else 1)
    motores["in2"].value(1 if ESQUERDO_INVERTIDO else 0)
    motores["in3"].value(0 if DIREITO_INVERTIDO else 1)
    motores["in4"].value(1 if DIREITO_INVERTIDO else 0)
    motores["pwm_esquerdo"].duty_u16(int(VELOCIDADE_ESQUERDA * 65535 / 100))
    motores["pwm_direito"].duty_u16(int(VELOCIDADE_DIREITA * 65535 / 100))


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
    # Garante as habilitacoes em zero tambem depois de liberar o PWM.
    motores["ena"].init(Pin.OUT, value=0)
    motores["enb"].init(Pin.OUT, value=0)


def inicializar_sensor(xshut):
    # Primeiro zera TODOS os XSHUT, como no test.py validado.
    for gpio in (XSHUT_FRENTE_PIN, XSHUT_ESQUERDA_PIN, XSHUT_DIREITA_PIN):
        xshut.append(Pin(gpio, Pin.OPEN_DRAIN, value=0))
    time.sleep_ms(100)
    print("Todos os XSHUT configurados em 0")

    i2c = SoftI2C(scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=100000)
    # Libera somente o frontal; os dois laterais continuam em zero.
    xshut[0].value(1)
    time.sleep_ms(100)
    enderecos = i2c.scan()
    print("Dispositivos I2C:", [hex(x) for x in enderecos])
    if 0x29 in enderecos and 0x30 not in enderecos:
        endereco = 0x29
    elif enderecos == [0x30]:
        endereco = 0x30
        print("AVISO: usando o endereco anterior 0x30; confira a ligacao XSHUT.")
    else:
        raise RuntimeError("Sensor frontal ausente ou enderecos em conflito")

    sensor = vl53l0x.VL53L0X(
        i2c, address=endereco, io_timeout_ms=SENSOR_TIMEOUT_MS
    )
    if endereco != 0x30:
        sensor.set_address(0x30)
    if 0x30 not in i2c.scan():
        raise RuntimeError("Sensor frontal ausente apos mudar endereco")
    print("Sensor frontal pronto em 0x30")
    return sensor


def parada_solicitada(teclado):
    # Le sem bloquear a leitura do sensor. Limita o trabalho por consulta.
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


def aguardar_ou_parar(teclado):
    inicio = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), inicio) < INTERVALO_LEITURA_MS:
        if parada_solicitada(teclado):
            return True
        time.sleep_ms(10)
    return False


def executar():
    motores = inicializar_motores()
    xshut = []
    cont = 0
    try:
        teclado = select.poll()
        teclado.register(sys.stdin, select.POLLIN)
        sensor = inicializar_sensor(xshut)
        print("Envie p + Enter no console para encerrar. Ctrl+C tambem para.")
        print("Limite de parede: {} mm".format(LIMITE_MM))
        print("Esquerdo: ENA={}, IN1={}, IN2={}, PWM={}%".format(
            ENA_PIN, IN1_PIN, IN2_PIN, VELOCIDADE_ESQUERDA
        ))
        print("Direito: ENB={}, IN3={}, IN4={}, PWM={}%".format(
            ENB_PIN, IN3_PIN, IN4_PIN, VELOCIDADE_DIREITA
        ))
        print("cont = comandos de avanco; nao mede o giro das rodas.")

        while True:
            if parada_solicitada(teclado):
                break
            try:
                distancia = sensor.range
                if (
                    not isinstance(distancia, (int, float))
                    or isinstance(distancia, bool)
                    or not 0 < distancia < float("inf")
                ):
                    raise ValueError("Leitura invalida: {}".format(distancia))
            except Exception as erro:
                parar(motores)
                print("Erro -> PARADO:", erro)
            else:
                # Uma tecla recebida durante a leitura impede novo acionamento.
                if parada_solicitada(teclado):
                    break
                if distancia <= LIMITE_MM:
                    parar(motores)
                    print("cont={} | {} mm: PAREDE | PWM E=0% D=0%".format(cont, distancia))
                else:
                    andar(motores)
                    cont += 1
                    print("cont={} | {} mm: AVANCO | PWM E={:.0f}% D={:.0f}%".format(
                        cont, distancia,
                        motores["pwm_esquerdo"].duty_u16() * 100 / 65535,
                        motores["pwm_direito"].duty_u16() * 100 / 65535,
                    ))

            if aguardar_ou_parar(teclado):
                break

    except KeyboardInterrupt:
        print("Interrompido por Ctrl+C")
    finally:
        # Encerra sem retomar o movimento, inclusive em erros de inicializacao.
        finalizar_motores(motores)
        for pino in xshut:
            pino.value(0)
        print("Programa encerrado. Motores desligados. cont={}".format(cont))


if __name__ == "__main__":
    executar()

