#!/bin/sh
set -e

# ==============================================================================
# Script sao lưu tự động cơ sở dữ liệu PostgreSQL cho Voxify
# ==============================================================================

BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/voxify_db_${TIMESTAMP}.sql.gz"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

HOST="${POSTGRES_HOST:-localhost}"
PORT="${POSTGRES_PORT:-5432}"
USER="${POSTGRES_USER:-voxify_user}"
DB="${POSTGRES_DB:-voxify_prod}"

mkdir -p "${BACKUP_DIR}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Bắt đầu sao lưu database ${DB} từ host ${HOST}..."

# Export PGPASSWORD để pg_dump không nhắc mật khẩu
export PGPASSWORD="${POSTGRES_PASSWORD}"

# Thực hiện pg_dump và nén gzip
pg_dump -h "${HOST}" -p "${PORT}" -U "${USER}" -d "${DB}" --clean --if-exists | gzip > "${BACKUP_FILE}"

FILESIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sao lưu thành công: ${BACKUP_FILE} (Kích thước: ${FILESIZE})"

# Xóa các bản sao lưu cũ hơn RETENTION_DAYS ngày
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Đang dọn dẹp các bản backup cũ hơn ${RETENTION_DAYS} ngày..."
find "${BACKUP_DIR}" -type f -name "voxify_db_*.sql.gz" -mtime +"${RETENTION_DAYS}" -exec rm -f {} \;

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Quá trình sao lưu và dọn dẹp hoàn tất."
