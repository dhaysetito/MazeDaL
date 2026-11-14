"""Receptor MazeDaL BLE para Windows: executar com Python 3 + bleak."""
import asyncio
import msvcrt  # Teclado do Windows, sem bloquear a recepcao.
from bleak import BleakScanner, BleakClient

NOME = "MazeDaL"
TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

ESTADOS = {
    "AV": "AVANCANDO",
    "PA": "PARADO",
    "GD": "GIRANDO DIREITA",
    "GE": "GIRANDO ESQUERDA",
    "ERRO": "ERRO DE SENSOR - MOTORES PARADOS",
    "STOP": "PARADA REMOTA - MOTORES BLOQUEADOS",
}


# Campos recebidos em notificacoes BLE separadas.
telemetria = {}


def receber(sender, dados):
    mensagem = dados.decode("utf-8", errors="replace").strip()
    campos = mensagem.split(",")
    tipo = campos[0]

    try:
        if tipo == "D" and len(campos) == 4:
            telemetria["f"], telemetria["e"], telemetria["d"] = campos[1:]

        elif tipo == "K" and len(campos) == 5:
            telemetria["sensor"] = campos[1]
            telemetria["ref"] = campos[2]
            telemetria["erro"] = campos[3]
            telemetria["aj"] = campos[4]

        elif tipo == "M" and len(campos) == 3:
            telemetria["pwm_e"], telemetria["pwm_d"] = campos[1:]

        elif tipo == "S" and len(campos) == 2:
            estado = ESTADOS.get(campos[1], campos[1])
            if all(k in telemetria for k in
                   ("f", "e", "d", "sensor", "ref", "erro", "aj", "pwm_e", "pwm_d")):
                print(
                    "F:{:>4} | E:{:>4} | D:{:>4} | S:{} | "
                    "REF:{:>4} | ERRO:{:>4} | AJ:{:>4} | "
                    "PWM:{:>3}/{:>3} | {}".format(
                        telemetria["f"], telemetria["e"], telemetria["d"],
                        telemetria["sensor"], telemetria["ref"],
                        telemetria["erro"], telemetria["aj"],
                        telemetria["pwm_e"], telemetria["pwm_d"], estado
                    ), flush=True
                )
            else:
                # Estado avulso, sem ciclo completo de telemetria.
                print(">>> {}".format(estado), flush=True)
            telemetria.clear()

        elif tipo == "E" and len(campos) == 2:
            # Transicao de estado: nao espera os 200 ms da telemetria.
            print(">>> {}".format(ESTADOS.get(campos[1], campos[1])), flush=True)

        elif tipo == "F" and len(campos) == 2:
            print(">>> GIRO | Frente: {} mm".format(campos[1]), flush=True)

        elif tipo == "A":
            if len(campos) == 4 and campos[1] == "REF":
                lado = "direita" if campos[2] == "D" else "esquerda"
                print(">>> CALIBRADO | {}: {} mm (pressione R)".format(
                    lado, campos[3]), flush=True)
            elif len(campos) >= 2 and campos[1] == "CAL":
                print(">>> RECALIBRANDO | motores parados", flush=True)
            elif len(campos) >= 2 and campos[1] == "SEM_PAREDE":
                print(">>> CALIBRACAO | sem parede, referencia mantida", flush=True)
            elif len(campos) >= 2 and campos[1] == "ERRO_CAL":
                print(">>> CALIBRACAO | erro", flush=True)
            else:
                print(">>> {}".format(mensagem), flush=True)

        else:
            print(">>> RECEBIDO | {}".format(mensagem), flush=True)

    except Exception as erro:
        print("Erro ao processar telemetria:", erro, repr(mensagem), flush=True)


async def main():
    print("Procurando ESP32 MazeDaL...")
    dispositivo = await BleakScanner.find_device_by_name(NOME, timeout=15.0)
    if dispositivo is None:
        print("MazeDaL nao encontrado. Verifique o main.py no ESP32 e o Bluetooth do Windows.")
        return

    print("Dispositivo encontrado:", dispositivo.name)
    async with BleakClient(dispositivo) as cliente:
        print("BLE conectado. Pressione R para liberar o robo.")
        print("P = PARAR | R = RETOMAR | C = RECALIBRAR | I = REINICIAR")
        print("Ctrl+C = desconectar (robo para)")
        await cliente.start_notify(TX_UUID, receber)
        while cliente.is_connected:
            if msvcrt.kbhit():
                tecla = msvcrt.getwch().lower()
                if tecla in ("p", "r", "c", "i"):
                    comando = {"p": "STOP", "r": "RESUME",
                               "c": "CAL", "i": "RESTART"}[tecla]
                    try:
                        await cliente.write_gatt_char(
                            RX_UUID, comando.encode(), response=True
                        )
                        print(">>> COMANDO | {} enviado".format(comando), flush=True)
                        if tecla == "i":
                            print(">>> ESP32 reiniciando; execute o receptor novamente.", flush=True)
                    except Exception as erro:
                        print("Falha ao enviar comando:", erro)
            await asyncio.sleep(0.05)

    print("ESP32 desconectado.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Receptor encerrado pelo usuario.")
