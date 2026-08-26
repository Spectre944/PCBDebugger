from enum import Enum
from PySide6.QtCore import Qt, QModelIndex, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush
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

# статус <-> ключ в options
STATUS_TO_OPTION_KEY = {
    TaskStatus.PASSED: "pass",
    TaskStatus.FAILED: "fail",
}


class TaskListModel(QStandardItemModel):
    # Сигнал: текст для записи в лог (без таймштампа — это забота View)
    logRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels(["Назва", "Тип перевірки", "Статус"])
        self.scenario_name = ""
        self.start_id = None

    def load_from_file(self, path: str):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        self.removeRows(0, self.rowCount())
        self.scenario_name = data.get("name", "")
        self.start_id = data.get("start")

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

    def get_index_by_id(self, step_id: str) -> QModelIndex | None:
        for row in range(self.rowCount()):
            index = self.index(row, 0)
            if self.get_id(index) == step_id:
                return index
        return None

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