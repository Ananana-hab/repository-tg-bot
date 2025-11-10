#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Тест Open Interest API"""

from data_collector import DataCollector

def test_open_interest():
    print("Testing Open Interest...")
    
    dc = DataCollector()
    oi = dc.get_open_interest()
    
    print(f"OI Value: {oi['value']:,.0f} BTC")
    print(f"Change 5m: {oi['change_5m']:+.2f}%")
    print(f"Change 1h: {oi['change_1h']:+.2f}%")
    print(f"Change 4h: {oi['change_4h']:+.2f}%")
    print("\nOK: Open Interest API works!")
    
    return True

if __name__ == "__main__":
    test_open_interest()
