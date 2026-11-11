#!/usr/bin/env bash
set -e

echo "==> [Voxify] Initializing service..."

# Tự động chạy database migration nếu bật (mặc định bật)
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "==> Running database migrations: alembic upgrade head"
  MAX_RETRIES=5
  COUNT=0
  until alembic upgrade head || [ $COUNT -eq $MAX_RETRIES ]; do
    COUNT=$((COUNT + 1))
    echo "==> Migration failed, retrying in 3 seconds ($COUNT/$MAX_RETRIES)..."
    sleep 3
  done

  if [ $COUNT -eq $MAX_RETRIES ]; then
    echo "==> [ERROR] Database migrations failed after $MAX_RETRIES attempts."
    exit 1
  fi
  echo "==> Database migrations completed successfully."
fi

# Thực thi lệnh chính của container
echo "==> Executing container command: $@"
exec "$@"
