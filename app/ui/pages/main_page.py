# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'untitledhhKZKD.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QHeaderView, QSizePolicy,
    QTextEdit, QTreeView, QWidget)

class Ui_mainPage(object):
    def setupUi(self, mainPage):
        if not mainPage.objectName():
            mainPage.setObjectName(u"mainPage")
        mainPage.resize(850, 539)
        self.gridLayout = QGridLayout(mainPage)
        self.gridLayout.setObjectName(u"gridLayout")
        self.textEditLog = QTextEdit(mainPage)
        self.textEditLog.setObjectName(u"textEditLog")

        self.gridLayout.addWidget(self.textEditLog, 1, 1, 1, 1)

        self.textEditComment = QTextEdit(mainPage)
        self.textEditComment.setObjectName(u"textEditComment")
        self.textEditComment.setMaximumSize(QSize(16777215, 300))

        self.gridLayout.addWidget(self.textEditComment, 0, 1, 1, 1)

        self.treeViewTaskList = QTreeView(mainPage)
        self.treeViewTaskList.setObjectName(u"treeViewTaskList")

        self.gridLayout.addWidget(self.treeViewTaskList, 0, 0, 2, 1)


        self.retranslateUi(mainPage)

        QMetaObject.connectSlotsByName(mainPage)
    # setupUi

    def retranslateUi(self, mainPage):
        mainPage.setWindowTitle(QCoreApplication.translate("mainPage", u"MainPage", None))
        self.textEditLog.setPlaceholderText(QCoreApplication.translate("mainPage", u"\u041b\u043e\u0433\u0443\u0432\u0430\u043d\u043d\u044f \u043f\u0435\u0440\u0435\u0432\u0456\u0440\u043a\u0438", None))
        self.textEditComment.setPlaceholderText(QCoreApplication.translate("mainPage", u"\u041e\u043f\u0438\u0441 \u0432 \u0434\u043e\u0432\u0456\u043b\u044c\u043d\u043e\u043c\u0443 \u0444\u043e\u0440\u043c\u0430\u0442\u0456 \u043f\u043e\u043c\u0438\u043b\u043a\u0438 \u0449\u043e \u0432\u0438\u043d\u0438\u043a\u043b\u0430", None))
    # retranslateUi

