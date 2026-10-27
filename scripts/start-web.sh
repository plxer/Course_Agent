#!/usr/bin/env bash
# 手动启动前端开发服务器（非 Docker 环境）
# 使用前请确保已安装 pnpm、Node 20+，并已先启动 API（scripts/start-api.sh）

set -e
cd "$(dirname "$0")/.."

# 前端请求通过 Vite 代理到后端，手动启动时 API 在本地 5050 端口
export VITE_API_URL=http://127.0.0.1:5050

echo "Starting web dev server (API proxy -> $VITE_API_URL) ..."
cd web && exec pnpm run server
