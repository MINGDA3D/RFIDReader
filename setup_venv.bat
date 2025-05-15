@echo off
echo 正在检查Python环境...

REM 检查是否已安装Python
python --version 2>nul
if %errorlevel% neq 0 (
    echo 错误：未检测到Python
    echo 请确保Python已安装并添加到PATH中
    echo 您可以从以下地址下载Python：https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 清理旧的虚拟环境
if exist venv (
    echo 检测到已存在的虚拟环境
    choice /C YN /M "是否删除并重新创建虚拟环境？这将删除所有已安装的依赖 (Y/N)"
    if errorlevel 1 (
        if errorlevel 2 (
            echo 继续使用现有虚拟环境
        ) else (
            echo 正在删除旧的虚拟环境...
            rmdir /S /Q venv
            echo 已删除旧的虚拟环境
        )
    )
)

REM 创建虚拟环境
if not exist venv (
    echo 正在创建虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo 创建虚拟环境失败，请确保已安装venv模块
        echo 您可以尝试运行: python -m pip install virtualenv
        pause
        exit /b 1
    )
)

REM 激活虚拟环境并安装依赖
echo 正在激活虚拟环境...
call venv\Scripts\activate.bat

echo 正在更新pip...
python -m pip install --upgrade pip

echo 正在安装依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 安装依赖失败，请检查网络连接或requirements.txt文件
    echo 您可以尝试使用国内镜像源：
    echo pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    choice /C YN /M "是否尝试使用国内镜像源安装？(Y/N)"
    if errorlevel 1 (
        if errorlevel 2 (
            echo 已取消安装
            pause
            exit /b 1
        ) else (
            pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
            if %errorlevel% neq 0 (
                echo 使用国内镜像源安装依赖仍然失败
                pause
                exit /b 1
            )
        )
    )
)

echo 环境设置完成！

REM 运行程序
echo 正在启动RFID读写器管理软件...
python main.py

REM 保持命令窗口打开
pause 