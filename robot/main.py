"""Teste independente dos tres sensores VL53L0X no NodeMCU ESP8266."""

from sensors import create_sensor_array


READ_INTERVAL_MS = 500


def main():
    """Imprime leituras em milimetros ate Ctrl-C."""
    from utime import sleep_ms

    sensors = create_sensor_array()
    try:
        print("I2C antes da inicializacao:", sensors.i2c.scan())
        sensors.initialize()
        print("Sensores inicializados: frontal=0x30, esquerdo=0x31, direito=0x32")

        while True:
            print(sensors.read_all())
            if sensors.last_errors:
                print("Erros de leitura:", sensors.last_errors)
            sleep_ms(READ_INTERVAL_MS)
    except KeyboardInterrupt:
        print("Teste interrompido.")
    finally:
        sensors.shutdown()
        print("Sensores desligados.")


if __name__ == "__main__":
    main()
