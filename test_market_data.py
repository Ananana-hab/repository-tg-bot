#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Тест полного сбора рыночных данных"""

from data_collector import DataCollector

def test_market_data():
    print("Testing full market data collection...")
    
    dc = DataCollector()
    market_data = dc.get_market_data(timeframe='5m', limit=100)
    
    if market_data is None:
        print("ERROR: Failed to collect market data")
        return False
    
    print(f"\nOK: Market data collected successfully!")
    print(f"  Price: ${market_data['current_price']:,.2f}")
    print(f"  Change 1h: {market_data['price_change_1h']:+.2f}%")
    print(f"  Change 4h: {market_data['price_change_4h']:+.2f}%")
    print(f"  Volume: ${market_data['current_volume']:,.0f}")
    print(f"  Fear & Greed: {market_data['fear_greed']}")
    
    # Проверяем наличие новых полей OI
    if 'open_interest' in market_data:
        print(f"\nOK: Open Interest fields present!")
        print(f"  OI: {market_data['open_interest']:,.0f} BTC")
        print(f"  OI 5m: {market_data['oi_change_5m']:+.2f}%")
        print(f"  OI 1h: {market_data['oi_change_1h']:+.2f}%")
        print(f"  OI 4h: {market_data['oi_change_4h']:+.2f}%")
    else:
        print("\nERROR: Open Interest fields missing!")
        return False
    
    print("\nSUCCESS: All tests passed!")
    return True

if __name__ == "__main__":
    test_market_data()
