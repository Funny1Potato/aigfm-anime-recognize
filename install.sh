#!/usr/bin/env bash
# aigfm-anime-recognize 一键部署（Linux/macOS）
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/4] 创建虚拟环境 .venv ..."
[ -d .venv ] || python3 -m venv .venv

echo "[2/4] 安装依赖（钉版本，首次约几分钟）..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "[3/4] 预热：下载并加载 WD14 模型（约 446MB）..."
# 国内环境用 hf-mirror 镜像；国外直连可注释掉下一行
export HF_ENDPOINT=https://hf-mirror.com
.venv/bin/python -c "from tagging import prewarm; prewarm()"

echo "[4/4] 启动服务（默认 0.0.0.0:8000，Ctrl+C 停止）..."
echo "提示：正式部署建议用 systemd/nohup 托管，例如："
echo "  nohup .venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000 >> serve.log 2>&1 &"
.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
