"""Composicao do hardware do MazeDaL: liga pinout + sensors + control + runner.

E o UNICO arquivo que cria Pin/I2C/PWM de verdade. Os outros modulos recebem
tudo pronto, entao podem ser testados no computador sem acionar GPIOs.

Na placa:
    import hardware
    hardware.start()
"""

from machine import I2C, Pin

import pinout
import robot_config
from control import Controller, build_drivebase
from runner import run
from sensors import VL53L0XArray
from strategies import make_strategy


def vl53l0x_factory(i2c, address):
    """Cria o driver do VL53L0X. ADAPTAR ao driver MicroPython escolhido.

    sensors.py exige que o objeto devolvido tenha set_address()/change_address()
    e read() (ou read_range_single_millimeters()).
    """
    from vl53l0x import VL53L0X  # driver colocado na placa pelo colega

    return VL53L0X(i2c, address)


def build_sensors():
    i2c = I2C(
        scl=Pin(pinout.I2C_SCL_GPIO),
        sda=Pin(pinout.I2C_SDA_GPIO),
        freq=pinout.I2C_FREQUENCY_HZ,
    )
    definitions = [
        {"name": name, "xshut": Pin(gpio, Pin.OUT), "address": address}
        for name, gpio, address in pinout.SENSOR_CONFIG
    ]
    return VL53L0XArray(i2c, definitions, vl53l0x_factory)


def start():
    sensors = build_sensors()
    controller = Controller(
        build_drivebase(),
        make_strategy(robot_config.ALGORITHM, robot_config),
        turn_90_ms=robot_config.TURN_90_MS,
        step_ms=robot_config.STEP_MS,
        wall_mm=robot_config.WALL_MM,
    )
    run(sensors, controller)  # loop de runner.py; para os motores em qualquer erro
