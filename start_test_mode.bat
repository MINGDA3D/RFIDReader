@echo off
echo 正在启动RFID读写器管理软件（测试模式）...
echo ============================================

:: 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未检测到Python安装。
    echo 请安装Python 3.6或更高版本。
    echo 可从 https://www.python.org/downloads/ 下载。
    pause
    exit /b 1
)

:: 检查Python版本
python -c "import sys; print('Python版本检查: ', sys.version_info >= (3,6) and sys.version_info < (3,11))" > version_check.tmp
findstr "True" version_check.tmp > nul
if %errorlevel% neq 0 (
    echo 错误: 不兼容的Python版本。
    echo 当前程序需要Python 3.6-3.10版本。
    echo 您当前的Python版本可能过高或过低。
    echo.
    echo 请运行compatibility_guide.bat获取详细指导。
    del version_check.tmp
    pause
    exit /b 1
)
del version_check.tmp

:: 安装依赖
python -m pip install -r requirements.txt

:: 执行测试模式启动脚本
python test_mode.py

if %errorlevel% neq 0 (
    echo 应用程序启动失败。
    echo 请运行compatibility_guide.bat获取详细指导。
    pause
)

exit /b 0 