"""Controle de movimento do MazeDaL (NodeMCU ESP8266 + L298N).

API exigida por main.py:
    controller.update(readings)
    controller.stop()

Camadas:
    Motor      -> um lado do L298N (pinos IN de direcao)
    DriveBase  -> dois motores + enable compartilhado (PWM de velocidade)
    Controller -> recebe as leituras dos sensores e decide o movimento

Os numeros de GPIO vem de pinout.py. Importar este modulo no computador nao
aciona nenhum pino: so build_drivebase() usa o modulo machine.
"""

try:
    from utime import ticks_ms, ticks_diff
except ImportError:
    from time import monotonic

    def ticks_ms():
        return int(monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b

# machine.PWM do ESP8266 usa duty de 0 a 1023.
MAX_DUTY = 1023


class Motor:
    """Um lado da ponte H: so direcao (IN1/IN2 ou IN3/IN4)."""

    def __init__(self, in_a, in_b):
        self.in_a = in_a
        self.in_b = in_b
        self.stop()

    def forward(self):
        self.in_a.value(1)
        self.in_b.value(0)

    def backward(self):
        self.in_a.value(0)
        self.in_b.value(1)

    def stop(self):
        self.in_a.value(0)
        self.in_b.value(0)


class DriveBase:
    """Movimentos do robo. `enable` e o PWM ligado a ENA+ENB (pode ser None)."""

    def __init__(self, left, right, enable=None, speed=0.7, turn_speed=0.6):
        self.left = left
        self.right = right
        self.enable = enable
        self.speed = speed
        self.turn_speed = turn_speed

    def _set_speed(self, speed):
        if self.enable is not None:
            self.enable.duty(int(max(0.0, min(1.0, speed)) * MAX_DUTY))

    def forward(self):
        self._set_speed(self.speed)
        self.left.forward()
        self.right.forward()

    def backward(self):
        self._set_speed(self.speed)
        self.left.backward()
        self.right.backward()

    def turn_left(self):
        # giro no proprio eixo: roda esquerda para tras, direita para frente
        self._set_speed(self.turn_speed)
        self.left.backward()
        self.right.forward()

    def turn_right(self):
        self._set_speed(self.turn_speed)
        self.left.forward()
        self.right.backward()

    def stop(self):
        self.left.stop()
        self.right.stop()
        self._set_speed(0)


def build_drivebase(freq=1000):
    """Cria o DriveBase a partir de pinout.py (so funciona na placa).

    Espera em pinout.py:
        MOTOR_LEFT_GPIO  = (IN1, IN2)
        MOTOR_RIGHT_GPIO = (IN3, IN4)
        MOTOR_ENABLE_GPIO  (opcional; None = ENA/ENB fixos em 5V, sem PWM)
    """
    from machine import Pin, PWM
    import pinout

    def motor(pins):
        return Motor(Pin(pins[0], Pin.OUT), Pin(pins[1], Pin.OUT))

    enable_gpio = getattr(pinout, "MOTOR_ENABLE_GPIO", None)
    enable = None
    if enable_gpio is not None:
        enable = PWM(Pin(enable_gpio), freq=freq, duty=0)

    return DriveBase(
        motor(pinout.MOTOR_LEFT_GPIO),
        motor(pinout.MOTOR_RIGHT_GPIO),
        enable,
    )


class Controller:
    """Maquina de estados simples, nao bloqueante (compativel com main.run).

    Estados: forward, turning_left, turning_right, stopped.
    Os giros sao por TEMPO, entao turn_90_ms precisa ser calibrado no robo.

    `readings` vem de sensors.read_all(): nome -> distancia em mm, com as
    chaves "left", "front" e "right" (os nomes de pinout.SENSOR_CONFIG).
    Uma distancia menor que wall_mm conta como parede.
    """

    def __init__(self, drive, turn_90_ms=450, wall_mm=150):
        self.drive = drive
        self.turn_90_ms = turn_90_ms
        self.wall_mm = wall_mm
        self.state = "stopped"
        self._turn_start = 0
        self._turn_total_ms = 0

    def _start_turn(self, state, degrees):
        self.state = state
        self._turn_total_ms = self.turn_90_ms * degrees // 90
        self._turn_start = ticks_ms()
        if state == "turning_left":
            self.drive.turn_left()
        else:
            self.drive.turn_right()

    def _turn_done(self):
        return ticks_diff(ticks_ms(), self._turn_start) >= self._turn_total_ms

    def update(self, readings):
        if self.state in ("turning_left", "turning_right"):
            if not self._turn_done():
                return
            self.drive.stop()
            self.state = "stopped"

        left = readings["left"] < self.wall_mm
        front = readings["front"] < self.wall_mm
        right = readings["right"] < self.wall_mm

        # Regra da mao esquerda: esquerda livre > frente livre > direita > meia-volta
        if not left:
            self._start_turn("turning_left", 90)
        elif not front:
            self.state = "forward"
            self.drive.forward()
        elif not right:
            self._start_turn("turning_right", 90)
        else:
            self._start_turn("turning_right", 180)

    def stop(self):
        self.drive.stop()
        self.state = "stopped"
