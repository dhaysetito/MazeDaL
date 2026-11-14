"""MazeDaL - Navegacao autonoma com tres sensores VL53L0X.

Funcionamento:
1. Inicializa motores e sensores.
2. Avanca enquanto a frente estiver livre.
3. Ao detectar parede a LIMITE_MM ou menos, para.
4. Gira aproximadamente 90 graus para a direita.
5. Mede novamente e repete o processo.
6. Aguarda 5 segundos, parado, e registra a distancia inicial a esquerda.
7. Usa um controle proporcional (KP) para manter essa distancia.
8. Interrompe a correcao quando detecta parede a frente e gira normalmente.

A referencia lateral e medida apenas no inicio. Ela NAO muda apos os giros.

Recebe STOP/RESUME via BLE e inicia com motores bloqueados.
Em caso de erro de sensor, os motores sao desligados.
O tempo de giro precisa ser calibrado.
"""

from machine import Pin, SoftI2C, PWM
import machine
import time
import vl53l0x
from ble_maze import MazeBLE


# ==========================================
# PINAGEM DOS SENSORES
# ==========================================

SDA_PIN = 21
SCL_PIN = 22

SENSORES = {
    "frente": (32, 0x30),
    "direita": (33, 0x31),
    "esquerda": (13, 0x32),
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

VELOCIDADE_ESQUERDA = 50
VELOCIDADE_DIREITA = 56

PWM_FREQ = 1000

LIMITE_MM = 155

# Sensor inicial do KP; muda se perder a parede e o outro lado a encontrar.
SENSOR_KP_INICIAL = "esquerda"  # "direita" ou "esquerda"

# Controle proporcional para manter a distancia da parede selecionada.
TEMPO_ESPERA_INICIAL_MS = 5000  # Aguarda 5 segundos parado antes de medir
KP = 0.4                     # Pontos percentuais de PWM por mm de erro 0.5
KD = 0.04                    # Termo derivativo: PWM por (mm/s), valor para teste 0.03
ALFA_D = 0.2                 # Filtro da derivada: 0 < ALFA_D <= 1
ZONA_MORTA_MM = 20           # Ignora oscilacoes pequenas do sensor
MAX_AJUSTE_PWM = 8           # Correcao maxima de +/- 8 pontos por roda
MAX_LATERAL_MM = 250         # Acima disso, considera que nao ha parede lateral

SENSOR_TIMEOUT_MS = 500
INTERVALO_LEITURA_MS = 10
INTERVALO_BLE_MS = 20  # Periodo da telemetria, sem alterar o controle
TEMPO_ESPERA_BLE_MS = 30000  # Se nunca conectar, inicia sozinho apos 30 s

# Timeout de seguranca: o giro termina pela leitura do sensor.
TEMPO_MAX_GIRO_MS = 2500

# Distancia frontal necessaria para encerrar o giro.
LIMITE_FIM_GIRO_MM = 150

QUEDA_PICO_GIRO_MM = 5  # Queda minima para confirmar inicio da diminuicao

PAUSA_ANTES_GIRO_MS = 1500
PAUSA_APOS_GIRO_MS = 1500


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

        if TEMPO_MAX_GIRO_MS <= 0:
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


def resetar_derivada(estado_pd):
    estado_pd["erro_anterior"] = None
    estado_pd["tempo_anterior"] = None
    estado_pd["derivada_filtrada"] = 0.0


def calcular_ajuste_lateral(atual, referencia, lado, estado_pd):
    # Mantem a convencao de sinal do controlador proporcional original.
    erro = atual - referencia
    if lado == "esquerda":
        erro = -erro

    agora = time.ticks_ms()
    anterior = estado_pd["erro_anterior"]
    tempo = estado_pd["tempo_anterior"]
    derivada = 0.0

    if anterior is not None and tempo is not None:
        dt_ms = time.ticks_diff(agora, tempo)
        # Nao usa uma diferenca artificial apos uma pausa longa.
        if 0 < dt_ms <= 500:
            derivada_bruta = (erro - anterior) * 1000.0 / dt_ms
            derivada = (
                ALFA_D * derivada_bruta
                + (1 - ALFA_D) * estado_pd["derivada_filtrada"]
            )

    estado_pd["erro_anterior"] = erro
    estado_pd["tempo_anterior"] = agora
    estado_pd["derivada_filtrada"] = derivada

    # Conserva a zona morta existente e evita movimento por ruido no alvo.
    if abs(erro) <= ZONA_MORTA_MM:
        return 0

    ajuste = KP * erro + KD * derivada
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
# TELEMETRIA BLUETOOTH (SOMENTE MONITORAMENTO)
# ==========================================

def enviar_ble(ble, mensagem):
    # Erros de envio BLE nao podem interromper a navegacao.
    if ble is None:
        return
    try:
        ble.enviar(mensagem)
    except OSError as erro:
        print("Falha no envio BLE:", erro)


def telemetria_avanco(ble, distancias, sensor_kp,
                      distancia_referencia, ajuste, motores):
    # Mensagens curtas para notificacoes BLE com MTU padrao.
    enviar_ble(ble, "D,{},{},{}".format(
        distancias["frente"],
        distancias["esquerda"],
        distancias["direita"]
    ))
    erro = (distancias[sensor_kp] - distancia_referencia) * (
        1 if sensor_kp == "direita" else -1
    )
    enviar_ble(ble, "K,{},{},{},{}".format(
        "D" if sensor_kp == "direita" else "E",
        int(distancia_referencia), int(erro), round(ajuste, 1)
    ))
    enviar_ble(ble, "M,{},{}".format(
        round(motores["pwm_esquerdo"].duty_u16() * 100 / 65535),
        round(motores["pwm_direito"].duty_u16() * 100 / 65535)
    ))
    enviar_ble(ble, "S,AV")


def telemetria_parado(ble, distancias, sensor_kp,
                      distancia_referencia):
    # Leitura completa mesmo antes de receber R.
    enviar_ble(ble, "D,{},{},{}".format(
        distancias["frente"],
        distancias["esquerda"],
        distancias["direita"]
    ))
    erro = (distancias[sensor_kp] - distancia_referencia) * (
        1 if sensor_kp == "direita" else -1
    )
    enviar_ble(ble, "K,{},{},{},0".format(
        "D" if sensor_kp == "direita" else "E",
        int(distancia_referencia), int(erro)
    ))
    enviar_ble(ble, "M,0,0")
    enviar_ble(ble, "S,STOP")


# ==========================================
# GIRO CONTROLADO PELO SENSOR FRONTAL
# ==========================================

def girar_ate_parede(motores, sensores, direcao, ble=None):

    parar(motores)
    if ble is not None and ble.parado:
        return False

    time.sleep_ms(PAUSA_ANTES_GIRO_MS)
    if ble is not None and ble.parado:
        return False

    print(
        "Girando para {} | alvo frontal={} mm".format(
            direcao, LIMITE_FIM_GIRO_MM
        )
    )

    inicio = time.ticks_ms()
    ultimo_ble_giro = time.ticks_ms()
    concluido = False

    try:
        # Giro sobre o proprio eixo.
        if ble is not None and ble.parado:
            return False
        if direcao == "direita":
            mover(motores, True, False)
        else:
            mover(motores, False, True)

        while True:

            if ble is not None and ble.parado:
                print("Giro interrompido por STOP BLE")
                return False

            # Durante o giro, le somente o sensor frontal.
            distancia = sensores["frente"].range

            if ble is not None and ble.parado:
                return False

            # Valida a leitura.
            if (
                not isinstance(distancia, (int, float))
                or isinstance(distancia, bool)
                or not 0 < distancia < float("inf")
            ):
                raise ValueError(
                    "Leitura frontal invalida no giro: {}".format(
                        distancia
                    )
                )

            print(
                "GIRO | direcao={} | frente={} mm | alvo={} mm".format(
                    direcao,
                    distancia,
                    LIMITE_FIM_GIRO_MM
                )
            )

            # Transmite apenas a distancia frontal durante a rotacao.
            agora = time.ticks_ms()
            if time.ticks_diff(agora, ultimo_ble_giro) >= INTERVALO_BLE_MS:
                enviar_ble(ble, "F,{}".format(distancia))
                ultimo_ble_giro = agora

            # Para quando a frente estiver livre o suficiente.
            if distancia >= LIMITE_FIM_GIRO_MM:

                print(
                    "GIRO CONCLUIDO | frente={} mm".format(
                        distancia
                    )
                )

                concluido = True
                break

            # Timeout de seguranca.
            if time.ticks_diff(
                time.ticks_ms(), inicio
            ) >= TEMPO_MAX_GIRO_MS:

                raise RuntimeError(
                    "Tempo maximo de giro excedido"
                )

            time.sleep_ms(INTERVALO_LEITURA_MS)

    finally:
        parar(motores)

    time.sleep_ms(PAUSA_APOS_GIRO_MS)
    return concluido

# ==========================================
# EXECUCAO PRINCIPAL
# ==========================================

def executar():

    motores = inicializar_motores()

    xshut = {}

    cont = 0
    giros = 0
    distancia_referencia = None
    sensor_kp = SENSOR_KP_INICIAL
    estado_pd = {}
    resetar_derivada(estado_pd)
    ble = None
    ultimo_ble = time.ticks_ms()

    if sensor_kp not in ("direita", "esquerda"):
        raise ValueError("SENSOR_KP_INICIAL deve ser direita ou esquerda")

    try:

        sensores = inicializar_sensores(xshut)
        ble = MazeBLE(on_stop=lambda: parar(motores))
        inicio_espera_ble = time.ticks_ms()
        inicio_automatico_realizado = False
        print("Controle BLE: P=parar | R=retomar | C=recalibrar | I=reiniciar.")
        print("Sem conexao BLE por 30 s: inicio automatico.")

        # Mantem os motores desligados enquanto aguarda a calibracao.
        parar(motores)
        print("Aguardando 5 segundos para medir a distancia inicial...")
        # Pausa dividida para permitir reinicializacao remota durante a espera.
        tempo_esperado = 0
        while tempo_esperado < TEMPO_ESPERA_INICIAL_MS:
            if ble.reiniciar:
                parar(motores)
                machine.reset()
            passo = min(50, TEMPO_ESPERA_INICIAL_MS - tempo_esperado)
            time.sleep_ms(passo)
            tempo_esperado += passo

        # Leitura inicial; a referencia vem do lado configurado.
        distancias_iniciais = ler_distancias(sensores, motores)
        distancia_referencia = distancias_iniciais[sensor_kp]

        print("Sensores iniciais (mm):", distancias_iniciais)
        print("Distancia de referencia {}: {} mm".format(
            sensor_kp.upper(), distancia_referencia
        ))

        if distancia_referencia > MAX_LATERAL_MM:
            raise RuntimeError(
                "Sem parede {} na calibracao ({} mm > {} mm). "
                "Posicione o robo perto da parede e reinicie.".format(
                    sensor_kp, distancia_referencia, MAX_LATERAL_MM
                )
            )

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
        estado_pausa_anunciado = False
        while True:

            # Inicia automaticamente somente se NUNCA houve conexao BLE.
            # Uma conexao, mesmo que depois seja perdida, desativa este recurso.
            if (not inicio_automatico_realizado
                    and not ble.ja_conectou
                    and not ble.conexoes
                    and ble.parado
                    and not ble.recalibrar
                    and not ble.reiniciar
                    and time.ticks_diff(time.ticks_ms(), inicio_espera_ble)
                    >= TEMPO_ESPERA_BLE_MS):
                inicio_automatico_realizado = True
                ble.parado = False
                print("BLE nao conectado em 30 s: iniciando navegacao autonoma")

            # Reinicializacao solicitada via BLE, fora do callback de IRQ.
            if ble.reiniciar:
                parar(motores)
                print("BLE I: reiniciando ESP32")
                machine.reset()

            # Recalibracao solicitada: motores parados ate proximo R.
            if ble.recalibrar:
                parar(motores)
                resetar_derivada(estado_pd)
                ble.recalibrar = False
                print("BLE C: recalibrando referencia de {}".format(sensor_kp))
                enviar_ble(ble, "A,CAL")
                try:
                    novas_distancias = ler_distancias(sensores, motores)
                    nova_referencia = novas_distancias[sensor_kp]
                    if nova_referencia > MAX_LATERAL_MM:
                        print("Recalibracao recusada: sem parede {} a ate {} mm".format(
                            sensor_kp, MAX_LATERAL_MM))
                        enviar_ble(ble, "A,SEM_PAREDE")
                    else:
                        distancia_referencia = nova_referencia
                        print("Nova referencia {}: {} mm".format(
                            sensor_kp, distancia_referencia))
                        enviar_ble(ble, "A,REF,{},{}".format(
                            "D" if sensor_kp == "direita" else "E",
                            int(distancia_referencia)))
                except Exception as erro:
                    parar(motores)
                    print("Erro ao recalibrar:", erro)
                    enviar_ble(ble, "A,ERRO_CAL")
                estado_pausa_anunciado = False
                ultimo_ble = time.ticks_ms() - INTERVALO_BLE_MS
                continue

            # STOP e desconexao tem prioridade sobre o movimento.
            if ble.parado:
                parar(motores)
                resetar_derivada(estado_pd)
                if not estado_pausa_anunciado:
                    print("BLE STOP: motores bloqueados; pressione R para retomar")
                    estado_pausa_anunciado = True

                agora = time.ticks_ms()
                if time.ticks_diff(agora, ultimo_ble) >= INTERVALO_BLE_MS:
                    try:
                        # Ler mesmo durante STOP, sem acionar os motores.
                        distancias_parado = ler_distancias(sensores, motores)
                        telemetria_parado(
                            ble, distancias_parado, sensor_kp,
                            distancia_referencia
                        )
                    except Exception as erro:
                        parar(motores)
                        print("Erro de sensor com robo parado:", erro)
                        enviar_ble(ble, "S,ERRO")
                    ultimo_ble = time.ticks_ms()

                time.sleep_ms(INTERVALO_LEITURA_MS)
                continue
            estado_pausa_anunciado = False

            try:
                distancias = ler_distancias(
                    sensores,
                    motores
                )

            except Exception as erro:

                parar(motores)
                resetar_derivada(estado_pd)
                enviar_ble(ble, "S,ERRO")

                print(
                    "Erro de sensor -> PARADO:",
                    erro
                )

                time.sleep_ms(
                    INTERVALO_LEITURA_MS
                )

                continue

            if ble.parado:
                parar(motores)
                resetar_derivada(estado_pd)
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
                resetar_derivada(estado_pd)
                enviar_ble(ble, "S,PA")

                if distancias["direita"] > MAX_LATERAL_MM:
                    direcao = "direita"
                elif distancias["esquerda"] > MAX_LATERAL_MM:
                    direcao = "esquerda"
                else:
                    raise RuntimeError(
                        "Sem saida lateral: ambos os lados bloqueados"
                    )

                print("PAREDE -> PARAR E GIRAR {}".format(direcao.upper()))
                
                # O giro nao muda o sensor usado pelo KP.
                enviar_ble(ble, "S,GD" if direcao == "direita" else "S,GE")

                giro_concluido = girar_ate_parede(
                    motores, sensores, direcao, ble
                )
                enviar_ble(ble, "S,PA" if giro_concluido else "S,STOP")
                
                if not giro_concluido:
                    continue

                giros += 1
                # O giro nao altera o sensor do KP nem a referencia.

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

            # Troca o sensor do KP somente se o lado atual perdeu
            # a parede e o outro lado possui uma parede detectavel.
            outro_sensor = (
                "direita" if sensor_kp == "esquerda" else "esquerda"
            )
            if (distancias[sensor_kp] > MAX_LATERAL_MM
                    and distancias[outro_sensor] <= MAX_LATERAL_MM):
                sensor_kp = outro_sensor
                resetar_derivada(estado_pd)
                print("KP: sensor alterado para {}".format(sensor_kp))

            lateral = distancias[sensor_kp]
            if lateral <= MAX_LATERAL_MM:
                ajuste = calcular_ajuste_lateral(
                    lateral, distancia_referencia, sensor_kp, estado_pd
                )
            else:
                # Sem parede no lado selecionado, avanca sem correcao.
                resetar_derivada(estado_pd)
                ajuste = 0

            if ble.parado:
                parar(motores)
                resetar_derivada(estado_pd)
                continue
            andar(motores, ajuste)

            agora = time.ticks_ms()
            if time.ticks_diff(agora, ultimo_ble) >= INTERVALO_BLE_MS:
                telemetria_avanco(
                    ble, distancias, sensor_kp,
                    distancia_referencia, ajuste, motores
                )
                ultimo_ble = agora

            cont += 1

            print(
                "cont={} | giros={} | sensor={} | ref={}mm | lateral={}mm | erro={:+.0f}mm | ajuste={:+.1f} | PWM E={:.0f}% D={:.0f}%".format(
                    cont,
                    giros,
                    sensor_kp,
                    distancia_referencia,
                    lateral,
                    (lateral - distancia_referencia) * (1 if sensor_kp == "direita" else -1),
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
