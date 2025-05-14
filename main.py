#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
from datetime import datetime
import serial
import serial.tools.list_ports

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QComboBox, QLineEdit, QFormLayout, 
    QSpinBox, QDoubleSpinBox, QTextEdit, QGroupBox, QFrame, 
    QMessageBox, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QIcon, QPalette

# 导入自定义RFID协议模块
from rfid_protocol import RFIDProtocol

class LogPanel(QTextEdit):
    """日志面板组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        font = QFont("JetBrains Mono", 10)
        self.setFont(font)
        self.setStyleSheet("background-color: #F3F3F3; color: #333333; border-radius: 4px;")
    
    def add_log(self, message):
        """添加日志信息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.append(log_entry)
        # 自动滚动到底部
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


class RFIDReaderThread(QThread):
    """RFID读写器通信线程"""
    
    # 定义信号
    status_changed = pyqtSignal(bool, str)
    data_received = pyqtSignal(dict)
    log_message = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.serial_port = None
        self.is_running = False
        self.port_name = ""
        self.baud_rate = 115200
        self.rfid_protocol = RFIDProtocol()
        
    def connect_reader(self, port_name, baud_rate=115200):
        """连接RFID读写器"""
        try:
            self.port_name = port_name
            self.baud_rate = baud_rate
            
            # 尝试打开串口
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=baud_rate,
                timeout=1
            )
            
            if self.serial_port.is_open:
                self.is_running = True
                # 设置RFID协议模块的串口
                self.rfid_protocol.set_serial(self.serial_port)
                
                self.status_changed.emit(True, f"已连接 {port_name}，波特率 {baud_rate}")
                self.log_message.emit(f"已连接 {port_name}，波特率 {baud_rate}")
                self.start()  # 启动线程
                return True
            else:
                self.status_changed.emit(False, "连接失败")
                self.log_message.emit(f"无法连接到 {port_name}")
                return False
                
        except Exception as e:
            self.status_changed.emit(False, f"连接错误: {str(e)}")
            self.log_message.emit(f"连接错误: {str(e)}")
            return False
            
    def disconnect_reader(self):
        """断开RFID读写器连接"""
        self.is_running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.status_changed.emit(False, "已断开连接")
            self.log_message.emit("已断开读写器连接")
            
    def run(self):
        """线程主循环"""
        while self.is_running:
            # 这里只是示例，实际应用需要根据RFID读写器的协议进行通信
            time.sleep(0.1)
            
    def read_tag(self):
        """读取标签信息"""
        if not self.serial_port or not self.serial_port.is_open:
            self.log_message.emit("读写器未连接，无法读取标签")
            return False
            
        try:
            self.log_message.emit("正在读取标签...")
            
            # 使用RFID协议模块读取标签
            success, result = self.rfid_protocol.read_tag()
            
            if success:
                self.data_received.emit(result)
                self.log_message.emit("成功读取标签内容")
                return True
            else:
                self.log_message.emit(f"读取标签失败: {result}")
                return False
                
        except Exception as e:
            self.log_message.emit(f"读取标签出错: {str(e)}")
            return False
            
    def write_tag(self, data):
        """写入标签信息"""
        if not self.serial_port or not self.serial_port.is_open:
            self.log_message.emit("读写器未连接，无法写入标签")
            return False
            
        try:
            self.log_message.emit("正在写入标签...")
            
            # 使用RFID协议模块写入标签
            success, message = self.rfid_protocol.write_tag(data)
            
            if success:
                self.log_message.emit(message)
                return True
            else:
                self.log_message.emit(f"写入标签失败: {message}")
                return False
                
        except Exception as e:
            self.log_message.emit(f"写入标签出错: {str(e)}")
            return False


