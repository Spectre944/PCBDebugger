import sys

from PySide6.QtCore import QCoreApplication

from serial_simulator import SerialSimulator


app = QCoreApplication(sys.argv)

simulator = SerialSimulator(
    usb_port_name="COM30",
    bluetooth_port_name="COM31",
)

simulator.data_sent.connect(
    lambda port, data: print(
        f"[TX {port.upper()}] {data.decode(errors='replace')}"
    )
)

simulator.command_received.connect(
    lambda port, data: print(
        f"[RX {port.upper()}] {data.decode(errors='replace')}"
    )
)

simulator.error_occurred.connect(
    lambda port, error: print(
        f"[ERROR {port.upper()}] {error}"
    )
)

simulator.start()

sys.exit(app.exec())