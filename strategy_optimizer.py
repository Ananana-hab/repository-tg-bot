
import logging
import itertools
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from backtester import Backtester
from strategy_framework import StrategyFactory
from database_analytics import DatabaseAnalytics

logger = logging.getLogger(__name__)

class StrategyOptimizer:
    """
    Optimizes strategy parameters using Grid Search.
    """
    
    def __init__(self, db_path='crypto_bot.db', initial_capital=1000.0, position_size_pct=0.1):
        self.db_path = db_path
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct
        self.db = DatabaseAnalytics(db_path)
        
    def optimize(self, strategy_name: str, param_grid: Dict[str, List[Any]], days: int = 30):
        """
        Run Grid Search optimization.
        
        Args:
            strategy_name: Name of the strategy to optimize (e.g., 'rule_based')
            param_grid: Dictionary where keys are param names and values are lists of values to try
            days: Number of historical days to use for optimization
        
        Returns:
            DataFrame with optimization results, sorted by Sharpe Ratio
        """
        logger.info(f"Starting optimization for {strategy_name} over {days} days")
        
        # Load historical data
        data = self.db.get_historical_prices(limit=days*24*12)
        if data is None or data.empty:
            logger.error("No data available for optimization")
            return None
            
        # Generate parameter combinations
        keys, values = zip(*param_grid.items())
        combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
        
        logger.info(f"Testing {len(combinations)} parameter combinations...")
        
        results = []
        
        # Initialize backtester (can reuse instance)
        backtester = Backtester(initial_capital=self.initial_capital, position_size_pct=self.position_size_pct)
        backtester.db = self.db # Inject existing DB connection
        
        for i, params in enumerate(combinations):
            if (i+1) % 10 == 0:
                logger.info(f"Processing combination {i+1}/{len(combinations)}")
                
            # Instantiate strategy with current parameters
            try:
                strategy = StrategyFactory.get_strategy(strategy_name, **params)
            except Exception as e:
                logger.error(f"Failed to create strategy with params {params}: {e}")
                continue
            
            # Run simulation
            sim_results = backtester.simulate_trading(data.copy(), strategy=strategy, mode='swing')
            
            # Record metrics
            trade_count = sim_results.get('num_trades', 0)
            trades_df = sim_results.get('trades', pd.DataFrame())
            
            # Get performance metrics
            win_rate = 0.0
            sharpe = 0.0
            max_dd = 0.0
            
            if not trades_df.empty:
                perf_report = backtester.generate_backtest_report(sim_results)
                perf_metrics = perf_report.get('performance', {})
                win_rate = perf_metrics.get('win_rate', 0.0)
                sharpe = perf_metrics.get('sharpe_ratio', 0.0)
                max_dd = perf_metrics.get('max_drawdown', {}).get('drawdown_pct', 0.0)
            
            result_row = {
                'total_return_pct': sim_results.get('total_return_pct', 0.0),
                'sharpe_ratio': sharpe,
                'win_rate': win_rate,
                'trades': trade_count,
                'max_drawdown': max_dd
            }
            # Add parameters to result
            result_row.update(params)
            
            results.append(result_row)
            
        # Create DataFrame
        results_df = pd.DataFrame(results)
        
        # Sort by Sharpe Ratio (descending)
        if not results_df.empty:
            results_df = results_df.sort_values(by='sharpe_ratio', ascending=False)
            
        return results_df
