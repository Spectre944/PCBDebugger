from enum import Enum

from app.ui.widgets.board_widget import BoardWidget
from app.ui.widgets.tree_widget import TreeModel, TreeWidget
from app.ui.pages.main_page import Ui_mainPage
from app.ui.pages.main_window import Ui_MainWindow
from app.ui.pages.settings_page import Ui_settingsPage

from backend.kicad_api import KiCAD_API
from backend.models.list_model import TaskListModel, TaskStatus, STATUS_COLORS, STATUS_LABELS, STATUS_ROLE

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QFileDialog, QMessageBox, QPushButton, QLabel,
    QSizePolicy, QSplitter, QMenu, QTreeView
)
from PySide6.QtGui import (
    QPixmap, QColor, QUndoStack, QShortcut, QKeySequence, QStandardItemModel, QStandardItem, QColor, QBrush
)
from PySide6.QtCore import Qt, QTimer, Signal, QModelIndex

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        
        # Настраиваем UI с меню
        self.setupUi(self)
        
        # Дополнительные настройки окна
        self.setWindowTitle("PCB Debugger")
        self.resize(720, 600)
        self.setStyleSheet("QMainWindow { background:#0e1120; }")

        self.kicad = KiCAD_API()
        
        # Создаем страницу из второго UI
        self.main_page_widget = QWidget()
        self.ui_main_page = Ui_mainPage()
        self.ui_main_page.setupUi(self.main_page_widget)

        # Создаем страницу для настроек
        self.settings_page_widget = QWidget()
        self.ui_settings_page = Ui_settingsPage()
        self.ui_settings_page.setupUi(self.settings_page_widget)

        # Создаем стек и добавляем страницу
        self.stackWidget = QStackedWidget()
        self.stackWidget.addWidget(self.main_page_widget)
        self.stackWidget.addWidget(self.settings_page_widget)

        # Model
        self.model = TaskListModel()
        self.model.load_from_file("config\scenario.json")

        self.ui_main_page.treeViewTaskList

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

    # --- ЛКМ: выделить сети без зума ---
    def on_click(self, index: QModelIndex):
        if index.column() != 0:
            index = index.siblingAtColumn(0)
        nets = self.model.get_nets(index)
        for net_name in nets:
            self.kicad.select_net(net_name, zoomToFit=False)

    # --- Двойной клик: выделить сети + zoomToFit ---
    def on_double_click(self, index: QModelIndex):
        if index.column() != 0:
            index = index.siblingAtColumn(0)
        nets = self.model.get_nets(index)
        for net_name in nets:
            self.kicad.select_net(net_name, zoomToFit=True)

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

        action = menu.exec(self.ui_main_page.treeViewTaskList.viewport().mapToGlobal(pos))

        if action == act_passed:
            self.model.set_status(index, TaskStatus.PASSED)
        elif action == act_failed:
            self.model.set_status(index, TaskStatus.FAILED)
        elif action == act_not_tested:
            self.model.set_status(index, TaskStatus.NOT_TESTED)
        elif action == act_highlight_nets:
            for net_name in self.model.get_nets(index):
                self.kicad.select_net(net_name, zoomToFit=False)
        elif action == act_highlight_pins:
            for net_name in self.model.get_nets(index):
                self.kicad.select_net_pins(net_name, zoomToFit=False)
    
    # Слоты для действий меню
    def open_diagnostic(self):
        print("Open diagnostic")
    
    def save_diagnostic(self):
        print("Save diagnostic")
    
    def toggle_stay_on_top(self):
        if self.windowFlags() & Qt.WindowStaysOnTopHint:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.show()
    
    def connect_kicad(self):
        print("Connect to KiCAD")
        self.kicad.select_net("LDAC_REF", True)

    
    def debug_start_pause(self):
        print("Debug start/pause")
        # self.kicad.select_net("ZAH_VP1")
        self.kicad.select_net_pins("CLK_MOD")
    
    def debug_next_step(self):
        print("Debug next step")
    
    def debug_stop(self):
        print("Debug stop")
    
    def debug_restart(self):
        print("Debug restart")