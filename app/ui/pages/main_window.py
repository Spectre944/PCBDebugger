# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'untitledmutBiua.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QMainWindow, QMenu, QMenuBar,
    QSizePolicy, QStatusBar, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(852, 611)
        self.action_openDigagnostic = QAction(MainWindow)
        self.action_openDigagnostic.setObjectName(u"action_openDigagnostic")
        self.actionStay_On_Top = QAction(MainWindow)
        self.actionStay_On_Top.setObjectName(u"actionStay_On_Top")
        self.action_saveDiagnostic = QAction(MainWindow)
        self.action_saveDiagnostic.setObjectName(u"action_saveDiagnostic")
        self.action_connectKiCAD = QAction(MainWindow)
        self.action_connectKiCAD.setObjectName(u"action_connectKiCAD")
        self.action_debug_start_pause = QAction(MainWindow)
        self.action_debug_start_pause.setObjectName(u"action_debug_start_pause")
        self.action_2 = QAction(MainWindow)
        self.action_2.setObjectName(u"action_2")
        self.action_3 = QAction(MainWindow)
        self.action_3.setObjectName(u"action_3")
        self.action_debug_nextStep = QAction(MainWindow)
        self.action_debug_nextStep.setObjectName(u"action_debug_nextStep")
        self.action_debug_stop = QAction(MainWindow)
        self.action_debug_stop.setObjectName(u"action_debug_stop")
        self.action_debug_restart = QAction(MainWindow)
        self.action_debug_restart.setObjectName(u"action_debug_restart")
        self.action_mainPage = QAction(MainWindow)
        self.action_mainPage.setObjectName(u"action_mainPage")
        self.action_settingsPage = QAction(MainWindow)
        self.action_settingsPage.setObjectName(u"action_settingsPage")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 852, 33))
        self.menu = QMenu(self.menubar)
        self.menu.setObjectName(u"menu")
        self.menu_view = QMenu(self.menubar)
        self.menu_view.setObjectName(u"menu_view")
        self.menuKiCAD = QMenu(self.menubar)
        self.menuKiCAD.setObjectName(u"menuKiCAD")
        self.menu_debug = QMenu(self.menubar)
        self.menu_debug.setObjectName(u"menu_debug")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menu.menuAction())
        self.menubar.addAction(self.menu_view.menuAction())
        self.menubar.addAction(self.menu_debug.menuAction())
        self.menubar.addAction(self.menuKiCAD.menuAction())
        self.menu.addAction(self.action_openDigagnostic)
        self.menu.addAction(self.action_saveDiagnostic)
        self.menu_view.addAction(self.actionStay_On_Top)
        self.menu_view.addSeparator()
        self.menu_view.addAction(self.action_mainPage)
        self.menu_view.addAction(self.action_settingsPage)
        self.menuKiCAD.addAction(self.action_connectKiCAD)
        self.menu_debug.addAction(self.action_debug_start_pause)
        self.menu_debug.addAction(self.action_debug_nextStep)
        self.menu_debug.addAction(self.action_debug_stop)
        self.menu_debug.addAction(self.action_debug_restart)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.action_openDigagnostic.setText(QCoreApplication.translate("MainWindow", u"\u0412\u0456\u0434\u043a\u0440\u0438\u0442\u0438", None))
        self.actionStay_On_Top.setText(QCoreApplication.translate("MainWindow", u"Stay On Top", None))
#if QT_CONFIG(shortcut)
        self.actionStay_On_Top.setShortcut(QCoreApplication.translate("MainWindow", u"F11", None))
#endif // QT_CONFIG(shortcut)
        self.action_saveDiagnostic.setText(QCoreApplication.translate("MainWindow", u"\u0417\u0431\u0435\u0440\u0435\u0433\u0442\u0438", None))
        self.action_connectKiCAD.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0456\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u0438\u0441\u044c", None))
        self.action_debug_start_pause.setText(QCoreApplication.translate("MainWindow", u"\u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0438", None))
#if QT_CONFIG(shortcut)
        self.action_debug_start_pause.setShortcut(QCoreApplication.translate("MainWindow", u"F5", None))
#endif // QT_CONFIG(shortcut)
        self.action_2.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0430\u0443\u0437\u0430", None))
        self.action_3.setText(QCoreApplication.translate("MainWindow", u"\u0417\u0443\u043f\u0438\u043d\u0438\u0442\u0438", None))
        self.action_debug_nextStep.setText(QCoreApplication.translate("MainWindow", u"\u041d\u0430\u0441\u0442\u0443\u043f\u043d\u0438\u0439 \u043a\u0440\u043e\u043a", None))
#if QT_CONFIG(shortcut)
        self.action_debug_nextStep.setShortcut(QCoreApplication.translate("MainWindow", u"F10", None))
#endif // QT_CONFIG(shortcut)
        self.action_debug_stop.setText(QCoreApplication.translate("MainWindow", u"\u0417\u0443\u043f\u0438\u043d\u0438\u0442\u0438", None))
#if QT_CONFIG(shortcut)
        self.action_debug_stop.setShortcut(QCoreApplication.translate("MainWindow", u"Shift+F5", None))
#endif // QT_CONFIG(shortcut)
        self.action_debug_restart.setText(QCoreApplication.translate("MainWindow", u"\u0420\u0435\u0441\u0442\u0430\u0440\u0442", None))
#if QT_CONFIG(shortcut)
        self.action_debug_restart.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Shift+F5", None))
#endif // QT_CONFIG(shortcut)
        self.action_mainPage.setText(QCoreApplication.translate("MainWindow", u"\u0413\u043e\u043b\u043e\u0432\u043d\u0430 \u0441\u0442\u043e\u0440\u0456\u043d\u043a\u0430", None))
        self.action_settingsPage.setText(QCoreApplication.translate("MainWindow", u"\u041d\u0430\u043b\u0430\u0448\u0442\u0443\u0432\u0430\u043d\u043d\u044f", None))
        self.menu.setTitle(QCoreApplication.translate("MainWindow", u"\u0424\u0430\u0439\u043b", None))
        self.menu_view.setTitle(QCoreApplication.translate("MainWindow", u"\u0412\u0438\u0433\u043b\u044f\u0434", None))
        self.menuKiCAD.setTitle(QCoreApplication.translate("MainWindow", u"KiCAD", None))
        self.menu_debug.setTitle(QCoreApplication.translate("MainWindow", u"\u0414\u0435\u0431\u0430\u0433", None))
    # retranslateUi

