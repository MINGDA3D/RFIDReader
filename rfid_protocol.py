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
            
    def _tag_data_to_bytes(self, tag_data: dict) -> bytes:
        """
        将标签数据字典转换为符合RFID编码规则的112字节数据。
        前76字节根据提供的字段填充，后36字节用0x00填充。
        """
        buffer = bytearray()
        
        # Tag Version (2 bytes, uint16, big-endian)
        buffer.extend(struct.pack('>H', int(tag_data.get('tag_version', 0))))
        
        # Filament Manufacturer (16 bytes, ASCII, right-padded with \x00)
        manufacturer = tag_data.get('filament_manufacturer', '')
        buffer.extend(manufacturer.encode('ascii', errors='ignore')[:16].ljust(16, b'\x00'))
        
        # Material Name (16 bytes, ASCII, right-padded with \x00)
        material_name = tag_data.get('material_name', '')
        buffer.extend(material_name.encode('ascii', errors='ignore')[:16].ljust(16, b'\x00'))
        
        # Color Name (32 bytes, ASCII, right-padded with \x00)
        color_name = tag_data.get('color_name', '')
        buffer.extend(color_name.encode('ascii', errors='ignore')[:32].ljust(32, b'\x00'))
        
        # Diameter (Target) (2 bytes, uint16, big-endian)
        buffer.extend(struct.pack('>H', int(tag_data.get('diameter_target', 0))))
        
        # Weight (Nominal, grams) (2 bytes, uint16, big-endian)
        buffer.extend(struct.pack('>H', int(tag_data.get('weight_nominal', 0))))
        
        # Print Temp (C) (2 bytes, uint16, big-endian)
        buffer.extend(struct.pack('>H', int(tag_data.get('print_temp', 0))))
        
        # Bed Temp (C) (2 bytes, uint16, big-endian)
        buffer.extend(struct.pack('>H', int(tag_data.get('bed_temp', 0))))
        
        # Density (2 bytes, uint16, big-endian)
        buffer.extend(struct.pack('>H', int(tag_data.get('density', 0))))
        
        # 当前总字节数: 2+16+16+32+2+2+2+2+2 = 76字节
        # 填充到112字节
        if len(buffer) < 112:
            buffer.extend(b'\x00' * (112 - len(buffer)))
        
        return bytes(buffer[:112]) #确保正好112字节

    def write_tag(self, tag_data: dict, channel: int): # channel is 0-indexed
        """写入标签信息，使用 EF...FE 协议"""
        if not self.serial_port or not self.serial_port.is_open:
            return False, "串口未连接或未打开"

        try:
            data_to_write_bytes = self._tag_data_to_bytes(tag_data) # 112字节数据
            
            FH = b'\\xEF'
            LEN_VAL = 6 + len(data_to_write_bytes) # 6 = FH,LEN,CMDC,Channel,BCC,EOF
            LEN = struct.pack('B', LEN_VAL) # LEN_VAL should be 6 + 112 = 118 (0x76)
            CMDC = b'\\x12' # 写命令
            CHANNEL_BYTE = struct.pack('B', channel)
            EOF = b'\\xFE'

            # 计算BCC
            temp_frame_part = FH + LEN + CMDC + CHANNEL_BYTE + data_to_write_bytes
            bcc_val = 0
            for byte_val in temp_frame_part:
                bcc_val ^= byte_val
            BCC = struct.pack('B', (~bcc_val) & 0xFF)

            command_to_send = temp_frame_part + BCC + EOF

            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            bytes_written = self.serial_port.write(command_to_send)
            if bytes_written != len(command_to_send):
                return False, f"串口写入不足: 预期 {len(command_to_send)}, 实际 {bytes_written}"

            time.sleep(0.3) # 等待设备响应

            if self.serial_port.in_waiting > 0:
                response_bytes = self.serial_port.read(self.serial_port.in_waiting)
                
                # 解析响应 (预期7字节: EF, 07, 12, STA, CH, BCC, FE)
                if len(response_bytes) == 7 and \
                   response_bytes[0:1] == FH and \
                   response_bytes[1:2] == b'\\x07' and \
                   response_bytes[2:3] == CMDC and \
                   response_bytes[6:7] == EOF:
                    
                    # 校验BCC
                    resp_sta = response_bytes[3]
                    resp_channel_read = response_bytes[4]
                    resp_bcc_received = response_bytes[5]

                    bcc_check_data = response_bytes[0:5] # FH, LEN, CMDC, STA, CH
                    calculated_bcc_val = 0
                    for b_val in bcc_check_data:
                        calculated_bcc_val ^= b_val
                    calculated_bcc_byte = (~calculated_bcc_val) & 0xFF
                    
                    if calculated_bcc_byte == resp_bcc_received:
                        if resp_sta == 0x00:
                            return True, f"通道 {channel + 1} 写入成功"
                        elif resp_sta == 0x01:
                            return False, f"通道 {channel + 1} 写入失败: 块密钥错误/验证失败 (STA=0x01)"
                        elif resp_sta == 0x02:
                            return False, f"通道 {channel + 1} 写入失败: 无标签 (STA=0x02)"
                        else:
                            return False, f"通道 {channel + 1} 写入失败: 未知状态码 (STA=0x{resp_sta:02X})"
                    else:
                        return False, f"通道 {channel + 1} 写入响应BCC校验失败. Recv: {resp_bcc_received:02X}, Calc: {calculated_bcc_byte:02X}"
                else:
                    return False, f"通道 {channel + 1} 写入响应帧格式错误或长度不足. 收到: {binascii.hexlify(response_bytes).decode('ascii').upper()}"
            else:
                return False, f"通道 {channel + 1} 写入后无响应或响应超时"

        except serial.SerialTimeoutException:
            return False, f"通道 {channel + 1} 串口写入/读取操作超时"
        except serial.SerialException as se:
            return False, f"通道 {channel + 1} 串口通信错误: {str(se)}"
        except Exception as e:
            return False, f"通道 {channel + 1} 写入标签时发生未知异常: {str(e)}"

if __name__ == "__main__":
    protocol = RFIDProtocol() 
    print("rfid_protocol.py self-test section needs review for current protocol.")
    # 示例: 构造一个模拟的 tag_data
    # sample_tag_data = {
    #     'tag_version': 1000,
    #     'filament_manufacturer': "TestMake",
    #     'material_name': "TestMat",
    #     'color_name': "TestColorBlue",
    #     'diameter_target': 1750,
    #     'weight_nominal': 1000,
    #     'print_temp': 210,
    #     'bed_temp': 60,
    #     'density': 1240
    # }
    # 
    # # 模拟调用 _tag_data_to_bytes
    # try:
    #     byte_data = protocol._tag_data_to_bytes(sample_tag_data)
    # print(f"Generated byte data ({len(byte_data)} bytes): {binascii.hexlify(byte_data).decode('ascii')}")
    # except Exception as e:
    #     print(f"Error in _tag_data_to_bytes test: {e}")

    # 注意: write_tag 和 read_tag 需要一个实际的 serial.Serial 对象进行测试。
    # print("To test write_tag or read_tag, instantiate RFIDProtocol with a valid serial port.") 