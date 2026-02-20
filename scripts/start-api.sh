#!/usr/bin/env bash
# 手动启动后端 API（非 Docker 环境）
# 使用前请确保已安装 uv、Python 3.12+，并已配置 .env（见 docs/vibe/manual-setup.md）

set -e
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "Error: .env not found. Copy .env.template to .env and fill in manual_setup section."
  exit 1
fi

# 非 Docker 环境，不设置 RUNNING_IN_DOCKER，应用会使用 MODEL_DIR 及 localhost 等默认值
export RUNNING_IN_DOCKER=false

echo "Starting API at http://0.0.0.0:5050 ..."
exec uv run uvicorn server.main:app --host 0.0.0.0 --port 5050 --reload