class RFIDReaderApp(QMainWindow):
    """RFID读写器应用主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 设置窗口属性
        self.setWindowTitle("RFID 读写器管理软件")
        self.setMinimumSize(1000, 700)
        self.resize(1440, 900)
        
        # 初始化RFID读写器线程
        self.reader_thread = RFIDReaderThread()
        self.reader_thread.status_changed.connect(self.update_status)
        self.reader_thread.data_received.connect(self.update_form_data)
        self.reader_thread.log_message.connect(self.add_log)
        
        # 设置主界面
        self.setup_ui()
        
    def setup_ui(self):
        """设置用户界面"""
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 顶部栏
        self.setup_header()
        main_layout.addWidget(self.header_widget)
        
        # 连接操作区
        self.setup_connection_panel()
        main_layout.addWidget(self.connection_widget)
        
        # 内容区 (表单和日志)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        
        # 标签信息表单区
        self.setup_tag_form()
        content_layout.addWidget(self.form_group_box)
        
        # 日志输出区
        self.setup_log_panel()
        content_layout.addWidget(self.log_panel)
        
        # 将内容区添加到主布局
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)
        
    def setup_header(self):
        """设置顶部栏"""
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(60)
        self.header_widget.setStyleSheet("background-color: #1DADE5;")
        
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        # 应用名称标签
        app_name_label = QLabel("RFID 读写器管理软件")
        app_name_label.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        
        header_layout.addWidget(app_name_label)
        header_layout.addStretch()
        
    def setup_connection_panel(self):
        """设置连接操作区"""
        self.connection_widget = QWidget()
        self.connection_widget.setFixedHeight(60)
        self.connection_widget.setStyleSheet("background-color: #F5F5F5;")
        
        connection_layout = QHBoxLayout(self.connection_widget)
        connection_layout.setContentsMargins(20, 0, 20, 0)
        
        # 端口选择下拉框
        port_label = QLabel("端口:")
        self.port_combo = QComboBox()
        self.refresh_ports()
        self.port_combo.setMinimumWidth(150)
        
        # 波特率下拉框
        baud_label = QLabel("波特率:")
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("115200")
        self.baud_combo.setFixedWidth(100)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self.refresh_ports)
        
        # 连接/断开按钮
        self.connect_btn = QPushButton("连接读写器")
        self.connect_btn.setFixedWidth(120)
        self.connect_btn.setStyleSheet(
            "QPushButton {background-color: #1DADE5; color: white; border-radius: 4px; padding: 6px;}"
            "QPushButton:hover {background-color: #189DCF;}"
        )
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        # 状态指示
        self.status_label = QLabel("状态：● 未连接")
        self.status_label.setStyleSheet("color: #FF0000;")
        
        connection_layout.addWidget(port_label)
        connection_layout.addWidget(self.port_combo)
        connection_layout.addWidget(baud_label)
        connection_layout.addWidget(self.baud_combo)
        connection_layout.addWidget(refresh_btn)
        connection_layout.addWidget(self.connect_btn)
        connection_layout.addSpacing(20)
        connection_layout.addWidget(self.status_label)
        connection_layout.addStretch()
        
    def setup_tag_form(self):
        """设置标签信息表单区"""
        self.form_group_box = QGroupBox("标签信息")
        self.form_group_box.setStyleSheet(
            "QGroupBox {background-color: white; border-radius: 8px; border: 1px solid #DDDDDD; margin-top: 20px;}"
            "QGroupBox::title {subcontrol-origin: margin; left: 10px; padding: 0 5px;}"
        )
        
        form_layout = QFormLayout()
        form_layout.setContentsMargins(20, 30, 20, 20)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        # 版本号
        self.version_input = QLineEdit()
        self.version_input.setFixedWidth(300)
        form_layout.addRow(QLabel("版本号:"), self.version_input)
        
        # 厂商
        self.manufacturer_combo = QComboBox()
        self.manufacturer_combo.setFixedWidth(300)
        self.manufacturer_combo.addItems(["ACME", "SuperFilament", "BestPLA", "PremiumPrint"])
        self.manufacturer_combo.setEditable(True)
        form_layout.addRow(QLabel("厂商:"), self.manufacturer_combo)
        
        # 耗材名称
        self.material_name_input = QLineEdit()
        self.material_name_input.setFixedWidth(300)
        form_layout.addRow(QLabel("耗材名称:"), self.material_name_input)
        
        # 颜色名称
        self.color_name_input = QLineEdit()
        self.color_name_input.setFixedWidth(300)
        form_layout.addRow(QLabel("颜色名称:"), self.color_name_input)
        
        # 直径(mm)
        self.diameter_input = QDoubleSpinBox()
        self.diameter_input.setFixedWidth(120)
        self.diameter_input.setRange(0.1, 10.0)
        self.diameter_input.setSingleStep(0.05)
        self.diameter_input.setValue(1.75)
        self.diameter_input.setDecimals(2)
        form_layout.addRow(QLabel("直径(mm):"), self.diameter_input)
        
        # 重量(g)
        self.weight_input = QSpinBox()
        self.weight_input.setFixedWidth(120)
        self.weight_input.setRange(0, 10000)
        self.weight_input.setSingleStep(50)
        self.weight_input.setValue(1000)
        form_layout.addRow(QLabel("重量(g):"), self.weight_input)
        
        # 打印温度(℃)
        self.print_temp_input = QSpinBox()
        self.print_temp_input.setFixedWidth(120)
        self.print_temp_input.setRange(160, 300)
        self.print_temp_input.setSingleStep(5)
        self.print_temp_input.setValue(215)
        form_layout.addRow(QLabel("打印温度(℃):"), self.print_temp_input)
        
        # 热床温度(℃)
        self.bed_temp_input = QSpinBox()
        self.bed_temp_input.setFixedWidth(120)
        self.bed_temp_input.setRange(0, 150)
        self.bed_temp_input.setSingleStep(5)
        self.bed_temp_input.setValue(60)
        form_layout.addRow(QLabel("热床温度(℃):"), self.bed_temp_input)
        
        # 密度(g/cm³)
        self.density_input = QDoubleSpinBox()
        self.density_input.setFixedWidth(120)
        self.density_input.setRange(0.1, 10.0)
        self.density_input.setSingleStep(0.01)
        self.density_input.setValue(1.24)
        self.density_input.setDecimals(2)
        form_layout.addRow(QLabel("密度(g/cm³):"), self.density_input)
        
        # 按钮组
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.setSpacing(10)
        
        # 读取按钮
        self.read_btn = QPushButton("读取标签")
        self.read_btn.setFixedWidth(120)
        self.read_btn.setStyleSheet(
            "QPushButton {background-color: #1DADE5; color: white; border-radius: 4px; padding: 8px;}"
            "QPushButton:hover {background-color: #189DCF;}"
        )
        self.read_btn.clicked.connect(self.read_tag)
        
        # 写入按钮
        self.write_btn = QPushButton("写入标签")
        self.write_btn.setFixedWidth(120)
        self.write_btn.setStyleSheet(
            "QPushButton {background-color: #4CAF50; color: white; border-radius: 4px; padding: 8px;}"
            "QPushButton:hover {background-color: #43A047;}"
        )
        self.write_btn.clicked.connect(self.write_tag)
        
        button_layout.addStretch()
        button_layout.addWidget(self.read_btn)
        button_layout.addWidget(self.write_btn)
        
        # 添加按钮到表单布局
        form_layout.addRow("", button_layout)
        
        self.form_group_box.setLayout(form_layout)
        
    def setup_log_panel(self):
        """设置日志输出区"""
        log_group = QGroupBox("日志输出")
        log_group.setStyleSheet(
            "QGroupBox {background-color: white; border-radius: 8px; border: 1px solid #DDDDDD; margin-top: 10px;}"
            "QGroupBox::title {subcontrol-origin: margin; left: 10px; padding: 0 5px;}"
        )
        
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(10, 20, 10, 10)
        
        self.log_panel = LogPanel()
        self.log_panel.setFixedHeight(200)
        
        log_layout.addWidget(self.log_panel)
        
        return log_group
        
    def refresh_ports(self):
        """刷新可用串口列表"""
        self.port_combo.clear()
        
        # 获取可用串口列表
        ports = list(serial.tools.list_ports.comports())
        
        for port in ports:
            self.port_combo.addItem(port.device)
            
        if not ports:
            self.add_log("未检测到串口设备")
        else:
            self.add_log(f"检测到 {len(ports)} 个串口设备")
            
    def toggle_connection(self):
        """切换连接/断开状态"""
        if not self.reader_thread.is_running:
            # 连接读写器
            port = self.port_combo.currentText()
            baud_rate = int(self.baud_combo.currentText())
            
            if not port:
                QMessageBox.warning(self, "警告", "请选择串口")
                return
                
            success = self.reader_thread.connect_reader(port, baud_rate)
            
            if success:
                self.connect_btn.setText("断开连接")
                self.connect_btn.setStyleSheet(
                    "QPushButton {background-color: #CCCCCC; color: black; border-radius: 4px; padding: 6px;}"
                    "QPushButton:hover {background-color: #BBBBBB;}"
                )
                self.port_combo.setEnabled(False)
                self.baud_combo.setEnabled(False)
                
        else:
            # 断开连接
            self.reader_thread.disconnect_reader()
            self.connect_btn.setText("连接读写器")
            self.connect_btn.setStyleSheet(
                "QPushButton {background-color: #1DADE5; color: white; border-radius: 4px; padding: 6px;}"
                "QPushButton:hover {background-color: #189DCF;}"
            )
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            
    def update_status(self, connected, message):
        """更新连接状态"""
        if connected:
            self.status_label.setText(f"状态：● {message}")
            self.status_label.setStyleSheet("color: #4CAF50;")
        else:
            self.status_label.setText(f"状态：● {message}")
            self.status_label.setStyleSheet("color: #FF0000;")
            
    def add_log(self, message):
        """添加日志消息"""
        self.log_panel.add_log(message)
        
    def read_tag(self):
        """读取标签信息"""
        if not self.reader_thread.is_running:
            QMessageBox.warning(self, "警告", "请先连接读写器")
            return
            
        self.reader_thread.read_tag()
        
    def write_tag(self):
        """写入标签信息"""
        if not self.reader_thread.is_running:
            QMessageBox.warning(self, "警告", "请先连接读写器")
            return
            
        # 获取表单数据
        tag_data = {
            "version": self.version_input.text(),
            "manufacturer": self.manufacturer_combo.currentText(),
            "material_name": self.material_name_input.text(),
            "color_name": self.color_name_input.text(),
            "diameter": self.diameter_input.value(),
            "weight": self.weight_input.value(),
            "print_temp": self.print_temp_input.value(),
            "bed_temp": self.bed_temp_input.value(),
            "density": self.density_input.value()
        }
        
        # 数据验证
        if not tag_data["version"]:
            QMessageBox.warning(self, "警告", "版本号不能为空")
            return
            
        if not tag_data["manufacturer"]:
            QMessageBox.warning(self, "警告", "厂商不能为空")
            return
            
        if not tag_data["material_name"]:
            QMessageBox.warning(self, "警告", "耗材名称不能为空")
            return
            
        # 写入标签
        self.reader_thread.write_tag(tag_data)
        
    def update_form_data(self, data):
        """更新表单数据"""
        if "version" in data:
            self.version_input.setText(data["version"])
            
        if "manufacturer" in data:
            index = self.manufacturer_combo.findText(data["manufacturer"])
            if index >= 0:
                self.manufacturer_combo.setCurrentIndex(index)
            else:
                self.manufacturer_combo.setEditText(data["manufacturer"])
                
        if "material_name" in data:
            self.material_name_input.setText(data["material_name"])
            
        if "color_name" in data:
            self.color_name_input.setText(data["color_name"])
            
        if "diameter" in data:
            self.diameter_input.setValue(data["diameter"])
            
        if "weight" in data:
            self.weight_input.setValue(data["weight"])
            
        if "print_temp" in data:
            self.print_temp_input.setValue(data["print_temp"])
            
        if "bed_temp" in data:
            self.bed_temp_input.setValue(data["bed_temp"])
            
        if "density" in data:
            self.density_input.setValue(data["density"])


if __name__ == "__main__":
    # 创建应用
    app = QApplication(sys.argv)
    
    # 设置样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = RFIDReaderApp()
    window.show()
    
    # 添加初始日志
    window.add_log("应用程序已启动")
    window.add_log("请连接RFID读写器")
    
    # 启动应用
    sys.exit(app.exec_()) 