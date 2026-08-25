# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'untitledswyDzzy.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QGroupBox, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

class Ui_settingsPage(object):
    def setupUi(self, settingsPage):
        if not settingsPage.objectName():
            settingsPage.setObjectName(u"settingsPage")
        settingsPage.resize(838, 674)
        self.verticalLayout = QVBoxLayout(settingsPage)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.scrollArea = QScrollArea(settingsPage)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 816, 652))
        self.verticalLayout_3 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setSpacing(50)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(100, 20, 100, 20)
        self.groupBoxCOM = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBoxCOM.setObjectName(u"groupBoxCOM")
        self.verticalLayout_4 = QVBoxLayout(self.groupBoxCOM)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.pushButtonConnectBluetooth = QPushButton(self.groupBoxCOM)
        self.pushButtonConnectBluetooth.setObjectName(u"pushButtonConnectBluetooth")

        self.gridLayout.addWidget(self.pushButtonConnectBluetooth, 0, 2, 2, 1)

        self.comboBoxBluetoothCOM = QComboBox(self.groupBoxCOM)
        self.comboBoxBluetoothCOM.setObjectName(u"comboBoxBluetoothCOM")

        self.gridLayout.addWidget(self.comboBoxBluetoothCOM, 1, 0, 1, 1)

        self.label = QLabel(self.groupBoxCOM)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 0, 1, 1, 1)


        self.verticalLayout_4.addLayout(self.gridLayout)

        self.line = QFrame(self.groupBoxCOM)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_4.addWidget(self.line)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.pushButtonConnectRS = QPushButton(self.groupBoxCOM)
        self.pushButtonConnectRS.setObjectName(u"pushButtonConnectRS")

        self.gridLayout_2.addWidget(self.pushButtonConnectRS, 0, 2, 2, 1)

        self.comboBoxRSCOM = QComboBox(self.groupBoxCOM)
        self.comboBoxRSCOM.setObjectName(u"comboBoxRSCOM")

        self.gridLayout_2.addWidget(self.comboBoxRSCOM, 1, 0, 1, 1)

        self.label_2 = QLabel(self.groupBoxCOM)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_2.addWidget(self.label_2, 0, 0, 1, 1)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_2.addItem(self.horizontalSpacer_2, 0, 1, 1, 1)


        self.verticalLayout_4.addLayout(self.gridLayout_2)

        self.line_2 = QFrame(self.groupBoxCOM)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_4.addWidget(self.line_2)


        self.verticalLayout_2.addWidget(self.groupBoxCOM)

        self.groupBox_2 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_2.setObjectName(u"groupBox_2")

        self.verticalLayout_2.addWidget(self.groupBox_2)

        self.pushButton_SaveSettings = QPushButton(self.scrollAreaWidgetContents)
        self.pushButton_SaveSettings.setObjectName(u"pushButton_SaveSettings")

        self.verticalLayout_2.addWidget(self.pushButton_SaveSettings)


        self.verticalLayout_3.addLayout(self.verticalLayout_2)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout.addWidget(self.scrollArea)


        self.retranslateUi(settingsPage)

        QMetaObject.connectSlotsByName(settingsPage)
    # setupUi

    def retranslateUi(self, settingsPage):
        settingsPage.setWindowTitle(QCoreApplication.translate("settingsPage", u"SettingsPage", None))
        self.groupBoxCOM.setTitle(QCoreApplication.translate("settingsPage", u"COM \u043d\u0430\u043b\u0430\u0448\u0442\u0443\u0432\u0430\u043d\u043d\u044f", None))
        self.pushButtonConnectBluetooth.setText(QCoreApplication.translate("settingsPage", u"\u041f\u0456\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u0438", None))
        self.label.setText(QCoreApplication.translate("settingsPage", u"Bluetooth", None))
        self.pushButtonConnectRS.setText(QCoreApplication.translate("settingsPage", u"\u041f\u0456\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u0438", None))
        self.label_2.setText(QCoreApplication.translate("settingsPage", u"RS485", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("settingsPage", u"GroupBox", None))
        self.pushButton_SaveSettings.setText(QCoreApplication.translate("settingsPage", u"\u0417\u0431\u0435\u0440\u0435\u0433\u0442\u0438", None))
    # retranslateUi

