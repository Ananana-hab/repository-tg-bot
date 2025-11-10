#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Тест новых форматов сообщений"""

from telegram_bot import TelegramBot
import config

def test_messages():
    print("Testing message formats...")
    
    bot = TelegramBot(config.TELEGRAM_BOT_TOKEN)
    
    # Тестовые данные
    signal_data = {
        'signal': 'PUMP',
        'probability': 0.75,
        'confidence': 'HIGH'
    }
    
    market_data = {
        'current_price': 103520.00,
        'price_change_1h': 0.24,
        'price_change_4h': 1.35,
        'volume_change': 25,
        'oi_change_1h': 2.5,
        'oi_change_4h': 5.2,
        'oi_change_5m': 0.8
    }
    
    # Тест Swing сообщения
    print("\n=== SWING MESSAGE ===")
    swing_msg = bot.format_swing_message(signal_data, market_data)
    
    # Проверяем наличие ключевых элементов
    assert 'SWING' in swing_msg, "Mode missing"
    assert 'BTC/USDT' in swing_msg, "Symbol missing"
    assert 'Open Interest' in swing_msg, "OI missing"
    print(f"  Length: {len(swing_msg)} chars")
    print(f"  Has OI: {'Open Interest' in swing_msg}")
    print(f"  Has SWING: {'SWING' in swing_msg}")
    
    print("OK: Swing message format correct")
    
    # Тест Day trading сообщения (если есть day_details)
    signal_data_day = {
        'signal': 'PUMP',
        'probability': 0.80,
        'confidence': 'HIGH',
        'day_trading_details': {
            'volume_surge': 3.2,
            'trend': 'up'
        }
    }
    
    print("\n=== DAY TRADING MESSAGE ===")
    day_msg = bot.format_day_trading_message(signal_data_day, market_data)
    
    assert 'DAY TRADING' in day_msg, "Mode missing"
    assert 'Open Interest' in day_msg, "OI missing in day message"
    print(f"  Length: {len(day_msg)} chars")
    print(f"  Has OI: {'Open Interest' in day_msg}")
    print(f"  Has DAY TRADING: {'DAY TRADING' in day_msg}")
    
    print("OK: Day trading message format correct")
    
    print("\nSUCCESS: All message tests passed!")
    return True

if __name__ == "__main__":
    test_messages()
