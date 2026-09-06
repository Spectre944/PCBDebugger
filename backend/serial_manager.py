from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal, QByteArray
from PySide6.QtSerialPort import QSerialPort


MAX_BUFFER_SIZE = 8192


MatchFunction = Callable[[bytes], bytes | None]


@dataclass
class PendingRequest:
    """Information about an active response wait."""

    match_fn: MatchFunction
    timer: QTimer

class SerialManager(QObject):
    """
    Manage multiple serial ports.

    Supports three types of operations:

    - wait_signal:
        Wait for a packet sent by the device without sending anything.

    - send_and_wait:
        Send a command and wait for a matching response.

    - send_signal:
        Send a command without waiting for a response.

    Packet parsing is delegated to ``match_fn``. It receives the current
    buffer and must return the complete matched packet or ``None`` if
    the buffer does not contain a complete packet yet.
    """

    response_received = Signal(str, bytes)
    request_failed = Signal(str, str)
    port_error = Signal(str, str)
    raw_data_received = Signal(str, bytes)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._ports: dict[str, QSerialPort] = {}
        self._buffers: dict[str, bytearray] = {}
        self._pending: dict[str, PendingRequest] = {}

    # -------------------------------------------------------------------------
    # Ports
    # -------------------------------------------------------------------------

    def add_port(
        self,
        port_key: str,
        com_name: str,
        baud_rate: int = 9600,
        data_bits: QSerialPort.DataBits = QSerialPort.DataBits.Data8,
        parity: QSerialPort.Parity = QSerialPort.Parity.NoParity,
        stop_bits: QSerialPort.StopBits = QSerialPort.StopBits.OneStop,
    ) -> bool:
        """
        Add and open a serial port.

        If a port with the same key already exists, it is replaced.

        Args:
            port_key: Internal identifier of the port.
            com_name: System port name, for example ``COM3``.
            baud_rate: Communication speed.
            data_bits: Number of data bits.
            parity: Parity mode.
            stop_bits: Number of stop bits.

        Returns:
            True if the port was opened successfully.
        """

        if port_key in self._ports:
            self.remove_port(port_key)

        port = QSerialPort(self)
        port.setPortName(com_name)
        port.setBaudRate(baud_rate)
        port.setDataBits(data_bits)
        port.setParity(parity)
        port.setStopBits(stop_bits)

        if not port.open(QSerialPort.OpenModeFlag.ReadWrite):
            self.port_error.emit(port_key, port.errorString())
            port.deleteLater()
            return False

        port.readyRead.connect(
            lambda key=port_key: self._on_ready_read(key)
        )
        port.errorOccurred.connect(
            lambda error, key=port_key: self._on_port_error(key, error)
        )

        self._ports[port_key] = port
        self._buffers[port_key] = bytearray()

        return True

    def remove_port(self, port_key: str) -> None:
        """Close and remove a serial port."""

        self._cancel_pending(port_key)

        port = self._ports.pop(port_key, None)

        if port is not None:
            port.close()
            port.deleteLater()

        self._buffers.pop(port_key, None)

    def is_connected(self, port_key: str) -> bool:
        """Return True if the specified port is open."""

        port = self._ports.get(port_key)

        return port is not None and port.isOpen()

    # -------------------------------------------------------------------------
    # Communication
    # -------------------------------------------------------------------------

    def send_and_wait(
        self,
        port_key: str,
        data: bytes,
        match_fn: MatchFunction,
        timeout_ms: int = 2000,
    ) -> None:
        """
        Send data and wait for a matching response.

        ``match_fn`` receives the current receive buffer and must return
        the complete matched packet or ``None`` if more data is required.
        """

        port = self._get_available_port(port_key)

        if port is None:
            return

        if not self._start_waiting(port_key, match_fn, timeout_ms, discard_existing=True):
            return

        bytes_written = port.write(QByteArray(data))

        if bytes_written == -1:
            self._cancel_pending(port_key)
            self.request_failed.emit(port_key, "write_error")

    def send_signal(
        self,
        port_key: str,
        data: bytes,
    ) -> bool:
        """
        Send data without waiting for a response.

        Returns:
            True if the data was accepted by the serial port.
        """

        port = self._get_available_port(port_key)

        if port is None:
            return False

        if port_key in self._pending:
            self.request_failed.emit(port_key, "busy")
            return False

        return port.write(QByteArray(data)) != -1

    def wait_signal(
        self,
        port_key: str,
        match_fn: MatchFunction,
        timeout_ms: int = 2000,
    ) -> None:
        """
        Wait for a matching packet without sending anything.
        """

        if self._get_available_port(port_key) is None:
            return

        self._start_waiting(port_key, match_fn, timeout_ms)

    def cancel(self, port_key: str) -> None:
        """Cancel the active request on the specified port."""

        self._cancel_pending(port_key)

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _get_available_port(
        self,
        port_key: str,
    ) -> QSerialPort | None:
        """Return an open port or emit an appropriate error."""

        port = self._ports.get(port_key)

        if port is None or not port.isOpen():
            self.request_failed.emit(
                port_key,
                "port_not_connected",
            )
            return None

        return port

    def _start_waiting(
        self,
        port_key: str,
        match_fn: MatchFunction,
        timeout_ms: int,
        discard_existing: bool = False,
    ) -> bool:
        """Start waiting for a matching response."""

        if port_key in self._pending:
            self.request_failed.emit(port_key, "busy")
            return False

        if discard_existing:
            # ВАЖЛИВО: тут ми ще навіть НЕ відправили команду (виклик іде
            # ДО port.write у send_and_wait), тож плата фізично не могла
            # ще встигнути відповісти. Усе, що зараз лежить у буфері —
            # це або сміття, або застаріла відповідь на ПОПЕРЕДНІЙ запит,
            # яка чомусь не була спожита вчасно (запізнилась після
            # таймауту тощо). Без цього очищення _try_match() нижче міг би
            # миттєво "відповісти" цими старими байтами ще до того, як
            # прийде справжня відповідь на щойно відправлену команду —
            # саме тому повторний прогін кроку з іншими вхідними даними
            # міг показувати той самий старий результат.
            self._buffers[port_key].clear()

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(
            lambda key=port_key: self._on_timeout(key)
        )

        self._pending[port_key] = PendingRequest(
            match_fn=match_fn,
            timer=timer,
        )

        timer.start(timeout_ms)

        # Для wait_signal (discard_existing=False) це навмисно лишається:
        # тут ми НІЧОГО не надсилаємо, тож дані справді могли прийти
        # (несолісітовано) ще до того, як ми почали слухати.
        self._try_match(port_key)

        return True

    def _cancel_pending(self, port_key: str) -> None:
        """Cancel and remove an active request."""

        pending = self._pending.pop(port_key, None)

        if pending is None:
            return

        pending.timer.stop()
        pending.timer.deleteLater()

    def _on_timeout(self, port_key: str) -> None:
        """Handle a request timeout."""

        if port_key not in self._pending:
            return

        self._cancel_pending(port_key)

        # ВАЖЛИВО: якщо після таймауту реальна відповідь всі ж таки прийде
        # (плата просто забарилась), вона осяде в буфері і нікуди не
        # подінеться. Наступний, зовсім НЕ пов'язаний запит на цьому ж
        # порту одразу після старту робить "eager" перевірку буфера (див.
        # _start_waiting) — і без цього очищення він міг би миттєво
        # "з'їсти" застарілу відповідь замість того, щоб дочекатися
        # справжньої відповіді на СЕБЕ. Тому щойно ми визнали запит
        # провальним за таймаутом — все, що зараз у буфері, вже нерелевантне.
        self._buffers[port_key].clear()

        self.request_failed.emit(port_key, "timeout")

    def _on_port_error(
        self,
        port_key: str,
        error: QSerialPort.SerialPortError,
    ) -> None:
        """Handle a serial port error."""

        if error == QSerialPort.SerialPortError.NoError:
            return

        port = self._ports.get(port_key)
        message = port.errorString() if port else str(error)

        self.port_error.emit(port_key, message)

        if port_key in self._pending:
            self._cancel_pending(port_key)
            self.request_failed.emit(port_key, "port_error")

    def _on_ready_read(self, port_key: str) -> None:
        """Read incoming data and try to match the active request."""

        port = self._ports.get(port_key)

        if port is None:
            return

        chunk = bytes(port.readAll())

        if not chunk:
            return

        buffer = self._buffers[port_key]
        buffer.extend(chunk)

        self._trim_buffer(buffer)

        self.raw_data_received.emit(port_key, chunk)

        self._try_match(port_key)

    def _try_match(self, port_key: str) -> None:
        """Try to extract a complete response from the receive buffer."""

        pending = self._pending.get(port_key)

        if pending is None:
            return

        buffer = bytes(self._buffers[port_key])
        matched = pending.match_fn(buffer)

        if matched is None:
            return

        consumed_length = len(matched)

        del self._buffers[port_key][:consumed_length]

        self._cancel_pending(port_key)
        self.response_received.emit(port_key, matched)

    @staticmethod
    def _trim_buffer(buffer: bytearray) -> None:
        """Keep only the last MAX_BUFFER_SIZE bytes."""

        if len(buffer) <= MAX_BUFFER_SIZE:
            return

        del buffer[:-MAX_BUFFER_SIZE]