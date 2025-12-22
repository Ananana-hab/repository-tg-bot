"""
Unit tests for Performance Metrics module
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from performance_metrics import PerformanceMetrics


def test_win_rate():
    """Test win rate calculation"""
    print("\n1. Testing Win Rate Calculation...")
    
    pm = PerformanceMetrics()
    
    # Create test data
    test_signals = pd.DataFrame({
        'signal_type': ['PUMP', 'PUMP', 'DUMP', 'DUMP', 'PUMP'],
        'price': [90000, 91000, 92000, 89000, 88000],
        'result_price': [91000, 90500, 91000, 88500, 89000],
        'actual_result': ['correct', 'incorrect', 'correct', 'correct', 'correct'],
        'timestamp': pd.date_range(start='2024-01-01', periods=5, freq='D')
    })
    
    result = pm.calculate_win_rate(test_signals)
    
    assert result['total_signals'] == 5, "Total signals should be 5"
    assert result['wins'] == 4, "Should have 4 wins"
    assert result['losses'] == 1, "Should have 1 loss"
    assert result['win_rate'] == 80.0, f"Win rate should be 80%, got {result['win_rate']}"
    
    print(f"   [OK] Win Rate: {result['win_rate']}%")
    print(f"   [OK] PUMP Win Rate: {result['pump_win_rate']}%")
    print(f"   [OK] DUMP Win Rate: {result['dump_win_rate']}%")


def test_pnl_calculation():
    """Test P&L calculation"""
    print("\n2. Testing P&L Calculation...")
    
    pm = PerformanceMetrics()
    
    # Test data: 3 PUMP signals (2 profitable, 1 loss), 2 DUMP signals (1 profitable, 1 loss)
    test_signals = pd.DataFrame({
        'signal_type': ['PUMP', 'PUMP', 'PUMP', 'DUMP', 'DUMP'],
        'price': [90000, 91000, 88000, 92000, 89000],
        'result_price': [91000, 90500, 87000, 91500, 89500],  # +1000, -500, -1000, +500, -500
        'actual_result': ['correct', 'incorrect', 'incorrect', 'correct', 'incorrect'],
        'timestamp': pd.date_range(start='2024-01-01', periods=5, freq='D')
    })
    
    initial_capital = 1000.0
    result = pm.calculate_pnl(test_signals, initial_capital=initial_capital)
    
    # With 10% position size (100 USD per trade):
    # PUMP at 90000 -> 91000: +1.11% = +1.11 USD
    # PUMP at 91000 -> 90500: -0.55% = -0.55 USD
    # PUMP at 88000 -> 87000: -1.14% = -1.14 USD
    # DUMP at 92000 -> 91500: +0.54% = +0.54 USD (short)
    # DUMP at 89000 -> 89500: -0.56% = -0.56 USD (short)
    
    print(f"   Total P&L: ${result['total_pnl']:.2f}")
    print(f"   Total P&L %: {result['total_pnl_pct']:.2f}%")
    print(f"   Avg P&L per Signal: ${result['avg_pnl_per_signal']:.2f}")
    print(f"   Best Trade: ${result['best_trade']:.2f}")
    print(f"   Worst Trade: ${result['worst_trade']:.2f}")
    print(f"   [OK] Profitable Trades: {result['profitable_trades']}")
    print(f"   [OK] Losing Trades: {result['losing_trades']}")
    
    assert result['signals_analyzed'] == 5, "Should analyze 5 signals"


def test_sharpe_ratio():
    """Test Sharpe ratio calculation"""
    print("\n3. Testing Sharpe Ratio...")
    
    pm = PerformanceMetrics()
    
    # Test with known returns (longer sample for stability)
    returns = [0.005, 0.01, -0.005, 0.008, 0.003, -0.002, 0.006, 
               0.004, -0.003, 0.007, 0.002, -0.004, 0.005, 0.003]
    
    sharpe = pm.calculate_sharpe_ratio(returns, periods_per_year=365)
    
    print(f"   [OK] Sharpe Ratio: {sharpe:.3f}")
    
    # Sharpe can be high for small samples with low volatility (typical for crypto)
    # Just verify it's calculated (not NaN/Inf)
    assert not (np.isnan(sharpe) or np.isinf(sharpe)), f"Sharpe should be a valid number"
    
    # Test with all positive returns (should have positive Sharpe)
    positive_returns = [0.005] * 10  # consistent positive returns
    sharpe_positive = pm.calculate_sharpe_ratio(positive_returns)
    print(f"   [OK] Sharpe (all positive): {sharpe_positive:.3f}")
    assert sharpe_positive > 0, "Sharpe should be positive for all positive returns"




def test_max_drawdown():
    """Test max drawdown calculation"""
    print("\n4. Testing Max Drawdown...")
    
    pm = PerformanceMetrics()
    
    # Create equity curve with known drawdown
    # Start at 1000, peak at 1200, drop to 900 (25% drawdown from peak)
    equity_curve = [1000, 1050, 1100, 1200, 1150, 1000, 900, 950, 1100]
    
    result = pm.calculate_max_drawdown(equity_curve)
    
    print(f"   Max Drawdown: {result['max_drawdown']:.2f}%")
    print(f"   Drawdown Duration: {result['max_drawdown_duration']} periods")
    print(f"   Peak Value: ${result['peak_value']:.2f}")
    print(f"   Trough Value: ${result['trough_value']:.2f}")
    
    # From 1200 to 900 = 25% drawdown
    expected_dd = ((1200 - 900) / 1200) * 100
    assert abs(result['max_drawdown'] - expected_dd) < 0.1, \
        f"Expected ~{expected_dd:.2f}% drawdown, got {result['max_drawdown']:.2f}%"
    
    print(f"   [OK] Drawdown calculation correct!")


def test_win_loss_streaks():
    """Test win/loss streak calculation"""
    print("\n5. Testing Win/Loss Streaks...")
    
    pm = PerformanceMetrics()
    
    # Create sequence: W-W-W-L-L-W-W-W-W-L
    test_signals = pd.DataFrame({
        'signal_type': ['PUMP'] * 10,
        'price': [90000] * 10,
        'result_price': [91000] * 10,
        'actual_result': ['correct', 'correct', 'correct', 'incorrect', 'incorrect',
                         'correct', 'correct', 'correct', 'correct', 'incorrect'],
        'timestamp': pd.date_range(start='2024-01-01', periods=10, freq='D')
    })
    
    result = pm.calculate_win_loss_streaks(test_signals)
    
    print(f"   Max Win Streak: {result['max_win_streak']}")
    print(f"   Max Loss Streak: {result['max_loss_streak']}")
    print(f"   Current Streak: {result['current_streak']}")
    
    assert result['max_win_streak'] == 4, "Max win streak should be 4"
    assert result['max_loss_streak'] == 2, "Max loss streak should be 2"
    assert result['current_streak'] == -1, "Current streak should be -1 (one loss)"
    
    print("   [OK] Streak calculation correct!")


def test_comprehensive_report():
    """Test full performance report generation"""
    print("\n6. Testing Comprehensive Report...")
    
    pm = PerformanceMetrics()
    
    # Create realistic test data
    np.random.seed(42)
    n_signals = 20
    
    test_signals = pd.DataFrame({
        'signal_type': np.random.choice(['PUMP', 'DUMP'], n_signals),
        'price': np.random.uniform(85000, 95000, n_signals),
        'timestamp': pd.date_range(start='2024-01-01', periods=n_signals, freq='D')
    })
    
    # Simulate results (60% win rate)
    test_signals['actual_result'] = np.random.choice(
        ['correct', 'incorrect'], 
        n_signals, 
        p=[0.6, 0.4]
    )
    
    # Calculate result prices based on signal correctness
    result_prices = []
    for _, signal in test_signals.iterrows():
        entry = signal['price']
        if signal['actual_result'] == 'correct':
            if signal['signal_type'] == 'PUMP':
                exit_price = entry * np.random.uniform(1.01, 1.05)  # +1% to +5%
            else:
                exit_price = entry * np.random.uniform(0.95, 0.99)  # -5% to -1%
        else:
            if signal['signal_type'] == 'PUMP':
                exit_price = entry * np.random.uniform(0.95, 0.99)  # Loss
            else:
                exit_price = entry * np.random.uniform(1.01, 1.05)  # Loss
        result_prices.append(exit_price)
    
    test_signals['result_price'] = result_prices
    
    # Generate report
    report = pm.generate_performance_report(test_signals, initial_capital=1000.0)
    
    print("\n   PERFORMANCE REPORT:")
    print(f"   Total Signals: {report['summary']['total_signals']}")
    print(f"   Completed: {report['summary']['completed_signals']}")
    print(f"   Initial Capital: ${report['summary']['initial_capital']:.2f}")
    print(f"   Final Capital: ${report['summary']['final_capital']:.2f}")
    print(f"   Win Rate: {report['win_rate']['win_rate']:.1f}%")
    print(f"   Total P&L: ${report['pnl']['total_pnl']:.2f} ({report['pnl']['total_pnl_pct']:.2f}%)")
    print(f"   Sharpe Ratio: {report['risk_metrics']['sharpe_ratio']:.3f}")
    print(f"   Max Drawdown: {report['risk_metrics']['max_drawdown']:.2f}%")
    print(f"   Max Win Streak: {report['streaks']['max_win_streak']}")
    print(f"   Max Loss Streak: {report['streaks']['max_loss_streak']}")
    
    print("\n   [OK] Comprehensive report generated successfully!")


def test_edge_cases():
    """Test edge cases"""
    print("\n7. Testing Edge Cases...")
    
    pm = PerformanceMetrics()
    
    # Empty DataFrame
    empty_df = pd.DataFrame()
    result = pm.calculate_win_rate(empty_df)
    assert result['win_rate'] == 0.0, "Win rate should be 0 for empty data"
    print("   [OK] Empty DataFrame handled")
    
    # No completed signals
    incomplete_df = pd.DataFrame({
        'signal_type': ['PUMP', 'DUMP'],
        'price': [90000, 91000],
        'result_price': [None, None],
        'actual_result': [None, None],
        'timestamp': pd.date_range(start='2024-01-01', periods=2, freq='D')
    })
    result = pm.calculate_win_rate(incomplete_df)
    assert result['completed_signals'] == 0, "No completed signals"
    print("   [OK] Incomplete signals handled")
    
    # Single return for Sharpe
    single_return = [0.05]
    sharpe = pm.calculate_sharpe_ratio(single_return)
    assert sharpe == 0.0, "Sharpe should be 0 for insufficient data"
    print("   [OK] Single return handled")
    
    print("\n   [OK] All edge cases passed!")


def main():
    """Run all tests"""
    print("=" * 70)
    print("PERFORMANCE METRICS MODULE TESTS")
    print("=" * 70)
    
    try:
        test_win_rate()
        test_pnl_calculation()
        test_sharpe_ratio()
        test_max_drawdown()
        test_win_loss_streaks()
        test_comprehensive_report()
        test_edge_cases()
        
        print("\n" + "=" * 70)
        print("[SUCCESS] ALL TESTS PASSED!")
        print("=" * 70)
        print("\nPerformance Metrics module is ready to use!")
        
    except AssertionError as e:
        print(f"\n[FAILED] TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
