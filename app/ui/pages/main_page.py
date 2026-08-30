# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainWindowISCbFr.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QSizePolicy,
    QTextEdit, QTreeView, QVBoxLayout, QWidget)

class Ui_mainPage(object):
    def setupUi(self, mainPage):
        if not mainPage.objectName():
            mainPage.setObjectName(u"mainPage")
        mainPage.resize(851, 471)
        self.gridLayout = QGridLayout(mainPage)
        self.gridLayout.setObjectName(u"gridLayout")
        self.treeViewTaskList = QTreeView(mainPage)
        self.treeViewTaskList.setObjectName(u"treeViewTaskList")
        self.treeViewTaskList.setMinimumSize(QSize(550, 0))

        self.gridLayout.addWidget(self.treeViewTaskList, 0, 0, 1, 1)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.frame = QFrame(mainPage)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(10, 10, 10, 10)
        self.gridLayout_3 = QGridLayout()
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.label_debugOverallInfo = QLabel(self.frame)
        self.label_debugOverallInfo.setObjectName(u"label_debugOverallInfo")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_debugOverallInfo.sizePolicy().hasHeightForWidth())
        self.label_debugOverallInfo.setSizePolicy(sizePolicy)

        self.gridLayout_3.addWidget(self.label_debugOverallInfo, 3, 1, 1, 1)

        self.label_debugStatus = QLabel(self.frame)
        self.label_debugStatus.setObjectName(u"label_debugStatus")
        sizePolicy.setHeightForWidth(self.label_debugStatus.sizePolicy().hasHeightForWidth())
        self.label_debugStatus.setSizePolicy(sizePolicy)

        self.gridLayout_3.addWidget(self.label_debugStatus, 2, 1, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_7 = QLabel(self.frame)
        self.label_7.setObjectName(u"label_7")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_7.sizePolicy().hasHeightForWidth())
        self.label_7.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.label_7)

        self.pushButtonDebugStartStop = QPushButton(self.frame)
        self.pushButtonDebugStartStop.setObjectName(u"pushButtonDebugStartStop")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.pushButtonDebugStartStop.sizePolicy().hasHeightForWidth())
        self.pushButtonDebugStartStop.setSizePolicy(sizePolicy2)
        self.pushButtonDebugStartStop.setMinimumSize(QSize(40, 40))
        self.pushButtonDebugStartStop.setMaximumSize(QSize(40, 40))
        icon = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart))
        self.pushButtonDebugStartStop.setIcon(icon)

        self.horizontalLayout.addWidget(self.pushButtonDebugStartStop)

        self.pushButtonDebugNextStep = QPushButton(self.frame)
        self.pushButtonDebugNextStep.setObjectName(u"pushButtonDebugNextStep")
        sizePolicy2.setHeightForWidth(self.pushButtonDebugNextStep.sizePolicy().hasHeightForWidth())
        self.pushButtonDebugNextStep.setSizePolicy(sizePolicy2)
        self.pushButtonDebugNextStep.setMinimumSize(QSize(40, 40))
        self.pushButtonDebugNextStep.setMaximumSize(QSize(40, 40))
        icon1 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaSkipForward))
        self.pushButtonDebugNextStep.setIcon(icon1)

        self.horizontalLayout.addWidget(self.pushButtonDebugNextStep)

        self.pushButtonDebugRestart = QPushButton(self.frame)
        self.pushButtonDebugRestart.setObjectName(u"pushButtonDebugRestart")
        sizePolicy2.setHeightForWidth(self.pushButtonDebugRestart.sizePolicy().hasHeightForWidth())
        self.pushButtonDebugRestart.setSizePolicy(sizePolicy2)
        self.pushButtonDebugRestart.setMinimumSize(QSize(40, 40))
        self.pushButtonDebugRestart.setMaximumSize(QSize(40, 40))
        icon2 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.ViewRestore))
        self.pushButtonDebugRestart.setIcon(icon2)

        self.horizontalLayout.addWidget(self.pushButtonDebugRestart)

        self.pushButtonDebugStop = QPushButton(self.frame)
        self.pushButtonDebugStop.setObjectName(u"pushButtonDebugStop")
        sizePolicy2.setHeightForWidth(self.pushButtonDebugStop.sizePolicy().hasHeightForWidth())
        self.pushButtonDebugStop.setSizePolicy(sizePolicy2)
        self.pushButtonDebugStop.setMinimumSize(QSize(40, 40))
        self.pushButtonDebugStop.setMaximumSize(QSize(40, 40))
        icon3 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStop))
        self.pushButtonDebugStop.setIcon(icon3)

        self.horizontalLayout.addWidget(self.pushButtonDebugStop)


        self.gridLayout_3.addLayout(self.horizontalLayout, 0, 0, 1, 2)

        self.label_6 = QLabel(self.frame)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout_3.addWidget(self.label_6, 2, 0, 1, 1)

        self.label_5 = QLabel(self.frame)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout_3.addWidget(self.label_5, 3, 0, 1, 1)

        self.line_3 = QFrame(self.frame)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_3.addWidget(self.line_3, 1, 0, 1, 2)


        self.verticalLayout_2.addLayout(self.gridLayout_3)


        self.verticalLayout_3.addWidget(self.frame)

        self.textEditLog = QTextEdit(mainPage)
        self.textEditLog.setObjectName(u"textEditLog")
        self.textEditLog.setTabChangesFocus(True)

        self.verticalLayout_3.addWidget(self.textEditLog)


        self.gridLayout.addLayout(self.verticalLayout_3, 0, 1, 2, 1)

        self.frameInfo = QFrame(mainPage)
        self.frameInfo.setObjectName(u"frameInfo")
        self.frameInfo.setMinimumSize(QSize(0, 0))
        self.frameInfo.setMaximumSize(QSize(16777215, 16777215))
        self.frameInfo.setFrameShape(QFrame.Shape.StyledPanel)
        self.frameInfo.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout = QVBoxLayout(self.frameInfo)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(10, 10, 10, 10)
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_description = QLabel(self.frameInfo)
        self.label_description.setObjectName(u"label_description")
        self.label_description.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self.label_description.setWordWrap(True)

        self.gridLayout_2.addWidget(self.label_description, 0, 1, 1, 1)

        self.label_2 = QLabel(self.frameInfo)
        self.label_2.setObjectName(u"label_2")
        sizePolicy1.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy1)
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)

        self.gridLayout_2.addWidget(self.label_2, 1, 0, 1, 1)

        self.label = QLabel(self.frameInfo)
        self.label.setObjectName(u"label")
        sizePolicy1.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy1)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.label_hint = QLabel(self.frameInfo)
        self.label_hint.setObjectName(u"label_hint")
        self.label_hint.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self.label_hint.setWordWrap(True)

        self.gridLayout_2.addWidget(self.label_hint, 1, 1, 1, 1)

        self.line_2 = QFrame(self.frameInfo)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line_2, 2, 0, 1, 2)

        self.label_objSelect = QLabel(self.frameInfo)
        self.label_objSelect.setObjectName(u"label_objSelect")
        self.label_objSelect.setWordWrap(True)

        self.gridLayout_2.addWidget(self.label_objSelect, 3, 0, 1, 2)


        self.verticalLayout.addLayout(self.gridLayout_2)


        self.gridLayout.addWidget(self.frameInfo, 1, 0, 1, 1)


        self.retranslateUi(mainPage)

        QMetaObject.connectSlotsByName(mainPage)
    # setupUi

    def retranslateUi(self, mainPage):
        mainPage.setWindowTitle(QCoreApplication.translate("mainPage", u"MainPage", None))
        self.label_debugOverallInfo.setText(QCoreApplication.translate("mainPage", u"-", None))
        self.label_debugStatus.setText(QCoreApplication.translate("mainPage", u"-", None))
        self.label_7.setText(QCoreApplication.translate("mainPage", u"\u0423\u043f\u0440\u0430\u0432\u043b\u0456\u043d\u043d\u044f", None))
        self.pushButtonDebugStartStop.setText("")
        self.pushButtonDebugNextStep.setText("")
        self.pushButtonDebugRestart.setText("")
        self.pushButtonDebugStop.setText("")
        self.label_6.setText(QCoreApplication.translate("mainPage", u"\u0421\u0442\u0430\u0442\u0443\u0441:", None))
        self.label_5.setText(QCoreApplication.translate("mainPage", u"\u041f\u0440\u043e\u0439\u0434\u0435\u043d\u043e:", None))
        self.textEditLog.setPlaceholderText(QCoreApplication.translate("mainPage", u"\u041b\u043e\u0433\u0443\u0432\u0430\u043d\u043d\u044f \u043f\u0435\u0440\u0435\u0432\u0456\u0440\u043a\u0438", None))
        self.label_description.setText(QCoreApplication.translate("mainPage", u"-", None))
        self.label_2.setText(QCoreApplication.translate("mainPage", u"\u041f\u0456\u0434\u043a\u0430\u0437\u043a\u0430:", None))
        self.label.setText(QCoreApplication.translate("mainPage", u"\u041e\u043f\u0438\u0441 \u043f\u0435\u0440\u0435\u0432\u0456\u0440\u043a\u0438: ", None))
        self.label_hint.setText(QCoreApplication.translate("mainPage", u"-", None))
        self.label_objSelect.setText(QCoreApplication.translate("mainPage", u"\u041e\u0431\u0440\u0430\u043d\u043e nets:", None))
    # retranslateUi

