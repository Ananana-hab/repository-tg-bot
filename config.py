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

# ✅ Day Trading константы (для совместимости с main.py)
DAY_TIMEFRAME = '1m'
DAY_LIMIT = 100
DAY_CHECK_INTERVAL = 60

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

# Day Trading специфические параметры
DAY_TRADING_CONFIG = {
    'volatility_threshold': 0.5,  # Минимальный % волатильности для активации сканирования
    'volume_increase_threshold': 2.0,  # Минимальное увеличение объема (множитель от среднего)
    'max_spread': 0.15,  # Максимально допустимый спред в %
    'min_24h_volume': 1000000,  # Минимальный 24ч объем в USDT
    
    # Параметры технического анализа
    'fast_ma': 5,  # Быстрая скользящая средняя для дейтрейдинга
    'slow_ma': 20,  # Медленная скользящая средняя
    'rsi_overbought': 75,  # Уровень перекупленности для RSI
    'rsi_oversold': 25,    # Уровень перепроданности для RSI
    
    # Тайминги
    'consolidation_period': 5,  # Период консолидации в минутах
    'trend_confirmation_candles': 3,  # Количество свечей для подтверждения тренда
    
    # Уведомления
    'notification_cooldown': 60,  # Минимальный интервал между уведомлениями (секунды)
    'price_update_interval': 30,  # Интервал обновления цены (секунды)
}

# Расширяем существующий MODE_CONFIGS для day trading
MODE_CONFIGS['day'].update({
    'volatility_settings': DAY_TRADING_CONFIG,
    'max_trades_per_day': 5,  # Максимальное количество сделок в день
    'session_profit_target': 2.0,  # Целевой % прибыли за сессию
    'session_stop_loss': -1.0,  # Стоп-лосс % для всей сессии
})

# Общие параметры безопасности
SAFETY_SETTINGS = {
    'max_daily_notifications': 20,  # Максимальное количество уведомлений в день
    'market_correlation_threshold': 0.7,  # Минимальная корреляция с рынком
    'volume_validation': True,  # Включить проверку объема
    'spread_validation': True,  # Включить проверку спреда
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