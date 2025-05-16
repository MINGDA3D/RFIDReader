#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
from datetime import datetime
import serial
import serial.tools.list_ports
import re # 添加 re 模块导入
import binascii # 添加 binascii 模块导入
from read_rfid_tag import construct_read_command, parse_rfid_response # 从 read_rfid_tag.py 导入 parse_rfid_response
from read_rfid_tag import construct_write_command 

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QComboBox, QLineEdit, QFormLayout, 
    QSpinBox, QDoubleSpinBox, QTextEdit, QGroupBox, QFrame, 
    QMessageBox, QSplitter, QScrollBar, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QSettings
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
    continuous_action_status_changed = pyqtSignal(bool, str) # active, mode ('read', 'write', or '')
    about_to_read_in_loop = pyqtSignal() # 新增信号，用于在连续读取循环中通知UI清空表单
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.serial_port = None
        self.is_running = False
        self.port_name = ""
        self.baud_rate = 115200
        self.rfid_protocol = RFIDProtocol()
        
        # 连续操作相关状态
        self.is_performing_continuous_action = False
        self.continuous_mode = None  # 'read' or 'write'
        self.continuous_action_channel = None
        self.continuous_action_data = None
        self.CONTINUOUS_INTERVAL = 0.5  # 连续操作的间隔时间（秒）
        
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
        self.stop_continuous_action() #确保停止连续操作
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.status_changed.emit(False, "已断开连接")
            self.log_message.emit("已断开读写器连接")
            
    def run(self):
        """线程主循环"""
        while self.is_running:
            if self.is_performing_continuous_action and self.serial_port and self.serial_port.is_open:
                try:
                    if self.continuous_mode == 'read':
                        self.about_to_read_in_loop.emit() # 在执行读取前发射信号
                        self._execute_read_tag_once(self.continuous_action_channel, is_continuous_op=True)
                    elif self.continuous_mode == 'write':
                        if self.continuous_action_data: # 确保有数据可写
                            self._execute_write_tag_once(self.continuous_action_data, self.continuous_action_channel, is_continuous_op=True)
                    time.sleep(self.CONTINUOUS_INTERVAL)
                except Exception as e:
                    self.log_message.emit(f"连续操作中发生错误: {str(e)}")
                    self.stop_continuous_action() # 发生错误时停止连续操作
            else:
                # 即使不进行连续操作，也保持线程的响应性
                time.sleep(0.1)
            
    def _parse_raw_tag_data(self, raw_data: bytes) -> dict:
        """将原始标签字节数据解析为字典"""
        parsed_data = {}
        if not raw_data or len(raw_data) < 76: # 假设主要数据至少76字节
            self.log_message.emit(f"原始标签数据过短或为空，无法解析: {raw_data}")
            return {} # 返回空字典，避免后续错误

        try:
            # 按照假定的数据结构解析
            # Tag Version (2 bytes, uint16)
            parsed_data['tag_version'] = int.from_bytes(raw_data[0:2], 'big') # 假设大端字节序

            # Filament Manufacturer (16 bytes, ASCII)
            parsed_data['filament_manufacturer'] = raw_data[2:18].decode('ascii', errors='ignore').strip('\x00').strip()

            # Material Name (16 bytes, ASCII)
            parsed_data['material_name'] = raw_data[18:34].decode('ascii', errors='ignore').strip('\x00').strip()

            # Color Name (32 bytes, ASCII)
            parsed_data['color_name'] = raw_data[34:66].decode('ascii', errors='ignore').strip('\x00').strip()

            # Diameter (Target) (2 bytes, uint16)
            parsed_data['diameter_target'] = int.from_bytes(raw_data[66:68], 'big')

            # Weight (Nominal, grams) (2 bytes, uint16)
            parsed_data['weight_nominal'] = int.from_bytes(raw_data[68:70], 'big')

            # Print Temp (C) (2 bytes, uint16)
            parsed_data['print_temp'] = int.from_bytes(raw_data[70:72], 'big')

            # Bed Temp (C) (2 bytes, uint16)
            parsed_data['bed_temp'] = int.from_bytes(raw_data[72:74], 'big')
            
            # Density (2 bytes, uint16)
            parsed_data['density'] = int.from_bytes(raw_data[74:76], 'big')
            
            # 您可以根据实际的112字节完整结构，在这里添加更多字段的解析
            # 例如，如果后面还有数据：
            # parsed_data['some_other_field'] = raw_data[76:XX]...

            self.log_message.emit("标签数据解析成功")
            return parsed_data

        except Exception as e:
            self.log_message.emit(f"解析标签数据时出错: {str(e)}")
            return {}


    def _execute_read_tag_once(self, channel, is_continuous_op=False):
        """执行单次标签读取的核心逻辑"""
        prefix = "连续" if is_continuous_op else ""

        # 构建并记录待发送的读取命令
        command_to_send = construct_read_command(channel)
        if command_to_send:
            self.log_message.emit(f"准备发送读取命令 (通道 {channel + 1}): {binascii.hexlify(command_to_send).decode('ascii').upper()}")
        else:
            self.log_message.emit(f"错误: 无法为通道 {channel + 1} 构建读取命令。操作中止。")
            return False

        try:
            # 调用 rfid_protocol 的 read_tag，传入 channel
            # rfid_protocol.read_tag 现在内部也使用 construct_read_command 并发送
            # 它返回 (True, raw_response_bytes) 或 (False, error_message)
            success, result_from_protocol = self.rfid_protocol.read_tag(channel)
            
            if success:
                if isinstance(result_from_protocol, bytes): # 确保是字节串
                    raw_response_frame = result_from_protocol
                    self.log_message.emit(f"接收到原始响应帧 (通道 {channel + 1}): {binascii.hexlify(raw_response_frame).decode('ascii').upper()}")

                    # 使用从 read_rfid_tag.py 导入的 parse_rfid_response 解析原始帧
                    tag_content_bytes = parse_rfid_response(raw_response_frame)
                    
                    if tag_content_bytes is not None: # parse_rfid_response 成功解析并提取了数据部分 (可能为空字节串)
                        if tag_content_bytes: # 如果提取的数据部分不为空
                            parsed_data_dict = self._parse_raw_tag_data(tag_content_bytes)
                            if parsed_data_dict:
                                self.data_received.emit(parsed_data_dict)
                                self.log_message.emit(f"成功{prefix}读取通道 {channel+1}: 已解析标签内容。")
                            else:
                                self.log_message.emit(f"成功{prefix}读取通道 {channel+1}: 标签内容提取成功，但解析为字典失败。内容: {binascii.hexlify(tag_content_bytes).decode('ascii')}")
                        else: # tag_content_bytes 是 b'' (例如，STA=0x00 但无数据内容)
                            self.log_message.emit(f"成功{prefix}读取通道 {channel+1}: 响应成功，但标签数据内容为空。")
                        return True # 操作成功，即使数据为空或解析字典失败，但协议层面成功
                    else: # parse_rfid_response 返回 None (表示帧错误、校验失败、或STA指示无标签等)
                          # parse_rfid_response 内部会打印具体原因
                        self.log_message.emit(f"{prefix}读取通道 {channel+1}: 响应帧解析失败或指示无标签/错误。")
                        return False # 操作失败
                else:
                    # 这不应该发生，因为 rfid_protocol.read_tag(channel) 在成功时保证返回 bytes
                    self.log_message.emit(f"{prefix}读取通道 {channel+1} 成功，但协议层返回数据类型非字节: {type(result_from_protocol)}")
                    return False
            else: # rfid_protocol.read_tag(channel) 返回 success = False
                error_message_from_protocol = result_from_protocol
                self.log_message.emit(f"{prefix}读取通道 {channel+1} 标签失败: {error_message_from_protocol}")
                return False
        except Exception as e:
            self.log_message.emit(f"{prefix}读取通道 {channel+1} 标签时发生顶层异常: {str(e)}")
            return False

    def read_tag(self, channel):
        """读取标签信息 (单次操作)"""
        if not self.serial_port or not self.serial_port.is_open:
            self.log_message.emit("读写器未连接，无法读取标签")
            return False
        
        self.log_message.emit(f"正在读取通道 {channel+1} 标签...")
        return self._execute_read_tag_once(channel, is_continuous_op=False)
            
    def _execute_write_tag_once(self, data, channel, is_continuous_op=False):
        """执行单次标签写入的核心逻辑"""
        prefix = "连续" if is_continuous_op else ""
        
        # "正在写入..." 日志由调用方 (单次写入方法或开始连续写入方法) 处理

        # 首先尝试构建并记录待发送的写入命令
        try:
            # 假设 construct_write_command(data_dict, channel) 返回构建好的命令字节串
            # data 参数即为包含标签信息的字典
            command_to_send = construct_write_command(data, channel)
            if command_to_send:
                self.log_message.emit(f"准备发送写入命令 (通道 {channel + 1}): {binascii.hexlify(command_to_send).decode('ascii').upper()}")
            else:
                # 如果构建命令失败（例如，数据无效），也记录下来
                self.log_message.emit(f"错误: 无法为通道 {channel + 1} 构建写入命令 (数据: {data})。将尝试通过协议层直接写入。")
        except Exception as e_construct:
            self.log_message.emit(f"构建写入命令时发生错误 (通道 {channel + 1}): {str(e_construct)}。将尝试通过协议层直接写入。")

        # 执行实际的写入操作
        try:
            success, message = self.rfid_protocol.write_tag(data, channel)
            
            if success:
                self.log_message.emit(f"成功{prefix}写入通道 {channel+1} 标签: {message}")
                return True
            else:
                self.log_message.emit(f"{prefix}写入通道 {channel+1} 标签失败: {message}")
                return False
        except Exception as e:
            self.log_message.emit(f"{prefix}写入通道 {channel+1} 标签时出错: {str(e)}")
            return False

    def write_tag(self, data, channel):
        """写入标签信息 (单次操作)"""
        if not self.serial_port or not self.serial_port.is_open:
            self.log_message.emit("读写器未连接，无法写入标签")
            return False
            
        self.log_message.emit(f"正在写入通道 {channel+1} 标签...")
        return self._execute_write_tag_once(data, channel, is_continuous_op=False)

    def start_continuous_read(self, channel):
        """开始连续读取"""
        if not self.serial_port or not self.serial_port.is_open:
            self.log_message.emit("读写器未连接，无法开始连续读取")
            return

        if self.is_performing_continuous_action and self.continuous_mode == 'write':
            self.stop_continuous_action() # 如果正在连续写入，则停止

        self.is_performing_continuous_action = True
        self.continuous_mode = 'read'
        self.continuous_action_channel = channel
        self.log_message.emit(f"开始连续读取通道 {channel+1}...")
        self.continuous_action_status_changed.emit(True, 'read')

    def start_continuous_write(self, data, channel):
        """开始连续写入"""
        if not self.serial_port or not self.serial_port.is_open:
            self.log_message.emit("读写器未连接，无法开始连续写入")
            return

        if self.is_performing_continuous_action and self.continuous_mode == 'read':
            self.stop_continuous_action() # 如果正在连续读取，则停止

        self.is_performing_continuous_action = True
        self.continuous_mode = 'write'
        self.continuous_action_data = data
        self.continuous_action_channel = channel
        self.log_message.emit(f"开始连续写入通道 {channel+1}...")
        self.continuous_action_status_changed.emit(True, 'write')

    def stop_continuous_action(self):
        """停止所有连续操作"""
        if self.is_performing_continuous_action:
            mode_text = "读取" if self.continuous_mode == 'read' else "写入"
            self.log_message.emit(f"停止连续{mode_text}操作")
            self.is_performing_continuous_action = False
            self.continuous_mode = None
            self.continuous_action_channel = None
            self.continuous_action_data = None
            self.continuous_action_status_changed.emit(False, '')


