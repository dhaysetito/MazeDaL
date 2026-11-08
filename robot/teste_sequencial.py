"""Liga um sensor por vez por 5 segundos. Sem motores e sem mudar enderecos."""

from machine import Pin, SoftI2C
import time


# Comeca com todos os XSHUT em zero.
frente = Pin(32, Pin.OPEN_DRAIN, value=0)
esquerda = Pin(33, Pin.OPEN_DRAIN, value=0)
direita = Pin(13, Pin.OPEN_DRAIN, value=0)

try:
    i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=100000)
    time.sleep_ms(100)
    print("Todos os XSHUT = 0")
    print("I2C:", [hex(a) for a in i2c.scan()])

    for nome, xshut in (
        ("FRENTE", frente),
        ("ESQUERDA", esquerda),
        ("DIREITA", direita),
    ):
        print("\nLigando somente", nome)
        xshut.value(1)
        time.sleep_ms(100)
        try:
            print("I2C:", [hex(a) for a in i2c.scan()])
        except OSError as erro:
            print("Erro no I2C:", erro)
        time.sleep(5)
        xshut.value(0)
        time.sleep_ms(100)
        print(nome, "desligado")

except KeyboardInterrupt:
    print("Teste interrompido")
finally:
    frente.value(0)
    esquerda.value(0)
    direita.value(0)
    print("Todos os XSHUT = 0. Fim do teste.")
