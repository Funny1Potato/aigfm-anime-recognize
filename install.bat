@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0

echo [1/3] 创建虚拟环境 .venv ...
if not exist .venv (
    python -m venv .venv || goto :fail
)

echo [2/3] 安装依赖（钉版本，首次约几分钟）...
.venv\Scripts\python -m pip install --upgrade pip || goto :fail
.venv\Scripts\python -m pip install -r requirements.txt || goto :fail

echo [3/3] 预热：下载并加载 WD14 模型（约 446MB）...
REM 国内环境用 hf-mirror 镜像；国外直连可注释掉下一行
set HF_ENDPOINT=https://hf-mirror.com
.venv\Scripts\python -c "from tagging import prewarm; prewarm()" || goto :fail

echo.
echo 安装完成。运行 start.bat 启动服务。
goto :eof

:fail
echo 安装失败，请检查上方错误输出。
exit /b 1
