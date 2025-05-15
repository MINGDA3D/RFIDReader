#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RFID读写器管理软件测试模式
允许在没有实际RFID读写器硬件的情况下测试软件功能
"""

import time
import random
import threading
from datetime import datetime
import sys
import types

class VirtualSerialPort:
    """
    虚拟串口类，模拟串口通信
    """
    
    def __init__(self, port_name="COM99", baudrate=115200):
        self.port = port_name
        self.baudrate = baudrate
        self.is_open = False
        self.in_waiting = 0
        self.buffer = bytearray()
        self.lock = threading.Lock()
        
    def open(self):
        """打开虚拟串口"""
        self.is_open = True
        return True
        
    def close(self):
        """关闭虚拟串口"""
        self.is_open = False
        
    def write(self, data):
        """写入数据到虚拟串口"""
        if not self.is_open:
            raise Exception("Port not open")
            
        # 模拟写入延迟
        time.sleep(0.01 * len(data))
        
        # 解析命令并准备响应
        with self.lock:
            if len(data) > 3 and data[0] == 0xAA and data[1] == 0x55:
                cmd = data[2]
                
                # 1秒后会有数据可读
                def delayed_response():
                    time.sleep(0.2)
                    with self.lock:
                        if cmd == 0x01:  # 读取命令
                            self._prepare_read_response()
                        elif cmd == 0x02:  # 写入命令
                            self._prepare_write_response()
                            
                threading.Thread(target=delayed_response).start()
                
        return len(data)
        
    def read(self, size=1):
        """从虚拟串口读取数据"""
        if not self.is_open:
            raise Exception("Port not open")
            
        with self.lock:
            data = self.buffer[:size]
            self.buffer = self.buffer[size:]
            self.in_waiting = len(self.buffer)
            return bytes(data)
            
    def _prepare_read_response(self):
        """准备读取命令的响应"""
        from rfid_protocol import RFIDProtocol
        import json
        
        # 获取模拟数据
        sample_data = {
            "version": f"V{random.randint(1, 5)}.{random.randint(0, 9)}",
            "manufacturer": random.choice(["ACME", "SuperFilament", "BestPLA", "PremiumPrint"]),
            "material_name": random.choice(["PLA", "PLA+", "ABS", "PETG", "TPU"]),
            "color_name": random.choice(["BLACK", "WHITE", "DARK SPACE GRAY", "SILVER GRAY", "BLUE", "RED"]),
            "diameter": round(random.uniform(1.65, 1.85), 2),
            "weight": random.choice([250, 500, 1000, 2000]),
            "print_temp": random.randint(190, 240),
            "bed_temp": random.randint(50, 80),
            "density": round(random.uniform(1.2, 1.3), 2)
        }
        
        # 将数据转换为JSON字符串并编码
        json_data = json.dumps(sample_data).encode('utf-8')
        
        # 构建响应包
        # 帧头(2字节) + 命令(1字节) + 长度(1字节) + 状态(1字节) + 数据 + 校验和(1字节)
        response = bytearray([0xAA, 0x55, 0x01, len(json_data) + 1, 0x00])  # 0x00表示成功
        response.extend(json_data)
        
        # 计算校验和
        checksum = sum(response) & 0xFF
        response.append(checksum)
        
        # 添加到缓冲区
        self.buffer.extend(response)
        self.in_waiting = len(self.buffer)
        
    def _prepare_write_response(self):
        """准备写入命令的响应"""
        # 构建响应包
        # 帧头(2字节) + 命令(1字节) + 长度(1字节) + 状态(1字节) + 校验和(1字节)
        response = bytearray([0xAA, 0x55, 0x02, 0x01, 0x00])  # 0x00表示成功
        
        # 计算校验和
        checksum = sum(response) & 0xFF
        response.append(checksum)
        
        # 添加到缓冲区
        self.buffer.extend(response)
        self.in_waiting = len(self.buffer)


def enable_test_mode():
    """启用测试模式，将替代serial模块"""
    # 创建模拟的serial模块
    mock_serial = types.ModuleType('serial')
    mock_serial.Serial = VirtualSerialPort
    
    # 创建模拟的serial.tools模块
    mock_tools = types.ModuleType('serial.tools')
    sys.modules['serial.tools'] = mock_tools
    
    # 创建模拟的serial.tools.list_ports模块
    mock_list_ports = types.ModuleType('serial.tools.list_ports')
    
    # 添加comports函数
    def comports():
        class MockPort:
            def __init__(self, device, description):
                self.device = device
                self.description = description
        
        return [
            MockPort("COM1", "Virtual Serial Port 1"),
            MockPort("COM2", "Virtual Serial Port 2"),
            MockPort("COM3", "Virtual Serial Port 3")
        ]
    
    mock_list_ports.comports = comports
    sys.modules['serial.tools.list_ports'] = mock_list_ports
    
    # 设置模块关系
    mock_serial.tools = mock_tools
    mock_tools.list_ports = mock_list_ports
    
    # 替换模块
    sys.modules['serial'] = mock_serial
    
    # 输出测试模式信息
    print("="*50)
    print("RFID读写器管理软件 - 测试模式已启用")
    print("该模式下使用虚拟串口和模拟数据进行测试")
    print("="*50)


if __name__ == "__main__":
    # 启用测试模式
    enable_test_mode()
    
    # 导入并运行主程序
    import main 