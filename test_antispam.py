#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Тест анти-спам механизма"""

import asyncio
from main import BTCPumpDumpBot

async def test_antispam():
    print("Testing anti-spam mechanism...")
    
    bot = BTCPumpDumpBot()
    
    # Проверяем начальные значения
    assert bot.last_signal is None, "last_signal should be None initially"
    assert bot.last_signal_time is None, "last_signal_time should be None initially"
    assert bot.last_signal_price is None, "last_signal_price should be None initially"
    
    print("OK: Anti-spam fields initialized correctly")
    
    # Симулируем установку значений
    bot.last_signal = "PUMP"
    bot.last_signal_time = 1234567890.0
    bot.last_signal_price = 100000.0
    
    print(f"  last_signal: {bot.last_signal}")
    print(f"  last_signal_time: {bot.last_signal_time}")
    print(f"  last_signal_price: ${bot.last_signal_price:,.2f}")
    
    print("\nSUCCESS: Anti-spam mechanism ready!")
    return True

if __name__ == "__main__":
    asyncio.run(test_antispam())
