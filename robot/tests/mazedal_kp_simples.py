
"""MazeDaL - Navegacao autonoma com tres sensores VL53L0X.

Funcionamento:
1. Inicializa motores e sensores.
2. Avanca enquanto a frente estiver livre.
3. Ao detectar parede a LIMITE_MM ou menos, para.
4. Gira aproximadamente 90 graus para a direita.
5. Mede novamente e repete o processo.
6. Usa a variacao da distancia lateral para corrigir a direcao.

Nao utiliza comandos do computador para parada.
Em caso de erro de sensor, os motores sao desligados.
O tempo de giro precisa ser calibrado.
"""

from machine import Pin, SoftI2C, PWM
import time
import vl53l0x


# ==========================================
# PINAGEM DOS SENSORES
# ==========================================

SDA_PIN = 21
SCL_PIN = 22

SENSORES = {
    "frente": (32, 0x30),
    "esquerda": (33, 0x31),
    "direita": (13, 0x32),
}


# ==========================================
# PINAGEM DOS MOTORES
# ==========================================

ENA_PIN = 25
ENB_PIN = 27

IN1_PIN = 18
IN2_PIN = 19
IN3_PIN = 23
IN4_PIN = 14

ESQUERDO_INVERTIDO = False
DIREITO_INVERTIDO = False


# ==========================================
# CONFIGURACOES
# ==========================================

VELOCIDADE_ESQUERDA = 40
VELOCIDADE_DIREITA = 45

PWM_FREQ = 1000

LIMITE_MM = 70

# Correcao suave de direcao com sensor lateral.
# "esquerda" ou "direita": escolha o lado com parede de referencia.
LADO_REFERENCIA = "esquerda"
KP = 0.35                 # Pontos percentuais de PWM por mm de variacao
ZONA_MORTA_MM = 3        # Ignora pequenas variacoes/ruido do sensor
MAX_AJUSTE_PWM = 8       # Limita a correcao em cada roda a +/- 8 pontos
MAX_LATERAL_MM = 250     # Sem parede proxima, segue em linha reta sem correcao

SENSOR_TIMEOUT_MS = 500
INTERVALO_LEITURA_MS = 200

# Tempo inicial estimado para giro de 90 graus.
TEMPO_GIRO_90_MS = 500

PAUSA_ANTES_GIRO_MS = 150
PAUSA_APOS_GIRO_MS = 150


# ==========================================
# INICIALIZACAO DOS MOTORES
# ==========================================

def inicializar_motores():

    motores = {
        "ena": Pin(ENA_PIN, Pin.OUT, value=0),
        "enb": Pin(ENB_PIN, Pin.OUT, value=0),
    }

    for nome, gpio in (
        ("in1", IN1_PIN),
        ("in2", IN2_PIN),
        ("in3", IN3_PIN),
        ("in4", IN4_PIN),
    ):
        motores[nome] = Pin(
            gpio, Pin.OUT, value=0
        )

    try:
        if not (
            0 < VELOCIDADE_ESQUERDA <= 100
            and 0 < VELOCIDADE_DIREITA <= 100
        ):
            raise ValueError(
                "Velocidades devem estar entre 1 e 100"
            )

        if TEMPO_GIRO_90_MS <= 0:
            raise ValueError(
                "Tempo de giro deve ser positivo"
            )

        motores["pwm_esquerdo"] = PWM(
            motores["ena"],
            freq=PWM_FREQ,
            duty_u16=0
        )

        motores["pwm_direito"] = PWM(
            motores["enb"],
            freq=PWM_FREQ,
            duty_u16=0
        )

    except BaseException:
        finalizar_motores(motores)
        raise

    return motores


# ==========================================
# CONTROLE DOS MOTORES
# ==========================================

