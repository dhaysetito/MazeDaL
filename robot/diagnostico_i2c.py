"""Diagnostico do frontal e esquerdo juntos, sem motores e sem driver VL53L0X.

SDA compartilhado=21; SCL compartilhado=22; XSHUT frente=32/esquerda=33.
Deixe o sensor direito desconectado durante o teste.
Nao muda enderecos: com ambos ativos, 0x29 nao distingue os dois sensores.
"""

from machine import Pin, SoftI2C
import time


def executar():
    frente = Pin(32, Pin.OPEN_DRAIN, value=0)
    esquerda = Pin(33, Pin.OPEN_DRAIN, value=0)
    sda = Pin(21, Pin.OPEN_DRAIN, value=1)
    scl = Pin(22, Pin.OPEN_DRAIN, value=1)

    try:
        for descricao, ligar_frente, ligar_esquerda in (
            ("AMBOS EM STANDBY", 0, 0),
            ("SO FRENTE ATIVO", 1, 0),
            ("SO ESQUERDA ATIVO", 0, 1),
            ("AMBOS ATIVOS", 1, 1),
        ):
            frente.value(0)
            esquerda.value(0)
            time.sleep_ms(100)
            frente.value(ligar_frente)
            esquerda.value(ligar_esquerda)
            time.sleep_ms(100)

            # Libera as linhas e le o nivel real antes de iniciar o scan.
            sda.value(1)
            scl.value(1)
            time.sleep_ms(10)
            print("\n--- {} ---".format(descricao))
            print("Nivel SDA:", sda.value(), "Nivel SCL:", scl.value())
            try:
                i2c = SoftI2C(sda=sda, scl=scl, freq=100000, timeout=10000)
                print("I2C:", [hex(a) for a in i2c.scan()])
            except Exception as erro:
                print("Erro no I2C:", erro)

    except KeyboardInterrupt:
        print("Diagnostico interrompido")
    finally:
        frente.value(0)
        esquerda.value(0)
        sda.value(1)
        scl.value(1)
        print("\nDiagnostico encerrado")


if __name__ == "__main__":
    executar()
