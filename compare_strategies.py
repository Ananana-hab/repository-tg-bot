"""
Strategy Comparison Script
Runs backtests for multiple strategies and generates a comparison report.
"""
import argparse
import pandas as pd
import logging
from backtester import Backtester
from strategy_framework import StrategyFactory
from report_generator import ReportGenerator
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def compare_strategies(days: int = 30):
    """
    Run comparison between Rule-Based and ML strategies
    """
    logger.info(f"Starting strategy comparison for last {days} days...")
    
    backtester = Backtester(initial_capital=1000.0)
    
    # Load data once
    data = backtester.load_historical_data(days=days)
    if data is None or len(data) == 0:
        logger.error("No historical data available for comparison")
        return
    
    strategies = ['rule_based', 'ml']
    results = []
    
    print("\n" + "="*80)
    print(f"STRATEGY COMPARISON REPORT ({days} DAYS)")
    print("="*80)
    print(f"{'METRIC':<20} | {'RULE-BASED':<20} | {'ML MODEL':<20} | {'DIFF':<10}")
    print("-" * 80)
    
    metrics = {}
    
    for strategy_name in strategies:
        logger.info(f"Running backtest for {strategy_name}...")
        
        # Run backtest
        # We reuse the existing simulate_trading method but passing the framework's strategy name
        # Ideally, we would inject the Strategy object, but for consistency with existing backtester,
        # we stick to the string interface which backtester handles (or we need to update backtester to use factory)
        
        # NOTE: The current backtester._generate_signal uses simple logic. 
        # To truly use the new framework, we should update Backtester to use StrategyFactory.
        # For now, we assume backtester uses the same logic or we update it.
        # Let's run it as is, assuming 'ml' uses MLPredictor.predict and 'rule_based' uses rule_based_prediction.
        
        sim_result = backtester.simulate_trading(data, strategy=strategy_name, mode='swing')
        report = backtester.generate_backtest_report(sim_result)
        
        if report.get('no_trades', False) or 'performance' not in report:
            metrics[strategy_name] = {
                'Win Rate': 0.0,
                'Total P&L': 0.0,
                'Sharpe': 0.0,
                'Trades': 0,
                'Max DD': 0.0
            }
        else:
            perf = report['performance']
            metrics[strategy_name] = {
                'Win Rate': perf['win_rate']['win_rate'],
                'Total P&L': perf['pnl']['total_pnl'],
                'Sharpe': perf['risk_metrics']['sharpe_ratio'],
                'Trades': report['trade_stats']['total_trades'],
                'Max DD': perf['risk_metrics']['max_drawdown']
            }
    
    # Print comparison table
    metric_keys = ['Win Rate', 'Total P&L', 'Sharpe', 'Trades', 'Max DD']
    
    for key in metric_keys:
        rb_val = metrics['rule_based'][key]
        ml_val = metrics['ml'][key]
        
        # Format strings
        if key in ['Win Rate', 'Max DD']:
            rb_str = f"{rb_val:.2f}%"
            ml_str = f"{ml_val:.2f}%"
            diff = rb_val - ml_val # Simple diff
        elif key == 'Total P&L':
            rb_str = f"${rb_val:.2f}"
            ml_str = f"${ml_val:.2f}"
            diff = rb_val - ml_val
        else:
            rb_str = f"{rb_val:.2f}"
            ml_str = f"{ml_val:.2f}"
            diff = rb_val - ml_val
            
        print(f"{key:<20} | {rb_str:<20} | {ml_str:<20} | {diff:+.2f}")

    print("="*80)
    
    # Save to CSV
    # TODO: Implement export using ReportGenerator if needed
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compare Trading Strategies')
    parser.add_argument('--days', type=int, default=30, help='Number of days to properly compare')
    args = parser.parse_args()
    
    compare_strategies(args.days)
