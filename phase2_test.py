#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Тест изменений Фазы 2"""

from data_collector import DataCollector
from indicators import TechnicalIndicators  
from ml_model import MLPredictor

def test_phase2():
    print("=" * 50)
    print("PHASE 2 TEST - RSI/MACD Removal + OI")
    print("=" * 50)
    
    # Тест 1: Indicators без RSI/MACD
    print("\n[1/3] Testing indicators calculation...")
    dc = DataCollector()
    market_data = dc.get_market_data(timeframe='5m', limit=100)
    
    indicators = TechnicalIndicators.calculate_all_indicators(
        market_data['df'], 
        market_data['orderbook']
    )
    
    assert indicators is not None, "Indicators calculation failed"
    
    # RSI и MACD должны быть заглушками
    assert indicators['rsi'] == 50.0, f"RSI should be 50.0, got {indicators['rsi']}"
    assert indicators['macd'] == 0.0, f"MACD should be 0.0, got {indicators['macd']}"
    assert indicators['macd_crossover'] == 'none', "MACD crossover should be 'none'"
    
    # Активные индикаторы должны работать
    assert 'volume_ratio' in indicators, "Volume ratio missing"
    assert 'momentum' in indicators, "Momentum missing"
    assert 'bb_position' in indicators, "BB position missing"
    
    print(f"  OK: Indicators calculated")
    print(f"  OK: RSI stub = {indicators['rsi']}")
    print(f"  OK: MACD stub = {indicators['macd']}")
    print(f"  OK: Volume = {indicators['volume_ratio']:.2f}x")
    print(f"  OK: Momentum = {indicators['momentum']:.2f}")
    
    # Тест 2: ML Model с OI
    print("\n[2/3] Testing ML model with OI...")
    predictor = MLPredictor()
    prediction = predictor.predict(indicators, market_data)
    
    assert prediction is not None, "Prediction failed"
    assert 'signal' in prediction, "Signal missing"
    assert 'probability' in prediction, "Probability missing"
    assert 'confidence' in prediction, "Confidence missing"
    
    print(f"  OK: Prediction = {prediction['signal']}")
    print(f"  OK: Probability = {prediction['probability']:.1%}")
    print(f"  OK: Confidence = {prediction['confidence']}")
    
    if 'reasons' in prediction:
        print(f"  OK: Reasons count = {len(prediction['reasons'])}")
        for reason in prediction['reasons'][:3]:
            print(f"    - {reason}")
    
    # Тест 3: Open Interest в market_data
    print("\n[3/3] Testing Open Interest integration...")
    assert 'oi_change_1h' in market_data, "OI 1h missing"
    assert 'oi_change_5m' in market_data, "OI 5m missing"
    assert 'oi_change_4h' in market_data, "OI 4h missing"
    
    print(f"  OK: OI 5m = {market_data['oi_change_5m']:+.2f}%")
    print(f"  OK: OI 1h = {market_data['oi_change_1h']:+.2f}%")
    print(f"  OK: OI 4h = {market_data['oi_change_4h']:+.2f}%")
    
    print("\n" + "=" * 50)
    print("ALL PHASE 2 TESTS PASSED!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    test_phase2()
