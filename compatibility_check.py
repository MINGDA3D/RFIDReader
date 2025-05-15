#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RFID读写器管理软件兼容性检查
"""

import sys
import tkinter as tk
from tkinter import messagebox
import subprocess

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    return version.major == 3 and 6 <= version.minor <= 10

def check_pyqt_compatibility():
    """检查PyQt5兼容性"""
    try:
        import PyQt5
        return True
    except ImportError:
        return False

def main():
    # 创建根窗口但不显示
    root = tk.Tk()
    root.withdraw()
    
    # 检查Python版本
    if not check_python_version():
        messagebox.showerror(
            "版本不兼容", 
            f"当前Python版本 {sys.version} 不兼容\n"
            f"RFID读写器管理软件需要Python 3.6-3.10版本\n"
            f"请安装兼容的Python版本后重试"
        )
        return 1
        
    # 检查PyQt5兼容性
    if not check_pyqt_compatibility():
        messagebox.showerror(
            "缺少依赖", 
            "无法导入PyQt5模块\n"
            "请确保已正确安装PyQt5:\n"
            "pip install PyQt5==5.15.9"
        )
        return 1
        
    # 尝试启动应用
    try:
        messagebox.showinfo(
            "兼容性检查", 
            "兼容性检查通过！\n"
            "现在将尝试启动应用程序...\n"
            "如果应用程序没有显示，请检查控制台输出是否有错误信息。"
        )
        
        # 尝试导入并运行主程序
        import main
        return 0
        
    except Exception as e:
        messagebox.showerror(
            "启动错误", 
            f"启动应用程序时出错:\n{str(e)}\n"
            f"请联系开发者获取帮助。"
        )
        return 1

if __name__ == "__main__":
    sys.exit(main()) 