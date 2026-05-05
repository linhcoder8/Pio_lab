#!/usr/bin/env bash
# Workaround tạm cho Portable Export (Phase 1)
# Dùng đến khi Phase 2+ build module export chuyên dụng

set -e
cd "$(dirname "$0")/.."

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

set -a
source .env 2>/dev/null || true
set +a

echo "[1/3] Backing up files..."
tar czf "$BACKUP_DIR/files_$DATE.tar.gz" \
    config/ vault/ .env 2>/dev/null

echo "[2/3] Dumping Postgres..."
PGPASSWORD="${POSTGRES_PASSWORD:-changeme}" pg_dump \
    -h "${POSTGRES_HOST:-localhost}" \
    -p "${POSTGRES_PORT:-5432}" \
    -U "${POSTGRES_USER:-pio_lab}" \
    "${POSTGRES_DB:-pio_lab}" \
    > "$BACKUP_DIR/db_$DATE.sql"

echo "[3/3] Done"
echo "Files: $BACKUP_DIR/files_$DATE.tar.gz"
echo "  DB : $BACKUP_DIR/db_$DATE.sql"
