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

# Строковые значения (из UI / settings.json) -> enum-ы QSerialPort.
# Ключи в нижнем регистре, сравнение регистронезависимое.
DATA_BITS_MAP = {
    "5": QSerialPort.DataBits.Data5,
    "6": QSerialPort.DataBits.Data6,
    "7": QSerialPort.DataBits.Data7,
    "8": QSerialPort.DataBits.Data8,
}

PARITY_MAP = {
    "none": QSerialPort.Parity.NoParity,
    "even": QSerialPort.Parity.EvenParity,
    "odd": QSerialPort.Parity.OddParity,
    "mark": QSerialPort.Parity.MarkParity,
    "space": QSerialPort.Parity.SpaceParity,
}

STOP_BITS_MAP = {
    "1": QSerialPort.StopBits.OneStop,
    "1.5": QSerialPort.StopBits.OneAndHalfStop,
    "2": QSerialPort.StopBits.TwoStop,
}

# У Qt нет режима DSR/DTR, поддерживаются только эти три
FLOW_CONTROL_MAP = {
    "none": QSerialPort.FlowControl.NoFlowControl,
    "rts/cts": QSerialPort.FlowControl.HardwareControl,
    "xon/xoff": QSerialPort.FlowControl.SoftwareControl,
}

# Ошибки, после которых порт считается потерянным (отключили USB, питание
# платы, порт захватила другая программа) и нужно переподключаться.
FATAL_PORT_ERRORS = {
    QSerialPort.SerialPortError.ResourceError,
    QSerialPort.SerialPortError.DeviceNotFoundError,
    QSerialPort.SerialPortError.PermissionError,
    QSerialPort.SerialPortError.ReadError,
    QSerialPort.SerialPortError.WriteError,
}


def _parse_option(value, enum_type, mapping: dict, label: str):
    """Принимает enum или строку/число и возвращает enum."""

    if isinstance(value, enum_type):
        return value

    try:
        return mapping[str(value).strip().lower()]
    except KeyError:
        raise ValueError(f"Непідтримуване значення {label}: {value!r}") from None


def parse_data_bits(value) -> QSerialPort.DataBits:
    return _parse_option(value, QSerialPort.DataBits, DATA_BITS_MAP, "data bits")


def parse_parity(value) -> QSerialPort.Parity:
    return _parse_option(value, QSerialPort.Parity, PARITY_MAP, "parity")


def parse_stop_bits(value) -> QSerialPort.StopBits:
    return _parse_option(value, QSerialPort.StopBits, STOP_BITS_MAP, "stop bits")


def parse_flow_control(value) -> QSerialPort.FlowControl:
    return _parse_option(value, QSerialPort.FlowControl, FLOW_CONTROL_MAP, "flow control")


