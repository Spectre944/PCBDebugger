from app.ui.widgets.board_widget import BoardWidget
from app.ui.widgets.tree_widget import TreeModel, TreeWidget

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QFileDialog, QMessageBox, QPushButton, QLabel,
    QSizePolicy, QSplitter
)
from PySide6.QtGui import (
    QPixmap, QColor, QUndoStack, QShortcut, QKeySequence
)
from PySide6.QtCore import Qt, QTimer, Signal

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PCB Debugger")
        # self.setMinimumSize(1000, 640)
        self.resize(1280, 800)
        self.setStyleSheet("QMainWindow { background:#0e1120; }")

        # self.board = BoardWidget()
        # self.setCentralWidget(self.board)

        self.treeWidget = TreeWidget()
        self.setCentralWidget(self.treeWidget)