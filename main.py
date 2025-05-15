#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
from datetime import datetime
import serial
import serial.tools.list_ports
import re # 添加 re 模块导入

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QComboBox, QLineEdit, QFormLayout, 
    QSpinBox, QDoubleSpinBox, QTextEdit, QGroupBox, QFrame, 
    QMessageBox, QSplitter, QScrollBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QPalette

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
            
    def read_tag(self, channel):
        """读取标签信息"""
        if not self.serial_port or not self.serial_port.is_open:
            self.log_message.emit("读写器未连接，无法读取标签")
            return False
            
        try:
            self.log_message.emit(f"正在读取通道 {channel} 标签...")
            
            # 使用RFID协议模块读取标签
            success, result = self.rfid_protocol.read_tag(channel)
            
            if success:
                self.data_received.emit(result)
                self.log_message.emit(f"成功读取通道 {channel} 标签内容")
                return True
            else:
                self.log_message.emit(f"读取通道 {channel} 标签失败: {result}")
                return False
                
        except Exception as e:
            self.log_message.emit(f"读取通道 {channel} 标签出错: {str(e)}")
            return False
            
    def write_tag(self, data, channel):
        """写入标签信息"""
        if not self.serial_port or not self.serial_port.is_open:
            self.log_message.emit("读写器未连接，无法写入标签")
            return False
            
        try:
            self.log_message.emit(f"正在写入通道 {channel} 标签...")
            
            # 使用RFID协议模块写入标签
            success, message = self.rfid_protocol.write_tag(data, channel)
            
            if success:
                self.log_message.emit(message)
                return True
            else:
                self.log_message.emit(f"写入通道 {channel} 标签失败: {message}")
                return False
                
        except Exception as e:
            self.log_message.emit(f"写入通道 {channel} 标签出错: {str(e)}")
            return False


