# RFID读写器管理软件 - 环境设置脚本

# 设置错误操作首选项
$ErrorActionPreference = "Stop"

Write-Host "正在检查Python环境..." -ForegroundColor Cyan

# 检查是否已安装Python
try {
    $pythonVersion = (python --version) 2>&1
    Write-Host "已检测到 $pythonVersion，继续执行..." -ForegroundColor Green
} catch {
    Write-Host "错误：未找到Python。请确保Python已安装并添加到PATH中。" -ForegroundColor Red
    Write-Host "您可以从以下地址下载Python：https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "按Enter键退出"
    exit 1
}

# 清理旧的虚拟环境
if (Test-Path -Path "venv") {
    Write-Host "检测到已存在的虚拟环境" -ForegroundColor Yellow
    $cleanVenv = Read-Host "是否删除并重新创建虚拟环境？这将删除所有已安装的依赖 (Y/N)"
    if ($cleanVenv -eq "Y" -or $cleanVenv -eq "y") {
        Write-Host "正在删除旧的虚拟环境..." -ForegroundColor Yellow
        Remove-Item -Path "venv" -Recurse -Force
        Write-Host "已删除旧的虚拟环境" -ForegroundColor Green
    } else {
        Write-Host "继续使用现有虚拟环境" -ForegroundColor Cyan
    }
}

# 创建虚拟环境
if (-not (Test-Path -Path "venv")) {
    Write-Host "正在创建虚拟环境..." -ForegroundColor Cyan
    try {
        python -m venv venv
    } catch {
        Write-Host "创建虚拟环境失败，请确保已安装venv模块" -ForegroundColor Red
        Write-Host "您可以尝试运行: python -m pip install virtualenv" -ForegroundColor Yellow
        Read-Host "按Enter键退出"
        exit 1
    }
}

# 激活虚拟环境
Write-Host "正在激活虚拟环境..." -ForegroundColor Cyan
try {
    & .\venv\Scripts\Activate.ps1
} catch {
    Write-Host "激活虚拟环境失败。请以管理员身份运行PowerShell并执行 Set-ExecutionPolicy RemoteSigned" -ForegroundColor Red
    Write-Host "或者尝试使用setup_venv.bat脚本替代" -ForegroundColor Yellow
    Read-Host "按Enter键退出"
    exit 1
}

# 更新pip
Write-Host "正在更新pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# 安装依赖
Write-Host "正在安装依赖..." -ForegroundColor Cyan
try {
    pip install -r requirements.txt
} catch {
    Write-Host "安装依赖失败，请检查网络连接或requirements.txt文件" -ForegroundColor Red
    Write-Host "您可以尝试使用国内镜像源：" -ForegroundColor Yellow
    Write-Host "pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple" -ForegroundColor Yellow
    
    $useMirror = Read-Host "是否尝试使用国内镜像源安装？(Y/N)"
    if ($useMirror -eq "Y" -or $useMirror -eq "y") {
        try {
            pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        } catch {
            Write-Host "使用国内镜像源安装依赖仍然失败" -ForegroundColor Red
            Read-Host "按Enter键退出"
            exit 1
        }
    } else {
        Write-Host "已取消安装" -ForegroundColor Red
        Read-Host "按Enter键退出"
        exit 1
    }
}

Write-Host "环境设置完成！" -ForegroundColor Green

# 运行程序
Write-Host "正在启动RFID读写器管理软件..." -ForegroundColor Cyan
python main.py

# 脚本结束
Write-Host "程序已退出" -ForegroundColor Yellow
Read-Host "按Enter键退出" 