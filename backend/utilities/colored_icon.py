from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QSize, QByteArray
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette

class IconHelper:
    @staticmethod
    def createThemedIcon(svg_path: str, size: QSize = QSize(24, 24)) -> QIcon:
        # Читаем SVG из ресурсов через QFile
        from PySide6.QtCore import QFile, QIODevice
        file = QFile(svg_path)
        if not file.open(QIODevice.OpenModeFlag.ReadOnly):
            return QIcon()

        svg_data = file.readAll()  # QByteArray
        file.close()

        # Получаем цвет текста из системной палитры
        palette = QApplication.instance().palette()
        text_color = palette.color(QPalette.ColorRole.WindowText)

        # Заменяем currentColor на актуальный цвет
        svg_content = svg_data.toStdString()
        svg_content = svg_content.replace("currentColor", text_color.name())

        # Рендерим SVG через QSvgRenderer — без смазывания
        renderer = QSvgRenderer(QByteArray(svg_content.encode("utf-8")))

        pixmap = QPixmap(size)
        pixmap.fill("transparent")

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)