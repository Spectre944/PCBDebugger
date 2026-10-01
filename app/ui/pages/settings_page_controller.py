# app/ui/pages/settings_page_controller.py
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtCore import Signal, Qt

from app.ui.pages.settings_page import Ui_settingsPage


class PortSettingsWidget(QWidget, Ui_settingsPage):
    """
    Контроллер страницы настроек портов (Bluetooth / RS).
    
    Логика:
      - заполняет все QComboBox значениями по-умолчанию;
      - кнопки "..." раскрывают/скрывают дополнительные параметры
        (Baudrate, Stop Bit, Parity, Flow Control);
      - кнопки подключения переключают текст "Підключитись" / "Відключитись";
      - сигналы наружу о запросе подключения/отключения и смене параметров.
    """

    # (port_key, port_name, baudrate, stop_bit, parity, flow_control)
    port_connect_requested = Signal(str, str, int, str, str, str)
    port_disconnect_requested = Signal(str)

    # Ключи портов, которые обслуживает страница
    PORT_BT = "BT"
    PORT_RS = "RS"

    # Значения по-умолчанию для доп. параметров
    BAUDRATES = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
    STOP_BITS = ["1", "1.5", "2"]
    PARITIES = ["None", "Even", "Odd", "Mark", "Space"]
    FLOW_CONTROLS = ["None", "RTS/CTS", "XON/XOFF", "DSR/DTR"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # Храним состояние "подключён ли порт"
        self._connected = {
            self.PORT_BT: False,
            self.PORT_RS: False,
        }

        # Изначально доп. параметры скрыты
        self._extra_widgets = {
            self.PORT_BT: [
                self.label_2, self.comboBox_bt_baudrate,
                self.label_3, self.comboBox_bt_stop_bit,
                self.label_4, self.comboBox_bt_parity,
                self.label_5, self.comboBox_bt_flow_control,
            ],
            self.PORT_RS: [
                self.label_9, self.comboBox_rs_baudrate,
                self.label_7, self.comboBox_rs_stop_bit,
                self.label_6, self.comboBox_rs_parity,
                self.label_10, self.comboBox_rs_flow_control,
            ],
        }

        self._populate_comboboxes()
        self._connect_signals()
        self._set_extra_visible(self.PORT_BT, False)
        self._set_extra_visible(self.PORT_RS, False)

    # ------------------------------------------------------------------ #
    #  Инициализация
    # ------------------------------------------------------------------ #

    def _populate_comboboxes(self):
        """Заполняет все QComboBox значениями по-умолчанию."""
        ports = [f"COM{i}" for i in range(1, 201)]

        # Имена портов
        self.comboBox_bt_port_name.addItems(ports)
        self.comboBox_rs_port_name.addItems(ports)

        # Baudrate
        for br in self.BAUDRATES:
            self.comboBox_bt_baudrate.addItem(str(br), br)
            self.comboBox_rs_baudrate.addItem(str(br), br)
        self.comboBox_bt_baudrate.setCurrentText("19200")
        self.comboBox_rs_baudrate.setCurrentText("19200")

        # Stop Bit
        self.comboBox_bt_stop_bit.addItems(self.STOP_BITS)
        self.comboBox_rs_stop_bit.addItems(self.STOP_BITS)
        self.comboBox_bt_stop_bit.setCurrentText("1")
        self.comboBox_rs_stop_bit.setCurrentText("1")

        # Parity
        self.comboBox_bt_parity.addItems(self.PARITIES)
        self.comboBox_rs_parity.addItems(self.PARITIES)
        self.comboBox_bt_parity.setCurrentText("None")
        self.comboBox_rs_parity.setCurrentText("None")

        # Flow Control
        self.comboBox_bt_flow_control.addItems(self.FLOW_CONTROLS)
        self.comboBox_rs_flow_control.addItems(self.FLOW_CONTROLS)
        self.comboBox_bt_flow_control.setCurrentText("None")
        self.comboBox_rs_flow_control.setCurrentText("None")

    def _connect_signals(self):
        """Подключает внутренние сигналы страницы."""
        # Кнопки-переключатели доп. параметров
        self.pushButton_bt_settings.clicked.connect(
            lambda: self._toggle_extra(self.PORT_BT)
        )
        self.pushButton_rs_settings.clicked.connect(
            lambda: self._toggle_extra(self.PORT_RS)
        )

        # Кнопки подключения/отключения
        self.pushButton_bt_connect.clicked.connect(
            lambda: self._on_connect_clicked(self.PORT_BT)
        )
        self.pushButton_rs_connect.clicked.connect(
            lambda: self._on_connect_clicked(self.PORT_RS)
        )

    # ------------------------------------------------------------------ #
    #  Вспомогательные методы
    # ------------------------------------------------------------------ #

    def _toggle_extra(self, port_key: str):
        widgets = self._extra_widgets[port_key]
        visible = widgets[0].isVisible()
        self._set_extra_visible(port_key, not visible)

    def _set_extra_visible(self, port_key: str, visible: bool):
        for w in self._extra_widgets[port_key]:
            w.setVisible(visible)

    def _on_connect_clicked(self, port_key: str):
        if self._connected[port_key]:
            self.port_disconnect_requested.emit(port_key)
        else:
            self.port_connect_requested.emit(*self._collect_params(port_key))

    def _collect_params(self, port_key: str):
        if port_key == self.PORT_BT:
            port_name = self.comboBox_bt_port_name.currentText()
            baudrate = self.comboBox_bt_baudrate.currentData()
            stop_bit = self.comboBox_bt_stop_bit.currentText()
            parity = self.comboBox_bt_parity.currentText()
            flow = self.comboBox_bt_flow_control.currentText()
        else:
            port_name = self.comboBox_rs_port_name.currentText()
            baudrate = self.comboBox_rs_baudrate.currentData()
            stop_bit = self.comboBox_rs_stop_bit.currentText()
            parity = self.comboBox_rs_parity.currentText()
            flow = self.comboBox_rs_flow_control.currentText()

        return port_key, port_name, baudrate, stop_bit, parity, flow

    # ------------------------------------------------------------------ #
    #  Публичный API
    # ------------------------------------------------------------------ #

    def set_connected(self, port_key: str, connected: bool):
        """Меняет подпись кнопки и (де)активирует поля ввода."""
        self._connected[port_key] = connected

        if port_key == self.PORT_BT:
            button = self.pushButton_bt_connect
            inputs = [
                self.comboBox_bt_port_name,
                self.comboBox_bt_baudrate,
                self.comboBox_bt_stop_bit,
                self.comboBox_bt_parity,
                self.comboBox_bt_flow_control,
                self.pushButton_bt_settings,
            ]
        else:
            button = self.pushButton_rs_connect
            inputs = [
                self.comboBox_rs_port_name,
                self.comboBox_rs_baudrate,
                self.comboBox_rs_stop_bit,
                self.comboBox_rs_parity,
                self.comboBox_rs_flow_control,
                self.pushButton_rs_settings,
            ]

        button.setText("Відключитись" if connected else "Підключитись")
        for w in inputs:
            w.setEnabled(not connected)

    def is_connected(self, port_key: str) -> bool:
        return self._connected.get(port_key, False)

    def show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    def show_info(self, title: str, message: str):
        QMessageBox.information(self, title, message)