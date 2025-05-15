# RFID读写器管理软件

这是一个基于PyQt5的RFID读写器桌面应用程序，用于读写RFID标签信息。

## 功能

- 连接/断开RFID读写器
- 读取标签信息
- 写入标签信息
- 实时日志显示

## 系统要求

- **Python版本**: 3.6 - 3.10 (不支持Python 3.11及以上版本)
- Windows 7/8/10/11

## 安装

1. 确保已安装Python 3.6-3.10
2. 安装所需依赖：

```bash
pip install -r requirements.txt
```

## 运行

### 正常模式

双击`start.bat`文件或运行：

```bash
python run.py
```

### 测试模式

如果没有实际的RFID读写器硬件，可以使用测试模式来测试软件功能。
测试模式使用虚拟串口和模拟数据。

双击`start_test_mode.bat`文件或运行：

```bash
python test_mode.py
```

### 兼容性问题

如果遇到兼容性问题，请运行：

```bash
compatibility_guide.bat
```

这将提供详细的兼容性信息和解决方案。

## 项目结构

- `main.py` - 主程序文件
- `rfid_protocol.py` - RFID通信协议模块
- `test_mode.py` - 测试模式模块
- `run.py` - 启动脚本
- `requirements.txt` - 依赖列表
- `start.bat` - Windows启动批处理文件
- `start_test_mode.bat` - 测试模式启动批处理文件
- `compatibility_guide.bat` - 兼容性指南

## 技术说明

- 使用PyQt5构建GUI界面
- 使用PySerial进行串口通信
- 多线程处理串口通信，确保界面响应
- 模块化设计，便于扩展

## 界面说明

- 顶部栏：显示应用程序名称
- 连接操作区：用于选择端口和连接读写器
- 标签信息表单：显示和编辑标签信息
- 日志输出区：显示操作日志 