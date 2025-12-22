
import unittest
import pandas as pd
import numpy as np
import sys
import os
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_model import MLPredictor

class TestMLPredictor(unittest.TestCase):
    def setUp(self):
        # Create predictor with disabled loading to avoid file not found
        # (Assuming the class handles missing models gracefully or we can mock it)
        with patch('joblib.load') as mock_load:
            mock_load.side_effect = Exception("Model not found")
            self.predictor = MLPredictor()
            
    def test_rule_based_prediction_pump(self):
        # Setup indicators for PUMP
        indicators = {
            'rsi': 25,          # Low RSI (<30)
            'macd_crossover': 'bullish',
            'bb_position': 'below_lower',
            'volume_ratio': 1.5,
            'is_high_volume': True
        }
        
        market_data = {
            'fear_greed': 30  # Low fear/greed
        }
        
        prediction = self.predictor.rule_based_prediction(indicators, market_data)
        
        self.assertEqual(prediction['signal'], 'PUMP')
        self.assertEqual(prediction['confidence'], 'HIGH')

    def test_rule_based_prediction_dump(self):
        # Setup indicators for DUMP
        indicators = {
            'rsi': 75,          # High RSI (>70)
            'macd_crossover': 'bearish',
            'bb_position': 'above_upper',
            'volume_ratio': 1.5,
            'is_high_volume': True
        }
        
        market_data = {
            'fear_greed': 80  # Extreme greed
        }
        
        prediction = self.predictor.rule_based_prediction(indicators, market_data)
        
        self.assertEqual(prediction['signal'], 'DUMP')
        self.assertEqual(prediction['confidence'], 'HIGH')

    def test_rule_based_prediction_hold(self):
        # Neutral indicators
        indicators = {
            'rsi': 50,
            'macd_crossover': 'none',
            'bb_position': 'inside',
            'volume_ratio': 1.0,
            'is_high_volume': False
        }
        
        market_data = {
            'fear_greed': 50
        }
        
        prediction = self.predictor.rule_based_prediction(indicators, market_data)
        
        # Code returns NEUTRAL, not HOLD
        self.assertEqual(prediction['signal'], 'NEUTRAL')

    def test_predict_fallback(self):
        # Test that predict uses rule-based when model is None
        # Must provide all required keys for rule_based_prediction
        indicators = {
            'rsi': 20, 
            'bb_position': 'below_lower',
            'is_high_volume': True,
            'macd_crossover': 'bullish',
            'volume_ratio': 1.5
        }
        market_data = {'fear_greed': 20}
        
        # Ensure model is None
        self.assertIsNone(self.predictor.model)
        
        prediction = self.predictor.predict(indicators, market_data)
        self.assertEqual(prediction['signal'], 'PUMP')


if __name__ == '__main__':
    unittest.main()
