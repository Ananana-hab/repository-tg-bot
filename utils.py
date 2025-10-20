"""
Вспомогательные утилиты для бота
"""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def format_price(price):
    """Форматирует цену для отображения"""
    return f"${price:,.2f}"

def format_percentage(value):
    """Форматирует процентное значение"""
    sign = '+' if value > 0 else ''
    return f"{sign}{value:.2f}%"

def format_timestamp(timestamp):
    """Форматирует timestamp для отображения"""
    return timestamp.strftime('%d.%m.%Y %H:%M:%S')

def calculate_profit_loss(entry_price, current_price, signal_type):
    """
    Рассчитывает прибыль/убыток от сигнала
    
    Args:
        entry_price: цена входа
        current_price: текущая цена
        signal_type: 'PUMP' или 'DUMP'
        
    Returns:
        dict: {'percent': float, 'profit': bool}
    """
    if signal_type == 'PUMP':
        change = ((current_price - entry_price) / entry_price) * 100
        profit = change > 0
    else:  # DUMP
        change = ((entry_price - current_price) / entry_price) * 100
        profit = change > 0
    
    return {
        'percent': abs(change),
        'profit': profit
    }

def get_emoji_for_value(value, thresholds):
    """
    Возвращает эмодзи на основе значения и порогов
    
    Args:
        value: числовое значение
        thresholds: dict с порогами {'low': 30, 'high': 70}
    """
    if value < thresholds['low']:
        return '🟢'
    elif value > thresholds['high']:
        return '🔴'
    else:
        return '🟡'

def validate_config():
    """Проверяет корректность конфигурации"""
    import config
    
    errors = []
    
    if config.TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        errors.append("Telegram Bot Token не настроен")
    
    if config.PUMP_THRESHOLD < 0 or config.PUMP_THRESHOLD > 1:
        errors.append("PUMP_THRESHOLD должен быть между 0 и 1")
    
    if config.DUMP_THRESHOLD < 0 or config.DUMP_THRESHOLD > 1:
        errors.append("DUMP_THRESHOLD должен быть между 0 и 1")
    
    if config.CHECK_INTERVAL < 60:
        errors.append("CHECK_INTERVAL слишком маленький (минимум 60 секунд)")
    
    if errors:
        logger.error("Configuration errors found:")
        for error in errors:
            logger.error(f"  - {error}")
        return False
    
    logger.info("Configuration validated successfully")
    return True

def log_system_info():
    """Логирует информацию о системе"""
    import sys
    import platform
    
    logger.info("=" * 50)
    logger.info("System Information:")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Started at: {datetime.now()}")
    logger.info("=" * 50)
