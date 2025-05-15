#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyQt5测试脚本
"""

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout

def main():
    # 创建应用
    app = QApplication(sys.argv)
    
    # 创建窗口
    window = QWidget()
    window.setWindowTitle("PyQt5测试")
    window.setGeometry(100, 100, 400, 200)
    
    # 创建布局
    layout = QVBoxLayout()
    
    # 创建标签
    label = QLabel("如果您能看到这个窗口，说明PyQt5工作正常！")
    label.setStyleSheet("font-size: 16px;")
    
    # 添加标签到布局
    layout.addWidget(label)
    
    # 设置窗口布局
    window.setLayout(layout)
    
    # 显示窗口
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 