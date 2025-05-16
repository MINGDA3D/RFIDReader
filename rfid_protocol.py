#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RFID读写器通信协议模拟模块
实际应用中需要根据RFID读写器的协议进行实现
"""

import time
import json
import random
import binascii
import struct
import datetime
import serial
from read_rfid_tag import construct_read_command # 导入正确的命令构建函数

class RFIDProtocol:
    """RFID读写器通信协议处理类"""
    
    # 下列命令字和状态码是旧协议 (AA 55 ...) 的，在新的 EF...FE 协议中不直接使用
    # CMD_READ = 0x01
    # CMD_WRITE = 0x02
    # CMD_SCAN = 0x03
    # STATUS_SUCCESS = 0x00
    # STATUS_ERROR = 0x01
    # STATUS_NO_TAG = 0x02
    # STATUS_READ_ERROR = 0x03
    # STATUS_WRITE_ERROR = 0x04
    
    def __init__(self, serial_port=None):
        """初始化RFID协议处理器"""
        self.serial_port = serial_port
        
    def set_serial(self, serial_port):
        """设置串口"""
        self.serial_port = serial_port
        
    # _calculate_checksum, _build_packet, _parse_packet 是旧协议 (AA 55...) 的辅助方法
    # 在新的 EF...FE 协议下，命令构建由 construct_read_command 处理，
    # 响应解析由 read_rfid_tag.parse_rfid_response 处理 (在 main.py 中调用)
    # def _calculate_checksum(self, data): ...
    # def _build_packet(self, cmd, data=None): ...
    # def _parse_packet(self, packet_bytes): ...
        
    def read_tag(self, channel: int): # channel 参数是 0-indexed
        """读取标签信息，使用 EF...FE 协议"""
        if not self.serial_port or not self.serial_port.is_open:
            return False, "串口未连接或未打开"

        command_to_send = construct_read_command(channel)
        if not command_to_send:
            return False, f"错误: 无法为通道 {channel + 1} 构建读取命令。"

        try:
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            # self.log_message.emit(f"RFIDProtocol 发送命令: {binascii.hexlify(command_to_send).decode('ascii').upper()}") # 若需在此处日志
            bytes_written = self.serial_port.write(command_to_send)
            if bytes_written != len(command_to_send):
                return False, f"串口写入不足: 预期 {len(command_to_send)}, 实际 {bytes_written}"

            # 等待设备响应。串口本身的超时设置 (timeout=1 in main.py) 会在read时起作用。
            # 增加一个短暂延时确保设备有时间处理并开始发送。
            time.sleep(0.3) 

            if self.serial_port.in_waiting > 0:
                response_bytes = self.serial_port.read(self.serial_port.in_waiting)
                # self.log_message.emit(f"RFIDProtocol 收到原始数据: {binascii.hexlify(response_bytes).decode('ascii').upper()}") # 若需在此处日志
                return True, response_bytes
            else:
                return False, "读取响应超时或无数据 (串口缓冲区无数据)"
        
        except serial.SerialTimeoutException:
            return False, "串口写入/读取操作超时"
        except serial.SerialException as se:
            return False, f"串口通信错误: {str(se)}"
        except Exception as e:
            return False, f"读取标签时发生未知异常: {str(e)}"
            
    def write_tag(self, tag_data): # TODO: 此方法仍使用旧的 _build_packet
        """写入标签信息"""
        if not self.serial_port:
            return False, "串口未设置"
            
        try:
            # 将数据转换为字节数据
            data_bytes = self._tag_data_to_bytes(tag_data) #此方法可能也需适配新协议
            
            # 构建写入标签命令包 - 注意：这里仍使用旧的 _build_packet
            # 需要修改为符合 EF...FE 协议的写命令构建方式
            packet = self._build_packet(0x02, data_bytes) # 0x02 是旧的 CMD_WRITE
            
            self.serial_port.write(packet)
            time.sleep(0.5)
            
            if self.serial_port.in_waiting:
                response = self.serial_port.read(self.serial_port.in_waiting)
                # _parse_packet 也是旧协议的
                # result, error = self._parse_packet(response) 
                # 模拟解析，实际需要按 EF...FE 协议解析写响应
                if response: # 简化模拟
                    # 假设写响应的 STA 在特定位置，例如 response[3] for EF...FE
                    # STA = 0x00 (成功), 0x01 (密码错误), 0x02 (无标签)
                    # 此处仅为示意，实际解析应更严谨
                    if len(response) > 3 and response[0] == 0xEF and response[3] == 0x00: # 模拟成功
                         return True, "标签写入成功 (模拟)"
                    else:
                         return False, f"写入失败或响应异常 (模拟响应: {binascii.hexlify(response).decode('ascii').upper()})"
                else:
                    return False, "写入后无响应"

            return True, "标签写入成功 (无响应，模拟)" # Fallback simulation
            
        except Exception as e:
            return False, f"写入标签异常: {str(e)}"
            
    # _parse_tag_data, _tag_data_to_bytes, _get_sample_tag_data
    # 这些方法与旧的模拟数据或JSON处理有关，可能需要重构或移除
    # 以适应新的基于字节流和特定字段的RFID编码规则 (如Doc/RFID应用通信协议.md中定义)

    def _tag_data_to_bytes(self, tag_data):
        """将标签数据转换为字节数据 (旧的JSON实现，需要修改)"""
        try:
            json_str = json.dumps(tag_data)
            return list(json_str.encode('utf-8'))
        except Exception as e:
            print(f"转换标签数据异常: {str(e)}")
            return []

    def _get_sample_tag_data(self):
        """获取示例标签数据"""
        tag_id = ''.join([f"{random.randint(0, 15):X}" for _ in range(6)])
        today = datetime.date.today()
        issue_date = today.strftime("%Y-%m-%d")
        expire_date = (today.replace(year=today.year + 1)).strftime("%Y-%m-%d")
        sample_data = {
            "tag_id": tag_id,
            "user_name": random.choice(["张三", "李四", "王五", "赵六", "钱七"]),
            "user_id": f"UID{random.randint(10000, 99999)}",
            "department": random.choice(["技术部", "市场部", "人事部", "财务部", "行政部"]),
            "points": random.randint(0, 5000),
            "balance": round(random.uniform(0, 500), 2),
            "issue_date": issue_date,
            "expire_date": expire_date,
            "additional_info": "这是一个示例RFID标签数据"
        }
        return sample_data

if __name__ == "__main__":
    # 注意: 此处的测试代码可能无法直接工作，因为它没有真实的串口对象
    # 且依赖于可能已过时或不适用的 RFIDProtocol 内部方法
    protocol = RFIDProtocol() 
    # success, data = protocol.read_tag(0) # 需要传入 channel
    # if success:
    #     print("读取标签成功 (原始字节):", binascii.hexlify(data))
    # else:
    #     print(f"读取标签失败: {data}")
    print("rfid_protocol.py self-test section needs review for current protocol.") 