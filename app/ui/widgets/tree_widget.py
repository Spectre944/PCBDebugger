from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt, QObject
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeView, QVBoxLayout, QWidget, QStyle, QStyleOption
from typing import Optional, List, Any, Dict
import sys


class TreeNode:
    """Узел дерева"""
    def __init__(self, data: Any, parent: Optional['TreeNode'] = None):
        self._data = data
        self._parent = parent
        self._children: List['TreeNode'] = []
        self._row = 0
    
    def append_child(self, child: 'TreeNode') -> None:
        child._parent = self
        child._row = len(self._children)
        self._children.append(child)
    
    def insert_child(self, row: int, child: 'TreeNode') -> bool:
        if row < 0 or row > len(self._children):
            return False
        child._parent = self
        child._row = row
        self._children.insert(row, child)
        self._update_rows(row + 1)
        return True
    
    def remove_child(self, row: int) -> bool:
        if row < 0 or row >= len(self._children):
            return False
        self._children.pop(row)
        self._update_rows(row)
        return True
    
    def _update_rows(self, start_row: int) -> None:
        for i in range(start_row, len(self._children)):
            self._children[i]._row = i
    
    def child(self, row: int) -> Optional['TreeNode']:
        if 0 <= row < len(self._children):
            return self._children[row]
        return None
    
    def child_count(self) -> int:
        return len(self._children)
    
    def row(self) -> int:
        return self._row
    
    def parent(self) -> Optional['TreeNode']:
        return self._parent
    
    def data(self) -> Any:
        return self._data
    
    def set_data(self, data: Any) -> None:
        self._data = data


class TreeModel(QAbstractItemModel):
    """Модель дерева"""
    def __init__(self, root_data: Any = "Root"):
        super().__init__()
        self._root = TreeNode(root_data)
        self._columns = 1  # Количество колонок
    
    def set_columns(self, columns: int) -> None:
        """Установить количество колонок"""
        self._columns = columns
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return self._columns
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            node = parent.internalPointer()
            return node.child_count() if node else 0
        return self._root.child_count()
    
    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        
        if parent.isValid():
            parent_node = parent.internalPointer()
        else:
            parent_node = self._root
        
        child_node = parent_node.child(row)
        if child_node:
            return self.createIndex(row, column, child_node)
        return QModelIndex()
    
    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()
        
        node = index.internalPointer()
        parent_node = node.parent()
        
        if parent_node == self._root or parent_node is None:
            return QModelIndex()
        
        return self.createIndex(parent_node.row(), 0, parent_node)
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        
        node = index.internalPointer()
        
        if role == Qt.DisplayRole:
            data = node.data()
            if isinstance(data, (list, tuple)):
                if index.column() < len(data):
                    return data[index.column()]
                return None
            elif index.column() == 0:
                return str(data)
            return None
        
        elif role == Qt.EditRole:
            return node.data()
        
        return None
    
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid():
            return False
        
        node = index.internalPointer()
        
        if role == Qt.EditRole:
            # Если данные - список, обновляем только конкретную колонку
            if isinstance(node.data(), (list, tuple)):
                data = list(node.data())
                if index.column() < len(data):
                    data[index.column()] = value
                    node.set_data(data)
                else:
                    return False
            else:
                node.set_data(value)
            
            self.dataChanged.emit(index, index, [role])
            return True
        
        return False
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.NoItemFlags
        
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        
        # Разрешаем редактирование
        flags |= Qt.ItemIsEditable
        
        return flags
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return f"Колонка {section + 1}"
        return None
    
    def add_node(self, data: Any, parent: QModelIndex = QModelIndex(), position: int = -1) -> QModelIndex:
        """Добавление узла"""
        if parent.isValid():
            parent_node = parent.internalPointer()
        else:
            parent_node = self._root
        
        node = TreeNode(data)
        
        if position < 0:
            position = parent_node.child_count()
        
        self.beginInsertRows(parent, position, position)
        parent_node.insert_child(position, node)
        self.endInsertRows()
        
        return self.createIndex(position, 0, node)
    
    def remove_node(self, index: QModelIndex) -> bool:
        """Удаление узла"""
        if not index.isValid():
            return False
        
        node = index.internalPointer()
        parent_node = node.parent()
        
        if parent_node is None:
            return False
        
        row = node.row()
        self.beginRemoveRows(index.parent(), row, row)
        result = parent_node.remove_child(row)
        self.endRemoveRows()
        
        return result
    
    def clear(self) -> None:
        """Очистка дерева"""
        self.beginResetModel()
        self._root = TreeNode("Root")
        self.endResetModel()
    
    def get_node_data(self, index: QModelIndex) -> Any:
        """Получить данные узла по индексу"""
        if not index.isValid():
            return None
        node = index.internalPointer()
        return node.data()
    
    def get_node(self, index: QModelIndex) -> Optional[TreeNode]:
        """Получить узел по индексу"""
        if not index.isValid():
            return None
        return index.internalPointer()
    
    def find_nodes(self, data: Any, role: int = Qt.DisplayRole) -> List[QModelIndex]:
        """Поиск узлов с определенными данными"""
        result = []
        self._find_nodes_recursive(self._root, data, role, result)
        return result
    
    def _find_nodes_recursive(self, node: TreeNode, data: Any, role: int, result: List[QModelIndex]) -> None:
        if node.data() == data:
            # Создаем индекс для найденного узла
            if node.parent():
                index = self.createIndex(node.row(), 0, node)
                result.append(index)
        
        for i in range(node.child_count()):
            child = node.child(i)
            self._find_nodes_recursive(child, data, role, result)


class TreeWidget(QWidget):
    """Виджет с TreeView"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Создаем основной layout для виджета
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Убираем отступы, если нужно
        
        # Создаем модель
        self.model = TreeModel("Root")
        self.model.set_columns(2)  # Две колонки
        
        # Создаем TreeView
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        
        # Настройка TreeView
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setIndentation(20)
        self.tree_view.setExpandsOnDoubleClick(True)
        
        # Добавляем TreeView в layout
        layout.addWidget(self.tree_view)
        
        # Заполняем данными
        self.populate_data()
        
        # Разворачиваем все узлы
        self.tree_view.expandAll()
        
        # Настройка колонок
        self.tree_view.header().setStretchLastSection(True)
    
    def populate_data(self):
        """Заполнение данными"""
        root = self.model.index(0, 0)
        
        # Добавляем узлы первого уровня
        node1 = self.model.add_node(["Фрукты", "Описание фруктов"], root)
        node2 = self.model.add_node(["Овощи", "Описание овощей"], root)
        node3 = self.model.add_node(["Ягоды", "Описание ягод"], root)
        
        # Добавляем подузлы для "Фрукты"
        self.model.add_node(["Яблоко", "Красное"], node1)
        self.model.add_node(["Банан", "Желтый"], node1)
        self.model.add_node(["Апельсин", "Оранжевый"], node1)
        
        # Добавляем подузлы для "Овощи"
        self.model.add_node(["Морковь", "Оранжевая"], node2)
        self.model.add_node(["Помидор", "Красный"], node2)
        self.model.add_node(["Огурец", "Зеленый"], node2)
        
        # Добавляем подузлы для "Ягоды"
        self.model.add_node(["Клубника", "Красная"], node3)
        self.model.add_node(["Черника", "Синяя"], node3)
        self.model.add_node(["Малина", "Красная"], node3)
        
        # Добавляем глубокий уровень
        apple_node = self.model.index(0, 0, node1)
        self.model.add_node(["Гренни Смит", "Зеленое"], apple_node)
        self.model.add_node(["Голден", "Желтое"], apple_node)

