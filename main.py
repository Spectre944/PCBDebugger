import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("PCB Tracer")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
