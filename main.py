import sys
import ctypes

# import assets.rc_res

from PySide6.QtCore import QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow

# Изменение иконки на панеле задач Windows
if sys.platform == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.yourcompany.appname")

app = QApplication(sys.argv)
app.setWindowIcon(QIcon(":/icons/svg/custom/PCB_icon.svg"))
window = MainWindow()

translator = QTranslator(app) 
if translator.load(":/locale/qtbase_uk.qm"):
    app.installTranslator(translator)
else:
    print("Fail to load default translation")

window.show()
app.exec()