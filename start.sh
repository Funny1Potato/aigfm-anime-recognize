#!/usr/bin/env bash
# aigfm-anime-recognize 启动（Linux/macOS）
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/uvicorn ]; then
    echo "未找到虚拟环境 .venv，请先运行 ./install.sh 完成安装。" >&2
    exit 1
fi

echo "启动服务（默认 0.0.0.0:8000，Ctrl+C 停止）..."
echo "提示：正式部署建议用 systemd/nohup 托管，例如："
echo "  nohup .venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000 >> serve.log 2>&1 &"
.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
