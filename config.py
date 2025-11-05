import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot Token (получить у @BotFather)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Binance API (опционально, для получения данных используем публичный API)
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')

# ✅ НОВОЕ: Режим торговли по умолчанию
TRADING_MODE = os.getenv('TRADING_MODE', 'swing')  # 'swing' или 'day'

# Настройки торговой пары
SYMBOL = 'BTC/USDT'
TIMEFRAME = '5m'  # 5-минутные свечи (будет меняться динамически)

# Параметры анализа
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BOLLINGER_PERIOD = 20
VOLUME_MA_PERIOD = 20

# Пороги для сигналов
PUMP_THRESHOLD = 0.70  # 70% вероятность для сигнала PUMP
DUMP_THRESHOLD = 0.70  # 70% вероятность для сигнала DUMP

# Минимальное изменение цены для классификации (в процентах)
MIN_PRICE_CHANGE_PUMP = 3.0  # 3% рост
MIN_PRICE_CHANGE_DUMP = -3.0  # 3% падение

# Интервал проверки (в секундах)
CHECK_INTERVAL = 300  # 5 минут

# ✅ НОВОЕ: Параметры для разных режимов торговли
MODE_CONFIGS = {
    'swing': {
        'timeframe': '5m',
        'check_interval': 300,  # 5 минут
        'pump_threshold': 0.70,
        'dump_threshold': 0.70,
        'min_price_change': 3.0
    },
    'day': {
        'timeframe': '1m',
        'check_interval': 60,   # 1 минута
        'pump_threshold': 0.75,  # Выше порог для большей точности
        'dump_threshold': 0.75,
        'min_price_change': 1.5  # Меньше минимальное изменение
    }
}

# База данных
DB_PATH = 'btc_signals.db'

# Fear & Greed API
FEAR_GREED_API = 'https://api.alternative.me/fng/'

# ✅ НОВОЕ: Telegram Rate Limits
TELEGRAM_QPS = 20  # queries per second
TELEGRAM_BATCH_SIZE = 10  # размер батча для отправки сообщений

# Логирование
LOG_LEVEL = 'INFO'
LOG_FILE = 'bot.log'