class RFIDReaderApp(QMainWindow):
    """RFID读写器应用主窗口"""
    
    APP_VERSION = "v0.0.1"  # 添加软件版本号

    # 定义耗材模板数据
    DEFAULT_MATERIAL_TEMPLATES = {
        "选择耗材模板...": {}, # 添加一个默认的空选项
        "PLA": {
            'tag_version': 1000,
            'filament_manufacturer': "MINGDA 3D",
            'material_name': "PLA",
            'color_name': "White",
            'diameter_target': 1750,
            'weight_nominal': "1000",
            'print_temp': 210,
            'bed_temp': 60,
            'density': 1240
        },
        "ABS": {
            'tag_version': 1000,
            'filament_manufacturer': "MINGDA 3D",
            'material_name': "ABS",
            'color_name': "Black",
            'diameter_target': 1750,
            'weight_nominal': "1000",
            'print_temp': 240,
            'bed_temp': 100,
            'density': 1040
        },
        "PETG": {
            'tag_version': 1000,
            'filament_manufacturer': "MINGDA 3D",
            'material_name': "PETG",
            'color_name': "Transparent",
            'diameter_target': 1750,
            'weight_nominal': "1000",
            'print_temp': 230,
            'bed_temp': 70,
            'density': 1270
        },
        "PET-CF": {
            'tag_version': 1000,
            'filament_manufacturer': "MINGDA 3D",
            'material_name': "PET-CF",
            'color_name': "Carbon Black",
            'diameter_target': 1750,
            'weight_nominal': "1000",
            'print_temp': 280,
            'bed_temp': 80,
            'density': 1300 # 示例值，请按实际修改
        },
        "ASA": {
            'tag_version': 1000,
            'filament_manufacturer': "MINGDA 3D",
            'material_name': "ASA",
            'color_name': "Natural",
            'diameter_target': 1750,
            'weight_nominal': "1000",
            'print_temp': 250,
            'bed_temp': 90,
            'density': 1070
        },
        "HtPA": { # High Temperature PA
            'tag_version': 1000,
            'filament_manufacturer': "MINGDA 3D",
            'material_name': "HtPA",
            'color_name': "Natural",
            'diameter_target': 1750,
            'weight_nominal': "1000",
            'print_temp': 290,
            'bed_temp': 110,
            'density': 1150 # 示例值
        },
        "TPU": {
            'tag_version': 1000,
            'filament_manufacturer': "MINGDA 3D",
            'material_name': "TPU",
            'color_name': "Flexible Black",
            'diameter_target': 1750,
            'weight_nominal': "1000",
            'print_temp': 220,
            'bed_temp': 50,
            'density': 1210
        }
    }

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
        self.reader_thread.continuous_action_status_changed.connect(self.on_continuous_action_status_changed)
        self.reader_thread.about_to_read_in_loop.connect(self.clear_tag_form) # 连接新信号到清空表单方法
        
        # 设置主界面
        self.setup_ui()
        self.load_settings() # 启动时加载设置
        
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
        self.continuous_read_checkbox = QCheckBox("连续读取")
        self.continuous_read_checkbox.setStyleSheet("color: black;")
        self.continuous_read_checkbox.stateChanged.connect(
            lambda state: self.handle_continuous_checkbox_changed(state, 'read')
        )
        
        self.read_button = QPushButton("读取标签")
        self.read_button.setStyleSheet("color: black;")
        self.read_button.setFixedWidth(100)
        self.read_button.clicked.connect(self.read_tag)
        
        self.continuous_write_checkbox = QCheckBox("连续写入")
        self.continuous_write_checkbox.setStyleSheet("color: black;")
        self.continuous_write_checkbox.stateChanged.connect(
            lambda state: self.handle_continuous_checkbox_changed(state, 'write')
        )
        
        self.write_button = QPushButton("写入标签")
        self.write_button.setStyleSheet("color: black;")
        self.write_button.setFixedWidth(100)
        self.write_button.clicked.connect(self.write_tag)

        connection_layout.addWidget(self.continuous_read_checkbox)
        connection_layout.addWidget(self.read_button)
        connection_layout.addWidget(self.continuous_write_checkbox)
        connection_layout.addWidget(self.write_button)

        # 添加清空日志按钮
        self.clear_logs_btn = QPushButton("清空日志")
        self.clear_logs_btn.setStyleSheet("color: black;")
        self.clear_logs_btn.setFixedWidth(100)
        self.clear_logs_btn.clicked.connect(self.clear_log_panel)
        connection_layout.addWidget(self.clear_logs_btn)
        
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

        # 新增：耗材模板选择
        self.material_template_combo = QComboBox()
        self.material_template_combo.addItems(self.DEFAULT_MATERIAL_TEMPLATES.keys())
        self.material_template_combo.currentTextChanged.connect(self.apply_material_template)
        self.material_template_combo.setToolTip("选择一个耗材模板快速填充信息")
        form_layout.addRow(QLabel("耗材模板:"), self.material_template_combo)

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
        self.weight_nominal_spin.addItem("选择重量...") # 添加占位符
        self.weight_nominal_spin.addItems(["1000", "3000", "5000"]) # 添加选项
        self.weight_nominal_spin.setCurrentIndex(0) # 默认选中占位符
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
        
    def handle_continuous_checkbox_changed(self, state, checkbox_type):
        """处理连续操作复选框状态变化"""
        source_checkbox = None
        other_checkbox = None

        if checkbox_type == 'read':
            source_checkbox = self.continuous_read_checkbox
            other_checkbox = self.continuous_write_checkbox
        elif checkbox_type == 'write':
            source_checkbox = self.continuous_write_checkbox
            other_checkbox = self.continuous_read_checkbox

        if source_checkbox.isChecked():
            if other_checkbox.isChecked():
                other_checkbox.setChecked(False) # 确保互斥
            # 如果当前有其他类型的连续操作正在进行，则停止它
            if self.reader_thread.is_performing_continuous_action and \
               self.reader_thread.continuous_mode != checkbox_type:
                self.reader_thread.stop_continuous_action()
        else: # 复选框被取消选中
            # 如果当前选中的是此类型的连续操作，则停止它
            if self.reader_thread.is_performing_continuous_action and \
               self.reader_thread.continuous_mode == checkbox_type:
                self.reader_thread.stop_continuous_action()

    def on_continuous_action_status_changed(self, is_active, mode):
        """当连续操作状态改变时调用"""
        if is_active:
            if mode == 'read':
                self.read_button.setText("停止读取")
                self.write_button.setText("写入标签") # 重置另一个按钮
                self.continuous_read_checkbox.setChecked(True) # 确保勾选框状态一致
                # 禁止另一个连续操作
                self.continuous_write_checkbox.setEnabled(False)
                self.write_button.setEnabled(False)
                self.read_button.setEnabled(True)
            elif mode == 'write':
                self.write_button.setText("停止写入")
                self.read_button.setText("读取标签") # 重置另一个按钮
                self.continuous_write_checkbox.setChecked(True) # 确保勾选框状态一致
                # 禁止另一个连续操作
                self.continuous_read_checkbox.setEnabled(False)
                self.read_button.setEnabled(False)
                self.write_button.setEnabled(True)
        else: # 不再活动
            self.read_button.setText("读取标签")
            self.write_button.setText("写入标签")
            self.continuous_read_checkbox.setEnabled(True)
            self.continuous_write_checkbox.setEnabled(True)
            self.read_button.setEnabled(True)
            self.write_button.setEnabled(True)
            # 当操作停止时，不要主动取消复选框的选中状态，由用户控制或互斥逻辑控制
            # if self.continuous_read_checkbox.isChecked() and self.reader_thread.continuous_mode != 'read':
            # self.continuous_read_checkbox.setChecked(False) # Potentially problematic
            # if self.continuous_write_checkbox.isChecked() and self.reader_thread.continuous_mode != 'write':
            # self.continuous_write_checkbox.setChecked(False) # Potentially problematic
        
    def read_tag(self):
        """读取标签"""
        if not self.reader_thread.is_running:
            self.add_log("读写器未连接")
            QMessageBox.warning(self, "提示", "请先连接读写器")
            return

        channel_number = self.channel_combo.currentIndex() # 获取当前选择的索引 (0-7)

        # 情况1：如果当前正在连续读取，则点击按钮表示停止
        if self.reader_thread.is_performing_continuous_action and self.reader_thread.continuous_mode == 'read':
            self.reader_thread.stop_continuous_action()
        # 情况2：如果"连续读取"复选框被选中，则开始连续读取
        elif self.continuous_read_checkbox.isChecked():
            # self.clear_tag_form() # 此处不再需要，由线程信号处理首次清空
            self.reader_thread.start_continuous_read(channel_number)
        # 情况3：执行单次读取
        else:
            # 如果有任何其他连续操作正在进行（比如连续写入），先停止它
            if self.reader_thread.is_performing_continuous_action:
                self.reader_thread.stop_continuous_action()
            self.clear_tag_form() # 单次读取前清空表单
            self.reader_thread.read_tag(channel_number)
        
    def write_tag(self):
        """写入标签"""
        # First, validate weight_nominal
        current_weight_text = self.weight_nominal_spin.currentText()
        if current_weight_text == "选择重量...":
            QMessageBox.warning(self, "验证失败", "请选择一个有效的标称重量")
            return
        
        try:
            weight_nominal_value = int(current_weight_text)
        except ValueError:
            QMessageBox.warning(self, "错误", f"标称重量值 '{current_weight_text}' 无效，无法转换为数字。")
            return

        # 收集表单数据
        tag_data = {
            'tag_version': self.tag_version_spin.value(),
            'filament_manufacturer': self.filament_manufacturer_edit.text().strip(), # 去除首尾空格
            'material_name': self.material_name_edit.text().strip(), # 去除首尾空格
            'color_name': self.color_name_edit.text().strip(), # 去除首尾空格
            'diameter_target': self.diameter_target_spin.value(),
            'weight_nominal': weight_nominal_value, # 使用经过验证和转换的值
            'print_temp': self.print_temp_spin.value(),
            'bed_temp': self.bed_temp_spin.value(),
            'density': self.density_spin.value()
        }
        
        # 定义校验函数
        def is_valid_string_format(text):
            return bool(re.fullmatch(r"[a-zA-Z0-9 -]*", text))

        # 验证必填字段和格式
        if not tag_data['filament_manufacturer']:
            QMessageBox.warning(self, "验证失败", "耗材制造商不能为空")
            return
        if not is_valid_string_format(tag_data['filament_manufacturer']):
            QMessageBox.warning(self, "验证失败", "耗材制造商只能包含大小写字母、数字和横杠")
            return

        if not tag_data['material_name']:
            QMessageBox.warning(self, "验证失败", "耗材名称不能为空")
            return
        if not is_valid_string_format(tag_data['material_name']):
            QMessageBox.warning(self, "验证失败", "耗材名称只能包含大小写字母、数字和横杠")
            return

        if not tag_data['color_name']:
            QMessageBox.warning(self, "验证失败", "颜色名称不能为空")
            return
        if not is_valid_string_format(tag_data['color_name']):
            QMessageBox.warning(self, "验证失败", "颜色名称只能包含大小写字母、数字和横杠")
            return
            
        # QSpinBox 通常会保证有值
        if tag_data['diameter_target'] <= 0: # 直径必须大于0
            QMessageBox.warning(self, "验证失败", "目标直径必须大于0")
            return
            
        # 标称重量的校验已移到tag_data创建之前
            
        if tag_data['print_temp'] < 170:
            QMessageBox.warning(self, "验证失败", "打印温度不能小于170°C")
            return

        # 打印温度和热床温度，QSpinBox 已经有范围限制，一般不需要额外检查是否为空或为0 (除非0是无效值)
        # 标称重量的校验已移到tag_data创建之前

        channel_number = self.channel_combo.currentIndex()

        # 情况1：如果当前正在连续写入，则点击按钮表示停止
        if self.reader_thread.is_performing_continuous_action and self.reader_thread.continuous_mode == 'write':
            self.reader_thread.stop_continuous_action()
        # 情况2：如果"连续写入"复选框被选中，则开始连续写入
        elif self.continuous_write_checkbox.isChecked():
            reply = QMessageBox.question(
                self,
                "确认连续写入",
                "确定要开始连续写入标签数据吗？此操作将循环覆盖标签上的现有数据，直到手动停止。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.reader_thread.start_continuous_write(tag_data, channel_number)
        # 情况3：执行单次写入
        else:
            # 如果有任何其他连续操作正在进行（比如连续读取），先停止它
            if self.reader_thread.is_performing_continuous_action:
                self.reader_thread.stop_continuous_action()
                
            reply = QMessageBox.question(
                self,
                "确认写入",
                "确定要写入标签数据吗？此操作将覆盖标签上的现有数据。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.reader_thread.write_tag(tag_data, channel_number)
            
    def update_form_data(self, data):
        """更新表单数据"""
        if not data: # 如果传入空数据 (例如 "选择耗材模板..." 选项)
            # 可以选择清空表单或恢复默认值，这里暂时不清空，让用户自己操作
            # self.tag_version_spin.setValue(1000) 
            # self.filament_manufacturer_edit.setText("MINGDA 3D")
            # self.material_name_edit.clear() 
            # self.color_name_edit.clear()
            # self.diameter_target_spin.setValue(1750)
            # self.weight_nominal_spin.setCurrentText("1000")
            # self.print_temp_spin.setValue(0) # Or a sensible default
            # self.bed_temp_spin.setValue(0)   # Or a sensible default
            # self.density_spin.setValue(0)    # Or a sensible default
            return

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
            current_weight_text = str(data['weight_nominal'])
            # 确保 QComboBox 中存在该选项，如果不存在，可以考虑是否添加或记录日志
            index = self.weight_nominal_spin.findText(current_weight_text)
            if index != -1:
                self.weight_nominal_spin.setCurrentText(current_weight_text)
            else:
                # 如果配置中的重量值不在预设列表中，可以选择添加到列表或记录一个警告
                # self.weight_nominal_spin.addItem(current_weight_text) # 动态添加
                # self.weight_nominal_spin.setCurrentText(current_weight_text)
                self.add_log(f"警告: 从标签读取的重量值 '{current_weight_text}' 不在预设列表中。")
                # 可以选择将其设置为默认的 "选择重量..."
                if self.weight_nominal_spin.count() > 0:
                    self.weight_nominal_spin.setCurrentIndex(0)


            
        if 'print_temp' in data:
            self.print_temp_spin.setValue(int(data['print_temp']))
            
        if 'bed_temp' in data:
            self.bed_temp_spin.setValue(int(data['bed_temp']))
            
        if 'density' in data:
            self.density_spin.setValue(int(data['density']))

    def clear_tag_form(self):
        """清空标签信息表单至其最小值或空白状态"""
        self.tag_version_spin.lineEdit().clear() # 清空视觉显示
        self.filament_manufacturer_edit.clear() # 清空文本
        self.material_name_edit.clear()
        self.color_name_edit.clear()
        self.diameter_target_spin.lineEdit().clear() # 清空视觉显示
        
        # 将标称重量下拉框重置为占位符 (第一个项目)
        if self.weight_nominal_spin.count() > 0:
            self.weight_nominal_spin.setCurrentIndex(0)
        
        self.print_temp_spin.lineEdit().clear() # 清空视觉显示
        self.bed_temp_spin.lineEdit().clear() # 清空视觉显示
        self.density_spin.lineEdit().clear() # 清空视觉显示
        
        # 将耗材模板下拉框重置为 "选择耗材模板..." 选项
        if self.material_template_combo.count() > 0: 
            self.material_template_combo.setCurrentIndex(0)

        self.add_log("标签信息表单已清空至初始状态")

    def apply_material_template(self, material_name):
        """根据选择的耗材模板名称填充表单"""
        if material_name in self.DEFAULT_MATERIAL_TEMPLATES:
            template_data = self.DEFAULT_MATERIAL_TEMPLATES[material_name]
            if template_data: # 确保不是空的 "选择耗材模板..."
                self.update_form_data(template_data)
                self.add_log(f"已应用耗材模板: {material_name}") # 添加日志记录
            # 如果template_data为空 (对应 "选择耗材模板...")，可以选择是否清空表单
            else:
                self.clear_tag_form() # 调用清空方法

    def clear_log_panel(self):
        """清空日志面板"""
        self.log_panel.clear()
        self.add_log("日志已清空。")

    def closeEvent(self, event):
        """重写 closeEvent 以在关闭前保存设置"""
        self.save_settings()
        super().closeEvent(event)

    def save_settings(self):
        """保存表单数据到配置文件"""
        settings = QSettings("MINGDA", "RFIDReaderApp") # 公司名和应用名，用于定位配置文件

        settings.beginGroup("TagForm")
        settings.setValue("channel_index", self.channel_combo.currentIndex())
        settings.setValue("material_template_text", self.material_template_combo.currentText()) # 保存文本以便恢复
        settings.setValue("tag_version", self.tag_version_spin.value())
        settings.setValue("filament_manufacturer", self.filament_manufacturer_edit.text())
        settings.setValue("material_name", self.material_name_edit.text())
        settings.setValue("color_name", self.color_name_edit.text())
        settings.setValue("diameter_target", self.diameter_target_spin.value())
        settings.setValue("weight_nominal_text", self.weight_nominal_spin.currentText()) # 保存当前选中的文本
        settings.setValue("print_temp", self.print_temp_spin.value())
        settings.setValue("bed_temp", self.bed_temp_spin.value())
        settings.setValue("density", self.density_spin.value())
        settings.endGroup()
        self.add_log("应用程序设置已保存。")

    def load_settings(self):
        """从配置文件加载表单数据"""
        settings = QSettings("MINGDA", "RFIDReaderApp")

        settings.beginGroup("TagForm")
        # 加载通道号
        channel_index = settings.value("channel_index", 0, type=int) # 默认值为0 (通道1)
        if 0 <= channel_index < self.channel_combo.count():
            self.channel_combo.setCurrentIndex(channel_index)

        # 加载耗材模板 - 先尝试恢复选择，如果模板不存在，则不改变
        material_template_text = settings.value("material_template_text", "选择耗材模板...", type=str)
        template_index = self.material_template_combo.findText(material_template_text)
        if template_index != -1:
            self.material_template_combo.setCurrentIndex(template_index)
            # 如果加载的不是"选择耗材模板...", 则应用它
            if material_template_text != "选择耗材模板...":
                 self.apply_material_template(material_template_text) # 应用模板数据
        
        # 只有在没有成功加载并应用有效模板时，才加载单个字段的值
        # 这样可以避免模板数据被旧的单个字段数据覆盖
        # 或者，如果希望总是优先加载单个字段，则移除此条件
        if template_index == -1 or material_template_text == "选择耗材模板...":
            self.tag_version_spin.setValue(settings.value("tag_version", 1000, type=int))
            self.filament_manufacturer_edit.setText(settings.value("filament_manufacturer", "MINGDA 3D", type=str))
            self.material_name_edit.setText(settings.value("material_name", "", type=str))
            self.color_name_edit.setText(settings.value("color_name", "", type=str))
            self.diameter_target_spin.setValue(settings.value("diameter_target", 1750, type=int))
            
            # 加载标称重量
            weight_nominal_text = settings.value("weight_nominal_text", "选择重量...", type=str)
            weight_index = self.weight_nominal_spin.findText(weight_nominal_text)
            if weight_index != -1:
                self.weight_nominal_spin.setCurrentIndex(weight_index)
            elif self.weight_nominal_spin.count() > 0: # 如果找不到保存的值，且有选项，则默认选第一个
                self.weight_nominal_spin.setCurrentIndex(0)


            self.print_temp_spin.setValue(settings.value("print_temp", 210, type=int)) # 默认PLA打印温度
            self.bed_temp_spin.setValue(settings.value("bed_temp", 60, type=int))     # 默认PLA床温
            self.density_spin.setValue(settings.value("density", 1240, type=int))     # 默认PLA密度

        settings.endGroup()
        self.add_log("应用程序设置已加载。")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = RFIDReaderApp()
    window.show()
    
    sys.exit(app.exec()) 