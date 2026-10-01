# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'settingPagehpVGnO.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
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
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_settingsPage(object):
    def setupUi(self, settingsPage):
        if not settingsPage.objectName():
            settingsPage.setObjectName(u"settingsPage")
        settingsPage.resize(878, 1009)
        self.verticalLayout = QVBoxLayout(settingsPage)
        self.verticalLayout.setSpacing(100)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(100, 20, 100, 20)
        self.frame = QFrame(settingsPage)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.NoFrame)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.labelSerialSettingName = QLabel(self.frame)
        self.labelSerialSettingName.setObjectName(u"labelSerialSettingName")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.labelSerialSettingName.sizePolicy().hasHeightForWidth())
        self.labelSerialSettingName.setSizePolicy(sizePolicy)

        self.verticalLayout_2.addWidget(self.labelSerialSettingName)

        self.frame_3 = QFrame(self.frame)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_3)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.pushButton_bt_settings = QPushButton(self.frame_3)
        self.pushButton_bt_settings.setObjectName(u"pushButton_bt_settings")
        sizePolicy.setHeightForWidth(self.pushButton_bt_settings.sizePolicy().hasHeightForWidth())
        self.pushButton_bt_settings.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.pushButton_bt_settings, 0, 4, 1, 1)

        self.label_4 = QLabel(self.frame_3)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)

        self.label_3 = QLabel(self.frame_3)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)

        self.label = QLabel(self.frame_3)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 0, 1, 1, 1)

        self.label_2 = QLabel(self.frame_3)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.comboBox_bt_port_name = QComboBox(self.frame_3)
        self.comboBox_bt_port_name.setObjectName(u"comboBox_bt_port_name")

        self.gridLayout.addWidget(self.comboBox_bt_port_name, 0, 3, 1, 1)

        self.pushButton_bt_connect = QPushButton(self.frame_3)
        self.pushButton_bt_connect.setObjectName(u"pushButton_bt_connect")

        self.gridLayout.addWidget(self.pushButton_bt_connect, 0, 2, 1, 1)

        self.label_5 = QLabel(self.frame_3)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout.addWidget(self.label_5, 4, 0, 1, 1)

        self.comboBox_bt_baudrate = QComboBox(self.frame_3)
        self.comboBox_bt_baudrate.setObjectName(u"comboBox_bt_baudrate")

        self.gridLayout.addWidget(self.comboBox_bt_baudrate, 1, 3, 1, 2)

        self.comboBox_bt_stop_bit = QComboBox(self.frame_3)
        self.comboBox_bt_stop_bit.setObjectName(u"comboBox_bt_stop_bit")

        self.gridLayout.addWidget(self.comboBox_bt_stop_bit, 2, 3, 1, 2)

        self.comboBox_bt_parity = QComboBox(self.frame_3)
        self.comboBox_bt_parity.setObjectName(u"comboBox_bt_parity")

        self.gridLayout.addWidget(self.comboBox_bt_parity, 3, 3, 1, 2)

        self.comboBox_bt_flow_control = QComboBox(self.frame_3)
        self.comboBox_bt_flow_control.setObjectName(u"comboBox_bt_flow_control")

        self.gridLayout.addWidget(self.comboBox_bt_flow_control, 4, 3, 1, 2)


        self.verticalLayout_3.addLayout(self.gridLayout)

        self.line = QFrame(self.frame_3)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_3.addWidget(self.line)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.pushButton_rs_settings = QPushButton(self.frame_3)
        self.pushButton_rs_settings.setObjectName(u"pushButton_rs_settings")
        sizePolicy.setHeightForWidth(self.pushButton_rs_settings.sizePolicy().hasHeightForWidth())
        self.pushButton_rs_settings.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.pushButton_rs_settings, 0, 4, 1, 1)

        self.label_6 = QLabel(self.frame_3)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout_2.addWidget(self.label_6, 3, 0, 1, 1)

        self.label_7 = QLabel(self.frame_3)
        self.label_7.setObjectName(u"label_7")

        self.gridLayout_2.addWidget(self.label_7, 2, 0, 1, 1)

        self.label_8 = QLabel(self.frame_3)
        self.label_8.setObjectName(u"label_8")

        self.gridLayout_2.addWidget(self.label_8, 0, 0, 1, 1)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_2.addItem(self.horizontalSpacer_2, 0, 1, 1, 1)

        self.label_9 = QLabel(self.frame_3)
        self.label_9.setObjectName(u"label_9")

        self.gridLayout_2.addWidget(self.label_9, 1, 0, 1, 1)

        self.comboBox_rs_port_name = QComboBox(self.frame_3)
        self.comboBox_rs_port_name.setObjectName(u"comboBox_rs_port_name")

        self.gridLayout_2.addWidget(self.comboBox_rs_port_name, 0, 3, 1, 1)

        self.pushButton_rs_connect = QPushButton(self.frame_3)
        self.pushButton_rs_connect.setObjectName(u"pushButton_rs_connect")

        self.gridLayout_2.addWidget(self.pushButton_rs_connect, 0, 2, 1, 1)

        self.label_10 = QLabel(self.frame_3)
        self.label_10.setObjectName(u"label_10")

        self.gridLayout_2.addWidget(self.label_10, 4, 0, 1, 1)

        self.comboBox_rs_baudrate = QComboBox(self.frame_3)
        self.comboBox_rs_baudrate.setObjectName(u"comboBox_rs_baudrate")

        self.gridLayout_2.addWidget(self.comboBox_rs_baudrate, 1, 3, 1, 2)

        self.comboBox_rs_stop_bit = QComboBox(self.frame_3)
        self.comboBox_rs_stop_bit.setObjectName(u"comboBox_rs_stop_bit")

        self.gridLayout_2.addWidget(self.comboBox_rs_stop_bit, 2, 3, 1, 2)

        self.comboBox_rs_parity = QComboBox(self.frame_3)
        self.comboBox_rs_parity.setObjectName(u"comboBox_rs_parity")

        self.gridLayout_2.addWidget(self.comboBox_rs_parity, 3, 3, 1, 2)

        self.comboBox_rs_flow_control = QComboBox(self.frame_3)
        self.comboBox_rs_flow_control.setObjectName(u"comboBox_rs_flow_control")

        self.gridLayout_2.addWidget(self.comboBox_rs_flow_control, 4, 3, 1, 2)


        self.verticalLayout_3.addLayout(self.gridLayout_2)


        self.verticalLayout_2.addWidget(self.frame_3)


        self.verticalLayout.addWidget(self.frame)

        self.frame_2 = QFrame(settingsPage)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMinimumSize(QSize(0, 200))
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)

        self.verticalLayout.addWidget(self.frame_2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(settingsPage)

        QMetaObject.connectSlotsByName(settingsPage)
    # setupUi

    def retranslateUi(self, settingsPage):
        settingsPage.setWindowTitle(QCoreApplication.translate("settingsPage", u"Form", None))
        self.labelSerialSettingName.setText(QCoreApplication.translate("settingsPage", u"\u041d\u0430\u043b\u0430\u0448\u0442\u0443\u0432\u0430\u043d\u043d\u044f \u043f\u043e\u0440\u0442\u0456\u0432", None))
        self.pushButton_bt_settings.setText(QCoreApplication.translate("settingsPage", u"...", None))
        self.label_4.setText(QCoreApplication.translate("settingsPage", u"Parity", None))
        self.label_3.setText(QCoreApplication.translate("settingsPage", u"Stop Bit", None))
        self.label.setText(QCoreApplication.translate("settingsPage", u"Bluetooth", None))
        self.label_2.setText(QCoreApplication.translate("settingsPage", u"Baudrate", None))
        self.pushButton_bt_connect.setText(QCoreApplication.translate("settingsPage", u"\u041f\u0456\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u0438\u0441\u044c", None))
        self.label_5.setText(QCoreApplication.translate("settingsPage", u"Flow Control", None))
        self.pushButton_rs_settings.setText(QCoreApplication.translate("settingsPage", u"...", None))
        self.label_6.setText(QCoreApplication.translate("settingsPage", u"Parity", None))
        self.label_7.setText(QCoreApplication.translate("settingsPage", u"Stop Bit", None))
        self.label_8.setText(QCoreApplication.translate("settingsPage", u"RS", None))
        self.label_9.setText(QCoreApplication.translate("settingsPage", u"Baudrate", None))
        self.pushButton_rs_connect.setText(QCoreApplication.translate("settingsPage", u"\u041f\u0456\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u0438\u0441\u044c", None))
        self.label_10.setText(QCoreApplication.translate("settingsPage", u"Flow Control", None))
    # retranslateUi

