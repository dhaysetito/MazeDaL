from machine import Pin, SoftI2C, Signal
import time
import vl53l0x

# -------------------------
# Configs
# -------------------------

SCL_PIN = 4       # D2
SDA_PIN = 5       # D1

MOTOR_PIN = 12    # D6

LIMITE_MM = 150   # 15 cm

time.sleep_ms(100)
print ("Ready")
# -------------------------
# I2C
# -------------------------



i2c = SoftI2C(
    scl=Pin(SCL_PIN),
    sda=Pin(SDA_PIN),
    freq=100000
)

print("Dispositivos I2C:", [hex(x) for x in i2c.scan()])

# -------------------------
# VL53L0X
# -------------------------

sensor = vl53l0x.VL53L0X(
    i2c,
    io_timeout_ms=500
)

# -------------------------
# LED integrado
# -------------------------

led = Signal(
    Pin(2, Pin.OUT),
    invert=True
)

led.off()

# -------------------------
# Motores
# -------------------------

# D6 / GPIO12 controla ENA e ENB ao mesmo tempo
motor = Pin(MOTOR_PIN, Pin.OUT)

# Começa parado por segurança
motor.value(0)

# -------------------------
# Funções
# -------------------------

def andar():
    motor.value(1)

def parar():
    motor.value(0)

# -------------------------
# Loop principal
# -------------------------

while True:
    try:
        distancia = sensor.range

        print("Distancia: {} mm".format(distancia))

        if 0 < distancia <= LIMITE_MM:
            parar()
            led.on()

            print("OBSTACULO -> PARADO")

        elif distancia > LIMITE_MM:
            andar()
            led.off()

            print("CAMINHO LIVRE -> ANDANDO")

        else:
            # Leitura inválida, por exemplo 0 mm
            parar()
            led.off()

            print("LEITURA INVALIDA -> PARADO")

    except Exception as erro:
        # Em qualquer erro do sensor, para o robô
        parar()
        led.off()

        print("Erro na leitura:", erro)

    time.sleep_ms(200)


