#!/bin/sh
set -e

# Tự động khởi tạo .env từ .env.example nếu chưa có trong container
if [ ! -f /app/.env ] && [ -f /app/.env.example ]; then
    cp /app/.env.example /app/.env
fi

# Thực thi lệnh chính của container (CMD)
exec "$@"
