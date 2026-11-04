#!/bin/sh
set -e

# Tự động khởi tạo .env từ .env.example nếu chưa có trong container
if [ ! -f /app/.env ] && [ -f /app/.env.example ]; then
    cp /app/.env.example /app/.env
fi

APP_PORT="${PORT:-8000}"
NAME="${APP_NAME:-Voxify}"

echo ""
echo "=========================================================="
echo "  🚀 $NAME Container Ready!"
echo "  ➜  Local:   http://localhost:${APP_PORT}/"
echo "  ➜  Docs:    http://localhost:${APP_PORT}/docs"
echo "=========================================================="
echo ""

# Thực thi lệnh chính của container (CMD)
exec "$@"
