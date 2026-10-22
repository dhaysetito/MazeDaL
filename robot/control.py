"""Controle de movimento do MazeDaL (NodeMCU ESP8266 + L298N).

API exigida por runner.py:
    controller.update(readings)
    controller.stop()

Camadas:
    Motor      -> um lado do L298N (pinos IN de direcao)
    DriveBase  -> dois motores + enable compartilhado (PWM de velocidade)
    Controller -> executa as acoes escolhidas por uma estrategia
                  (strategies.py: left_hand, dfs) a partir dos sensores

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

from strategies import LeftHand

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
    """Executa as acoes de uma estrategia (strategies.py) sem bloquear.

    A estrategia decide (esquerda, frente, passo de uma celula, ...); o
    Controller move o DriveBase e mede o tempo dos giros e passos. Chame
    update(readings) em loop, compativel com runner.run.

    Estados: stopped, forward, stepping, turning_left, turning_right.
    Giros e passos sao por TEMPO, entao turn_90_ms e step_ms precisam ser
    calibrados no robo.

    `readings` vem de sensors.read_all(): nome -> distancia em mm, com as
    chaves "left", "front" e "right" (os nomes de pinout.SENSOR_CONFIG).
    Uma distancia menor que wall_mm conta como parede; leitura None (falha
    do sensor) tambem conta como parede.
    """

    def __init__(
        self, drive, strategy=None, turn_90_ms=450, step_ms=800, wall_mm=150
    ):
        self.drive = drive
        self.strategy = strategy if strategy is not None else LeftHand()
        self.turn_90_ms = turn_90_ms
        self.step_ms = step_ms
        self.wall_mm = wall_mm
        self.state = "stopped"
        self.finished = False  # True quando a estrategia pediu "stop"
        self._action = None
        self._start = 0
        self._total_ms = 0

    def _is_wall(self, distance):
        return distance is None or distance < self.wall_mm

    def _walls(self, readings):
        return {
            "left": self._is_wall(readings["left"]),
            "front": self._is_wall(readings["front"]),
            "right": self._is_wall(readings["right"]),
        }

    def _start_timed(self, action, state, total_ms):
        self._action = action
        self.state = state
        self._total_ms = total_ms
        self._start = ticks_ms()

    def _timed_done(self):
        return ticks_diff(ticks_ms(), self._start) >= self._total_ms

    def _execute(self, action):
        if action == "forward":
            self.state = "forward"
            self.drive.forward()
        elif action == "step":
            self._start_timed("step", "stepping", self.step_ms)
            self.drive.forward()
        elif action == "left":
            self._start_timed("left", "turning_left", self.turn_90_ms)
            self.drive.turn_left()
        elif action == "right":
            self._start_timed("right", "turning_right", self.turn_90_ms)
            self.drive.turn_right()
        elif action == "around":
            self._start_timed("around", "turning_right", self.turn_90_ms * 2)
            self.drive.turn_right()
        elif action == "stop":
            self.stop()
            self.finished = True
        else:
            raise ValueError("Acao desconhecida: %s" % action)

    def update(self, readings):
        if self.finished:
            return

        if self.state in ("stepping", "turning_left", "turning_right"):
            if not self._timed_done():
                return
            self.drive.stop()
            self.state = "stopped"
            done, self._action = self._action, None
            self.strategy.on_done(done)

        self._execute(self.strategy.decide(self._walls(readings)))

    def stop(self):
        self.drive.stop()
        self.state = "stopped"
        self._action = None
