#!/usr/bin/env bash
# aigfm-anime-recognize 安装（Linux/macOS）：建 venv + 装依赖 + 预热模型
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/3] 创建虚拟环境 .venv ..."
[ -d .venv ] || python3 -m venv .venv

echo "[2/3] 安装依赖（钉版本，首次约几分钟）..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "[3/3] 预热：下载并加载 WD14 模型（约 446MB）..."
# 国内环境用 hf-mirror 镜像；国外直连可注释掉下一行
export HF_ENDPOINT=https://hf-mirror.com
.venv/bin/python -c "from tagging import prewarm; prewarm()"

echo
echo "安装完成。运行 ./start.sh 启动服务。"