class RFIDReaderApp(QMainWindow):
    """RFID读写器应用主窗口"""
    
    APP_VERSION = "v0.0.1"  # 添加软件版本号

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
        
        # 连接操作区 - 移到日志面板创建之后
        self.setup_connection_panel()
        main_layout.insertWidget(1, self.connection_widget)
        
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
        
        # 添加版本号标签
        version_label = QLabel(f"{self.APP_VERSION}")
        version_label.setStyleSheet("color: #FFFFFF; font-size: 15px; margin-top: 5px; margin-left: -3px;")

        header_layout.addWidget(app_name_label)
        header_layout.addWidget(version_label) # 将版本号标签添加到应用名称后面
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
        port_label.setStyleSheet("color: black;")
        self.port_combo = QComboBox()
        self.port_combo.setStyleSheet("color: black;")
        self.refresh_ports()
        self.port_combo.setMinimumWidth(150)
        
        # 波特率下拉框
        baud_label = QLabel("波特率:")
        baud_label.setStyleSheet("color: black;")
        self.baud_combo = QComboBox()
        self.baud_combo.setStyleSheet("color: black;")
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("115200")
        self.baud_combo.setFixedWidth(100)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet("color: black;")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self.refresh_ports)
        
        # 连接/断开按钮
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setStyleSheet("color: black;")
        self.connect_btn.setFixedWidth(80)
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        # 状态标签
        self.status_label = QLabel("状态： <font color='#FF5252' style='font-size:16pt;'>●</font> 未连接")
        self.status_label.setStyleSheet("color: black; margin-top: -10px; margin-left: 10px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # 添加到布局
        connection_layout.addWidget(port_label)
        connection_layout.addWidget(self.port_combo)
        connection_layout.addWidget(baud_label)
        connection_layout.addWidget(self.baud_combo)
        connection_layout.addWidget(refresh_btn)
        connection_layout.addWidget(self.connect_btn)
        connection_layout.addWidget(self.status_label)
        connection_layout.addStretch()
        
        # 添加读写按钮
        read_btn = QPushButton("读取标签")
        read_btn.setStyleSheet("color: black;")
        read_btn.setFixedWidth(100)
        read_btn.clicked.connect(self.read_tag)
        
        write_btn = QPushButton("写入标签")
        write_btn.setStyleSheet("color: black;")
        write_btn.setFixedWidth(100)
        write_btn.clicked.connect(self.write_tag)
        
        connection_layout.addWidget(read_btn)
        connection_layout.addWidget(write_btn)
        
    def setup_tag_form(self):
        """设置标签信息表单"""
        self.form_group_box = QGroupBox("标签信息")
        form_layout = QFormLayout()
        form_layout.setContentsMargins(20, 30, 20, 30)
        form_layout.setSpacing(15)
        
        # 通道号选择
        self.channel_combo = QComboBox()
        self.channel_combo.addItems([f"通道{i}" for i in range(1, 9)])
        self.channel_combo.setCurrentText("通道1")
        self.channel_combo.setToolTip("选择读写器通道 (1-8)")
        form_layout.addRow(QLabel("通道号:"), self.channel_combo)

        # 新增字段根据用户提供的表格
        # Tag Version
        self.tag_version_spin = QSpinBox()
        self.tag_version_spin.setRange(0, 9999) # e.g., 1000 for 1.000
        self.tag_version_spin.setValue(1000)  # 设置默认值
        self.tag_version_spin.setToolTip("RFID标签数据格式版本 (例如: 1000 代表 1.000)")
        form_layout.addRow(QLabel("标签版本:"), self.tag_version_spin)

        # Filament Manufacturer
        self.filament_manufacturer_edit = QLineEdit()
        self.filament_manufacturer_edit.setMaxLength(16) # Max 16 bytes, assuming mostly ASCII
        self.filament_manufacturer_edit.setText("MINGDA 3D")  # 设置默认值
        self.filament_manufacturer_edit.setToolTip("耗材制造商 (最多16字符)")
        form_layout.addRow(QLabel("耗材制造商:"), self.filament_manufacturer_edit)

        # Material Name
        self.material_name_edit = QLineEdit()
        self.material_name_edit.setMaxLength(16) # Max 16 bytes
        self.material_name_edit.setToolTip("材料名称 (例如: PLA, ABS, PETG, 最多16字符)")
        form_layout.addRow(QLabel("材料名称:"), self.material_name_edit)

        # Color Name
        self.color_name_edit = QLineEdit()
        self.color_name_edit.setMaxLength(32) # Max 32 bytes
        self.color_name_edit.setToolTip("颜色名称 (最多32字符)")
        form_layout.addRow(QLabel("颜色名称:"), self.color_name_edit)

        # Diameter (Target)
        self.diameter_target_spin = QSpinBox()
        self.diameter_target_spin.setRange(1000, 3000) # e.g., 1750 for 1.750mm
        self.diameter_target_spin.setValue(1750)  # 设置默认值
        self.diameter_target_spin.setSuffix(" µm")
        self.diameter_target_spin.setToolTip("目标直径 (微米, 例如: 1750 代表 1.750mm)")
        form_layout.addRow(QLabel("目标直径 (µm):"), self.diameter_target_spin)

        # Weight (Nominal, grams)
        self.weight_nominal_spin = QComboBox() # 更改为 QComboBox
        self.weight_nominal_spin.addItems(["1000", "3000", "5000"]) # 添加选项
        self.weight_nominal_spin.setCurrentText("1000") # 设置默认选项
        self.weight_nominal_spin.setToolTip("标称重量 (克)")
        form_layout.addRow(QLabel("标称重量 (g):"), self.weight_nominal_spin)

        # Print Temp (C)
        self.print_temp_spin = QSpinBox()
        self.print_temp_spin.setRange(0, 400) # e.g., 210 for PLA
        self.print_temp_spin.setSuffix(" °C")
        self.print_temp_spin.setToolTip("推荐打印温度 (°C)")
        form_layout.addRow(QLabel("打印温度 (°C):"), self.print_temp_spin)

        # Bed Temp (C)
        self.bed_temp_spin = QSpinBox()
        self.bed_temp_spin.setRange(0, 150) # e.g., 60 for PLA
        self.bed_temp_spin.setSuffix(" °C")
        self.bed_temp_spin.setToolTip("推荐热床温度 (°C)")
        form_layout.addRow(QLabel("热床温度 (°C):"), self.bed_temp_spin)
        
        # Density
        self.density_spin = QSpinBox()
        self.density_spin.setRange(0, 5000) # e.g., 1240 for 1.240 g/cm^3
        self.density_spin.setToolTip("耗材密度 (µg/cm³, 例如: 1240 代表 1.240 g/cm³)")
        # Suffix µg/cm³ might be tricky with special characters, could use QLabel instead or simple " (µg/cm³)" in label
        form_layout.addRow(QLabel("密度 (µg/cm³):"), self.density_spin)
        
        # 设置表单布局
        self.form_group_box.setLayout(form_layout)
        
    def setup_log_panel(self):
        """设置日志面板"""
        self.log_panel = LogPanel()
        self.log_panel.setMaximumHeight(200)
        
        # 添加初始日志
        self.log_panel.add_log("RFID 读写器管理软件已启动")
        self.log_panel.add_log("请连接RFID读写器以开始操作")
        
    def refresh_ports(self):
        """刷新可用串口列表"""
        self.port_combo.clear()
        
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # 排除 COM1
            if port.device.upper() == "COM1":
                continue
            self.port_combo.addItem(port.device)
            
        if self.port_combo.count() == 0:
            self.log_panel.add_log("未找到可用串口 (已排除 COM1)")
        else:
            self.log_panel.add_log(f"找到 {self.port_combo.count()} 个可用串口 (已排除 COM1)")
            
    def toggle_connection(self):
        """切换连接状态"""
        if self.reader_thread.is_running:
            # 断开连接
            self.reader_thread.disconnect_reader()
            self.connect_btn.setText("连接")
        else:
            # 连接设备
            port = self.port_combo.currentText()
            if not port:
                QMessageBox.warning(self, "错误", "请先选择一个串口")
                return
                
            baud_rate = int(self.baud_combo.currentText())
            
            # 尝试连接
            success = self.reader_thread.connect_reader(port, baud_rate)
            if success:
                self.connect_btn.setText("断开")
                
    def update_status(self, connected, message):
        """更新连接状态"""
        if connected:
            self.status_label.setText("状态： <font color='#4CAF50' style='font-size:16pt;'>●</font> 已连接")
        else:
            self.status_label.setText("状态： <font color='#FF5252' style='font-size:16pt;'>●</font> 未连接")
            
    def add_log(self, message):
        """添加日志"""
        self.log_panel.add_log(message)
        
    def read_tag(self):
        """读取标签"""
        channel_number = self.channel_combo.currentIndex() # 获取当前选择的索引 (0-7)
        self.reader_thread.read_tag(channel_number)
        
    def write_tag(self):
        """写入标签"""
        # 收集表单数据
        tag_data = {
            'tag_version': self.tag_version_spin.value(),
            'filament_manufacturer': self.filament_manufacturer_edit.text().strip(), # 去除首尾空格
            'material_name': self.material_name_edit.text().strip(), # 去除首尾空格
            'color_name': self.color_name_edit.text().strip(), # 去除首尾空格
            'diameter_target': self.diameter_target_spin.value(),
            'weight_nominal': int(self.weight_nominal_spin.currentText()), # 从 QComboBox 获取并转为 int
            'print_temp': self.print_temp_spin.value(),
            'bed_temp': self.bed_temp_spin.value(),
            'density': self.density_spin.value()
        }
        
        # 定义校验函数
        def is_valid_string_format(text):
            return bool(re.fullmatch(r"[a-zA-Z0-9 ]*", text))

        # 验证必填字段和格式
        if not tag_data['filament_manufacturer']:
            QMessageBox.warning(self, "验证失败", "耗材制造商不能为空")
            return
        if not is_valid_string_format(tag_data['filament_manufacturer']):
            QMessageBox.warning(self, "验证失败", "耗材制造商只能包含大小写字母、数字和空格")
            return

        if not tag_data['material_name']:
            QMessageBox.warning(self, "验证失败", "耗材名称不能为空")
            return
        if not is_valid_string_format(tag_data['material_name']):
            QMessageBox.warning(self, "验证失败", "耗材名称只能包含大小写字母、数字和空格")
            return

        if not tag_data['color_name']:
            QMessageBox.warning(self, "验证失败", "颜色名称不能为空")
            return
        if not is_valid_string_format(tag_data['color_name']):
            QMessageBox.warning(self, "验证失败", "颜色名称只能包含大小写字母、数字和空格")
            return
            
        # QSpinBox 和 QComboBox 通常会保证有值，但可以根据需要添加更严格的检查
        # 例如，确保温度值在合理范围内（虽然SpinBox已经限制了范围）
        if tag_data['diameter_target'] <= 0: # 直径必须大于0
            QMessageBox.warning(self, "验证失败", "目标直径必须大于0")
            return
            
        if tag_data['print_temp'] < 170:
            QMessageBox.warning(self, "验证失败", "打印温度不能小于170°C")
            return

        # 打印温度和热床温度，QSpinBox 已经有范围限制，一般不需要额外检查是否为空或为0 (除非0是无效值)
        # 标称重量是从 QComboBox 获取的，也会有值

        # 确认写入
        reply = QMessageBox.question(
            self,
            "确认写入",
            "确定要写入标签数据吗？此操作将覆盖标签上的现有数据。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            channel_number = self.channel_combo.currentIndex() # 获取当前选择的索引 (0-7)
            self.reader_thread.write_tag(tag_data, channel_number)
            
    def update_form_data(self, data):
        """更新表单数据"""
        # 更新新的字段
        if 'tag_version' in data:
            self.tag_version_spin.setValue(int(data['tag_version']))
            
        if 'filament_manufacturer' in data:
            self.filament_manufacturer_edit.setText(str(data['filament_manufacturer']))
        
        if 'material_name' in data:
            self.material_name_edit.setText(str(data['material_name']))
            
        if 'color_name' in data:
            self.color_name_edit.setText(str(data['color_name']))
            
        if 'diameter_target' in data:
            self.diameter_target_spin.setValue(int(data['diameter_target']))
            
        if 'weight_nominal' in data:
            self.weight_nominal_spin.setCurrentText(str(data['weight_nominal'])) # 设置 QComboBox 的值
            
        if 'print_temp' in data:
            self.print_temp_spin.setValue(int(data['print_temp']))
            
        if 'bed_temp' in data:
            self.bed_temp_spin.setValue(int(data['bed_temp']))
            
        if 'density' in data:
            self.density_spin.setValue(int(data['density']))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = RFIDReaderApp()
    window.show()
    
    sys.exit(app.exec()) 