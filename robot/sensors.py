"""Leitura de um conjunto de sensores VL53L0X no mesmo barramento I2C."""

try:
    from utime import sleep_ms
except ImportError:  # Permite testar a sequencia no Python do computador.
    from time import sleep

    def sleep_ms(milliseconds):
        sleep(milliseconds / 1000.0)


DEFAULT_I2C_ADDRESS = 0x29


class SensorInitializationError(Exception):
    """Erro ao habilitar ou configurar os sensores."""


class SensorReadError(Exception):
    """Erro ao obter uma distancia valida."""


def _create_driver(i2c, address):
    """Cria o driver instalado na placa."""
    from vl53l0x import VL53L0X

    return VL53L0X(i2c, address)


def create_sensor_array():
    """Inicializa I2C e GPIOs XSHUT conforme as definicoes de ``pinout``."""
    from machine import I2C, Pin
    from pinout import (
        I2C_FREQUENCY_HZ,
        I2C_SCL_GPIO,
        I2C_SDA_GPIO,
        SENSOR_CONFIG,
    )

    definitions = []
    for name, gpio, address in SENSOR_CONFIG:
        xshut = Pin(gpio, Pin.OUT)
        xshut.value(0)
        definitions.append(
            {"name": name, "xshut": xshut, "address": address}
        )

    i2c = I2C(
        scl=Pin(I2C_SCL_GPIO),
        sda=Pin(I2C_SDA_GPIO),
        freq=I2C_FREQUENCY_HZ,
    )
    return VL53L0XArray(i2c, definitions, _create_driver)


class VL53L0XArray:
    """Controla sensores VL53L0X com pinos XSHUT individuais.

    Cada definicao contem ``name``, ``xshut`` (objeto Pin) e ``address``.
    ``driver_factory(i2c, address)`` deve construir uma instancia do driver.
    O driver deve oferecer ``set_address(address)`` ou
    ``change_address(address)`` e ``read()`` ou
    ``read_range_single_millimeters()``. O metodo ``start()`` e opcional.
    """

    def __init__(self, i2c, definitions, driver_factory):
        self.i2c = i2c
        self.definitions = tuple(definitions)
        self.driver_factory = driver_factory
        self._sensors = {}
        self.last_errors = {}
        self._initialized = False
        self._validate_definitions()

    def _validate_definitions(self):
        names = set()
        addresses = set()

        for definition in self.definitions:
            name = definition["name"]
            address = definition["address"]
            if name in names:
                raise ValueError("Nome de sensor duplicado: %s" % name)
            if address in addresses:
                raise ValueError("Endereco I2C duplicado: 0x%02x" % address)
            if address == DEFAULT_I2C_ADDRESS:
                raise ValueError(
                    "O endereco 0x29 esta reservado para a inicializacao"
                )
            if address < 0x08 or address > 0x77:
                raise ValueError("Endereco I2C invalido: 0x%02x" % address)
            if "xshut" not in definition:
                raise ValueError("Falta pino XSHUT para %s" % name)

            names.add(name)
            addresses.add(address)

    @staticmethod
    def _write_pin(pin, value):
        pin.value(value)

    @staticmethod
    def _change_address(sensor, address):
        if hasattr(sensor, "set_address"):
            sensor.set_address(address)
        elif hasattr(sensor, "change_address"):
            sensor.change_address(address)
        else:
            raise SensorInitializationError(
                "O driver precisa implementar set_address() "
                "ou change_address()"
            )

    @staticmethod
    def _read_distance(sensor):
        if hasattr(sensor, "read"):
            return sensor.read()
        if hasattr(sensor, "read_range_single_millimeters"):
            return sensor.read_range_single_millimeters()
        raise SensorReadError(
            "O driver precisa implementar read() ou "
            "read_range_single_millimeters()"
        )

    def _verify_address(self, address):
        if address not in self.i2c.scan():
            raise SensorInitializationError(
                "Sensor nao encontrado no endereco 0x%02x" % address
            )

    def initialize(self):
        """Reinicia os sensores, atribuindo um endereco a cada um."""
        self.shutdown()
        sleep_ms(10)

        try:
            for definition in self.definitions:
                self._write_pin(definition["xshut"], 1)
                sleep_ms(10)

                sensor = self.driver_factory(self.i2c, DEFAULT_I2C_ADDRESS)
                self._change_address(sensor, definition["address"])
                self._verify_address(definition["address"])
                if hasattr(sensor, "start"):
                    sensor.start()
                self._sensors[definition["name"]] = sensor

            self._initialized = True
        except Exception as error:
            try:
                self.shutdown()
            except Exception as shutdown_error:
                raise SensorInitializationError(
                    "Falha ao inicializar os VL53L0X: %s; "
                    "falha ao desliga-los: %s" % (error, shutdown_error)
                )
            raise SensorInitializationError(
                "Falha ao inicializar os VL53L0X: %s" % error
            )

    def _read_one_strict(self, name):
        """Le uma distancia e levanta ``SensorReadError`` em caso de falha."""
        if not self._initialized:
            raise SensorReadError("Os sensores ainda nao foram inicializados")
        if name not in self._sensors:
            raise SensorReadError("Sensor desconhecido: %s" % name)

        try:
            distance = int(self._read_distance(self._sensors[name]))
        except Exception as error:
            raise SensorReadError("Falha ao ler %s: %s" % (name, error))

        if distance <= 0:
            raise SensorReadError(
                "Leitura invalida de %s: %d mm" % (name, distance)
            )
        return distance

    def read_one(self, name, default=None):
        """Le um sensor sem propagar falhas de comunicacao.

        Retorna ``default`` quando a leitura falha e guarda a mensagem em
        ``last_errors[name]``. Uma leitura valida apaga o erro anterior.
        """
        try:
            distance = self._read_one_strict(name)
            self.last_errors.pop(name, None)
            return distance
        except SensorReadError as error:
            self.last_errors[name] = str(error)
            return default

    def read_front(self, default=None):
        """Retorna a distancia frontal em milimetros."""
        return self.read_one("front", default)

    def read_left(self, default=None):
        """Retorna a distancia esquerda em milimetros."""
        return self.read_one("left", default)

    def read_right(self, default=None):
        """Retorna a distancia direita em milimetros."""
        return self.read_one("right", default)

    def get_sensor(self, name):
        """Retorna a instancia do driver associada a ``name``, se ativa."""
        return self._sensors.get(name)

    def read_all(self):
        """Retorna ``nome -> distancia``; falhas isoladas aparecem como None."""
        readings = {}
        for definition in self.definitions:
            name = definition["name"]
            readings[name] = self.read_one(name)
        return readings

    def shutdown(self):
        """Mantem todos os sensores desligados por meio de XSHUT."""
        first_error = None
        for definition in self.definitions:
            try:
                self._write_pin(definition["xshut"], 0)
            except Exception as error:
                if first_error is None:
                    first_error = error

        self._sensors = {}
        self.last_errors = {}
        self._initialized = False
        if first_error is not None:
            raise SensorInitializationError(
                "Nao foi possivel colocar todos os XSHUT em nivel baixo: %s"
                % first_error
            )
