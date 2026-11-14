"""MazeDaL - Navegacao autonoma com tres sensores VL53L0X.

Funcionamento:
1. Inicializa motores e sensores.
2. Avanca enquanto a frente estiver livre.
3. Durante o avanco, corrige a aproximacao lateral pela variacao das distancias.
4. A menos de 80 mm de uma parede lateral, aplica correcao preventiva.
5. Ao encontrar uma parede frontal (LIMITE_MM), para e gira a direita.
6. Mede novamente e repete o processo.

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
VELOCIDADE_DIREITA = 40 #49

PWM_FREQ = 1000

LIMITE_MM = 85

SENSOR_TIMEOUT_MS = 500
INTERVALO_LEITURA_MS = 200

# Tempo inicial estimado para giro de 90 graus.
TEMPO_GIRO_90_MS = 450

PAUSA_ANTES_GIRO_MS = 150
PAUSA_APOS_GIRO_MS = 150

# Controle lateral: sem integral e sem centralizacao obrigatoria.
LATERAL_LIMITE_MM = 80          # Inicia correcao obrigatoria abaixo de 80 mm
LATERAL_LIBERACAO_MM = 88      # Histerese: termina protecao acima de 88 mm
LATERAL_CRITICO_MM = 45        # Parada preventiva em distancia muito pequena
LATERAL_MAX_VALIDO_MM = 700    # Acima disso, ignora para fins de alinhamento

# Delta de distancia por segundo (mm/s) e ganho PWM por mm/s.
TAXA_MINIMA_MM_S = 12.0        # Ignora pequenas variacoes/ruido
KP_LATERAL = 0.045             # 100 mm/s => ate 4,5 pontos percentuais
FILTRO_TAXA = 0.40             # Suavizacao de 0 a 1 (maior = resposta mais rapida)
CORRECAO_MIN_PERTO = 3.0      # Minimo quando d < 80 mm
CORRECAO_MAX = 6.0            # Maximo de pontos percentuais por roda
PASSO_CORRECAO = 1.5          # Variacao maxima em um ciclo normal
PASSO_CORRECAO_PERTO = 4.0    # Resposta mais rapida em proximidade
SALTO_MAXIMO_MM = 100         # Descarta saltos incoerentes de leitura


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

    # Se omitidas, usa as velocidades originais, inclusive no giro.
    if velocidade_esquerda is None:
        velocidade_esquerda = VELOCIDADE_ESQUERDA
    if velocidade_direita is None:
        velocidade_direita = VELOCIDADE_DIREITA

    velocidade_esquerda = max(0, min(100, velocidade_esquerda))
    velocidade_direita = max(0, min(100, velocidade_direita))

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


def andar(motores, velocidade_esquerda=None, velocidade_direita=None):
    mover(motores, True, True, velocidade_esquerda, velocidade_direita)


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
# CONTROLE LATERAL PELO DELTA DE DISTANCIA
# ==========================================

def limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


class ControleLateral:
    """Corrige apenas durante aproximacao lateral ou abaixo de 80 mm.

    ajuste > 0: roda esquerda acelera, direita desacelera (vira direita).
    ajuste < 0: roda direita acelera, esquerda desacelera (vira esquerda).
    """

    def __init__(self):
        self.reset()

    def reset(self):
        # Resetar apos um giro impede utilizar leituras da direcao anterior.
        self.tempo_anterior = None
        self.esquerda_anterior = None
        self.direita_anterior = None
        self.taxa_esquerda = 0.0
        self.taxa_direita = 0.0
        self.ajuste = 0.0
        self.protecao = None

    def distancia_valida(self, distancia):
        if distancia is None:
            return None
        if 0 < distancia <= LATERAL_MAX_VALIDO_MM:
            return distancia
        return None

    def calcular_taxa(self, atual, anterior, dt):
        # Positiva quando o robo se aproxima daquela parede.
        if atual is None or anterior is None or dt <= 0 or dt > 1.0:
            return 0.0
        delta = anterior - atual
        if abs(delta) > SALTO_MAXIMO_MM:
            return 0.0
        return delta / dt

    def atualizar(self, dist_esquerda, dist_direita):
        agora = time.ticks_ms()

        de = self.distancia_valida(dist_esquerda)
        dd = self.distancia_valida(dist_direita)

        # Se a lateral estiver excessivamente perto, nao confiar no giro
        # apenas por PWM: parar e solicitar intervencao/reposicionamento.
        if ((de is not None and de < LATERAL_CRITICO_MM)
                or (dd is not None and dd < LATERAL_CRITICO_MM)):
            self.reset()
            return None, None, "PARADA_LATERAL_CRITICA", 0.0, 0.0

        # Se ambas estao abaixo de 80 mm, desviar de uma aproxima da outra.
        # Nao ha direcao de correcao segura; parar.
        if ((de is not None and de < LATERAL_LIMITE_MM)
                and (dd is not None and dd < LATERAL_LIMITE_MM)):
            self.reset()
            return None, None, "PARADA_CORREDOR_ESTREITO", 0.0, 0.0

        if self.tempo_anterior is None:
            dt = 0.0
        else:
            dt = time.ticks_diff(agora, self.tempo_anterior) / 1000.0

        taxa_e = self.calcular_taxa(de, self.esquerda_anterior, dt)
        taxa_d = self.calcular_taxa(dd, self.direita_anterior, dt)

        # Media exponencial para evitar reacao a uma unica leitura ruidosa.
        self.taxa_esquerda = (
            FILTRO_TAXA * taxa_e
            + (1 - FILTRO_TAXA) * self.taxa_esquerda
        )
        self.taxa_direita = (
            FILTRO_TAXA * taxa_d
            + (1 - FILTRO_TAXA) * self.taxa_direita
        )

        self.tempo_anterior = agora
        self.esquerda_anterior = de
        self.direita_anterior = dd

        # Prioridade 1: parede abaixo de 80 mm. Mantem protecao ate 88 mm.
        if de is not None and de < LATERAL_LIMITE_MM:
            lado = "ESQUERDA"
            self.protecao = "ESQUERDA"
            urgente = True
        elif dd is not None and dd < LATERAL_LIMITE_MM:
            lado = "DIREITA"
            self.protecao = "DIREITA"
            urgente = True
        elif self.protecao == "ESQUERDA" and de is not None and de < LATERAL_LIBERACAO_MM:
            lado = "ESQUERDA"
            urgente = True
        elif self.protecao == "DIREITA" and dd is not None and dd < LATERAL_LIBERACAO_MM:
            lado = "DIREITA"
            urgente = True
        else:
            self.protecao = None
            urgente = False
            # Prioridade 2: aproximacao, mesmo acima de 80 mm.
            aproximacao_e = max(0.0, self.taxa_esquerda)
            aproximacao_d = max(0.0, self.taxa_direita)

            if (aproximacao_e >= TAXA_MINIMA_MM_S
                    and aproximacao_e >= aproximacao_d):
                lado = "ESQUERDA"
            elif aproximacao_d >= TAXA_MINIMA_MM_S:
                lado = "DIREITA"
            else:
                lado = None

        # Ajuste positivo: gira para direita (afasta da parede esquerda).
        # Ajuste negativo: gira para esquerda (afasta da parede direita).
        if lado == "ESQUERDA":
            intensidade = KP_LATERAL * max(0.0, self.taxa_esquerda)
            if urgente:
                intensidade = max(CORRECAO_MIN_PERTO, intensidade)
            alvo = limitar(intensidade, 0.0, CORRECAO_MAX)
        elif lado == "DIREITA":
            intensidade = KP_LATERAL * max(0.0, self.taxa_direita)
            if urgente:
                intensidade = max(CORRECAO_MIN_PERTO, intensidade)
            alvo = -limitar(intensidade, 0.0, CORRECAO_MAX)
        else:
            alvo = 0.0

        # Limita a mudanca de PWM entre ciclos, inclusive na volta ao padrao.
        passo_max = PASSO_CORRECAO_PERTO if urgente else PASSO_CORRECAO
        self.ajuste += limitar(alvo - self.ajuste, -passo_max, passo_max)

        ve = limitar(VELOCIDADE_ESQUERDA + self.ajuste, 0, 100)
        vd = limitar(VELOCIDADE_DIREITA - self.ajuste, 0, 100)

        if urgente:
            modo = "PROTECAO_" + lado
        elif lado is not None:
            modo = "DELTA_" + lado
        elif abs(self.ajuste) >= 0.05:
            modo = "RETORNO_PADRAO"
        else:
            modo = "RETO_PADRAO"

        return ve, vd, modo, self.taxa_esquerda, self.taxa_direita


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
    controle_lateral = ControleLateral()

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
                controle_lateral.reset()

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
                controle_lateral.reset()

                giros += 1

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

            ve, vd, modo, taxa_e, taxa_d = controle_lateral.atualizar(
                distancias["esquerda"],
                distancias["direita"]
            )

            if ve is None:
                parar(motores)
                print("CONTROLE LATERAL ->", modo)
                time.sleep_ms(INTERVALO_LEITURA_MS)
                continue

            andar(motores, ve, vd)

            cont += 1

            print(
                "cont={} | giros={} | {} | "
                "PWM E={:.1f}% D={:.1f}% | "
                "taxa E={:.1f} D={:.1f} mm/s".format(
                    cont,
                    giros,
                    modo,
                    ve,
                    vd,
                    taxa_e,
                    taxa_d,
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



