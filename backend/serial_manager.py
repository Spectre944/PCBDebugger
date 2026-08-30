from PySide6.QtCore import QObject, Signal, QTimer, QByteArray
from PySide6.QtSerialPort import QSerialPort


# Максимальний розмір буфера на порт. _try_match "з'їдає" буфер лише тоді,
# коли на порту є активне очікування (wait_signal/send_and_wait) — якщо
# плата шле щось періодично, а зараз саме немає жодного активного кроку,
# який це чекає, буфер ніколи не тримується і росте необмежено весь час
# роботи програми. Достатньо тримати "хвіст" останніх кількох кілобайт —
# для рамки "$...*" цього з великим запасом вистачає.
MAX_BUFFER_SIZE = 8192


class SerialManager(QObject):
    """
    Управляет несколькими COM-портами (например, RS485 и Bluetooth).
    Поддерживает два режима работы с командами:
    - wait_signal:   ничего не отправляем, просто ждём, что плата сама
                        пришлёт ожидаемые данные (например периодические пакеты).
    - send_and_wait: отправляем команду, потом ждём ответ и сравниваем.   

    Реальное сравнение/парсинг ответа передаётся снаружи через match_fn,
    чтобы формат send/expect в scenario.json можно было менять как угодно
    без переделки этого класса.
    """

    responseReceived = Signal(str, bytes)   # port_key, matched_data
    requestFailed = Signal(str, str)        # port_key, reason ('timeout' / 'port_error' / ...)
    portError = Signal(str, str)            # port_key, error_string
    rawDataReceived = Signal(str, bytes)    # port_key, raw_bytes — для лога/отладки

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ports: dict[str, QSerialPort] = {}
        self._buffers: dict[str, bytearray] = {}
        self._pending: dict[str, dict] = {}  # port_key -> {match_fn, timer, mode}

    # ---------- Подключение портов ----------

    def add_port(self, port_key: str, com_name: str, baud_rate: int = 9600,
                    data_bits=QSerialPort.DataBits.Data8,
                    parity=QSerialPort.Parity.NoParity,
                    stop_bits=QSerialPort.StopBits.OneStop) -> bool:
        """port_key — произвольное имя, например 'rs485' или 'bluetooth'."""
        if port_key in self._ports:
            self.remove_port(port_key)

        port = QSerialPort(self)
        port.setPortName(com_name)
        port.setBaudRate(baud_rate)
        port.setDataBits(data_bits)
        port.setParity(parity)
        port.setStopBits(stop_bits)

        if not port.open(QSerialPort.OpenModeFlag.ReadWrite):
            self.portError.emit(port_key, port.errorString())
            return False

        port.readyRead.connect(lambda pk=port_key: self._on_ready_read(pk))
        port.errorOccurred.connect(
            lambda err, pk=port_key: self._on_port_error(pk, err)
        )

        self._ports[port_key] = port
        self._buffers[port_key] = bytearray()
        return True

    def remove_port(self, port_key: str):
        port = self._ports.pop(port_key, None)
        if port is not None:
            port.close()
            port.deleteLater()
        self._buffers.pop(port_key, None)
        self._cancel_pending(port_key)

    def is_connected(self, port_key: str) -> bool:
        port = self._ports.get(port_key)
        return port is not None and port.isOpen()

    # ---------- Команды ----------

    def send_and_wait(self, port_key: str, data: bytes, match_fn, timeout_ms: int = 2000):
        """
        Отправляет data в порт port_key, затем ждёт ответ.
        match_fn(buffer: bytes) -> bytes | None
            Должна вернуть "съеденную" часть буфера, если ответ распознан
            (совпал), либо None, если ответа ещё недостаточно.
            Сравнение (что считать pass/fail) — забота вызывающего кода:
            эта функция говорит только "распознан пакет или нет".
        """
        port = self._ports.get(port_key)
        if port is None or not port.isOpen():
            self.requestFailed.emit(port_key, "port_not_connected")
            return

        if port_key in self._pending:
            self.requestFailed.emit(port_key, "busy")
            return

        self._start_waiting(port_key, match_fn, timeout_ms)
        port.write(QByteArray(data))
        port.flush()

    def wait_signal(self, port_key: str, match_fn, timeout_ms: int = 2000):
        """
        Ничего не отправляет — просто ждёт, пока в буфере не появится
        пакет, распознанный match_fn (например периодическая посылка от платы).
        """
        port = self._ports.get(port_key)
        if port is None or not port.isOpen():
            self.requestFailed.emit(port_key, "port_not_connected")
            return

        if port_key in self._pending:
            self.requestFailed.emit(port_key, "busy")
            return

        self._start_waiting(port_key, match_fn, timeout_ms)

    def cancel(self, port_key: str):
        """Отменить текущее ожидание на порту (например, при stop() раннера)."""
        self._cancel_pending(port_key)


    # ---------- Внутреннее ----------

    def _start_waiting(self, port_key: str, match_fn, timeout_ms: int):
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda pk=port_key: self._on_timeout(pk))

        self._pending[port_key] = {"match_fn": match_fn, "timer": timer}
        timer.start(timeout_ms)

        # буфер мог накопить данные ДО вызова wait_signal/send_and_wait —
        # сразу проверим, вдруг ответ уже пришёл
        self._try_match(port_key)

    def _cancel_pending(self, port_key: str):
        pending = self._pending.pop(port_key, None)
        if pending is not None:
            pending["timer"].stop()
            pending["timer"].deleteLater()

    def _on_timeout(self, port_key: str):
        self._pending.pop(port_key, None)
        self.requestFailed.emit(port_key, "timeout")

    def _on_port_error(self, port_key: str, error):
        if error == QSerialPort.SerialPortError.NoError:
            return
        port = self._ports.get(port_key)
        message = port.errorString() if port else str(error)
        self.portError.emit(port_key, message)
        self._cancel_pending(port_key)

    def _on_ready_read(self, port_key: str):
        port = self._ports.get(port_key)
        if port is None:
            return

        chunk = bytes(port.readAll())
        buffer = self._buffers[port_key]
        buffer.extend(chunk)
        if len(buffer) > MAX_BUFFER_SIZE:
            del buffer[: len(buffer) - MAX_BUFFER_SIZE]
        self.rawDataReceived.emit(port_key, chunk)

        self._try_match(port_key)

    def _try_match(self, port_key: str):
        pending = self._pending.get(port_key)
        if pending is None:
            return

        buffer = bytes(self._buffers[port_key])
        matched = pending["match_fn"](buffer)
        if matched is None:
            return

        # "съедаем" распознанный кусок из буфера
        consumed_len = len(matched)
        self._buffers[port_key] = self._buffers[port_key][consumed_len:]

        self._cancel_pending(port_key)
        self.responseReceived.emit(port_key, matched)