def mover(motores, esquerda_frente, direita_frente,
          velocidade_esquerda=None, velocidade_direita=None):

    # Nos giros, usa as velocidades padrao.
    if velocidade_esquerda is None:
        velocidade_esquerda = VELOCIDADE_ESQUERDA
    if velocidade_direita is None:
        velocidade_direita = VELOCIDADE_DIREITA

    if ESQUERDO_INVERTIDO:
        esquerda_frente = not esquerda_frente

    if DIREITO_INVERTIDO:
        direita_frente = not direita_frente

    motores["in1"].value(
        1 if esquerda_frente else 0
    )
    motores["in2"].value(
        0 if esquerda_frente else 1
    )

    motores["in3"].value(
        1 if direita_frente else 0
    )
    motores["in4"].value(
        0 if direita_frente else 1
    )

    motores["pwm_esquerdo"].duty_u16(
        int(velocidade_esquerda * 65535 / 100)
    )

    motores["pwm_direito"].duty_u16(
        int(velocidade_direita * 65535 / 100)
    )


def andar(motores, ajuste=0):
    # Ajuste positivo -> vira para a direita.
    # Ajuste negativo -> vira para a esquerda.
    vel_esq = max(0, min(100, VELOCIDADE_ESQUERDA + ajuste))
    vel_dir = max(0, min(100, VELOCIDADE_DIREITA - ajuste))
    mover(motores, True, True, vel_esq, vel_dir)


def calcular_ajuste_lateral(atual, anterior):
    # Primeira leitura: nao ha variacao a calcular.
    if anterior is None:
        return 0

    delta = atual - anterior
    if abs(delta) <= ZONA_MORTA_MM:
        return 0

    # Esquerda diminuindo -> virar para a direita.
    # Direita diminuindo -> virar para a esquerda.
    sinal = -1 if LADO_REFERENCIA == "esquerda" else 1
    ajuste = KP * sinal * delta
    return max(-MAX_AJUSTE_PWM, min(MAX_AJUSTE_PWM, ajuste))


def parar(motores):

    for pwm, pino in (
        ("pwm_esquerdo", "ena"),
        ("pwm_direito", "enb"),
    ):
        if pwm in motores:
            motores[pwm].duty_u16(0)
        else:
            motores[pino].value(0)


def finalizar_motores(motores):

    parar(motores)

    for nome in (
        "pwm_esquerdo",
        "pwm_direito",
    ):
        if nome in motores:
            motores[nome].deinit()

    motores["ena"].init(
        Pin.OUT, value=0
    )

    motores["enb"].init(
        Pin.OUT, value=0
    )


# ==========================================
# INICIALIZACAO DOS SENSORES
# ==========================================

def inicializar_sensores(xshut):

    # Inicialmente desliga todos os sensores.
    for nome, (gpio, _) in SENSORES.items():

        xshut[nome] = Pin(
            gpio,
            Pin.OPEN_DRAIN,
            value=0
        )

    time.sleep_ms(100)

    print("Todos os XSHUT em 0")

    i2c = SoftI2C(
        scl=Pin(SCL_PIN),
        sda=Pin(SDA_PIN),
        freq=100000
    )

    sensores = {}

    for nome, (_, endereco) in SENSORES.items():

        # Liga um sensor por vez.
        xshut[nome].value(1)

        time.sleep_ms(100)

        encontrados = i2c.scan()

        print(
            nome,
            "I2C:",
            [hex(a) for a in encontrados]
        )

        if (
            0x29 not in encontrados
            or endereco in encontrados
        ):
            raise RuntimeError(
                nome + ": sensor ausente ou conflito"
            )

        sensor = vl53l0x.VL53L0X(
            i2c,
            address=0x29,
            io_timeout_ms=SENSOR_TIMEOUT_MS
        )

        sensor.set_address(endereco)

        sensores[nome] = sensor

    encontrados = i2c.scan()

    print(
        "Sensores prontos:",
        [hex(a) for a in encontrados]
    )

    for nome, (_, endereco) in SENSORES.items():

        if endereco not in encontrados:
            raise RuntimeError(
                nome + ": ausente apos configuracao"
            )

    return sensores


# ==========================================
# LEITURA DOS SENSORES
# ==========================================

