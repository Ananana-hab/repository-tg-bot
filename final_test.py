#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Финальный тест всех изменений Фазы 1"""

from main import BTCPumpDumpBot
from data_collector import DataCollector

def test_phase1():
    print("=" * 50)
    print("FINAL TEST - PHASE 1")
    print("=" * 50)
    
    # Тест 1: Инициализация бота
    print("\n[1/4] Testing bot initialization...")
    bot = BTCPumpDumpBot()
    assert hasattr(bot, 'last_signal_price'), "last_signal_price missing"
    assert bot.last_signal_price is None, "Should be None initially"
    print("  OK: Anti-spam fields present")
    
    # Тест 2: Open Interest
    print("\n[2/4] Testing Open Interest...")
    dc = DataCollector()
    oi = dc.get_open_interest()
    assert 'value' in oi, "OI value missing"
    assert 'change_5m' in oi, "OI 5m change missing"
    assert 'change_1h' in oi, "OI 1h change missing"
    assert 'change_4h' in oi, "OI 4h change missing"
    print(f"  OK: OI = {oi['value']:,.0f} BTC")
    
    # Тест 3: Market Data с OI
    print("\n[3/4] Testing Market Data collection...")
    market_data = dc.get_market_data(timeframe='5m', limit=100)
    assert market_data is not None, "Market data is None"
    assert 'open_interest' in market_data, "OI missing in market_data"
    assert 'oi_change_5m' in market_data, "OI 5m missing"
    assert 'oi_change_1h' in market_data, "OI 1h missing"
    assert 'oi_change_4h' in market_data, "OI 4h missing"
    print(f"  OK: Price = ${market_data['current_price']:,.2f}")
    print(f"  OK: OI fields present")
    
    # Тест 4: Сообщения
    print("\n[4/4] Testing message formats...")
    from telegram_bot import TelegramBot
    import config
    tb = TelegramBot(config.TELEGRAM_BOT_TOKEN)
    
    test_signal = {
        'signal': 'PUMP',
        'probability': 0.75,
        'confidence': 'HIGH'
    }
    test_market = {
        'current_price': 103520.00,
        'price_change_1h': 0.24,
        'price_change_4h': 1.35,
        'volume_change': 25,
        'oi_change_1h': 2.5,
        'oi_change_4h': 5.2,
        'oi_change_5m': 0.8
    }
    
    swing_msg = tb.format_swing_message(test_signal, test_market)
    assert 'Open Interest' in swing_msg, "OI missing in swing message"
    assert 'SWING' in swing_msg, "SWING mode missing"
    print(f"  OK: Swing message ({len(swing_msg)} chars)")
    
    print("\n" + "=" * 50)
    print("ALL TESTS PASSED!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    test_phase1()
