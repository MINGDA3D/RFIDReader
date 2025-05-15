@echo off
echo ============================================================
echo RFID读写器管理软件 - 兼容性指南
echo ============================================================
echo.
echo 检测到您正在使用 Python 3.13.3 版本
echo.
echo 问题: RFID读写器管理软件需要 Python 3.6-3.10 版本才能正常运行
echo       PyQt5 5.15.9 与 Python 3.13.3 不兼容
echo.
echo 解决方案:
echo.
echo 1. 安装兼容的Python版本:
echo    - 下载并安装 Python 3.9 或 3.10
echo    - 下载地址: https://www.python.org/downloads/
echo.
echo 2. 使用兼容的Python版本安装依赖:
echo    - 打开命令提示符
echo    - 运行: python -m pip install -r requirements.txt
echo.
echo 3. 使用兼容的Python版本运行程序:
echo    - 运行: python3.9 main.py
echo    或
echo    - 运行: python3.10 main.py
echo.
echo ============================================================
echo.
pause 