@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
    echo 未找到虚拟环境 .venv，请先运行 install.bat 完成安装。
    exit /b 1
)

echo 启动服务（默认 0.0.0.0:8000，Ctrl+C 停止）...
echo 提示：正式部署建议用 NSSM/计划任务托管，或用下面命令直接起：
echo   .venv\Scripts\python -m uvicorn server:app --host 0.0.0.0 --port 8000
.venv\Scripts\python -m uvicorn server:app --host 0.0.0.0 --port 8000
