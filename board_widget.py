"""
board_widget.py — упрощённый виджет просмотра PCB-скана.

Возможности:
  • зум колесом мыши
  • пан правой кнопкой мыши или Space
  • drag&drop изображения (просто перетащите файл в виджет)

Импорт в MainWindow:

    from board_widget import BoardWidget

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            ...
            self.board = BoardWidget()
            self.setCentralWidget(self.board)
"""
from typing import Optional

from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPixmapItem
from PySide6.QtGui import QBrush, QColor, QPainter, QCursor, QKeyEvent, QPixmap
from PySide6.QtCore import Qt, QPoint, QRectF


# ─────────────────────────────────────────────────────────────────────
# Сцена: хранит только фоновое изображение
# ─────────────────────────────────────────────────────────────────────
class BoardScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self._bg: Optional[QGraphicsPixmapItem] = None

    def set_background(self, pixmap: QPixmap):
        if self._bg:
            self.removeItem(self._bg)
        self._bg = self.addPixmap(pixmap)
        self._bg.setZValue(-10)
        self.setSceneRect(QRectF(pixmap.rect()))

    def has_background(self) -> bool:
        return self._bg is not None


# ─────────────────────────────────────────────────────────────────────
# View: зум + пан
# ─────────────────────────────────────────────────────────────────────
class BoardView(QGraphicsView):
    def __init__(self, scene: BoardScene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor("#111218")))
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        self._panning = False
        self._pan_start = QPoint()
        self._space = False

    # ── Pan ───────────────────────────────────────────────────────────

    def _begin_pan(self, pos: QPoint):
        self._panning = True
        self._pan_start = pos
        self.viewport().setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

    def _end_pan(self):
        self._panning = False
        self.viewport().setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    # ── Events ────────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton:
            self._begin_pan(e.pos())
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._panning:
            d = e.pos() - self._pan_start
            self._pan_start = e.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton and self._panning:
            self._end_pan()
            return
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() == Qt.Key.Key_Space and not e.isAutoRepeat():
            self._space = True
            if not self._panning:
                self._begin_pan(self.mapFromGlobal(QCursor.pos()))
            e.accept()
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e: QKeyEvent):
        if e.key() == Qt.Key.Key_Space and not e.isAutoRepeat():
            self._space = False
            if self._panning:
                self._end_pan()
            e.accept()
            return
        super().keyReleaseEvent(e)

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.scale(f, f)

    # ── Public ────────────────────────────────────────────────────────

    def fit(self):
        if self.scene() is not None and not self.scene().sceneRect().isEmpty():
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_in(self):
        self.scale(1.3, 1.3)

    def zoom_out(self):
        self.scale(1 / 1.3, 1 / 1.3)


# ─────────────────────────────────────────────────────────────────────
# Готовый виджет: сцена + вид + drag&drop
# ─────────────────────────────────────────────────────────────────────
class BoardWidget(BoardView):
    """
    Самодостаточный виджет: просто вставьте его в MainWindow.

        self.board = BoardWidget()
        self.setCentralWidget(self.board)

    Перетащите картинку в окно — она станет фоном.
    Либо вызовите board.load_image(path) вручную.
    """

    _IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")

    def __init__(self, parent=None):
        # Ссылка на сцену обязательна: без неё Python может собрать объект
        # как мусор, и self.scene() начнёт возвращать None.
        self._scene = BoardScene()
        super().__init__(self._scene)
        if parent is not None:
            self.setParent(parent)
        self.setAcceptDrops(True)

    # ── Drag & Drop ───────────────────────────────────────────────────

    def dragEnterEvent(self, e):
        if self._is_image_drop(e):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if self._is_image_drop(e):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if not self._is_image_drop(e):
            e.ignore()
            return
        path = e.mimeData().urls()[0].toLocalFile()
        if self.load_image(path):
            e.acceptProposedAction()
        else:
            e.ignore()

    def _is_image_drop(self, e) -> bool:
        if not e.mimeData().hasUrls():
            return False
        url = e.mimeData().urls()[0]
        return url.isLocalFile() and url.toLocalFile().lower().endswith(self._IMAGE_EXTS)

    # ── Public ────────────────────────────────────────────────────────

    def load_image(self, path: str) -> bool:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return False
        self.scene().set_background(pixmap)
        self.fit()
        return True