#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RFID读写器管理软件启动脚本
"""

import sys
import os
import subprocess

def main():
    # 检查Python版本
    if sys.version_info < (3, 6):
        print("错误: 需要Python 3.6或更高版本。")
        return 1
        
    # 检查依赖
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except subprocess.CalledProcessError:
        print("错误: 安装依赖失败。")
        return 1
        
    # 启动主程序
    try:
        import main
        return 0
    except ImportError as e:
        print(f"错误: 导入主程序失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 