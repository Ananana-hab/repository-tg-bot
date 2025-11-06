#!/bin/bash
#
# Скрипт автоматического бэкапа базы данных бота
# Создаёт ежедневные бэкапы с ротацией (хранит 7 дней)
#

set -e

# Конфигурация
BOT_DIR="/opt/btc-bot"
DB_FILE="$BOT_DIR/btc_signals.db"
BACKUP_DIR="$BOT_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/btc_signals_${DATE}.db.gz"
RETENTION_DAYS=7

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "BTC Bot Database Backup"
echo "=========================================="
echo "Started at: $(date)"
echo ""

# Проверка существования базы данных
if [ ! -f "$DB_FILE" ]; then
    echo -e "${RED}Error: Database file not found: $DB_FILE${NC}"
    exit 1
fi

# Создание папки для бэкапов если не существует
mkdir -p "$BACKUP_DIR"

# Создание бэкапа
echo "Creating backup..."
if gzip -c "$DB_FILE" > "$BACKUP_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Backup created: $BACKUP_FILE (${BACKUP_SIZE})${NC}"
else
    echo -e "${RED}✗ Failed to create backup${NC}"
    exit 1
fi

# Удаление старых бэкапов (старше RETENTION_DAYS)
echo ""
echo "Cleaning old backups (retention: $RETENTION_DAYS days)..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "btc_signals_*.db.gz" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)
echo "Deleted $DELETED_COUNT old backup(s)"

# Список текущих бэкапов
echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"/btc_signals_*.db.gz 2>/dev/null | tail -5 || echo "No backups found"

# Статистика использования диска
echo ""
echo "Disk usage in backup directory:"
du -sh "$BACKUP_DIR"

echo ""
echo "=========================================="
echo "Backup completed successfully!"
echo "Finished at: $(date)"
echo "=========================================="

exit 0
