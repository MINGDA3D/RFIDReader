@echo off
echo 正在启动RFID读写器管理软件...
echo =================================

:: 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未检测到Python安装。
    echo 请安装Python 3.6或更高版本。
    echo 可从 https://www.python.org/downloads/ 下载。
    pause
    exit /b 1
)

:: 执行启动脚本
python run.py

if %errorlevel% neq 0 (
    echo 应用程序启动失败。
    pause
)

exit /b 0 