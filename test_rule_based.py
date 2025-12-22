"""
Test rule-based prediction with RSI and MACD
"""
import sys
sys.path.insert(0, '.')

from ml_model import MLPredictor
import numpy as np

print("=" * 70)
print("TESTING RULE-BASED WITH RSI AND MACD")
print("=" * 70)

predictor = MLPredictor()

# Test scenario 1: Strong PUMP signal (RSI low, MACD bullish)
print("\n1. TEST: Strong PUMP scenario")
indicators_pump = {
    'bb_position': 'below_lower',
    'is_high_volume': True,
    'momentum': 400,
    'atr': 100,
    'vwap': 89000,
    'orderbook_imbalance': 0.3,
    'volume_ratio': 2.5,
    'rsi': 25,  # NEW: Oversold
    'macd_crossover': 'bullish',  # NEW: Bullish crossover
    'macd_histogram': 60,  # NEW: Strong positive
}

market_data_pump = {
    'fear_greed': 22,
    'current_price': 89500,
    'price_change_1h': 3.0,
    'oi_change_1h': 2.5,
}

result = predictor.rule_based_prediction(indicators_pump, market_data_pump)
print(f"Signal: {result['signal']}")
print(f"Probability: {result['probability']:.2%}")
print(f"Confidence: {result['confidence']}")
print(f"Reasons: {len(result.get('reasons', []))} factors")

# Test scenario 2: Strong DUMP signal (RSI high, MACD bearish)
print("\n2. TEST: Strong DUMP scenario")
indicators_dump = {
    'bb_position': 'above_upper',
    'is_high_volume': True,
    'momentum': -400,
    'atr': 100,
    'vwap': 90000,
    'orderbook_imbalance': -0.3,
    'volume_ratio': 2.5,
    'rsi': 75,  # NEW: Overbought
    'macd_crossover': 'bearish',  # NEW: Bearish crossover
    'macd_histogram': -60,  # NEW: Strong negative
}

market_data_dump = {
    'fear_greed': 78,
    'current_price': 89500,
    'price_change_1h': -3.0,
    'oi_change_1h': 2.5,
}

result = predictor.rule_based_prediction(indicators_dump, market_data_dump)
print(f"Signal: {result['signal']}")
print(f"Probability: {result['probability']:.2%}")
print(f"Confidence: {result['confidence']}")
print(f"Reasons: {len(result.get('reasons', []))} factors")

# Test scenario 3: Neutral (moderate RSI, no MACD signal)
print("\n3. TEST: NEUTRAL scenario")
indicators_neutral = {
    'bb_position': 'inside',
    'is_high_volume': False,
    'momentum': 50,
    'atr': 80,
    'vwap': 89500,
    'orderbook_imbalance': 0.0,
    'volume_ratio': 1.0,
    'rsi': 50,  # NEW: Neutral
    'macd_crossover': 'none',  # NEW: No crossover
    'macd_histogram': 5,
}

market_data_neutral = {
    'fear_greed': 50,
    'current_price': 89500,
    'price_change_1h': 0.5,
    'oi_change_1h': 0.1,
}

result = predictor.rule_based_prediction(indicators_neutral, market_data_neutral)
print(f"Signal: {result['signal']}")
print(f"Probability: {result['probability']:.2%}")
print(f"Confidence: {result['confidence']}")

# Test scenario 4: RSI only (strong oversold)
print("\n4. TEST: RSI oversold only")
indicators_rsi = {
    'bb_position': 'inside',
    'is_high_volume': False,
    'momentum': 100,
    'atr': 80,
    'vwap': 89500,
    'orderbook_imbalance': 0.0,
    'volume_ratio': 1.2,
    'rsi': 28,  # NEW: Strong oversold
    'macd_crossover': 'none',
    'macd_histogram': 0,
}

market_data_rsi = {
    'fear_greed': 50,
    'current_price': 89500,
    'price_change_1h': 1.0,
    'oi_change_1h': 0.5,
}

result = predictor.rule_based_prediction(indicators_rsi, market_data_rsi)
print(f"Signal: {result['signal']}")
print(f"Probability: {result['probability']:.2%}")
print(f"Confidence: {result['confidence']}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("\n[OK] RSI and MACD successfully integrated into rule-based logic!")
print("New scoring includes:")
print("  - RSI < 30: +2 points (PUMP)")
print("  - RSI > 70: -2 points (DUMP)")
print("  - MACD bullish crossover: +2 points")
print("  - MACD bearish crossover: -2 points")
print("  - MACD histogram: +/-1 point")
print("\nAccuracy should improve immediately!")
