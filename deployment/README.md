# 🚀 BTC Pump/Dump Bot - Deployment Guide

Полное руководство по развертыванию бота на production сервере.

---

## 📋 Требования к серверу

### Минимальные:
- **OS:** Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **CPU:** 1 core
- **RAM:** 512 MB
- **Disk:** 2 GB
- **Network:** Доступ к Telegram API и Binance API

### Рекомендуемые:
- **CPU:** 2 cores
- **RAM:** 1 GB
- **Disk:** 5 GB (с местом под логи и бэкапы)

---

## 🔧 Быстрая установка (Ubuntu/Debian)

### 1. Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Установка Python 3.10+

```bash
sudo apt install -y python3 python3-pip python3-venv git
python3 --version  # Проверка версии
```

### 3. Клонирование проекта

```bash
cd /opt
sudo git clone <YOUR_REPO_URL> btc-bot
cd btc-bot
```

### 4. Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Настройка конфигурации

```bash
cp .env.example .env
nano .env
```

**Обязательно заполните:**
- `TELEGRAM_BOT_TOKEN` - получить у @BotFather
- `TRADING_MODE` - `swing` или `day`
- `ENVIRONMENT` - `production`

**Опционально:**
- `ALERT_TELEGRAM_CHAT_ID` - ваш Telegram ID для алертов

### 6. Проверка работоспособности

```bash
python main.py
```

Нажмите `Ctrl+C` для остановки, если всё работает.

---

## 🔒 Настройка прав доступа

```bash
# Создаём пользователя для бота
sudo useradd -r -s /bin/false btcbot

# Устанавливаем права
sudo chown -R btcbot:btcbot /opt/btc-bot
sudo chmod 600 /opt/btc-bot/.env
```

---

## 🔄 Установка systemd service (автозапуск)

### 1. Создание service файла

```bash
sudo cp /opt/btc-bot/deployment/btc-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 2. Включение и запуск

```bash
sudo systemctl enable btc-bot
sudo systemctl start btc-bot
```

### 3. Проверка статуса

```bash
sudo systemctl status btc-bot
```

---

## 📊 Мониторинг

### Проверка логов

```bash
# Все логи
sudo journalctl -u btc-bot -f

# Только ошибки
sudo journalctl -u btc-bot -p err -f

# Логи из файла
tail -f /opt/btc-bot/bot.log
```

### Healthcheck endpoints

Бот предоставляет HTTP эндпоинты для мониторинга:

```bash
# Проверка жизнеспособности
curl http://localhost:8080/health

# Проверка готовности
curl http://localhost:8080/ready

# Метрики
curl http://localhost:8080/metrics
```

---

## 🔄 Управление ботом

```bash
# Запуск
sudo systemctl start btc-bot

# Остановка
sudo systemctl stop btc-bot

# Перезапуск
sudo systemctl restart btc-bot

# Статус
sudo systemctl status btc-bot

# Отключить автозапуск
sudo systemctl disable btc-bot
```

---

## 📦 Обновление бота

```bash
cd /opt/btc-bot
sudo systemctl stop btc-bot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl start btc-bot
sudo systemctl status btc-bot
```

---

## 💾 Настройка бэкапов

### 1. Установка cron задачи

```bash
sudo cp /opt/btc-bot/deployment/backup.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/backup.sh
sudo crontab -e
```

Добавьте строку:

```
0 3 * * * /usr/local/bin/backup.sh
```

Бэкапы будут создаваться ежедневно в 3:00 AM.

### 2. Ручной бэкап

```bash
sudo /usr/local/bin/backup.sh
```

Бэкапы сохраняются в `/opt/btc-bot/backups/`

---

## 🔍 Troubleshooting

### Бот не запускается

```bash
# Проверьте логи
sudo journalctl -u btc-bot -n 50

# Проверьте конфигурацию
python -c "import config; print('Config OK')"

# Проверьте токен
cat .env | grep TELEGRAM_BOT_TOKEN
```

### Healthcheck не отвечает

```bash
# Проверьте что порт открыт
sudo netstat -tlnp | grep 8080

# Проверьте firewall
sudo ufw status
```

### Нет сигналов

```bash
# Проверьте логи анализа
tail -f bot.log | grep "Analysis complete"

# Проверьте подключение к Binance
curl https://api.binance.com/api/v3/ping
```

### Высокое использование памяти

```bash
# Проверьте метрики
curl http://localhost:8080/metrics

# Перезапустите бота
sudo systemctl restart btc-bot
```

---

## 🔐 Безопасность

### 1. Firewall

```bash
sudo ufw allow ssh
sudo ufw allow 8080/tcp  # Healthcheck (только для monitoring)
sudo ufw enable
```

### 2. Обновление токена

```bash
# 1. Создайте новый токен у @BotFather
# 2. Обновите .env
nano .env
# 3. Перезапустите
sudo systemctl restart btc-bot
```

### 3. Ограничение логов

```bash
# Настройка ротации в systemd
sudo nano /etc/systemd/journald.conf
```

Установите:
```
SystemMaxUse=500M
MaxRetentionSec=7day
```

---

## 📈 Опциональные улучшения

### 1. Nginx reverse proxy (для webhook)

```bash
sudo apt install nginx
sudo nano /etc/nginx/sites-available/btc-bot
```

### 2. Let's Encrypt SSL (для webhook)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. Monitoring с alerting

Запустите monitoring процесс:

```bash
cd /opt/btc-bot
source venv/bin/activate
python monitoring.py &
```

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `sudo journalctl -u btc-bot -f`
2. Проверьте конфигурацию: файл `.env`
3. Проверьте healthcheck: `curl http://localhost:8080/metrics`

---

## 📝 Чеклист после установки

- [ ] Python 3.10+ установлен
- [ ] Зависимости установлены (`requirements.txt`)
- [ ] `.env` файл настроен с валидным токеном
- [ ] Права на файлы корректны (`.env` = 600)
- [ ] Systemd service включен
- [ ] Бот запущен и работает
- [ ] Healthcheck отвечает на `/health`
- [ ] Логи пишутся в `bot.log`
- [ ] Бэкапы настроены (cron)
- [ ] Firewall настроен

---

**✅ Готово! Бот развернут на production!**
