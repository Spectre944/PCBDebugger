from enum import Enum
from PySide6.QtCore import Qt, QModelIndex, Signal, QPointF
from PySide6.QtGui import (
    QStandardItemModel, QStandardItem, QColor, QBrush,
    QIcon, QPixmap, QPainter, QPolygonF
)
from PySide6.QtWidgets import QMenu, QTreeView
import json


class TaskStatus(Enum):
    NOT_TESTED = 0
    PASSED = 1
    FAILED = 2


STATUS_LABELS = {
    TaskStatus.NOT_TESTED: "Не перевірено",
    TaskStatus.PASSED: "Перевірено",
    TaskStatus.FAILED: "Провалено",
}

STATUS_COLORS = {
    TaskStatus.NOT_TESTED: None,
    TaskStatus.PASSED: QColor("#2ecc71"),
    TaskStatus.FAILED: QColor("#e74c3c"),
}

ID_ROLE = Qt.UserRole + 1
NETS_ROLE = Qt.UserRole + 2
MODE_ROLE = Qt.UserRole + 3
STATUS_ROLE = Qt.UserRole + 4
DESCRIPTION_ROLE = Qt.UserRole + 5
OPTIONS_ROLE = Qt.UserRole + 6
KIND_ROLE = Qt.UserRole + 7
TESTING_ROLE = Qt.UserRole + 8
CURRENT_ROLE = Qt.UserRole + 9  # NEW: чи є цей рядок "поточним кроком" раннера

# статус <-> ключ в options
STATUS_TO_OPTION_KEY = {
    TaskStatus.PASSED: "pass",
    TaskStatus.FAILED: "fail",
}

# Підсвітка поточного кроку — аналог жовтої стрілки на рядку в дебагері IDE
CURRENT_STEP_BACKGROUND = QColor("#3a3f5c")
CURRENT_STEP_MARKER_COLOR = QColor("#f1c40f")


def _make_current_step_icon() -> QIcon:
    """Іконка-трикутник 'сюди дійшов раннер', малюється один раз і кешується."""
    pixmap = QPixmap(14, 14)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(CURRENT_STEP_MARKER_COLOR))
    painter.setPen(Qt.NoPen)
    triangle = QPolygonF([QPointF(2, 2), QPointF(12, 7), QPointF(2, 12)])
    painter.drawPolygon(triangle)
    painter.end()
    return QIcon(pixmap)