@dataclass
class PortConfig:
    """Parameters used to (re)open a serial port."""

    com_name: str
    baud_rate: int = 9600
    data_bits: QSerialPort.DataBits = QSerialPort.DataBits.Data8
    parity: QSerialPort.Parity = QSerialPort.Parity.NoParity
    stop_bits: QSerialPort.StopBits = QSerialPort.StopBits.OneStop
    flow_control: QSerialPort.FlowControl = QSerialPort.FlowControl.NoFlowControl


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

    RECONNECT_INTERVAL_MS = 2000

    response_received = Signal(str, bytes)
    request_failed = Signal(str, str)
    port_error = Signal(str, str)
    raw_data_received = Signal(str, bytes)
    port_connected = Signal(str)      # port_key
    port_disconnected = Signal(str)   # port_key
    port_reconnecting = Signal(str)   # port_key: waiting for the port to come back

    def __init__(self, parent=None):
        super().__init__(parent)

        self._ports: dict[str, QSerialPort] = {}
        self._buffers: dict[str, bytearray] = {}
        self._pending: dict[str, PendingRequest] = {}

        self._configs: dict[str, PortConfig] = {}
        self._wanted: set[str] = set()          # ports that must be kept open
        self._last_error: dict[str, str] = {}   # last reported error per port

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setInterval(self.RECONNECT_INTERVAL_MS)
        self._reconnect_timer.timeout.connect(self._on_reconnect_tick)

    # -------------------------------------------------------------------------
    # Ports
    # -------------------------------------------------------------------------

    def configure_port(
        self,
        port_key: str,
        com_name: str,
        baud_rate: int = 9600,
        data_bits: QSerialPort.DataBits | str | int = QSerialPort.DataBits.Data8,
        parity: QSerialPort.Parity | str = QSerialPort.Parity.NoParity,
        stop_bits: QSerialPort.StopBits | str = QSerialPort.StopBits.OneStop,
        flow_control: QSerialPort.FlowControl | str = QSerialPort.FlowControl.NoFlowControl,
    ) -> None:
        """
        Store port parameters without opening the port.

        Enum values and plain strings (``"Even"``, ``"1.5"``, ``"RTS/CTS"``)
        are both accepted. New parameters are applied on the next (re)open.

        Raises:
            ValueError: if a parameter has an unsupported value.
        """

        self._configs[port_key] = PortConfig(
            com_name=com_name,
            baud_rate=int(baud_rate),
            data_bits=parse_data_bits(data_bits),
            parity=parse_parity(parity),
            stop_bits=parse_stop_bits(stop_bits),
            flow_control=parse_flow_control(flow_control),
        )

    def connect_port(self, port_key: str) -> bool:
        """
        Open a configured port and keep it connected.

        If the port cannot be opened right now (busy, device missing), the
        manager keeps retrying every RECONNECT_INTERVAL_MS until it succeeds
        or ``disconnect_port`` is called. The same happens if an open port
        is lost later (cable pulled, board powered off).

        Returns:
            True if the port is open right now.
        """

        if port_key not in self._configs:
            self.request_failed.emit(port_key, "port_not_configured")
            return False

        self._wanted.add(port_key)
        self._last_error.pop(port_key, None)

        if self.is_connected(port_key):
            return True

        if self._try_open(port_key):
            return True

        self.port_reconnecting.emit(port_key)
        self._ensure_reconnect_timer()
        return False

    def disconnect_port(self, port_key: str) -> None:
        """Close the port and stop any automatic reconnection."""

        self._wanted.discard(port_key)
        self._last_error.pop(port_key, None)

        self._close_port(port_key)
        self._stop_reconnect_timer_if_idle()

        self.port_disconnected.emit(port_key)

    def add_port(
        self,
        port_key: str,
        com_name: str,
        baud_rate: int = 9600,
        data_bits: QSerialPort.DataBits | str | int = QSerialPort.DataBits.Data8,
        parity: QSerialPort.Parity | str = QSerialPort.Parity.NoParity,
        stop_bits: QSerialPort.StopBits | str = QSerialPort.StopBits.OneStop,
        flow_control: QSerialPort.FlowControl | str = QSerialPort.FlowControl.NoFlowControl,
    ) -> bool:
        """
        Configure and open a serial port (with automatic reconnection).

        If a port with the same key already exists, it is replaced.

        Returns:
            True if the port was opened right away.
        """

        self._close_port(port_key)

        self.configure_port(
            port_key,
            com_name,
            baud_rate=baud_rate,
            data_bits=data_bits,
            parity=parity,
            stop_bits=stop_bits,
            flow_control=flow_control,
        )

        return self.connect_port(port_key)

    def remove_port(self, port_key: str) -> None:
        """Close the port and forget its configuration."""

        self.disconnect_port(port_key)
        self._configs.pop(port_key, None)

    def is_connected(self, port_key: str) -> bool:
        """Return True if the specified port is open."""

        port = self._ports.get(port_key)

        return port is not None and port.isOpen()

    # -------------------------------------------------------------------------
    # Ports: opening, losing, reconnecting
    # -------------------------------------------------------------------------

    def _try_open(self, port_key: str) -> bool:
        """Single attempt to open a port with its stored configuration."""

        config = self._configs[port_key]

        port = QSerialPort(self)
        port.setPortName(config.com_name)
        port.setBaudRate(config.baud_rate)
        port.setDataBits(config.data_bits)
        port.setParity(config.parity)
        port.setStopBits(config.stop_bits)
        port.setFlowControl(config.flow_control)

        if not port.open(QSerialPort.OpenModeFlag.ReadWrite):
            message = port.errorString()
            port.deleteLater()
            self._report_failure(port_key, message)
            return False

        port.readyRead.connect(
            lambda key=port_key: self._on_ready_read(key)
        )
        port.errorOccurred.connect(
            lambda error, key=port_key, p=port: self._on_port_error(key, p, error)
        )

        self._ports[port_key] = port
        self._buffers[port_key] = bytearray()
        self._last_error.pop(port_key, None)

        self.port_connected.emit(port_key)
        return True

    def _close_port(self, port_key: str) -> None:
        """Close and delete the port object, cancel its pending request."""

        self._cancel_pending(port_key)

        port = self._ports.pop(port_key, None)

        if port is not None:
            port.blockSignals(True)
            port.close()
            port.deleteLater()

        self._buffers.pop(port_key, None)

    def _handle_port_lost(
        self,
        port_key: str,
        port: QSerialPort,
        message: str,
    ) -> None:
        """An open port failed: clean up and start reconnecting."""

        # Ошибки могут прийти несколько раз подряд, обрабатываем только первую
        if self._ports.get(port_key) is not port:
            return

        had_pending = port_key in self._pending

        self._close_port(port_key)
        self._report_failure(port_key, message)

        if had_pending:
            self.request_failed.emit(port_key, "port_error")

        self.port_disconnected.emit(port_key)

        if port_key in self._wanted:
            self.port_reconnecting.emit(port_key)
            self._ensure_reconnect_timer()

    def _report_failure(self, port_key: str, message: str) -> None:
        """Emit port_error once per failure streak (no spam while retrying)."""

        if self._last_error.get(port_key) == message:
            return

        self._last_error[port_key] = message
        self.port_error.emit(port_key, message)

    def _on_reconnect_tick(self) -> None:
        """Try to reopen every wanted port that is not open."""

        for port_key in list(self._wanted):
            if port_key in self._configs and not self.is_connected(port_key):
                self._try_open(port_key)

        self._stop_reconnect_timer_if_idle()

    def _ensure_reconnect_timer(self) -> None:
        if not self._reconnect_timer.isActive():
            self._reconnect_timer.start()

    def _stop_reconnect_timer_if_idle(self) -> None:
        if all(self.is_connected(key) for key in self._wanted):
            self._reconnect_timer.stop()

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
        port: QSerialPort,
        error: QSerialPort.SerialPortError,
    ) -> None:
        """Handle a serial port error reported by Qt."""

        if error not in FATAL_PORT_ERRORS:
            return

        message = port.errorString()

        # Откладываем: нельзя закрывать и удалять порт прямо из его же сигнала
        QTimer.singleShot(
            0,
            lambda: self._handle_port_lost(port_key, port, message),
        )

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