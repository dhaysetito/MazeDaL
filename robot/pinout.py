"""Pinagem NodeMCU ESP8266 para sensores VL53L0X e habilitacao do L298N."""

I2C_SCL_GPIO = 4  # D2
I2C_SDA_GPIO = 5  # D1
I2C_FREQUENCY_HZ = 100000

# (nome, GPIO XSHUT, endereco I2C)
SENSOR_CONFIG = (
    ("front", 14, 0x30),  # D5
    ("left", 13, 0x31),  # D7
    ("right", 16, 0x32),  # D0
)

# L298N: dois motores com habilitacao/velocidade compartilhada.
# Remova os jumpers ENA e ENB do modulo antes de liga-los ao GPIO12.
MOTOR_LEFT_IN1_GPIO = 0  # D3 -> IN1
MOTOR_LEFT_IN2_GPIO = 2  # D4 -> IN2
MOTOR_RIGHT_IN3_GPIO = 15  # D8 -> IN3
MOTOR_RIGHT_IN4_GPIO = 3  # RX -> IN4
MOTOR_ENABLE_GPIO = 12  # D6 -> ENA + ENB

# Pares de direcao consumidos por control.build_drivebase().
MOTOR_LEFT_GPIO = (
    MOTOR_LEFT_IN1_GPIO,
    MOTOR_LEFT_IN2_GPIO,
)
MOTOR_RIGHT_GPIO = (
    MOTOR_RIGHT_IN3_GPIO,
    MOTOR_RIGHT_IN4_GPIO,
)
