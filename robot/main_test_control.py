"""Teste basico dos dois motores do MazeDaL com o L298N.

ENA e ENB compartilham o PWM de D6/GPIO12. Por isso, os dois motores usam
a mesma velocidade, embora suas direcoes sejam controladas separadamente.
"""

from machine import Pin, PWM
from utime import sleep_ms

from control import DriveBase, Motor
from pinout import (
    MOTOR_LEFT_IN1_GPIO,
    MOTOR_LEFT_IN2_GPIO,
    MOTOR_RIGHT_IN3_GPIO,
    MOTOR_RIGHT_IN4_GPIO,
    MOTOR_ENABLE_GPIO,
)


STEP_TIME_MS = 1000
PAUSE_TIME_MS = 500
MOTOR_SPEED = 0.7
TURN_SPEED = 0.6
PWM_FREQUENCY_HZ = 1000


def create_drivebase():
    """Cria dois motores que compartilham a mesma saida PWM."""
    shared_enable = PWM(
        Pin(MOTOR_ENABLE_GPIO, Pin.OUT),
        freq=PWM_FREQUENCY_HZ,
    )
    left = Motor(
        Pin(MOTOR_LEFT_IN1_GPIO, Pin.OUT),
        Pin(MOTOR_LEFT_IN2_GPIO, Pin.OUT),
    )
    right = Motor(
        Pin(MOTOR_RIGHT_IN3_GPIO, Pin.OUT),
        Pin(MOTOR_RIGHT_IN4_GPIO, Pin.OUT),
    )
    return DriveBase(
        left,
        right,
        enable=shared_enable,
        speed=MOTOR_SPEED,
        turn_speed=TURN_SPEED,
    )


def run_step(drive, message, movement):
    print(message)
    movement()
    sleep_ms(STEP_TIME_MS)
    drive.stop()
    sleep_ms(PAUSE_TIME_MS)


def main():
    drive = create_drivebase()
    drive.stop()

    print("Teste dos motores iniciara em 3 segundos.")
    for seconds in (3, 2, 1):
        print(seconds)
        sleep_ms(1000)

    try:
        run_step(drive, "Frente", drive.forward)
        run_step(drive, "Giro para a esquerda", drive.turn_left)
        run_step(drive, "Giro para a direita", drive.turn_right)
        run_step(drive, "Re", drive.backward)
    except KeyboardInterrupt:
        print("Teste interrompido.")
    finally:
        drive.stop()
        print("Motores parados.")


if __name__ == "__main__":
    main()
