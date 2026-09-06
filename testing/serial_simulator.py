from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtSerialPort import QSerialPort


READY_INTERVAL_MS = 500

USB_READY = b"$RS TXD READY1*"
BLUETOOTH_READY = b"$RS TXD READY2*"

USB_RX_TEST = b"$RS RXD TEST1*"
BLUETOOTH_RX_TEST = b"$RS RXD TEST2*"

ALL_OUT_NET_PREFIX = "$ALL OUT NET*"
ALL_TEST_OUT = "$ALL TEST OUT*"
PIN_PREFIX = "$PIN "


@dataclass
class SimulatedPin:
    """State of a simulated GPIO pin."""

    number: int
    value: int = 0
    forced_value: int | None = None

    @property
    def actual_value(self) -> int:
        """Return the value visible to the tested processor."""

        if self.forced_value is not None:
            return self.forced_value

        return self.value


class SerialSimulator(QObject):
    """
    Simulate the test board connected through USB and Bluetooth interfaces.

    The simulator understands the commands used by the PCB diagnostic
    algorithm and generates corresponding responses.
    """

    data_sent = Signal(str, bytes)
    command_received = Signal(str, bytes)
    error_occurred = Signal(str, str)

    def __init__(
        self,
        usb_port_name: str,
        bluetooth_port_name: str,
        parent=None,
    ):
        super().__init__(parent)

        self._ports: dict[str, QSerialPort] = {}
        self._buffers: dict[str, bytearray] = {}

        self._pins: dict[int, SimulatedPin] = {}

        self._usb_port_key = "usb"
        self._bluetooth_port_key = "bluetooth"

        self._ready_timer = QTimer(self)
        self._ready_timer.timeout.connect(self._send_ready_messages)

        self._create_default_pins()

        self._open_port(
            self._usb_port_key,
            usb_port_name,
        )

        self._open_port(
            self._bluetooth_port_key,
            bluetooth_port_name,
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """Start periodic READY messages."""

        self._ready_timer.start(READY_INTERVAL_MS)

    def stop(self) -> None:
        """Stop the simulator."""

        self._ready_timer.stop()

        for port in self._ports.values():
            port.close()

    def stop_ready_msg(self):
        self._ready_timer.stop()

    def set_pin_value(self, pin_number: int, value: int) -> None:
        """Set the simulated output value of a pin."""

        pin = self._pins.get(pin_number)

        if pin is None:
            return

        pin.value = 1 if value else 0

    def set_pin_fault(
        self,
        pin_number: int,
        forced_value: int | None,
    ) -> None:
        """
        Force a pin to a specific value.

        Use ``None`` to remove the fault.

        Example:

            set_pin_fault(63, 0)

        This makes P63 always appear as 0.
        """

        pin = self._pins.get(pin_number)

        if pin is None:
            return

        pin.forced_value = forced_value

    def set_short(
        self,
        pin_a: int,
        pin_b: int,
    ) -> None:
        """
        Simulate a short between two pins.

        Currently this is represented by mirroring the value of pin_a
        to pin_b.
        """

        if pin_a not in self._pins or pin_b not in self._pins:
            return

        self._pins[pin_b].forced_value = self._pins[pin_a].value

    # -------------------------------------------------------------------------
    # Port handling
    # -------------------------------------------------------------------------

    def _open_port(
        self,
        port_key: str,
        port_name: str,
    ) -> None:
        """Open a serial port."""

        port = QSerialPort(self)

        port.setPortName(port_name)
        port.setBaudRate(9600)
        port.setDataBits(QSerialPort.DataBits.Data8)
        port.setParity(QSerialPort.Parity.NoParity)
        port.setStopBits(QSerialPort.StopBits.OneStop)

        if not port.open(QSerialPort.OpenModeFlag.ReadWrite):
            self.error_occurred.emit(
                port_key,
                port.errorString(),
            )
            port.deleteLater()
            return

        port.readyRead.connect(
            lambda key=port_key: self._on_ready_read(key)
        )

        port.errorOccurred.connect(
            lambda error, key=port_key: self._on_port_error(
                key,
                error,
            )
        )

        self._ports[port_key] = port
        self._buffers[port_key] = bytearray()

    def _on_ready_read(self, port_key: str) -> None:
        """Read incoming serial data."""

        port = self._ports.get(port_key)

        if port is None:
            return

        self._buffers[port_key].extend(
            bytes(port.readAll())
        )

        self._process_buffer(port_key)

    def _process_buffer(self, port_key: str) -> None:
        """Extract complete commands from the receive buffer."""

        buffer = self._buffers[port_key]

        while b"*" in buffer:
            end_index = buffer.index(b"*")

            command = bytes(
                buffer[: end_index + 1]
            )

            del buffer[: end_index + 1]

            self.command_received.emit(
                port_key,
                command,
            )

            self._handle_command(
                port_key,
                command,
            )

    def _on_port_error(
        self,
        port_key: str,
        error: QSerialPort.SerialPortError,
    ) -> None:
        """Handle serial port errors."""

        if error == QSerialPort.SerialPortError.NoError:
            return

        port = self._ports.get(port_key)

        message = (
            port.errorString()
            if port is not None
            else str(error)
        )

        self.error_occurred.emit(
            port_key,
            message,
        )

    # -------------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------------

    def _handle_command(
        self,
        port_key: str,
        command: bytes,
    ) -> None:
        """Handle a command received from the test application."""

        command_text = command.decode(
            "ascii",
            errors="ignore",
        ).strip()

        if command == USB_RX_TEST:
            self._send(
                port_key,
                b"$RS RXD READY1*",
            )
            return

        if command == BLUETOOTH_RX_TEST:
            self._send(
                port_key,
                b"$RS RXD READY2*",
            )
            return

        if command_text.startswith(ALL_OUT_NET_PREFIX):
            self._handle_all_out_net(
                command_text,
            )
            self.stop_ready_msg()
            return

        if command_text == ALL_TEST_OUT:
            self._send_port_state(
                port_key,
            )
            self.stop_ready_msg()
            return

        if command_text.startswith(PIN_PREFIX):
            self._handle_pin_command(
                command_text,
            )
            self.stop_ready_msg()
            return

    def _handle_all_out_net(
        self,
        command: str,
    ) -> None:
        """Set all simulated output pins to 0 or 1."""

        value_text = command[
            len(ALL_OUT_NET_PREFIX):
        ].rstrip("*").strip()

        if value_text not in {"0", "1"}:
            return

        value = int(value_text)

        for pin in self._pins.values():
            pin.value = value

    def _handle_pin_command(
        self,
        command: str,
    ) -> None:
        """Set one simulated pin."""

        command = command.rstrip("*")

        parts = command.split()

        if len(parts) != 3:
            return

        _, pin_name, value_text = parts

        if not pin_name.startswith("P"):
            return

        try:
            pin_number = int(pin_name[1:])
            value = int(value_text)
        except ValueError:
            return

        if value not in {0, 1}:
            return

        self.set_pin_value(
            pin_number,
            value,
        )

    # -------------------------------------------------------------------------
    # Responses
    # -------------------------------------------------------------------------

    def _send_ready_messages(self) -> None:
        """Send periodic interface READY messages."""

        self._send(
            self._usb_port_key,
            USB_READY,
        )

        self._send(
            self._bluetooth_port_key,
            BLUETOOTH_READY,
        )

    def _send_port_state(
        self,
        port_key: str,
    ) -> None:
        """Send the current state of all simulated pins."""

        values = ",".join(
            f"P{pin.number}={pin.actual_value}"
            for pin in self._pins.values()
        )

        message = f"$PORT {values}*"

        self._send(
            port_key,
            message.encode("ascii"),
        )

    def _send(
        self,
        port_key: str,
        data: bytes,
    ) -> None:
        """Send data through a serial port."""

        port = self._ports.get(port_key)

        if port is None or not port.isOpen():
            return

        port.write(data)

        self.data_sent.emit(
            port_key,
            data,
        )

    # -------------------------------------------------------------------------
    # Pins
    # -------------------------------------------------------------------------

    def _create_default_pins(self) -> None:
        """Create pins used by the output test."""

        pin_numbers = (
            # Розділ 6 (виводи індикації/керування)
            63,
            64,
            67,
            77,
            78,
            79,
            80,
            81,
            82,
            87,
            88,
            89,
            90,
            91,
            92,
            93,
            133,
            135,
            136,
            # Розділ 7 (лінії входу) — БУЛИ ВІДСУТНІ: без них симулятор ніколи
            # не згадує ці піни у відповіді $PORT ...*, тож будь-яка перевірка
            # (port_check/pin_sweep), що торкається розділу 7, провалювалась
            # на КОЖНІЙ ітерації незалежно від логіки застосунку — не тому,
            # що щось зламано в коді, а тому що симулятор просто "не знає"
            # про ці піни.
            49,
            53,
            76,
            110,
            125,
            126,
            127,
        )

        for pin_number in pin_numbers:
            self._pins[pin_number] = SimulatedPin(
                number=pin_number,
            )