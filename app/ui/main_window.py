from enum import Enum
import os
import subprocess

from app.ui.widgets.board_widget import BoardWidget
from app.ui.widgets.tree_widget import TreeModel, TreeWidget
from app.ui.pages.main_page import Ui_mainPage
from app.ui.pages.main_window import Ui_MainWindow
from app.ui.pages.settings_page import Ui_settingsPage
from app.ui.pages.settings_page_controller import PortSettingsWidget

from backend.kicad_api import KiCadApi
from backend.session import DiagnosticSession
from backend.runner import ScenarioRunner, DebugState
from backend.serial_manager import SerialManager
from backend.settings import AppSettings
from backend.serial_step_handler import SerialStepHandler

from backend.models.list_model import TaskListModel, TaskStatus, STATUS_COLORS, STATUS_LABELS, STATUS_ROLE

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QFileDialog, QMessageBox, QPushButton,
    QSizePolicy, QSplitter, QMenu, QTreeView
)
from PySide6.QtGui import (
    QPixmap, QColor, QUndoStack, QShortcut, QKeySequence, QStandardItemModel, QStandardItem, QColor, QBrush, QIcon
)
from PySide6.QtCore import Qt, QTimer, Signal, QModelIndex, QDateTime, QStandardPaths

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        
        # Настраиваем UI с меню
        self.setupUi(self)
        
        # Дополнительные настройки окна
        self.setWindowTitle("PCB Debugger")
        self.resize(1280, 460)
        self.setStyleSheet("QMainWindow { background:#0e1120; }")

        # Настройки (порты, пути к KiCad и проекту) — config/settings.json
        self.app_settings = AppSettings("config\\settings.json")
        self._user_connect_pending = set()  # порты, подключаемые кнопкой

        # Запускаем KiCad и сохраняем процесс (None, если запуск не удался)
        self.kicad_process = None
        kicad_start_error = self._start_kicad()

        self.kicad = KiCadApi(self, kicad_process=self.kicad_process)
        self.kicad.connection_status_changed.connect(self.show_status_bar_msg)
        self.kicad.selected_nets_changed.connect(self.update_selected_nets)
        self.kicad.connection_error.connect(self.show_connection_error)

        if kicad_start_error is None:
            self.kicad.connect()
        else:
            # Без запущенного KiCad автоподключение бессмысленно (иначе будет
            # ещё и вторая ошибка через 30 с). Окно покажем после инициализации.
            QTimer.singleShot(
                0,
                lambda: self.show_connection_error(
                    "KiCad не запущено", kicad_start_error
                ),
            )


        
        # Создаем страницу из второго UI
        self.main_page_widget = QWidget()
        self.ui_main_page = Ui_mainPage()
        self.ui_main_page.setupUi(self.main_page_widget)

        # Создаем страницу для настроек
        self.settings_page_widget = PortSettingsWidget()

        # Создаем стек и добавляем страницу
        self.stackWidget = QStackedWidget()
        self.stackWidget.addWidget(self.main_page_widget)
        self.stackWidget.addWidget(self.settings_page_widget)

        # Model
        self.model = TaskListModel()
        self.model.logRequested.connect(self.append_log)
        self.model.load_from_file("config\\scenario.json")

        # Процесс автодиагностики
        self.runner = ScenarioRunner(self.model, self.kicad)
        self.serial = SerialManager()

        # Подключаем сигналы страницы настроек к слотам MainWindow
        self.settings_page_widget.port_connect_requested.connect(self.on_port_connect_requested)
        self.settings_page_widget.port_disconnect_requested.connect(self.on_port_disconnect_requested)

        # Реагируем на фактические изменения состояния портов в SerialManager
        self.serial.port_connected.connect(self.on_port_connected)
        self.serial.port_disconnected.connect(self.on_port_disconnected)
        self.serial.port_error.connect(self.on_port_error)

        # Порт ждёт возвращения (занят / отключён) — идут автоповторы
        self.serial.port_reconnecting.connect(self.on_port_reconnecting)

        # Параметры портов и пути KiCad из config/settings.json
        kicad_settings = self.app_settings.get_kicad()
        self.settings_page_widget.set_kicad_path(kicad_settings["executable_path"])
        self.settings_page_widget.set_project_path(kicad_settings["project_path"])
        self.settings_page_widget.kicad_path_changed.connect(self.on_kicad_path_changed)
        self.settings_page_widget.project_path_changed.connect(self.on_project_path_changed)

        self.settings_page_widget.params_changed.connect(self.on_port_params_changed)

        for key in (PortSettingsWidget.PORT_BT, PortSettingsWidget.PORT_RS):
            self.settings_page_widget.apply_params(key, self.app_settings.get_port(key))

        # Автоподключение портов, которые были подключены в прошлый раз
        QTimer.singleShot(0, self._auto_connect_ports)

        # Сохранения и загрузка сессии диагностики
        self.session = DiagnosticSession(self.model)
        self.model.logRequested.connect(self.session.append_log)    

        # Місток serial <-> runner: узгоджує запит/відповідь для auto-кроків
        # (замінює стару пряму реєстрацію self.serial.wait_signal/send_and_wait,
        # яка не працювала — runner викликає handler(index), а serial чекає
        # (port_key, match_fn, timeout))
        self.serial_step_handler = SerialStepHandler(self.runner, self.serial, self.model)

        # Сигнал из SerialStepHandler для подсветки неработающих линий
        self.serial_step_handler.select_bad_nets.connect(
            lambda nets: self.kicad.select_net(*nets, zoom_to_fit=False)
        )

        # Текстовий статус дебага (поки що просто дублюємо в той самий лог)
        self.runner.debugStatus.connect(self.append_log)

        self.ui_main_page.treeViewTaskList.setModel(self.model)
        self.ui_main_page.treeViewTaskList.setColumnWidth(0, 350)
        self.ui_main_page.treeViewTaskList.setContextMenuPolicy(Qt.CustomContextMenu)

        self.ui_main_page.treeViewTaskList.clicked.connect(self.on_click)
        self.ui_main_page.treeViewTaskList.doubleClicked.connect(self.on_double_click)
        self.ui_main_page.treeViewTaskList.customContextMenuRequested.connect(self.on_context_menu)
        
        # Устанавливаем центральный виджет
        self.setCentralWidget(self.stackWidget)
        
        # Подключаем действия из меню
        self.connect_actions()

        # Індикатори стану дебагу (кольорова точка + прогрес) і брейкпоінти
        self._init_debug_indicators()
    
    # ---- Індикатори дебагу: статус/прогрес/підказка на панелі + кнопки ----

    # Колір тексту для кожного "сенсу" паузи — не всі PAUSED однакові
    _INDICATOR_COLORS = {
        "idle": "#8a8f98",       # сірий — сесія не активна
        "running": "#2ecc71",    # зелений — йде автопрогін / чекаємо відповідь плати
        "manual": "#f1c40f",     # жовтий — чекаємо, поки оператор сам відмітить результат
        "breakpoint": "#e74c3c",  # червоний — зупинились на брейкпоінті (fail-graph або user)
        "paused": "#7f8fa6",     # приглушений синьо-сірий — оператор сам натиснув Пауза
        "finished": "#3498db",   # синій — сценарій пройдено до кінця
    }

    _HINT_TEXTS = {
        "manual": "Відмітьте результат кроку (ПКМ у дереві → Перевірено/Провалено), потім натисніть «Наступний крок».",
        "breakpoint": "Полагодьте плату і натисніть «Продовжити» (кнопка Старт/Пауза) — крок буде перевірено ще раз.",
        "paused": "Дебаг на паузі. Натисніть «Продовжити», щоб піти далі з того самого місця.",
        "running": "-",
        "finished": "Сценарій пройдено до кінця. «Перезапустити» — почати заново.",
        "idle": "Натисніть «Старт», щоб почати перевірку плати.",
    }

    def _init_debug_indicators(self):
        # Причина останньої паузи — щоб stateChanged=="paused" знав, яким
        # кольором/текстом/підказкою це показати (manual / breakpoint / просто pause).
        self._last_pause_reason = "paused"

        self.runner.waitingUser.connect(lambda step_id: self._set_pause_reason("manual"))
        self.runner.breakpointHit.connect(lambda step_id: self._set_pause_reason("breakpoint"))
        self.runner.stateChanged.connect(self._on_debug_state_changed)
        self.runner.stepFinished.connect(lambda *_: self._update_progress_label())
        self.runner.stepSkipped.connect(lambda *_: self._update_progress_label())
        self.runner.restartRequested.connect(lambda *_: self._update_progress_label())


        # Брейкпоінти в дереві — джерело правди runner, модель лише малює
        self.runner.breakpointsChanged.connect(self.model.set_breakpoint_marker)

        # Кнопки на панелі дебагу (mainPage) — дублюють дії з меню, тому
        # обидва шляхи керування (меню і кнопки) працюють однаково.
        self.ui_main_page.pushButtonDebugStartStop.clicked.connect(self.debug_start_pause)
        self.ui_main_page.pushButtonDebugNextStep.clicked.connect(self.debug_next_step)
        self.ui_main_page.pushButtonDebugRestart.clicked.connect(self.debug_restart)
        self.ui_main_page.pushButtonDebugStop.clicked.connect(self.debug_stop)

        self._on_debug_state_changed(self.runner.state.value)
        self._update_progress_label()

    def _set_pause_reason(self, reason: str):
        self._last_pause_reason = reason

    def _on_debug_state_changed(self, state_value: str):
        if state_value == DebugState.RUNNING.value:
            self._last_pause_reason = "paused"  # скидаємо — наступна пауза за замовчуванням "проста"
            reason, text = "running", "Виконується…"
            icon_theme, button_text = QIcon.ThemeIcon.MediaPlaybackPause, "Пауза"
        elif state_value == DebugState.PAUSED.value:
            reason = self._last_pause_reason
            text = {
                "manual": "Очікує дію оператора",
                "breakpoint": "Зупинено",
                "paused": "На паузі",
            }[reason]
            icon_theme, button_text = QIcon.ThemeIcon.MediaPlaybackStart, "Продовжити"
        elif state_value == DebugState.FINISHED.value:
            reason, text = "finished", "Сценарій завершено"
            icon_theme, button_text = QIcon.ThemeIcon.MediaPlaybackStart, "Старт"
        else:  # idle
            reason, text = "idle", "Дебаг не запущено"
            icon_theme, button_text = QIcon.ThemeIcon.MediaPlaybackStart, "Старт"

        color = self._INDICATOR_COLORS[reason]
        self.ui_main_page.label_debugStatus.setText(text)
        self.ui_main_page.label_debugStatus.setStyleSheet(f"color: {color}; font-weight: bold;")

        self.ui_main_page.pushButtonDebugStartStop.setIcon(QIcon(QIcon.fromTheme(icon_theme)))
        self.ui_main_page.pushButtonDebugStartStop.setToolTip(button_text)

    def _update_progress_label(self):
        counts = self.model.get_status_counts()
        done = counts[TaskStatus.PASSED] + counts[TaskStatus.FAILED] + counts[TaskStatus.SKIPPED]
        self.ui_main_page.label_debugOverallInfo.setText(
            f"{done}/{counts['total']}  (помилок: {counts[TaskStatus.FAILED]}, пропущено: {counts[TaskStatus.SKIPPED]})"
        )

    def connect_actions(self):
        """Подключение действий из меню к слотам"""
        self.action_openDigagnostic.triggered.connect(self.open_diagnostic)
        self.action_saveDiagnostic.triggered.connect(self.save_diagnostic)
        self.actionStay_On_Top.triggered.connect(self.toggle_stay_on_top)
        self.action_connectKiCAD.triggered.connect(self.connect_kicad)
        self.action_debug_start_pause.triggered.connect(self.debug_start_pause)
        self.action_debug_nextStep.triggered.connect(self.debug_next_step)
        self.action_debug_stop.triggered.connect(self.debug_stop)
        self.action_debug_restart.triggered.connect(self.debug_restart)
        self.action_mainPage.triggered.connect( lambda: self.stackWidget.setCurrentIndex(0) )
        self.action_settingsPage.triggered.connect( lambda: self.stackWidget.setCurrentIndex(1) )


    # --- ЛКМ: выделить сети без зума ---
    def on_click(self, index: QModelIndex):
        if index.column() != 0:
            index = index.siblingAtColumn(0)
        self.update_info(index)
        nets = self.model.get_nets(index)
        self.kicad.select_net(*nets, zoom_to_fit=False)

    # --- Двойной клик: выделить сети + zoomToFit ---
    def on_double_click(self, index: QModelIndex):
        if index.column() != 0:
            index = index.siblingAtColumn(0)
        self.update_info(index)
        nets = self.model.get_nets(index)
        self.kicad.select_net(*nets, zoom_to_fit=True)

    # --- Обновление info-панели по выбранному шагу ---
    def update_info(self, index: QModelIndex):
        description = self.model.get_description(index)
        hint = self.model.get_hint(index)
        nets = self.model.get_nets(index)

        self.ui_main_page.label_description.setText(description)
        self.ui_main_page.label_hint.setText(hint)

    # --- Добавление записи в лог с таймштампом ---
    def append_log(self, text: str):
        timestamp = QDateTime.currentDateTime().toString("HH:mm:ss")
        self.ui_main_page.textEditLog.append(f"[{timestamp}] {text}")

    # --- ПКМ: контекстное меню ---
    def on_context_menu(self, pos):
        index = self.ui_main_page.treeViewTaskList.indexAt(pos)
        if not index.isValid():
            return
        index = index.siblingAtColumn(0)

        menu = QMenu(self.ui_main_page.treeViewTaskList)

        status_menu = menu.addMenu("Статус перевірки")
        act_passed = status_menu.addAction(STATUS_LABELS[TaskStatus.PASSED])
        act_failed = status_menu.addAction(STATUS_LABELS[TaskStatus.FAILED])
        act_not_tested = status_menu.addAction(STATUS_LABELS[TaskStatus.NOT_TESTED])

        act_highlight_nets = menu.addAction("Підсвітити nets")
        act_highlight_pins = menu.addAction("Підсвітити контакти")

        menu.addSeparator()
        act_start_here = menu.addAction("Почати перевірку звідси")

        step_id = self.model.get_id(index)
        is_breakpoint = self.model.is_breakpoint_marker(index)
        act_toggle_breakpoint = menu.addAction(
            "Зняти брейкпоінт" if is_breakpoint else "Поставити брейкпоінт"
        )

        # Skip/Retry діють на ПОТОЧНИЙ крок раннера — застосовувати їх до
        # довільного рядка дерева безглуздо (runner про нього "не думає").
        act_skip = act_retry = None
        if step_id == self.runner.current_id and self.runner.current_id is not None:
            menu.addSeparator()
            act_skip = menu.addAction("Пропустити крок (skip)")
            act_retry = menu.addAction("Повторити крок")

        action = menu.exec(self.ui_main_page.treeViewTaskList.viewport().mapToGlobal(pos))

        if action == act_passed:
            self.model.set_status(index, TaskStatus.PASSED)
            self.update_info(index)
        elif action == act_failed:
            self.model.set_status(index, TaskStatus.FAILED)
            self.update_info(index)
        elif action == act_not_tested:
            self.model.set_status(index, TaskStatus.NOT_TESTED)
            self.update_info(index)
        elif action == act_highlight_nets:
            for net_name in self.model.get_nets(index):
                self.kicad.select_net(net_name, zoom_to_fit=False)
        elif action == act_highlight_pins:
            nets = self.model.get_nets(index)
            self.kicad.select_net_pins(*nets, zoom_to_fit=False)
        elif action == act_start_here:
            # "Run to here" — стартуємо/перестрибуємо дебаг на обраний крок,
            # незалежно від того, де він зараз стоїть.
            self.runner.start(self.model.get_id(index))
        elif action == act_toggle_breakpoint:
            self.runner.toggle_breakpoint(step_id)
        elif act_skip is not None and action == act_skip:
            self.runner.skip_current()
        elif act_retry is not None and action == act_retry:
            self.runner.retry_current()
    
    # Слоты для действий меню
    def open_diagnostic(self):
        # Получаем путь к домашней папке или последней использованной
        home_dir = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
        
        # Открываем диалог выбора файла
        file_path, _ = QFileDialog.getOpenFileName(
            self,                      # родительское окно
            "Відкрити діагностичний файл",  # заголовок
            home_dir,                  # начальная директория
            "JSON files (*.json);;All files (*.*)"  # фильтр расширений
        )
        
        if file_path:  # если файл выбран (не нажали "Отмена")
            self.session.load(file_path)
            QMessageBox.information(self, "Успіх", f"Файл завантажений: {file_path}")
    
    def save_diagnostic(self):
        # Предлагаем имя файла по умолчанию
        default_name = "diagnostic.json"
        home_dir = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
        
        # Открываем диалог сохранения
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Зберегти діагностичний файл",
            f"{home_dir}/{default_name}",  # полный путь с именем файла
            "JSON files (*.json);;All files (*.*)"
        )
        
        if file_path:
            # Добавляем расширение .json, если пользователь его не указал
            if not file_path.endswith('.json'):
                file_path += '.json'
            
            self.session.save(file_path)
            QMessageBox.information(self, "Успіх", f"Файл збережено: {file_path}")
        
    def toggle_stay_on_top(self):
        if self.windowFlags() & Qt.WindowStaysOnTopHint:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.show()
    
    def connect_kicad(self):
        self.kicad.disconnect()
        self.kicad.connect()

    def debug_start_pause(self):
        # Одна кнопка: Start (з початку), Resume (після паузи/fail-брейкпоінта)
        # або Pause (якщо зараз йде автопрогон) — вирішує сам раннер по стану.
        self.runner.toggle_start_pause()
    
    def debug_next_step(self):
        self.runner.next_step()
    
    def debug_stop(self):
        self.runner.stop()
    
    def debug_restart(self):
        self.runner.restart()

    def show_status_bar_msg(self, text):
        self.statusBar().showMessage(text, 3000)

    def update_selected_nets(self, nets):
        self.ui_main_page.label_objSelect.setText(
            "Обрано nets: " + (", ".join(nets) if nets else "-")
        )

    def show_connection_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)

    # ------------------------------------------------------------------ #
    #  Слоты страницы настроек портов
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Запуск KiCad
    # ------------------------------------------------------------------ #

    def _start_kicad(self) -> str | None:
        """
        Запускает KiCad с проектом из настроек.

        Returns:
            None при успехе, иначе текст ошибки для пользователя.
        """
        kicad = self.app_settings.get_kicad()
        exe_path = kicad["executable_path"]
        project_path = kicad["project_path"]

        if not exe_path or not os.path.isfile(exe_path):
            return (
                f"Не знайдено виконуваний файл KiCAD:\n{exe_path or '(шлях не вказано)'}\n\n"
                "Вкажіть шлях у Налаштування → Налаштування KiCAD."
            )

        command = [exe_path]

        if project_path:
            if os.path.isfile(project_path):
                command.append(project_path)
            else:
                return (
                    f"Не знайдено файл проєкту:\n{project_path}\n\n"
                    "Вкажіть шлях у Налаштування → Налаштування KiCAD."
                )

        try:
            self.kicad_process = subprocess.Popen(command)
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            # OSError: файл не запускается (WinError 193), нет прав / нужен
            # запуск от администратора (WinError 740), антивирус и т.п.
            self.kicad_process = None
            return f"Не вдалося запустити KiCAD:\n{exe_path}\n\nДеталі: {e}"

        return None

    def on_kicad_path_changed(self, path: str):
        self.app_settings.update_kicad(executable_path=path)
        self.show_status_bar_msg("Шлях до KiCAD збережено. Діє після перезапуску програми.")

    def on_project_path_changed(self, path: str):
        self.app_settings.update_kicad(project_path=path)
        self.show_status_bar_msg("Шлях до проєкту збережено. Діє після перезапуску програми.")

    def _auto_connect_ports(self):
        """Подключает порты, которые были подключены при прошлом выходе."""
        for key in (PortSettingsWidget.PORT_BT, PortSettingsWidget.PORT_RS):
            params = self.app_settings.get_port(key)

            if not params["auto_connect"]:
                continue

            self.on_port_connect_requested(
                key,
                params["port_name"],
                params["baudrate"],
                params["stop_bit"],
                params["parity"],
                params["flow_control"],
                user_initiated=False,
            )

    def on_port_params_changed(self, port_key: str):
        """Пользователь изменил параметры порта — сохраняем в settings.json."""
        self.app_settings.update_port(
            port_key, **self.settings_page_widget.get_params(port_key)
        )

    def on_port_connect_requested(self, port_key, port_name, baudrate,
                                  stop_bit, parity, flow_control,
                                  user_initiated=True):
        """Запрос на подключение порта (кнопка или автоподключение)."""
        self.app_settings.update_port(
            port_key,
            port_name=port_name,
            baudrate=baudrate,
            stop_bit=stop_bit,
            parity=parity,
            flow_control=flow_control,
            auto_connect=True,
        )

        if user_initiated:
            self._user_connect_pending.add(port_key)

        try:
            # Строки из UI (parity "Even", stop_bit "1.5" ...) SerialManager
            # сам преобразует в enum-ы QSerialPort.
            self.serial.configure_port(
                port_key,
                port_name,
                baud_rate=baudrate,
                stop_bits=stop_bit,
                parity=parity,
                flow_control=flow_control,
            )
            # Если порт занят/недоступен — SerialManager продолжит попытки сам
            self.serial.connect_port(port_key)
        except Exception as e:
            self.settings_page_widget.set_state(
                port_key, PortSettingsWidget.STATE_DISCONNECTED
            )
            self.settings_page_widget.show_error(
                "Помилка підключення",
                f"Не вдалося відкрити {port_key} ({port_name}):\n{e}"
            )
        finally:
            self._user_connect_pending.discard(port_key)

    def on_port_disconnect_requested(self, port_key: str):
        """Запрос на отключение порта (или отмену повторных попыток)."""
        self.app_settings.update_port(port_key, auto_connect=False)

        try:
            self.serial.disconnect_port(port_key)
        except Exception as e:
            self.settings_page_widget.show_error(
                "Помилка відключення",
                f"Не вдалося закрити {port_key}:\n{e}"
            )

    def on_port_connected(self, port_key: str):
        """SerialManager подтвердил подключение."""
        self.settings_page_widget.set_state(port_key, PortSettingsWidget.STATE_CONNECTED)
        self.append_log(f"Порт {port_key} підключено.")

    def on_port_disconnected(self, port_key: str):
        """Порт закрыт (пользователем или потерян)."""
        self.settings_page_widget.set_state(port_key, PortSettingsWidget.STATE_DISCONNECTED)
        self.append_log(f"Порт {port_key} відключено.")

    def on_port_reconnecting(self, port_key: str):
        """Порт недоступен — SerialManager повторяет попытки автоматично."""
        self.settings_page_widget.set_state(port_key, PortSettingsWidget.STATE_CONNECTING)
        self.append_log(f"Порт {port_key} недоступний, очікуємо на відновлення зв'язку…")
        self.show_status_bar_msg(f"Порт {port_key}: очікування відновлення зв'язку…")

    def on_port_error(self, port_key: str, message: str):
        """
        SerialManager сообщает об ошибке (один раз за серию неудач,
        повторные попытки молчат).
        """
        self.append_log(f"Помилка порту {port_key}: {message}")

        if port_key in self._user_connect_pending:
            # Диалог только когда пользователь сам нажал "Підключитись".
            # Откладываем, чтобы не открывать модальное окно внутри сигнала.
            text = (
                f"{port_key}: {message}\n\n"
                "Порт зайнятий або недоступний. Програма повторюватиме спробу "
                "автоматично. Натисніть «Скасувати», щоб зупинити."
            )
            QTimer.singleShot(
                0,
                lambda: self.settings_page_widget.show_error("Помилка порту", text),
            )
        else:
            self.show_status_bar_msg(f"Помилка порту {port_key}: {message}")