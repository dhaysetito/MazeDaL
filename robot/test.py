"""Teste de 1, 2 ou 3 VL53L0X. Ctrl+C encerra. Sem motores."""

from machine import Pin, SoftI2C
import time
import vl53l0x

# Escolha os sensores nesta linha:
SENSORES_ATIVOS = ("frente", "esquerda", "direita")
# Um:   ("frente",)
# Tres: ("frente", "esquerda", "direita")

# Nome: (GPIO do XSHUT, endereco I2C).
SENSORES = {
    "frente": (32, 0x30),
    "esquerda": (33, 0x31),
    "direita": (13, 0x32),
}


def executar():
    xshut = {}
    sensores = {}
    try:
        # Primeiro coloca TODOS os XSHUT em zero.
        for nome, (gpio, _) in SENSORES.items():
            xshut[nome] = Pin(gpio, Pin.OPEN_DRAIN, value=0)
        time.sleep_ms(100)
        print("Todos os XSHUT configurados em 0")

        if not SENSORES_ATIVOS:
            raise ValueError("Selecione pelo menos um sensor")
        i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=100000)

        for nome in SENSORES_ATIVOS:
            endereco = SENSORES[nome][1]
            xshut[nome].value(1)
            time.sleep_ms(100)
            encontrados = i2c.scan()
            print(nome, "I2C:", [hex(a) for a in encontrados])

            if 0x29 in encontrados and endereco not in encontrados:
                atual = 0x29
            elif len(SENSORES_ATIVOS) == 1 and encontrados == [endereco]:
                atual = endereco
                print("AVISO: endereco mantido; confira XSHUT")
            else:
                raise RuntimeError(nome + ": sensor ausente ou endereco em conflito")

            sensor = vl53l0x.VL53L0X(i2c, address=atual, io_timeout_ms=500)
            if atual != endereco:
                sensor.set_address(endereco)
            sensores[nome] = sensor

        print("Sensores prontos:", [hex(a) for a in i2c.scan()])
        while True:
            print_sensors = ""
            
            for nome, sensor in sensores.items():
                try:
                    print_sensors = print_sensors + nome + ":" + str(sensor.range) + "mm" + "\t|\t"
                except Exception as erro:
                    print(nome, ": erro:", erro)
            time.sleep_ms(200)
            print(print_sensors)

    except KeyboardInterrupt:
        print("Teste interrompido")
    finally:
        for pino in xshut.values():
            pino.value(0)


if __name__ == "__main__":
    executar()


