"""Receptor MazeDaL BLE para Windows: executar com Python 3 + bleak."""
import asyncio
from bleak import BleakScanner, BleakClient

NOME = "MazeDaL"
TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

ESTADOS = {
    "AV": "AVANCANDO",
    "PA": "PARADO",
    "GD": "GIRANDO DIREITA",
    "GE": "GIRANDO ESQUERDA",
    "ERRO": "ERRO DE SENSOR - MOTORES PARADOS",
}


def receber(sender, dados):
    mensagem = dados.decode("utf-8", errors="replace").strip()
    campos = mensagem.split(",")
    tipo = campos[0]

    try:
        if tipo == "D" and len(campos) == 4:
            print("-" * 68)
            print("DISTANCIAS | Frente: {} mm | Esquerda: {} mm | Direita: {} mm".format(*campos[1:]))
        elif tipo == "K" and len(campos) == 5:
            lado = "direita" if campos[1] == "D" else "esquerda"
            print("KP         | Sensor: {} | Referencia: {} mm".format(lado, campos[2]))
            print("           | Erro: {} mm | Ajuste: {}".format(campos[3], campos[4]))
        elif tipo == "M" and len(campos) == 3:
            print("MOTORES    | Esquerdo: {}% | Direito: {}%".format(*campos[1:]))
        elif tipo == "S" and len(campos) == 2:
            print("ESTADO     |", ESTADOS.get(campos[1], campos[1]))
            print()  # Espaco entre os ciclos, sem apagar o historico.
        elif tipo == "F" and len(campos) == 2:
            print("GIRO       | Distancia frontal: {} mm".format(campos[1]))
        else:
            print("RECEBIDO   |", mensagem)
    except Exception as erro:
        print("Erro ao processar telemetria:", erro, repr(mensagem))


async def main():
    print("Procurando ESP32 MazeDaL...")
    dispositivo = await BleakScanner.find_device_by_name(NOME, timeout=15.0)
    if dispositivo is None:
        print("MazeDaL nao encontrado. Verifique o main.py no ESP32 e o Bluetooth do Windows.")
        return

    print("Dispositivo encontrado:", dispositivo.name)
    async with BleakClient(dispositivo) as cliente:
        print("BLE conectado. Recebendo telemetria (Ctrl+C para encerrar).")
        await cliente.start_notify(TX_UUID, receber)
        while cliente.is_connected:
            await asyncio.sleep(1)

    print("ESP32 desconectado.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Receptor encerrado pelo usuario.")