class TaskListModel(QStandardItemModel):
    # Сигнал: текст для записи в лог (без таймштампа — это забота View)
    logRequested = Signal(str)
    # NEW: id кроку, який щойно став поточним ("" якщо маркер знято)
    currentStepChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels(["Назва", "Тип перевірки", "Статус"])
        self.scenario_name = ""
        self.start_id = None
        self._current_id = None
        self._current_icon = _make_current_step_icon()

    def load_from_file(self, path: str):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        self.removeRows(0, self.rowCount())
        self.scenario_name = data.get("name", "")
        self.start_id = data.get("start")
        self._current_id = None  # старий id більше не відповідає жодному рядку

        for step in data["steps"]:
            general = step.get("general", {})
            testing = step.get("testing", {})
            options = step.get("options", {})
            nets = step.get("nets", [])
            kind = testing.get("kind")

            step_id = general.get("id")
            title = general.get("title", step_id)
            description = general.get("description", "-")
            mode = testing.get("mode", "manual")

            name_item = QStandardItem(title)
            name_item.setEditable(False)
            name_item.setData(step_id, ID_ROLE)
            name_item.setData(nets, NETS_ROLE)
            name_item.setData(mode, MODE_ROLE)
            name_item.setData(TaskStatus.NOT_TESTED.value, STATUS_ROLE)
            name_item.setData(description, DESCRIPTION_ROLE)
            name_item.setData(options, OPTIONS_ROLE)
            name_item.setData(kind, KIND_ROLE)
            name_item.setData(testing, TESTING_ROLE)
            name_item.setData(False, CURRENT_ROLE)

            mode_labels = {"manual": "Ручний", "auto": "Автоматичний", "info": "Інформація"}
            type_item = QStandardItem(mode_labels.get(mode, mode))
            type_item.setEditable(False)

            status_item = QStandardItem(STATUS_LABELS[TaskStatus.NOT_TESTED])
            status_item.setEditable(False)

            self.appendRow([name_item, type_item, status_item])

    # ---- Геттеры ----

    def get_id(self, index: QModelIndex) -> str:
        return self.item(index.row(), 0).data(ID_ROLE)

    def get_nets(self, index: QModelIndex) -> list:
        return self.item(index.row(), 0).data(NETS_ROLE) or []

    def get_mode(self, index: QModelIndex) -> str:
        return self.item(index.row(), 0).data(MODE_ROLE)

    def get_description(self, index: QModelIndex) -> str:
        return self.item(index.row(), 0).data(DESCRIPTION_ROLE) or "-"

    def get_options(self, index: QModelIndex) -> dict:
        return self.item(index.row(), 0).data(OPTIONS_ROLE) or {}

    def get_status(self, index: QModelIndex) -> TaskStatus:
        return TaskStatus(self.item(index.row(), 0).data(STATUS_ROLE))

    def get_hint(self, index: QModelIndex) -> str:
        """Хинт по текущему (последнему установленному) результату шага."""
        status = self.get_status(index)
        key = STATUS_TO_OPTION_KEY.get(status)
        if key is None:
            return "-"
        return self.get_options(index).get(key, {}).get("hint", "-")

    def get_kind(self, index: QModelIndex) -> str | None:
        return self.item(index.row(), 0).data(KIND_ROLE)

    def get_testing(self, index: QModelIndex) -> dict:
        return self.item(index.row(), 0).data(TESTING_ROLE) or {}

    def get_index_by_id(self, step_id: str) -> QModelIndex | None:
        for row in range(self.rowCount()):
            index = self.index(row, 0)
            if self.get_id(index) == step_id:
                return index
        return None

    def get_current_id(self) -> str | None:
        return self._current_id

    def is_current(self, index: QModelIndex) -> bool:
        return bool(self.item(index.row(), 0).data(CURRENT_ROLE))

    def set_status_by_id(self, step_id: str, status: TaskStatus):
        index = self.get_index_by_id(step_id)
        if index is None:
            print(f"Крок '{step_id}' не знайдено")
            return
        self.set_status(index, status)

    def set_status(self, index: QModelIndex, status: TaskStatus):
        row = index.row()
        name_item = self.item(row, 0)
        status_item = self.item(row, 2)

        name_item.setData(status.value, STATUS_ROLE)
        status_item.setText(STATUS_LABELS[status])

        color = STATUS_COLORS[status]
        if color is not None:
            status_item.setForeground(QBrush(color))
        else:
            status_item.setData(None, Qt.ForegroundRole)

        # Логирование результата по options[pass/fail].log
        key = STATUS_TO_OPTION_KEY.get(status)
        if key is not None:
            log_text = self.get_options(index).get(key, {}).get("log")
            if log_text:
                self.logRequested.emit(log_text)

    # ---- Поточний крок (маркер дебагера, як стрілка на рядку в IDE) ----

    def set_current(self, index: QModelIndex | None):
        """
        Позначає рядок як 'поточний крок' раннера. Знімає позначку з
        попереднього поточного рядка (якщо був). index=None — просто
        прибрати маркер (дебаг зупинено/скинуто).
        """
        if self._current_id is not None:
            prev_index = self.get_index_by_id(self._current_id)
            if prev_index is not None:
                prev_item = self.item(prev_index.row(), 0)
                prev_item.setData(False, CURRENT_ROLE)
                prev_item.setIcon(QIcon())
                prev_item.setBackground(QBrush())

        if index is None:
            self._current_id = None
            self.currentStepChanged.emit("")
            return

        item = self.item(index.row(), 0)
        item.setData(True, CURRENT_ROLE)
        item.setIcon(self._current_icon)
        item.setBackground(QBrush(CURRENT_STEP_BACKGROUND))

        self._current_id = self.get_id(index)
        self.currentStepChanged.emit(self._current_id)

    def clear_current(self):
        self.set_current(None)