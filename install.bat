@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0

echo [1/4] 创建虚拟环境 .venv ...
if not exist .venv (
    python -m venv .venv || goto :fail
)

echo [2/4] 安装依赖（钉版本，首次约几分钟）...
.venv\Scripts\python -m pip install --upgrade pip || goto :fail
.venv\Scripts\python -m pip install -r requirements.txt || goto :fail

echo [3/4] 预热：下载并加载 WD14 模型（约 446MB）...
REM 国内环境用 hf-mirror 镜像；国外直连可注释掉下一行
set HF_ENDPOINT=https://hf-mirror.com
.venv\Scripts\python -c "from tagging import prewarm; prewarm()" || goto :fail

echo [4/4] 启动服务（默认 0.0.0.0:8000，Ctrl+C 停止）...
echo 提示：正式部署建议用 NSSM/计划任务托管本脚本，或用下面命令直接起：
echo   .venv\Scripts\python -m uvicorn server:app --host 0.0.0.0 --port 8000
.venv\Scripts\python -m uvicorn server:app --host 0.0.0.0 --port 8000
goto :eof

:fail
echo 部署失败，请检查上方错误输出。
exit /b 1
