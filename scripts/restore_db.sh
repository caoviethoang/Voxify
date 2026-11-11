#!/bin/sh
set -e

# ==============================================================================
# Script khôi phục cơ sở dữ liệu PostgreSQL cho Voxify
# Sử dụng: ./scripts/restore_db.sh /path/to/voxify_db_YYYYMMDD_HHMMSS.sql.gz
# ==============================================================================

if [ -z "$1" ]; then
  echo "Lỗi: Vui lòng cung cấp đường dẫn tới file backup!"
  echo "Cú pháp: $0 <duong_dan_file_backup.sql.gz>"
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "Lỗi: Không tìm thấy file backup tại: ${BACKUP_FILE}"
  exit 1
fi

HOST="${POSTGRES_HOST:-localhost}"
PORT="${POSTGRES_PORT:-5432}"
USER="${POSTGRES_USER:-voxify_user}"
DB="${POSTGRES_DB:-voxify_prod}"

echo "=================================================================="
echo "CẢNH BÁO: Thao tác này sẽ ghi đè toàn bộ dữ liệu trong database: ${DB}"
echo "File khôi phục: ${BACKUP_FILE}"
echo "Host: ${HOST}:${PORT}"
echo "=================================================================="

export PGPASSWORD="${POSTGRES_PASSWORD}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Bắt đầu khôi phục database..."

if echo "${BACKUP_FILE}" | grep -q '\.gz$'; then
  gunzip -c "${BACKUP_FILE}" | psql -h "${HOST}" -p "${PORT}" -U "${USER}" -d "${DB}"
else
  psql -h "${HOST}" -p "${PORT}" -U "${USER}" -d "${DB}" < "${BACKUP_FILE}"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Khôi phục dữ liệu thành công!"
