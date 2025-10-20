import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot Token (получить у @BotFather)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Binance API (опционально, для получения данных используем публичный API)
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')

# Настройки торговой пары
SYMBOL = 'BTC/USDT'
TIMEFRAME = '5m'  # 5-минутные свечи

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

# База данных
DB_PATH = 'btc_signals.db'

# Fear & Greed API
FEAR_GREED_API = 'https://api.alternative.me/fng/'

# Логирование
LOG_LEVEL = 'INFO'
LOG_FILE = 'bot.log'