"""
Test script for new indicators (ASCII only)
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from indicators import TechnicalIndicators

print("=" * 60)
print("TESTING NEW INDICATORS")
print("=" * 60)

# Create test data
np.random.seed(42)
test_data = {
    'high': np.random.uniform(90000, 100000, 100),
    'low': np.random.uniform(85000, 95000, 100),
    'close': np.random.uniform(87000, 98000, 100),
    'volume': np.random.uniform(1000, 5000, 100)
}
df = pd.DataFrame(test_data)

# Test 1: RSI
print("\n1. Testing RSI...")
try:
    rsi = TechnicalIndicators.calculate_rsi(df, 14)
    print(f"   RSI: {rsi:.2f}")
    assert 0 <= rsi <= 100, "RSI out of range!"
    print("   [OK] RSI calculation works!")
except Exception as e:
    print(f"   [ERROR] RSI error: {e}")

# Test 2: MACD
print("\n2. Testing MACD...")
try:
    macd = TechnicalIndicators.calculate_macd(df, 12, 26, 9)
    print(f"   MACD: {macd['macd']:.2f}")
    print(f"   Signal: {macd['signal']:.2f}")
    print(f"   Histogram: {macd['histogram']:.2f}")
    print(f"   Crossover: {macd['crossover']}")
    print("   [OK] MACD calculation works!")
except Exception as e:
    print(f"   [ERROR] MACD error: {e}")

# Test 3: Stochastic
print("\n3. Testing Stochastic...")
try:
    stoch = TechnicalIndicators.calculate_stochastic(df, 14, 3, 3)
    print(f"   %K: {stoch['k']:.2f}")
    print(f"   %D: {stoch['d']:.2f}")
    print(f"   Crossover: {stoch['crossover']}")
    assert 0 <= stoch['k'] <= 100, "Stochastic %K out of range!"
    assert 0 <= stoch['d'] <= 100, "Stochastic %D out of range!"
    print("   [OK] Stochastic calculation works!")
except Exception as e:
    print(f"   [ERROR] Stochastic error: {e}")

# Test 4: Integration in calculate_all_indicators (swing mode)
print("\n4. Testing Integration (swing mode)...")
try:
    indicators = TechnicalIndicators.calculate_all_indicators(df, None, mode='swing')
    if indicators:
        print(f"   RSI: {indicators.get('rsi', 'N/A')}")
        print(f"   MACD: {indicators.get('macd', 'N/A')}")
        print(f"   MACD Signal: {indicators.get('macd_signal', 'N/A')}")
        print(f"   MACD Crossover: {indicators.get('macd_crossover', 'N/A')}")
        print("   [OK] Swing mode integration works!")
    else:
        print("   [ERROR] No indicators returned!")
except Exception as e:
    print(f"   [ERROR] Integration error: {e}")

# Test 5: Integration in day trading
print("\n5. Testing Integration (day mode)...")
try:
    indicators = TechnicalIndicators.calculate_all_indicators(df, None, mode='day')
    if indicators and 'day_trading' in indicators:
        day_ind = indicators['day_trading']
        print(f"   RSI: {indicators.get('rsi', 'N/A')}")
        print(f"   Stochastic %K: {day_ind.get('stochastic_k', 'N/A')}")
        print(f"   Stochastic %D: {day_ind.get('stochastic_d', 'N/A')}")
        print(f"   Stochastic Crossover: {day_ind.get('stochastic_crossover', 'N/A')}")
        print("   [OK] Day mode integration works!")
    else:
        print("   [WARNING] Day trading indicators not found")
except Exception as e:
    print(f"   [ERROR] Day mode error: {e}")

print("\n" + "=" * 60)
print("TESTING COMPLETE!")
print("=" * 60)
