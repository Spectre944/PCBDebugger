# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainWindowQGhsTJ.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHeaderView,
    QLabel, QSizePolicy, QSpacerItem, QTextEdit,
    QTreeView, QVBoxLayout, QWidget)

class Ui_mainPage(object):
    def setupUi(self, mainPage):
        if not mainPage.objectName():
            mainPage.setObjectName(u"mainPage")
        mainPage.resize(799, 479)
        self.gridLayout = QGridLayout(mainPage)
        self.gridLayout.setObjectName(u"gridLayout")
        self.textEditLog = QTextEdit(mainPage)
        self.textEditLog.setObjectName(u"textEditLog")
        self.textEditLog.setTabChangesFocus(True)

        self.gridLayout.addWidget(self.textEditLog, 1, 1, 1, 1)

        self.frameInfo = QFrame(mainPage)
        self.frameInfo.setObjectName(u"frameInfo")
        self.frameInfo.setMinimumSize(QSize(0, 200))
        self.frameInfo.setMaximumSize(QSize(16777215, 200))
        self.frameInfo.setFrameShape(QFrame.Shape.StyledPanel)
        self.frameInfo.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout = QVBoxLayout(self.frameInfo)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(10, 10, 10, 10)
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_2 = QLabel(self.frameInfo)
        self.label_2.setObjectName(u"label_2")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)

        self.gridLayout_2.addWidget(self.label_2, 1, 0, 1, 1)

        self.label_3 = QLabel(self.frameInfo)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout_2.addWidget(self.label_3, 3, 0, 1, 1)

        self.label = QLabel(self.frameInfo)
        self.label.setObjectName(u"label")
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 6, 0, 1, 1)

        self.label_objSelect = QLabel(self.frameInfo)
        self.label_objSelect.setObjectName(u"label_objSelect")
        self.label_objSelect.setWordWrap(True)

        self.gridLayout_2.addWidget(self.label_objSelect, 7, 0, 1, 2)

        self.label_debug = QLabel(self.frameInfo)
        self.label_debug.setObjectName(u"label_debug")
        self.label_debug.setWordWrap(True)

        self.gridLayout_2.addWidget(self.label_debug, 3, 1, 1, 1)

        self.label_4 = QLabel(self.frameInfo)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout_2.addWidget(self.label_4, 4, 0, 1, 1)

        self.label_hint = QLabel(self.frameInfo)
        self.label_hint.setObjectName(u"label_hint")
        self.label_hint.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self.label_hint.setWordWrap(True)

        self.gridLayout_2.addWidget(self.label_hint, 1, 1, 1, 1)

        self.line = QFrame(self.frameInfo)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line, 2, 0, 1, 2)

        self.label_description = QLabel(self.frameInfo)
        self.label_description.setObjectName(u"label_description")
        self.label_description.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self.label_description.setWordWrap(True)

        self.gridLayout_2.addWidget(self.label_description, 0, 1, 1, 1)

        self.label_debug_hint = QLabel(self.frameInfo)
        self.label_debug_hint.setObjectName(u"label_debug_hint")
        self.label_debug_hint.setWordWrap(True)

        self.gridLayout_2.addWidget(self.label_debug_hint, 4, 1, 1, 1)

        self.line_2 = QFrame(self.frameInfo)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line_2, 5, 0, 1, 2)


        self.verticalLayout.addLayout(self.gridLayout_2)


        self.gridLayout.addWidget(self.frameInfo, 0, 1, 1, 1)

        self.treeViewTaskList = QTreeView(mainPage)
        self.treeViewTaskList.setObjectName(u"treeViewTaskList")

        self.gridLayout.addWidget(self.treeViewTaskList, 0, 0, 2, 1)


        self.retranslateUi(mainPage)

        QMetaObject.connectSlotsByName(mainPage)
    # setupUi

    def retranslateUi(self, mainPage):
        mainPage.setWindowTitle(QCoreApplication.translate("mainPage", u"MainPage", None))
        self.textEditLog.setPlaceholderText(QCoreApplication.translate("mainPage", u"\u041b\u043e\u0433\u0443\u0432\u0430\u043d\u043d\u044f \u043f\u0435\u0440\u0435\u0432\u0456\u0440\u043a\u0438", None))
        self.label_2.setText(QCoreApplication.translate("mainPage", u"\u041f\u0456\u0434\u043a\u0430\u0437\u043a\u0430:", None))
        self.label_3.setText(QCoreApplication.translate("mainPage", u"\u0412\u0456\u0434\u043b\u0430\u0434\u043a\u0430:", None))
        self.label.setText(QCoreApplication.translate("mainPage", u"\u041e\u043f\u0438\u0441 \u043f\u0435\u0440\u0435\u0432\u0456\u0440\u043a\u0438: ", None))
        self.label_objSelect.setText(QCoreApplication.translate("mainPage", u"\u041e\u0431\u0440\u0430\u043d\u043e nets:", None))
        self.label_debug.setText(QCoreApplication.translate("mainPage", u"-", None))
        self.label_4.setText(QCoreApplication.translate("mainPage", u"\u041f\u0456\u0434\u043a\u0430\u0437\u043a\u0430:", None))
        self.label_hint.setText(QCoreApplication.translate("mainPage", u"-", None))
        self.label_description.setText(QCoreApplication.translate("mainPage", u"-", None))
        self.label_debug_hint.setText(QCoreApplication.translate("mainPage", u"-", None))
    # retranslateUi

