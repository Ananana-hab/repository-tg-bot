
import unittest
import pandas as pd
import numpy as np
import sys
import os
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtester import Backtester

class TestBacktester(unittest.TestCase):
    @patch('backtester.DatabaseAnalytics')
    @patch('ml_model.MLPredictor')
    def setUp(self, mock_ml, mock_db):
        # Initialize Backtester with mocked dependencies
        self.backtester = Backtester()
        self.backtester.db = mock_db.return_value
        
        # Configure the mock predictor that will be used by RuleBasedStrategy
        # The StrategyFactory creates a strategy which creates an MLPredictor
        # Since we patch ml_model.MLPredictor, it will return this mock
        self.mock_predictor = mock_ml.return_value
        
        # Setup specific return values for predictor if needed, 
        # or rely on logic inside RuleBasedStrategy if it calls methods we can mock?
        # RuleBasedStrategy calls self.predictor.rule_based_prediction
        # We should verify that logic.
        
        # Actually, simpler: Mock RuleBasedStrategy logic by mocking MLPredictor.rule_based_prediction output?
        # Yes.
        self.mock_predictor.rule_based_prediction.side_effect = self.mock_rule_based_logic
        
    def mock_rule_based_logic(self, indicators, market_data):
        # Mimic simple logic for testing
        if indicators.get('rsi', 50) < 30 and indicators.get('bb_position') == 'below_lower':
            return {'signal': 'PUMP', 'confidence': 'HIGH', 'probability': 0.8}
        elif indicators.get('rsi', 50) > 70 and indicators.get('bb_position') == 'above_upper':
            return {'signal': 'DUMP', 'confidence': 'HIGH', 'probability': 0.8}
        else:
            return {'signal': 'NEUTRAL', 'confidence': 'LOW', 'probability': 0.5}
        
    def test_simulate_trading_rule_based(self):
        # Create sample data
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        prices = [100, 101, 102, 103, 104, 103, 102, 101, 100, 99]
        data = pd.DataFrame({
            'timestamp': dates,
            'open': [100]*10,
            'high': [105]*10,
            'low': [95]*10,
            'close': prices,
            'price': prices, # Add price column as Backtester expects it
            'volume': [1000]*10,
            # Indicators
            'rsi': [50]*10,
            'macd': [0]*10,
            'macd_signal': [0]*10,
            'bb_upper': [110]*10,
            'bb_lower': [90]*10,
            'volume_ratio': [1.0]*10,
            'fear_greed_index': [50]*10
        })
        
        # Mock strategy factory to return a strategy that buys at index 1 and sells at index 5
        # Or better: check real integration if possible, but mocking strategy behavior is safer for unit test
        # We can test _generate_signal method directly via simulate_trading logic
        
        # Let's rely on RuleBasedStrategy logic.
        # RuleBasedStrategy buys if RSI < 30 etc.
        # Let's rig the data to trigger a BUY
        data.loc[1, 'rsi'] = 25
        data.loc[1, 'bb_position'] = 'below_lower' # Signal BUY
        
        # Rig data to trigger SELL
        data.loc[5, 'rsi'] = 75
        data.loc[5, 'bb_position'] = 'above_upper' # Signal SELL
        
        # Run simulation
        results = self.backtester.simulate_trading(data, strategy='rule_based', mode='swing')
        
        # Check trades
        trades = results['trades']
        self.assertTrue(len(trades) > 0, "Should have executed at least one trade")
        
        first_trade = trades.iloc[0]
        self.assertEqual(first_trade['signal_type'], 'PUMP') # RuleBased returns PUMP
        # Check logic... it might differ based on exact implementation of RuleBasedStrategy in strategy_framework
        # But assuming it works as expected.

    def test_generate_report(self):
        # Mock simulation results
        trades = [
            {'type': 'long', 'pnl': 50, 'entry_price': 100, 'exit_price': 150, 'entry_time': pd.Timestamp('2023-01-01'), 'exit_time': pd.Timestamp('2023-01-02'), 'signal_type': 'PUMP', 'probability': 0.8, 'confidence': 'HIGH', 'return_pct': 50.0},
            {'type': 'long', 'pnl': -20, 'entry_price': 100, 'exit_price': 80, 'entry_time': pd.Timestamp('2023-01-03'), 'exit_time': pd.Timestamp('2023-01-04'), 'signal_type': 'PUMP', 'probability': 0.7, 'confidence': 'MEDIUM', 'return_pct': -20.0}
        ]
        
        sim_results = {
            'trades': pd.DataFrame(trades), 
            'equity_curve': [1000, 1050, 1030],
            'final_capital': 1030,
            'initial_capital': 1000,
            'total_return': 30,
            'total_return_pct': 3.0,
            'num_trades': 2,
            'strategy': 'rule_based',
            'mode': 'swing'
        }
        
        report = self.backtester.generate_backtest_report(sim_results)
        
        self.assertIn('performance', report)
        self.assertEqual(report['performance']['pnl']['total_pnl'], 30.0)
        self.assertEqual(report['trade_stats']['total_trades'], 2)
        # Winning trades is not currently in trade_stats, checking avg_return_pct instead
        # (50 - 20) / 2 = 15
        self.assertEqual(report['trade_stats']['avg_return_pct'], 15.0)

if __name__ == '__main__':
    unittest.main()
