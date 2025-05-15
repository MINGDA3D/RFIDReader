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

class RFIDProtocol:
    """RFID读写器通信协议处理类"""
    
    # 命令字
    CMD_READ = 0x01  # 读取标签
    CMD_WRITE = 0x02  # 写入标签
    CMD_SCAN = 0x03  # 扫描标签
    
    # 状态码
    STATUS_SUCCESS = 0x00  # 成功
    STATUS_ERROR = 0x01  # 一般错误
    STATUS_NO_TAG = 0x02  # 无标签
    STATUS_READ_ERROR = 0x03  # 读取错误
    STATUS_WRITE_ERROR = 0x04  # 写入错误
    
    def __init__(self, serial_port=None):
        """初始化RFID协议处理器"""
        self.serial_port = serial_port
        
    def set_serial(self, serial_port):
        """设置串口"""
        self.serial_port = serial_port
        
    def _calculate_checksum(self, data):
        """计算数据校验和"""
        return sum(data) & 0xFF
        
    def _build_packet(self, cmd, data=None):
        """构建数据包"""
        if data is None:
            data = []
            
        # 帧头 (2字节) + 命令 (1字节) + 长度 (1字节) + 数据 + 校验和 (1字节)
        frame_header = [0xAA, 0x55]
        length = len(data)
        
        packet = frame_header + [cmd, length] + data
        checksum = self._calculate_checksum(packet)
        packet.append(checksum)
        
        return bytes(packet)
        
    def _parse_packet(self, packet_bytes):
        """解析数据包"""
        if len(packet_bytes) < 5:  # 帧头(2) + 命令(1) + 长度(1) + 校验和(1)
            return None, "数据包长度错误"
            
        # 验证帧头
        if packet_bytes[0] != 0xAA or packet_bytes[1] != 0x55:
            return None, "帧头错误"
            
        # 获取命令和长度
        cmd = packet_bytes[2]
        length = packet_bytes[3]
        
        # 验证长度
        if len(packet_bytes) != length + 5:
            return None, "数据长度不匹配"
            
        # 计算并验证校验和
        received_checksum = packet_bytes[-1]
        calculated_checksum = self._calculate_checksum(packet_bytes[:-1])
        
        if received_checksum != calculated_checksum:
            return None, "校验和错误"
            
        # 提取数据
        data = packet_bytes[4:-1]
        
        return {"cmd": cmd, "data": data}, None
        
    def read_tag(self):
        """读取标签信息"""
        if not self.serial_port:
            return False, "串口未设置"
            
        try:
            # 构建读取标签命令包
            packet = self._build_packet(self.CMD_READ)
            
            # 发送命令
            self.serial_port.write(packet)
            
            # 等待响应
            time.sleep(0.2)
            
            # 在实际应用中应该有一个合适的超时和重试机制
            if self.serial_port.in_waiting:
                response = self.serial_port.read(self.serial_port.in_waiting)
                result, error = self._parse_packet(response)
                
                if error:
                    return False, error
                    
                if result["cmd"] == self.CMD_READ:
                    if result["data"][0] == self.STATUS_SUCCESS:
                        # 解析标签数据
                        return True, self._parse_tag_data(result["data"][1:])
                    elif result["data"][0] == self.STATUS_NO_TAG:
                        return False, "未检测到标签"
                    else:
                        return False, f"读取标签失败，错误码: {result['data'][0]}"
                        
            # 模拟返回示例数据
            return True, self._get_sample_tag_data()
            
        except Exception as e:
            return False, f"读取标签异常: {str(e)}"
            
    def write_tag(self, tag_data):
        """写入标签信息"""
        if not self.serial_port:
            return False, "串口未设置"
            
        try:
            # 将数据转换为字节数据
            data_bytes = self._tag_data_to_bytes(tag_data)
            
            # 构建写入标签命令包
            packet = self._build_packet(self.CMD_WRITE, data_bytes)
            
            # 发送命令
            self.serial_port.write(packet)
            
            # 等待响应
            time.sleep(0.5)
            
            # 在实际应用中应该有一个合适的超时和重试机制
            if self.serial_port.in_waiting:
                response = self.serial_port.read(self.serial_port.in_waiting)
                result, error = self._parse_packet(response)
                
                if error:
                    return False, error
                    
                if result["cmd"] == self.CMD_WRITE:
                    if result["data"][0] == self.STATUS_SUCCESS:
                        return True, "标签写入成功"
                    elif result["data"][0] == self.STATUS_NO_TAG:
                        return False, "未检测到标签"
                    else:
                        return False, f"写入标签失败，错误码: {result['data'][0]}"
                        
            # 模拟写入成功
            return True, "标签写入成功"
            
        except Exception as e:
            return False, f"写入标签异常: {str(e)}"
            
    def _parse_tag_data(self, data_bytes):
        """解析标签数据"""
        # 在实际应用中，需要根据RFID标签的数据格式进行解析
        # 这里仅作为示例
        
        # 假设数据是JSON格式
        try:
            json_data = json.loads(data_bytes.decode('utf-8'))
            return json_data
        except:
            # 如果不是JSON，返回示例数据
            return self._get_sample_tag_data()
            
    def _tag_data_to_bytes(self, tag_data):
        """将标签数据转换为字节数据"""
        # 在实际应用中，需要根据RFID标签的数据格式进行转换
        # 这里仅作为示例，将数据转换为JSON并编码为字节
        
        try:
            json_str = json.dumps(tag_data)
            return list(json_str.encode('utf-8'))
        except Exception as e:
            print(f"转换标签数据异常: {str(e)}")
            return []
            
    def _get_sample_tag_data(self):
        """获取示例标签数据"""
        # 生成随机的6位十六进制数作为标签ID
        tag_id = ''.join([f"{random.randint(0, 15):X}" for _ in range(6)])
        
        # 计算当前日期以及一年后日期
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


# 测试代码
if __name__ == "__main__":
    protocol = RFIDProtocol()
    success, data = protocol.read_tag()
    
    if success:
        print("读取标签成功:")
        for key, value in data.items():
            print(f"  {key}: {value}")
    else:
        print(f"读取标签失败: {data}")
        
    # 测试写入
    test_data = {
        "user_name": "测试用户",
        "user_id": "UID12345",
        "department": "测试部门",
        "points": 1000,
        "balance": 100.50,
        "issue_date": "2023-06-15",
        "expire_date": "2024-06-14",
        "additional_info": "这是测试数据"
    }
    
    success, message = protocol.write_tag(test_data)
    
    if success:
        print(message)
    else:
        print(f"写入标签失败: {message}") 