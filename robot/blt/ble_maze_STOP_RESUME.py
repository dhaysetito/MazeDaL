"""BLE do MazeDaL: telemetria TX e comandos STOP/RESUME RX."""
import bluetooth

NOME = "MazeDaL"
SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
RX_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
TX_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")


class MazeBLE:
    def __init__(self, on_stop=None):
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.conexoes = set()
        self.parado = True  # Bloqueado ate conexao e comando RESUME.
        self.on_stop = on_stop

        servico = (
            SERVICE_UUID,
            (
                (TX_UUID, bluetooth.FLAG_NOTIFY),
                (RX_UUID, bluetooth.FLAG_WRITE),
            ),
        )
        ((self.tx_handle, self.rx_handle),) = (
            self.ble.gatts_register_services((servico,))
        )
        self.ble.irq(self.evento)
        self.anunciar()

    def anunciar(self):
        nome = NOME.encode()
        payload = b"\x02\x01\x06" + bytes((len(nome) + 1, 0x09)) + nome
        self.ble.gap_advertise(100000, adv_data=payload)
        print("MazeDaL anunciando via BLE")

    def _bloquear(self):
        self.parado = True
        if self.on_stop is not None:
            # Desliga os motores sem esperar a proxima leitura de sensor.
            self.on_stop()

    def evento(self, evento, dados):
        if evento == 1:  # _IRQ_CENTRAL_CONNECT
            conexao, _, _ = dados
            self.conexoes.add(conexao)
            self._bloquear()
            print("BLE conectado: aguardando R")

        elif evento == 2:  # _IRQ_CENTRAL_DISCONNECT
            conexao, _, _ = dados
            self.conexoes.discard(conexao)
            self._bloquear()
            print("BLE desconectado: motores bloqueados")
            self.anunciar()

        elif evento == 3:  # _IRQ_GATTS_WRITE
            conexao, handle = dados
            if conexao not in self.conexoes or handle != self.rx_handle:
                return
            comando = self.ble.gatts_read(self.rx_handle).decode().strip().upper()
            if comando == "STOP":
                self._bloquear()
                print("Comando STOP recebido")
            elif comando == "RESUME":
                self.parado = False
                print("Comando RESUME recebido")
                self.enviar("S,PA")

    def enviar(self, mensagem):
        dados = mensagem.encode()
        for conexao in tuple(self.conexoes):
            self.ble.gatts_notify(conexao, self.tx_handle, dados)