def ler_distancias(sensores, motores):

    distancias = {}

    # Leitura frontal possui prioridade.
    for nome in (
        "frente",
        "esquerda",
        "direita",
    ):

        distancia = sensores[nome].range

        if (
            not isinstance(distancia, (int, float))
            or isinstance(distancia, bool)
            or not 0 < distancia < float("inf")
        ):
            raise ValueError(
                "Leitura invalida em {}: {}".format(
                    nome, distancia
                )
            )

        # Obstaculo frontal: para os motores.
        if (
            nome == "frente"
            and distancia <= LIMITE_MM
        ):
            parar(motores)

        distancias[nome] = distancia

    return distancias


# ==========================================
# GIRO DE 90 GRAUS PARA A DIREITA
# ==========================================

def girar_90_direita(motores):

    parar(motores)

    time.sleep_ms(PAUSA_ANTES_GIRO_MS)

    print(
        "Girando para direita por {} ms".format(
            TEMPO_GIRO_90_MS
        )
    )

    try:
        # Motor esquerdo para frente.
        # Motor direito para tras.
        # Giro sobre o proprio eixo.
        mover(motores, True, False)

        time.sleep_ms(TEMPO_GIRO_90_MS)

    finally:
        parar(motores)

    time.sleep_ms(PAUSA_APOS_GIRO_MS)


# ==========================================
# EXECUCAO PRINCIPAL
# ==========================================

def executar():

    motores = inicializar_motores()

    xshut = {}

    cont = 0
    giros = 0
    anterior_lateral = None

    if LADO_REFERENCIA not in ("esquerda", "direita"):
        raise ValueError("LADO_REFERENCIA deve ser esquerda ou direita")

    try:

        sensores = inicializar_sensores(xshut)

        print("MazeDaL iniciado")

        print(
            "PWM esquerdo={}%, direito={}%".format(
                VELOCIDADE_ESQUERDA,
                VELOCIDADE_DIREITA
            )
        )

        print(
            "Limite de parede: {} mm".format(
                LIMITE_MM
            )
        )

        # Navegacao autonoma continua.
        while True:

            try:
                distancias = ler_distancias(
                    sensores,
                    motores
                )

            except Exception as erro:

                parar(motores)
                anterior_lateral = None

                print(
                    "Erro de sensor -> PARADO:",
                    erro
                )

                time.sleep_ms(
                    INTERVALO_LEITURA_MS
                )

                continue

            print(
                "Distancias (mm):",
                distancias
            )

            # ----------------------------------
            # PAREDE DETECTADA
            # ----------------------------------

            if distancias["frente"] <= LIMITE_MM:

                parar(motores)

                print(
                    "PAREDE -> PARAR E GIRAR DIREITA"
                )

                girar_90_direita(motores)

                giros += 1
                anterior_lateral = None  # Giro muda a parede de referencia.

                print(
                    "Giro {} concluido".format(
                        giros
                    )
                )

                # Volta ao inicio do loop para
                # realizar nova leitura frontal.
                continue

            # ----------------------------------
            # CAMINHO LIVRE
            # ----------------------------------

            lateral = distancias[LADO_REFERENCIA]
            if lateral <= MAX_LATERAL_MM:
                ajuste = calcular_ajuste_lateral(lateral, anterior_lateral)
                anterior_lateral = lateral
            else:
                # Sem parede de referencia proxima: nao usa valor antigo.
                ajuste = 0
                anterior_lateral = None

            andar(motores, ajuste)

            cont += 1

            print(
                "cont={} | giros={} | lateral={}mm | ajuste={:+.1f} | PWM E={:.0f}% D={:.0f}%".format(
                    cont,
                    giros,
                    lateral,
                    ajuste,
                    motores["pwm_esquerdo"].duty_u16()
                    * 100 / 65535,
                    motores["pwm_direito"].duty_u16()
                    * 100 / 65535,
                )
            )

            time.sleep_ms(
                INTERVALO_LEITURA_MS
            )

    finally:

        try:
            finalizar_motores(motores)

        finally:
            for pino in xshut.values():
                pino.value(0)

        print(
            "Programa encerrado. "
            "Motores desligados. "
            "cont={} giros={}".format(
                cont,
                giros
            )
        )


if __name__ == "__main__":
    executar()


