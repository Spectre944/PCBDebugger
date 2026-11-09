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
      - кнопки подключения переключают текст "Підключитись" / "Скасувати" /
        "Відключитись" в зависимости от состояния порта;
      - сигналы наружу о запросе подключения/отключения и смене параметров.
    """

    # (port_key, port_name, baudrate, stop_bit, parity, flow_control)
    port_connect_requested = Signal(str, str, int, str, str, str)
    port_disconnect_requested = Signal(str)
    # port_key: любой параметр порта изменён пользователем (для сохранения)
    params_changed = Signal(str)

    # Состояния порта
    STATE_DISCONNECTED = "disconnected"
    STATE_CONNECTING = "connecting"   # порт недоступен, идут повторные попытки
    STATE_CONNECTED = "connected"

    # Ключи портов, которые обслуживает страница
    PORT_BT = "BT"
    PORT_RS = "RS"

    # Значения по-умолчанию для доп. параметров
    BAUDRATES = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
    STOP_BITS = ["1", "1.5", "2"]
    PARITIES = ["None", "Even", "Odd", "Mark", "Space"]
    FLOW_CONTROLS = ["None", "RTS/CTS", "XON/XOFF"]  # DSR/DTR в Qt не поддерживается

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # Храним состояние порта
        self._state = {
            self.PORT_BT: self.STATE_DISCONNECTED,
            self.PORT_RS: self.STATE_DISCONNECTED,
        }

        # Виджеты параметров каждого порта (имя, baudrate, stop, parity, flow)
        self._param_widgets = {
            self.PORT_BT: (
                self.comboBox_bt_port_name, self.comboBox_bt_baudrate,
                self.comboBox_bt_stop_bit, self.comboBox_bt_parity,
                self.comboBox_bt_flow_control,
            ),
            self.PORT_RS: (
                self.comboBox_rs_port_name, self.comboBox_rs_baudrate,
                self.comboBox_rs_stop_bit, self.comboBox_rs_parity,
                self.comboBox_rs_flow_control,
            ),
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

        # Любое изменение параметров -> наружу (сохранение в settings.json)
        for port_key, widgets in self._param_widgets.items():
            for combo in widgets:
                combo.currentIndexChanged.connect(
                    lambda _=None, key=port_key: self.params_changed.emit(key)
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
        if self._state[port_key] == self.STATE_DISCONNECTED:
            self.port_connect_requested.emit(*self._collect_params(port_key))
        else:
            # И "Відключитись", и "Скасувати" (остановить повторные попытки)
            self.port_disconnect_requested.emit(port_key)

    def _collect_params(self, port_key: str):
        params = self.get_params(port_key)

        return (
            port_key,
            params["port_name"],
            params["baudrate"],
            params["stop_bit"],
            params["parity"],
            params["flow_control"],
        )

    # ------------------------------------------------------------------ #
    #  Публичный API
    # ------------------------------------------------------------------ #

    def get_params(self, port_key: str) -> dict:
        """Текущие значения полей порта (для сохранения в settings.json)."""
        name, baud, stop, parity, flow = self._param_widgets[port_key]

        return {
            "port_name": name.currentText(),
            "baudrate": int(baud.currentData() or baud.currentText()),
            "stop_bit": stop.currentText(),
            "parity": parity.currentText(),
            "flow_control": flow.currentText(),
        }

    def apply_params(self, port_key: str, params: dict):
        """Выставляет поля порта из сохранённых настроек (без сигналов)."""
        name, baud, stop, parity, flow = self._param_widgets[port_key]

        for combo in (name, baud, stop, parity, flow):
            combo.blockSignals(True)

        try:
            port_name = params.get("port_name")
            if port_name:
                if name.findText(port_name) == -1:
                    name.addItem(port_name)
                name.setCurrentText(port_name)

            index = baud.findData(params.get("baudrate"))
            if index != -1:
                baud.setCurrentIndex(index)

            for combo, key in ((stop, "stop_bit"), (parity, "parity"), (flow, "flow_control")):
                index = combo.findText(str(params.get(key)))
                if index != -1:
                    combo.setCurrentIndex(index)
        finally:
            for combo in (name, baud, stop, parity, flow):
                combo.blockSignals(False)

    def set_state(self, port_key: str, state: str):
        """Меняет подпись кнопки и (де)активирует поля ввода."""
        self._state[port_key] = state

        if port_key == self.PORT_BT:
            button = self.pushButton_bt_connect
            settings_button = self.pushButton_bt_settings
        else:
            button = self.pushButton_rs_connect
            settings_button = self.pushButton_rs_settings

        button.setText({
            self.STATE_DISCONNECTED: "Підключитись",
            self.STATE_CONNECTING: "Скасувати",
            self.STATE_CONNECTED: "Відключитись",
        }[state])

        editable = state == self.STATE_DISCONNECTED

        for w in (*self._param_widgets[port_key], settings_button):
            w.setEnabled(editable)

    def set_connected(self, port_key: str, connected: bool):
        """Совместимость со старым API."""
        self.set_state(
            port_key,
            self.STATE_CONNECTED if connected else self.STATE_DISCONNECTED,
        )

    def is_connected(self, port_key: str) -> bool:
        return self._state.get(port_key) == self.STATE_CONNECTED

    def show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    def show_info(self, title: str, message: str):
        QMessageBox.information(self, title, message)