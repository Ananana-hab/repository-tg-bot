#!/bin/bash
#
# Скрипт деплоя/обновления бота на production сервере
# Использовать: sudo ./deploy.sh
#

set -e

# Конфигурация
BOT_DIR="/opt/btc-bot"
SERVICE_NAME="btc-bot"
VENV_DIR="$BOT_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo "BTC Pump/Dump Bot - Deployment Script"
echo -e "==========================================${NC}"
echo "Started at: $(date)"
echo ""

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Проверка существования директории
if [ ! -d "$BOT_DIR" ]; then
    echo -e "${RED}Error: Bot directory not found: $BOT_DIR${NC}"
    exit 1
fi

cd "$BOT_DIR"

# Шаг 1: Остановка бота
echo -e "${YELLOW}[1/7] Stopping bot service...${NC}"
if systemctl is-active --quiet $SERVICE_NAME; then
    systemctl stop $SERVICE_NAME
    echo -e "${GREEN}✓ Service stopped${NC}"
else
    echo "Service is not running"
fi

# Шаг 2: Создание бэкапа БД перед обновлением
echo ""
echo -e "${YELLOW}[2/7] Creating database backup...${NC}"
if [ -f "$BOT_DIR/btc_signals.db" ]; then
    BACKUP_FILE="$BOT_DIR/backups/pre_deploy_$(date +%Y%m%d_%H%M%S).db.gz"
    mkdir -p "$BOT_DIR/backups"
    gzip -c "$BOT_DIR/btc_signals.db" > "$BACKUP_FILE"
    echo -e "${GREEN}✓ Backup created: $BACKUP_FILE${NC}"
else
    echo "No database file found (first deploy?)"
fi

# Шаг 3: Обновление кода
echo ""
echo -e "${YELLOW}[3/7] Updating code from repository...${NC}"
if [ -d ".git" ]; then
    git fetch origin
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    echo "Current branch: $CURRENT_BRANCH"
    git pull origin $CURRENT_BRANCH
    echo -e "${GREEN}✓ Code updated${NC}"
else
    echo -e "${YELLOW}Warning: Not a git repository, skipping git pull${NC}"
fi

# Шаг 4: Обновление зависимостей
echo ""
echo -e "${YELLOW}[4/7] Updating Python dependencies...${NC}"
if [ -f "$PIP_BIN" ]; then
    $PIP_BIN install --upgrade pip
    $PIP_BIN install -r requirements.txt --upgrade
    echo -e "${GREEN}✓ Dependencies updated${NC}"
else
    echo -e "${RED}Error: Virtual environment not found${NC}"
    exit 1
fi

# Шаг 5: Проверка конфигурации
echo ""
echo -e "${YELLOW}[5/7] Validating configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Проверка синтаксиса Python
if $PYTHON_BIN -c "import config; print('Config OK')" 2>/dev/null; then
    echo -e "${GREEN}✓ Configuration valid${NC}"
else
    echo -e "${RED}Error: Configuration validation failed${NC}"
    exit 1
fi

# Шаг 6: Установка прав доступа
echo ""
echo -e "${YELLOW}[6/7] Setting file permissions...${NC}"
chown -R btcbot:btcbot "$BOT_DIR"
chmod 600 "$BOT_DIR/.env"
chmod +x "$BOT_DIR/deployment/"*.sh
echo -e "${GREEN}✓ Permissions set${NC}"

# Шаг 7: Запуск бота
echo ""
echo -e "${YELLOW}[7/7] Starting bot service...${NC}"
systemctl daemon-reload
systemctl start $SERVICE_NAME
sleep 3

# Проверка статуса
if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✓ Service started successfully${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo "Checking logs..."
    journalctl -u $SERVICE_NAME -n 20 --no-pager
    exit 1
fi

# Smoke test: проверка healthcheck
echo ""
echo -e "${YELLOW}Running smoke test...${NC}"
sleep 5
if curl -s http://localhost:8080/health | grep -q "OK"; then
    echo -e "${GREEN}✓ Healthcheck passed${NC}"
else
    echo -e "${YELLOW}Warning: Healthcheck not responding (bot may still be starting)${NC}"
fi

# Финальный статус
echo ""
echo -e "${BLUE}=========================================="
echo "Deployment Summary"
echo -e "==========================================${NC}"
systemctl status $SERVICE_NAME --no-pager -l
echo ""
echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
echo "Finished at: $(date)"
echo ""
echo "Useful commands:"
echo "  View logs:    journalctl -u $SERVICE_NAME -f"
echo "  Stop bot:     systemctl stop $SERVICE_NAME"
echo "  Restart bot:  systemctl restart $SERVICE_NAME"
echo "  Check status: systemctl status $SERVICE_NAME"
echo -e "${BLUE}==========================================${NC}"

exit 0
