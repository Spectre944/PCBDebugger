from enum import Enum
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush
from PySide6.QtWidgets import QMenu, QTreeView
import json


# ---------- Статусы и роли данных ----------

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
    TaskStatus.NOT_TESTED: None,               # обычный цвет темы
    TaskStatus.PASSED: QColor("#2ecc71"),
    TaskStatus.FAILED: QColor("#e74c3c"),
}

# Кастомные роли для хранения доп. данных на строке (на item колонки 0)
ID_ROLE = Qt.UserRole + 1
NETS_ROLE = Qt.UserRole + 2
MODE_ROLE = Qt.UserRole + 3
STATUS_ROLE = Qt.UserRole + 4


# ---------- Модель ----------

class TaskListModel(QStandardItemModel):
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
            nets = step.get("nets", [])

            step_id = general.get("id")
            title = general.get("title", step_id)
            mode = testing.get("mode", "manual")

            name_item = QStandardItem(title)
            name_item.setEditable(False)
            name_item.setData(step_id, ID_ROLE)
            name_item.setData(nets, NETS_ROLE)
            name_item.setData(mode, MODE_ROLE)
            name_item.setData(TaskStatus.NOT_TESTED.value, STATUS_ROLE)

            mode_labels = {"manual": "Ручний", "auto": "Автоматичний", "info": "Інформація"}
            type_item = QStandardItem(mode_labels.get(mode, mode))
            type_item.setEditable(False)

            status_item = QStandardItem(STATUS_LABELS[TaskStatus.NOT_TESTED])
            status_item.setEditable(False)

            self.appendRow([name_item, type_item, status_item])

    # ---- Вспомогательные геттеры по индексу строки ----

    def get_id(self, index: QModelIndex) -> str:
        return self.item(index.row(), 0).data(ID_ROLE)

    def get_nets(self, index: QModelIndex) -> list:
        return self.item(index.row(), 0).data(NETS_ROLE)

    def get_mode(self, index: QModelIndex) -> str:
        return self.item(index.row(), 0).data(MODE_ROLE)

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
            status_item.setData(None, Qt.ForegroundRole)  # сброс к цвету темы по умолчанию