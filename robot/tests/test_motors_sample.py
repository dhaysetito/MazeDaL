from machine import Pin, PWM
import time

# ==========================
# CONFIGURACOES
# ==========================

PWM_ESQUERDO = 40   # 0 a 100%
PWM_DIREITO = 40    # 0 a 100%

TEMPO_MS = 3000     # 3 segundos

# ==========================
# PINAGEM L298N
# ==========================

ENA = PWM(Pin(25), freq=1000)
ENB = PWM(Pin(27), freq=1000)

IN1 = Pin(18, Pin.OUT)
IN2 = Pin(19, Pin.OUT)

IN3 = Pin(23, Pin.OUT)
IN4 = Pin(14, Pin.OUT)

# ==========================
# MOTORES PARA FRENTE
# ==========================

IN1.value(1)
IN2.value(0)

IN3.value(1)
IN4.value(0)

# Aplica os valores de PWM
ENA.duty_u16(int(PWM_ESQUERDO * 65535 / 100))
ENB.duty_u16(int(PWM_DIREITO * 65535 / 100))

print("Motores girando...")
print("Esquerdo:", PWM_ESQUERDO, "%")
print("Direito:", PWM_DIREITO, "%")

# ==========================
# TEMPO DE MOVIMENTO
# ==========================

try:
    time.sleep_ms(TEMPO_MS)

finally:
    # Desliga os motores
    ENA.duty_u16(0)
    ENB.duty_u16(0)

    IN1.value(0)
    IN2.value(0)
    IN3.value(0)
    IN4.value(0)

    ENA.deinit()
    ENB.deinit()

    print("Motores parados")
