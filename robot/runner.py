"""Loop principal do robo: le os sensores e aciona o Controller.

Nao e executado sozinho no boot (diferente de main.py); chame
hardware.start() ou run() pelo REPL/Thonny.
"""

try:
    from utime import sleep_ms
except ImportError:  # Permite testar no Python do computador.
    from time import sleep

    def sleep_ms(milliseconds):
        sleep(milliseconds / 1000.0)


LOOP_INTERVAL_MS = 10


def run(sensors, controller, interval_ms=LOOP_INTERVAL_MS):
    """Roda ate a estrategia terminar (controller.finished) ou Ctrl-C.

    Em qualquer erro os motores sao parados e os sensores desligados.
    """
    try:
        sensors.initialize()
        while not controller.finished:
            controller.update(sensors.read_all())
            sleep_ms(interval_ms)
    except KeyboardInterrupt:
        print("Interrompido.")
    finally:
        controller.stop()
        sensors.shutdown()
        print("Motores parados e sensores desligados.")
        if controller.error:
            print("Parou por erro:", controller.error)
