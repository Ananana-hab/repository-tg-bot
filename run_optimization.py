
import logging
import argparse
import sys
from strategy_optimizer import StrategyOptimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Run Strategy Optimization')
    parser.add_argument('--days', type=int, default=30, help='Number of days of history to use')
    parser.add_argument('--full', action='store_true', help='Run full grid search (slower)')
    parser.add_argument('--db', type=str, default='crypto_bot.db', help='Database file to use')
    args = parser.parse_args()
    
    # Define Parameter Grid
    if args.full:
        param_grid = {
            'rsi_oversold': [25, 30, 35],
            'rsi_overbought': [65, 70, 75],
            'rsi_score': [1, 2, 3],
            'macd_score': [1, 2],
            'bb_score': [1, 2, 3]
        }
    else:
        # Smaller grid for quick test
        param_grid = {
            'rsi_oversold': [25, 30, 35],
            'rsi_overbought': [65, 70, 80],
            'score_threshold': [3, 4, 5]
        }
    
    optimizer = StrategyOptimizer(db_path=args.db)
    
    print(f"Running optimization over {args.days} days using {args.db}...")
    print(f"Grid: {param_grid}")
    
    results = optimizer.optimize('rule_based', param_grid, days=args.days)
    
    if results is not None and not results.empty:
        print("\n=== Top 5 Configurations ===")
        print(results.head(5).to_string())
        
        best = results.iloc[0]
        print("\n=== Best Configuration ===")
        for key in param_grid.keys():
            if key in best:
                print(f"{key}: {best[key]}")
        
        print(f"\nReturn: {best['total_return_pct']:.2f}%")
        print(f"Sharpe: {best['sharpe_ratio']:.2f}")
        print(f"Trades: {best['trades']}")
        
        # Save to CSV
        results.to_csv('optimization_results.csv', index=False)
        print("\nFull results saved to optimization_results.csv")
    else:
        print("No results found or data unavailable.")

if __name__ == "__main__":
    main()
