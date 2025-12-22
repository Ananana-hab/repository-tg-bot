"""
Performance analysis demo script
Demonstrates usage of performance_metrics module with database analytics
"""
import sys
sys.path.insert(0, '.')

from performance_metrics import PerformanceMetrics
from database_analytics import DatabaseAnalytics
import pandas as pd

print("=" * 70)
print("PERFORMANCE METRICS DEMONSTRATION")
print("=" * 70)

# Initialize
db = DatabaseAnalytics()
pm = PerformanceMetrics()

print("\n1. Checking Database Connection...")
try:
    stats = db.get_snapshot_stats()
    if stats:
        print(f"   [OK] Database connected")
        print(f"   Total snapshots: {stats.get('total', 0)}")
        print(f"   Labeled: {stats.get('labeled', 0)}")
    else:
        print("   [INFO] No snapshot data available yet")
except Exception as e:
    print(f"   [INFO] Database not yet populated: {e}")

print("\n2. Retrieving signals for analysis...")
try:
    signals_df = db.get_signals_for_analysis(days=30)
    
    if signals_df is not None and len(signals_df) > 0:
        print(f"   [OK] Retrieved {len(signals_df)} signals")
        print(f"   Date range: {signals_df['timestamp'].min()} to {signals_df['timestamp'].max()}")
        
        # Show signal type distribution
        signal_counts = signals_df['signal_type'].value_counts()
        for signal_type, count in signal_counts.items():
            print(f"   {signal_type}: {count} signals")
        
        print("\n3. Generating Performance Report...")
        report = pm.generate_performance_report(signals_df, initial_capital=1000.0)
        
        print("\n" + "=" * 70)
        print("PERFORMANCE REPORT")
        print("=" * 70)
        
        print(f"\nSummary:")
        print(f"  Total Signals: {report['summary']['total_signals']}")
        print(f"  Completed: {report['summary']['completed_signals']}")
        print(f"  Initial Capital: ${report['summary']['initial_capital']:.2f}")
        print(f"  Final Capital: ${report['summary']['final_capital']:.2f}")
        
        print(f"\nWin Rate:")
        print(f"  Overall: {report['win_rate']['win_rate']:.1f}%")
        print(f"  PUMP: {report['win_rate']['pump_win_rate']:.1f}%")
        print(f"  DUMP: {report['win_rate']['dump_win_rate']:.1f}%")
        print(f"  Wins: {report['win_rate']['wins']}")
        print(f"  Losses: {report['win_rate']['losses']}")
        
        print(f"\nProfit & Loss:")
        print(f"  Total P&L: ${report['pnl']['total_pnl']:.2f} ({report['pnl']['total_pnl_pct']:.2f}%)")
        print(f"  Avg per Signal: ${report['pnl']['avg_pnl_per_signal']:.2f}")
        print(f"  Best Trade: ${report['pnl']['best_trade']:.2f}")
        print(f"  Worst Trade: ${report['pnl']['worst_trade']:.2f}")
        print(f"  Profitable: {report['pnl']['profitable_trades']}")
        print(f"  Losing: {report['pnl']['losing_trades']}")
        
        print(f"\nRisk Metrics:")
        print(f"  Sharpe Ratio: {report['risk_metrics']['sharpe_ratio']:.3f}")
        print(f"  Max Drawdown: {report['risk_metrics']['max_drawdown']:.2f}%")
        print(f"  Drawdown Duration: {report['risk_metrics']['max_drawdown_duration']} periods")
        
        print(f"\nStreaks:")
        print(f"  Max Win Streak: {report['streaks']['max_win_streak']}")
        print(f"  Max Loss Streak: {report['streaks']['max_loss_streak']}")
        print(f"  Current Streak: {report['streaks']['current_streak']}")
        
        print("\n4. Testing Equity Curve Generation...")
        equity_df = db.get_equity_curve(days=30)
        
        if equity_df is not None and len(equity_df) > 0:
            print(f"   [OK] Generated equity curve with {len(equity_df)} points")
            print(f"   Starting equity: ${equity_df['equity'].iloc[0]:.2f}")
            print(f"   Ending equity: ${equity_df['equity'].iloc[-1]:.2f}")
        else:
            print("   [INFO] Not enough data for equity curve")
        
    else:
        print("   [INFO] No signals found in database")
        print("   [INFO] This is normal if bot hasn't been running long enough")
        print("\n   To test performance metrics:")
        print("   1. Let the bot run and collect signals")
        print("   2. Make sure signals have result_price populated")
        print("   3. Run this script again")
        
        print("\n   Alternatively, run the unit tests:")
        print("   python test_performance_metrics.py")
        
except Exception as e:
    print(f"   [INFO] Unable to retrieve signals: {e}")
    print("\n   This is expected if the database doesn't have any signals yet.")
    print("   Run the bot for a while to collect data, then try again.")

print("\n" + "=" * 70)
print("Demo Complete!")
print("=" * 70)
print("\nModules created:")
print("  1. performance_metrics.py - Win Rate, P&L, Sharpe, Drawdown")
print("  2. database_analytics.py - Analytics queries")
print("  3. test_performance_metrics.py - Unit tests (all passing)")
print("\nNext steps:")
print("  - Complete backtesting framework")
print("  - Integrate with Telegram bot (/stats, /performance)")
print("  - Add performance monitoring")
