
import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators import TechnicalIndicators

class TestTechnicalIndicators(unittest.TestCase):
    def setUp(self):
        # Create a sample DataFrame with predictable data
        # Rising prices for RSI > 50
        prices = [100 + i for i in range(100)]
        self.df = pd.DataFrame({
            'high': [p + 1 for p in prices],
            'low': [p - 1 for p in prices],
            'close': prices,
            'volume': [1000 for _ in range(100)]
        })
        
        # Volatile dataframe
        self.volatile_df = pd.DataFrame({
            'high': [105, 95] * 25,
            'low': [90, 80] * 25,
            'close': [100, 90] * 25,
            'volume': [1000] * 50
        })

    def test_rsi_calculation(self):
        # RSI for constantly rising price should be 100 or close to it
        rsi = TechnicalIndicators.calculate_rsi(self.df, period=14)
        self.assertTrue(rsi > 70, f"RSI should be high for rising prices, got {rsi}")
        
        # RSI for declining prices
        declining_df = self.df.sort_values('close', ascending=False)
        rsi_low = TechnicalIndicators.calculate_rsi(declining_df, period=14)
        self.assertTrue(rsi_low < 30, f"RSI should be low for declining prices, got {rsi_low}")

    def test_bollinger_bands(self):
        bb = TechnicalIndicators.calculate_bollinger_bands(self.df, period=20)
        
        self.assertIn('upper', bb)
        self.assertIn('lower', bb)
        self.assertIn('middle', bb)
        self.assertIn('position', bb)
        
        self.assertTrue(bb['upper'] > bb['middle'])
        self.assertTrue(bb['middle'] > bb['lower'])

    def test_ema(self):
        ema = TechnicalIndicators.calculate_ema(self.df, period=20)
        self.assertTrue(isinstance(ema, float))
        # EMA should be close to last price for steady trend
        last_price = self.df['close'].iloc[-1]
        self.assertTrue(abs(ema - last_price) < 20)

    def test_vwap(self):
        vwap = TechnicalIndicators.calculate_vwap(self.df)
        self.assertTrue(isinstance(vwap, float))
        # With constant volume, VWAP should be approx mean of Typical Price
        # Typical price ~ Close price here
        self.assertTrue(vwap > 0)

    def test_momentum(self):
        mom = TechnicalIndicators.calculate_momentum(self.df, period=10)
        # Rising prices -> positive momentum
        self.assertTrue(mom > 0)

    def test_atr(self):
        atr = TechnicalIndicators.calculate_atr(self.df, period=14)
        self.assertTrue(atr > 0)
        
        # Volatile data should have higher ATR check? 
        # Actually our rising df has constant range (high-low=2), close-prev_close=1
        # ATR should be small
        
        atr_vol = TechnicalIndicators.calculate_atr(self.volatile_df, period=14)
        self.assertTrue(atr_vol > atr, "Volatile DF should have higher ATR")

    def test_all_indicators(self):
        indicators = TechnicalIndicators.calculate_all_indicators(self.df, mode='swing')
        self.assertIsNotNone(indicators)
        self.assertIn('rsi', indicators)
        self.assertIn('macd', indicators)
        self.assertIn('bb_position', indicators)

    def test_empty_dataframe(self):
        empty_df = pd.DataFrame()
        indicators = TechnicalIndicators.calculate_all_indicators(empty_df)
        self.assertIsNone(indicators)

if __name__ == '__main__':
    unittest.main()
