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


LARGURA_TIPO = 10
LARGURA_DADO = 36
LARGURA_DADO2 = 20
LARGURA_DADO3 = 20

SEPARADOR = (
    "+" + "-" * (LARGURA_TIPO + 2)
    + "+" + "-" * (LARGURA_DADO + 2)
    + "+" + "-" * (LARGURA_DADO2 + 2)
    + "+" + "-" * (LARGURA_DADO3 + 2) + "+"
)


def linha(tipo="", dado1="", dado2="", dado3=""):
    print("| {:<10} | {:<36} | {:<20} | {:<20} |".format(
        str(tipo), str(dado1), str(dado2), str(dado3)
    ), flush=True)


def receber(sender, dados):
    mensagem = dados.decode("utf-8", errors="replace").strip()
    campos = mensagem.split(",")
    tipo = campos[0]

    try:
        if tipo == "D" and len(campos) == 4:
            print(SEPARADOR, flush=True)
            linha("DISTANCIAS", "Frente: {} mm".format(campos[1]),
                  "Esquerda: {} mm".format(campos[2]),
                  "Direita: {} mm".format(campos[3]))
        elif tipo == "K" and len(campos) == 5:
            lado = "direita" if campos[1] == "D" else "esquerda"
            linha("KP", "Sensor: {}".format(lado),
                  "Referencia: {} mm".format(campos[2]))
            linha("", "Erro: {} mm".format(campos[3]),
                  "Ajuste: {}".format(campos[4]))
        elif tipo == "M" and len(campos) == 3:
            linha("MOTORES", "Esquerdo: {}%".format(campos[1]),
                  "Direito: {}%".format(campos[2]))
        elif tipo == "S" and len(campos) == 2:
            linha("ESTADO", ESTADOS.get(campos[1], campos[1]))
            print(SEPARADOR + "\n", flush=True)
        elif tipo == "E" and len(campos) == 2:
            # Transicao de estado: imprime assim que a notificacao chega.
            linha("MUDANCA", ESTADOS.get(campos[1], campos[1]))
        elif tipo == "A":
            if len(campos) == 4 and campos[1] == "REF":
                lado = "direita" if campos[2] == "D" else "esquerda"
                print("*** NOVA REFERENCIA | {}: {} mm | pressione R para retomar".format(
                    lado, campos[3]), flush=True)
            elif len(campos) >= 2 and campos[1] == "CAL":
                print("*** RECALIBRANDO (motores parados)...", flush=True)
            elif len(campos) >= 2 and campos[1] == "SEM_PAREDE":
                print("*** SEM PAREDE | referencia anterior preservada", flush=True)
            elif len(campos) >= 2 and campos[1] == "ERRO_CAL":
                print("*** ERRO NA RECALIBRACAO", flush=True)
        elif tipo == "F" and len(campos) == 2:
            linha("GIRO", "Frente: {} mm".format(campos[1]))
        else:
            linha("RECEBIDO", mensagem)
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
                        print("COMANDO    | {} enviado".format(comando), flush=True)
                        if tecla == "i":
                            print("ESP32 vai reiniciar e desconectar. Execute este receptor novamente.", flush=True)
                    except Exception as erro:
                        print("Falha ao enviar comando:", erro)
            await asyncio.sleep(0.05)

    print("ESP32 desconectado.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Receptor encerrado pelo usuario.")
