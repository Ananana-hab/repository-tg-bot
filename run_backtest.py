"""
Run Backtest Script
Command-line tool for running backtests on historical data
"""
import sys
sys.path.insert(0, '.')

import argparse
from backtester import Backtester
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    """Main entry point for backtest execution"""
    
    parser = argparse.ArgumentParser(
        description='Run backtest on historical trading data'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days of historical data to use (default: 30)'
    )
    
    parser.add_argument(
        '--strategy',
        type=str,
        choices=['rule_based', 'ml'],
        default='rule_based',
        help='Trading strategy to test (default: rule_based)'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['swing', 'day'],
        default='swing',
        help='Trading mode: swing or day trading (default: swing)'
    )
    
    parser.add_argument(
        '--capital',
        type=float,
        default=1000.0,
        help='Initial capital in USD (default: 1000.0)'
    )
    
    parser.add_argument(
        '--position-size',
        type=float,
        default=0.1,
        help='Position size as decimal (0.1 = 10%% of capital, default: 0.1)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("BACKTEST CONFIGURATION")
    print("=" * 70)
    print(f"Historical Data: {args.days} days")
    print(f"Strategy: {args.strategy}")
    print(f"Mode: {args.mode}")
    print(f"Initial Capital: ${args.capital:.2f}")
    print(f"Position Size: {args.position_size * 100:.1f}%")
    print("=" * 70)
    
    # Initialize backtester
    
    # Force ML Model usage if strategy is ML
    if args.strategy == 'ml':
        import config
        config.USE_ML_MODEL = True
        print("[INFO] Forcing config.USE_ML_MODEL = True for ML strategy backtest")

    backtester = Backtester(
        initial_capital=args.capital,
        position_size_pct=args.position_size
    )
    
    # Run backtest
    result = backtester.run_backtest(
        days=args.days,
        strategy=args.strategy,
        mode=args.mode
    )
    
    if result:
        print("\n[SUCCESS] Backtest completed successfully!")
        
        # Optionally save results to file
        save = input("\nSave detailed results to file? (y/n): ").strip().lower()
        if save == 'y':
            import json
            from datetime import datetime
            
            filename = f"backtest_{args.strategy}_{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Prepare data for JSON serialization
            trades_list = result['results']['trades'].to_dict('records') if not result['results']['trades'].empty else []
            
            save_data = {
                'config': {
                    'days': args.days,
                    'strategy':args.strategy,
                    'mode': args.mode,
                    'initial_capital': args.capital,
                    'position_size_pct': args.position_size
                },
                'report': {
                    'backtest_period': {
                        'start': str(result['report']['backtest_period']['start']),
                        'end': str(result['report']['backtest_period']['end']),
                        'duration_days': result['report']['backtest_period']['duration_days']
                    },
                    'capital': result['report']['capital'],
                    'performance': {
                        'win_rate': result['report']['performance']['win_rate'],
                        'pnl': result['report']['performance']['pnl'],
                        'risk_metrics': result['report']['performance']['risk_metrics'],
                        'streaks': result['report']['performance']['streaks']
                    },
                    'trade_stats': result['report']['trade_stats']
                },
                'trades': trades_list
            }
            
            with open(filename, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            print(f"\n[OK] Results saved to: {filename}")
    else:
        print("\n[ERROR] Backtest failed. Check logs for details.")
        return 1
    
    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
