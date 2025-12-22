"""
Backtesting Framework
Simulates trading strategy on historical data and generates performance reports
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
from database_analytics import DatabaseAnalytics
from performance_metrics import PerformanceMetrics
from ml_model import MLPredictor
from indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class Backtester:
    """
    Backtesting engine for trading strategies
    """
    
    def __init__(self, initial_capital: float = 1000.0, position_size_pct: float = 0.1):
        """
        Initialize backtester
        
        Args:
            initial_capital: Starting capital in USD
            position_size_pct: Position size as percentage of capital (0.1 = 10%)
        """
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct
        self.db = DatabaseAnalytics()
        self.performance = PerformanceMetrics()
        self.ml_predictor = MLPredictor()
        
        logger.info(f"Backtester initialized: ${initial_capital} capital, {position_size_pct*100}% position size")
    
    def load_historical_data(self, days: int = 30) -> Optional[pd.DataFrame]:
        """
        Load historical price data from database
        
        Args:
            days: Number of days of history to load
            
        Returns:
            DataFrame with historical data or None
        """
        logger.info(f"Loading {days} days of historical data...")
        
        # Get price data
        price_df = self.db.get_historical_prices(limit=days * 24 * 12)  # Assuming 5-min intervals
        
        if price_df is None or len(price_df) == 0:
            logger.warning("No historical data available")
            return None
        
        logger.info(f"Loaded {len(price_df)} historical price records")
        return price_df
    
    def simulate_trading(self, data: pd.DataFrame, strategy='rule_based', mode='swing') -> Dict:
        """
        Simulate trading on historical data.
        
        Args:
            data: DataFrame with historical price data
            strategy: Strategy name (str) OR Strategy object instance
            mode: Trading mode ('swing' or 'day')
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Starting backtest simulation: strategy={strategy}, mode={mode}")
        
        if data is None or data.empty:
            logger.warning("No data provided for simulation")
            return {'trades': [], 'equity_curve': [], 'total_return': 0}

        # Calculate indicators if missing (Vectorised for speed)
        if 'rsi' not in data.columns or data['rsi'].isna().all():
            logger.info("Calculating technical indicators...")
            try:
                # RSI
                period = 14
                delta = data['price'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                data['rsi'] = 100 - (100 / (1 + rs))
                
                # Bollinger Bands
                data['bb_middle'] = data['price'].rolling(window=20).mean()
                data['bb_std'] = data['price'].rolling(window=20).std()
                data['bb_upper'] = data['bb_middle'] + (2 * data['bb_std'])
                data['bb_lower'] = data['bb_middle'] - (2 * data['bb_std'])
                data['bb_position'] = 'inside'
                data.loc[data['price'] > data['bb_upper'], 'bb_position'] = 'above_upper'
                data.loc[data['price'] < data['bb_lower'], 'bb_position'] = 'below_lower'
    
                # MACD
                exp1 = data['price'].ewm(span=12, adjust=False).mean()
                exp2 = data['price'].ewm(span=26, adjust=False).mean()
                data['macd'] = exp1 - exp2
                data['macd_signal'] = data['macd'].ewm(span=9, adjust=False).mean()
                data['macd_histogram'] = data['macd'] - data['macd_signal']
                
                data['macd_crossover'] = 'none'
                mask_bull = (data['macd_histogram'] > 0) & (data['macd_histogram'].shift(1) <= 0)
                mask_bear = (data['macd_histogram'] < 0) & (data['macd_histogram'].shift(1) >= 0)
                data.loc[mask_bull, 'macd_crossover'] = 'bullish'
                data.loc[mask_bear, 'macd_crossover'] = 'bearish'
                
                # Volume & Price Change (assuming 5m candles, 12 periods = 1h)
                # Fallback to simple pct_change(1) if index is not strictly 5m
                data['price_change_1h'] = data['price'].pct_change(periods=12).fillna(0) * 100
                
                # Volume Ratio
                vol_ma = data['volume'].rolling(20).mean()
                data['volume_ratio'] = (data['volume'] / vol_ma).fillna(1.0)
                data['is_high_volume'] = data['volume_ratio'] > 1.5
                
                # Open Interest Change (Fill 0 if not present)
                if 'oi' in data.columns:
                     data['oi_change_1h'] = data['oi'].pct_change(periods=12).fillna(0) * 100
                else:
                     data['oi_change_1h'] = 0.0
                
                # --- NEW: Calculate missing features for ML Model ---
                # EMA
                data['ema_50'] = data['price'].ewm(span=50, adjust=False).mean()
                data['ema_200'] = data['price'].ewm(span=200, adjust=False).mean()
                data['ema_200'] = data['ema_200'].fillna(data['ema_50']) # Fallback if not enough data
                
                # Mock High/Low for ATR (The DB only has 'price')
                data['high'] = data['price']
                data['low'] = data['price']
                
                # ATR (14)
                high_low = data['high'] - data['low']
                high_close = (data['high'] - data['price'].shift()).abs()
                low_close = (data['low'] - data['price'].shift()).abs()
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = ranges.max(axis=1)
                data['atr'] = true_range.rolling(14).mean().fillna(0) # FIX: Handle initial NaNs
                
                # VWAP (Approximate cumsum)
                tp = (data['high'] + data['low'] + data['price']) / 3
                data['vwap'] = (tp * data['volume']).cumsum() / data['volume'].cumsum()
                data['vwap'] = data['vwap'].fillna(data['price']) # Fallback
                
                # Momentum (10)
                data['momentum'] = data['price'].diff(10).fillna(0) # FIX: Handle initial NaNs


            except Exception as e:
                logger.error(f"Error calculating indicators: {e}")
            
            # Pre-calculate Day Trading specific columns if mode is day
            if mode == 'day':
                try:
                   # Fast/Slow MA for Trend
                   fast_ma = data['price'].ewm(span=9).mean()
                   slow_ma = data['price'].ewm(span=21).mean()
                   
                   data['trend'] = 'neutral'
                   data.loc[fast_ma > slow_ma, 'trend'] = 'up'
                   data.loc[fast_ma < slow_ma, 'trend'] = 'down'
                   
                   data['trend_strength'] = abs(fast_ma - slow_ma) / slow_ma * 100
                   data['ma_cross_val'] = fast_ma - slow_ma
                   data['ma_cross'] = 'none'
                   mask_buy = (data['ma_cross_val'] > 0) & (data['ma_cross_val'].shift(1) <= 0)
                   mask_sell = (data['ma_cross_val'] < 0) & (data['ma_cross_val'].shift(1) >= 0)
                   data.loc[mask_buy, 'ma_cross'] = 'buy'
                   data.loc[mask_sell, 'ma_cross'] = 'sell'
                   
                   # Volatility
                   data['volatility_value'] = data['price'].rolling(5).max() / data['price'].rolling(5).min() - 1
                   data['is_volatile'] = data['volatility_value'] > 0.002 # Mock threshold
                   
                   # Volume Surge
                   vol_ma = data['volume'].rolling(20).mean()
                   data['volume_surge'] = data['volume'] / vol_ma
                   data['volume_confirmed'] = data['volume_surge'] > 1.2 # Mock threshold
                   
                   # Consolidation
                   range_high = data['price'].rolling(10).max()
                   range_low = data['price'].rolling(10).min()
                   data['is_consolidating'] = (range_high - range_low) / data['price'] < 0.005
                   
                   # Momentum
                   data['price_momentum'] = data['price'].pct_change(5) * 100
                   
                   # Spread (Mock)
                   data['current_spread'] = 0.01
                   data['spread_ok'] = True
                   
                except Exception as e:
                    logger.error(f"Error calculating day trading indicators: {e}")
            
        # Initialize strategy instance
        from strategy_framework import StrategyFactory, Strategy
        
        if isinstance(strategy, str):
            strategy_impl = StrategyFactory.get_strategy(strategy)
            strategy_name = strategy
        elif hasattr(strategy, 'generate_signal'): # Duck typing for Strategy object
            strategy_impl = strategy
            strategy_name = getattr(strategy, 'name', 'custom')
        else:
            raise ValueError(f"Invalid strategy argument: {strategy}")
            
        logger.info(f"Data range: {data['timestamp'].min()} to {data['timestamp'].max()}")
        
        capital = self.initial_capital
        position = None
        trades = []
        equity_curve = [capital]
        
        # Simulate trading
        for i in range(len(data) - 1):
            current_row = data.iloc[i]
            next_row = data.iloc[i + 1]
            
            current_price = current_row['price']
            current_time = current_row['timestamp']
            
            # Generate signal using the instance
            signal = self._generate_signal(current_row, strategy_impl, mode)
            
            if signal and signal['signal'] != 'NEUTRAL':
                # Realistic TP/SL Logic matching PaperTrader
                # TP = 4%, SL = 2%
                entry_price = current_price
                tp_pct = 0.04
                sl_pct = 0.02
                
                if signal['signal'] == 'PUMP':
                    take_profit = entry_price * (1 + tp_pct)
                    stop_loss = entry_price * (1 - sl_pct)
                else: # DUMP
                    take_profit = entry_price * (1 - tp_pct)
                    stop_loss = entry_price * (1 + sl_pct)
                
                # Check subsequent candles for exit
                exit_price = None
                exit_time = None
                exit_reason = None
                
                # Limit max holding to 24 hours (288 5-min candles) to avoid infinite holding
                max_hold_idx = min(i + 288, len(data) - 1)
                
                for j in range(i + 1, max_hold_idx + 1):
                    future_row = data.iloc[j]
                    high = future_row.get('high', future_row['price']) # Use high/low if available, else close
                    low = future_row.get('low', future_row['price'])
                    
                    if signal['signal'] == 'PUMP':
                        if low <= stop_loss:
                            exit_price = stop_loss
                            exit_time = future_row['timestamp']
                            exit_reason = 'STOP_LOSS'
                            break
                        elif high >= take_profit:
                            exit_price = take_profit
                            exit_time = future_row['timestamp']
                            exit_reason = 'TAKE_PROFIT'
                            break
                    else: # DUMP
                        if high >= stop_loss:
                            exit_price = stop_loss
                            exit_time = future_row['timestamp']
                            exit_reason = 'STOP_LOSS'
                            break
                        elif low <= take_profit:
                            exit_price = take_profit
                            exit_time = future_row['timestamp']
                            exit_reason = 'TAKE_PROFIT'
                            break
                
                # If trade didn't hit TP/SL by max hold, close at market
                if exit_price is None:
                    exit_price = data.iloc[max_hold_idx]['price']
                    exit_time = data.iloc[max_hold_idx]['timestamp']
                    exit_reason = 'TIME_EXIT'
                
                # Calculate P&L
                position_size = capital * self.position_size_pct
                
                if signal['signal'] == 'PUMP':
                    return_pct = (exit_price - entry_price) / entry_price
                else:
                    return_pct = (entry_price - exit_price) / entry_price
                
                pnl = position_size * return_pct
                capital += pnl
                
                # Record trade
                trade = {
                    'entry_time': current_time,
                    'exit_time': exit_time,
                    'signal_type': signal['signal'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'position_size': position_size,
                    'pnl': pnl,
                    'return_pct': return_pct * 100,
                    'probability': signal.get('probability', 0),
                    'confidence': signal.get('confidence', 'UNKNOWN'),
                    'exit_reason': exit_reason
                }
                trades.append(trade)
                equity_curve.append(capital)
                
                # Skip processed candles (simplified: just jump i? No, loop handles i)
                # In a real backtester we might jump 'i' to 'j', but here signals might overlap in theory.
                # To be conservative/simple, let's just let it continue generating signals 
                # (assuming multiple positions allowed or just testing signal quality)
                # BUT PaperTrader says "one position at a time". Let's update 'i' to skip overlap?
                # Python loop 'for i' doesn't support modifying i easily. 
                # Correct approach: we should skip generating new signals while in a trade if we want to mimic strictly.
                # For Screener validation, evaluating every signal is actually better. 
                # Let's keep it generating all signals to see their raw quality.
        
        # Calculate results
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        results = {
            'initial_capital': self.initial_capital,
            'final_capital': capital,
            'total_return': capital - self.initial_capital,
            'total_return_pct': ((capital - self.initial_capital) / self.initial_capital) * 100,
            'num_trades': len(trades),
            'trades': trades_df,
            'equity_curve': equity_curve,
            'strategy': strategy_name,
            'mode': mode
        }
        
        logger.info(f"Simulation complete: {len(trades)} trades, "
                   f"${results['total_return']:.2f} ({results['total_return_pct']:.2f}%) return")
        
        return results
    
    def _generate_signal(self, row: pd.Series, strategy, mode: str) -> Optional[Dict]:
        """
        Generate trading signal for a given data point using Strategy Framework
        
        Args:
            row: Data row with price and indicators
            strategy: Strategy name (str) OR Strategy object instance
            mode: Trading mode
            
        Returns:
            Signal dict or None
        """
        try:
            from strategy_framework import StrategyFactory, Strategy
            
            # Get strategy instance (handle both string and object)
            if isinstance(strategy, str):
                strategy_impl = StrategyFactory.get_strategy(strategy)
            else:
                strategy_impl = strategy
            
            # Extract indicators from row (assuming they are columns in the dataframe)
            indicators = {
                'rsi': row.get('rsi', 50),
                'macd': row.get('macd', 0),
                'macd_signal': row.get('macd_signal', 0),
                'bb_upper': row.get('bb_upper', 0),
                'bb_middle': row.get('bb_middle', 0), # Added for completeness
                'bb_lower': row.get('bb_lower', 0),
                'bb_position': row.get('bb_position', 'inside'),
                'volume_ratio': row.get('volume_ratio', 1.0),
                'is_high_volume': row.get('is_high_volume', False),
                'macd_crossover': row.get('macd_crossover', 'none'),
                'momentum': row.get('momentum', 0),
                'fear_greed': row.get('fear_greed_index', 50),
                'ema_50': row.get('ema_50', 0), # Needed for ML features
                'ema_200': row.get('ema_200', 0), # Needed for ML features
                'atr': row.get('atr', 0), # Needed for ML features
                'vwap': row.get('vwap', 0) # Needed for ML features
            }
            
            # Simple derived indicators logic for context if not in row
            if 'bb_position' not in row:
                if row.get('price', 0) > indicators['bb_upper']:
                    indicators['bb_position'] = 'above_upper'
                elif row.get('price', 0) < indicators['bb_lower']:
                    indicators['bb_position'] = 'below_lower'
            
            # Inject Day Trading Indicators if mode is 'day'
            if mode == 'day':
                # We need to construct a mini-dataframe for calculation or approximate it
                # Since we are inside _generate_signal (per row), we don't have full context efficiently.
                # However, backtester should have pre-calculated these in simulate_trading ideally.
                # For now, let's mock the structure needed by ML model using available row data
                # Assuming 'row' has access to pre-calculated day columns if we added them in simulate_trading.
                # Since we haven't added them there yet, let's look for them or default them.
                
                # Check if we have day_trading columns (calculated in simulate_trading)
                # If not, we might need to rely on the fact that ML model skips them if missing, 
                # BUT we want to enable them.
                
                # Let's assume we will add calculation in simulate_trading. 
                # Here we pack them into the expected dict structure.
                
                day_inds = {
                    'trend': row.get('trend', 'neutral'),
                    'trend_strength': row.get('trend_strength', 0),
                    'volatility_value': row.get('volatility_value', 0),
                    'volume_surge': row.get('volume_surge', 0),
                    'is_consolidating': row.get('is_consolidating', False),
                    'price_momentum': row.get('price_momentum', 0),
                    'current_spread': row.get('current_spread', 0),
                    'is_volatile': row.get('is_volatile', False),
                    'signals': {
                        'ma_cross': row.get('ma_cross', None),
                        'volume_confirmed': row.get('volume_confirmed', False),
                        'spread_ok': row.get('spread_ok', True) # Default to True in backtest
                    }
                }
                indicators['day_trading'] = day_inds
                
                # We also need 'is_valid_for_daytrading'
                # Let's perform a lightweight check here closely matching indicators.py
                is_valid = (
                    day_inds['is_volatile'] and 
                    day_inds['signals']['volume_confirmed'] and 
                    indicators['bb_position'] == 'inside'
                )
                indicators['is_valid_for_daytrading'] = is_valid

            # Generate signal
            signal = strategy_impl.generate_signal(row, indicators, mode=mode)
            
            return signal
            
        except Exception as e:
            logger.debug(f"Error generating signal: {e}")
            return None
    
    def generate_backtest_report(self, results: Dict) -> Dict:
        """
        Generate comprehensive backtest report
        
        Args:
            results: Simulation results from simulate_trading
            
        Returns:
            dict with detailed performance metrics
        """
        if not results or results['num_trades'] == 0:
            logger.warning("No trades to analyze")
            return {
                'summary': 'No trades executed',
                'metrics': {},
                'no_trades': True,
                'capital': {
                    'initial': results.get('initial_capital', 0),
                    'final': results.get('final_capital', 0),
                    'total_return': 0,
                    'total_return_pct': 0
                }
            }
        
        trades_df = results['trades']
        
        # Convert trades to signals format for performance metrics
        signals_df = pd.DataFrame({
            'timestamp': trades_df['entry_time'],
            'signal_type': trades_df['signal_type'],
            'price': trades_df['entry_price'],
            'result_price': trades_df['exit_price'],
            'probability': trades_df['probability'],
            'confidence': trades_df['confidence'],
            'actual_result': trades_df['pnl'].apply(lambda x: 'correct' if x > 0 else 'incorrect')
        })
        
        # Generate performance report
        perf_report = self.performance.generate_performance_report(
            signals_df, 
            initial_capital=results['initial_capital']
        )
        
        # Add backtest-specific metrics
        report = {
            'backtest_period': {
                'start': trades_df['entry_time'].min(),
                'end': trades_df['exit_time'].max(),
                'duration_days': (trades_df['exit_time'].max() - trades_df['entry_time'].min()).days
            },
            'strategy': results['strategy'],
            'mode': results['mode'],
            'capital': {
                'initial': results['initial_capital'],
                'final': results['final_capital'],
                'total_return': results['total_return'],
                'total_return_pct': results['total_return_pct']
            },
            'performance': perf_report,
            'trade_stats': {
                'total_trades': results['num_trades'],
                'avg_trade_duration': self._calculate_avg_duration(trades_df),
                'best_trade_pct': trades_df['return_pct'].max() if len(trades_df) > 0 else 0,
                'worst_trade_pct': trades_df['return_pct'].min() if len(trades_df) > 0 else 0,
                'avg_return_pct': trades_df['return_pct'].mean() if len(trades_df) > 0 else 0
            },
            'no_trades': False
        }
        
        logger.info("Backtest report generated successfully")
        return report
    
    def _calculate_avg_duration(self, trades_df: pd.DataFrame) -> str:
        """Calculate average trade duration"""
        if len(trades_df) == 0:
            return "N/A"
        
        durations = trades_df['exit_time'] - trades_df['entry_time']
        avg_duration = durations.mean()
        
        # Format as human-readable
        hours = avg_duration.total_seconds() / 3600
        if hours < 1:
            return f"{avg_duration.total_seconds() / 60:.0f} minutes"
        elif hours < 24:
            return f"{hours:.1f} hours"
        else:
            return f"{hours / 24:.1f} days"
    
    def print_report(self, report: Dict):
        """
        Print backtest report to console
        
        Args:
            report: Report dict from generate_backtest_report
        """
        print("\n" + "=" * 70)
        print("BACKTEST REPORT")
        print("=" * 70)
        
        # Check if no trades
        if report.get('no_trades', False):
            print("\n[INFO] No trades executed during backtestperiod.")
            print("Possible reasons:")
            print("  - Insufficient historical data")
            print("  - No signals met trading criteria")
            print("  - Strategy thresholds too strict")
            print(f"\nCapital remained unchanged: ${report['capital']['initial']:.2f}")
            print("\n" + "=" * 70)
            return
        
        # Period
        print(f"\nBacktest Period:")
        print(f"  Start: {report['backtest_period']['start']}")
        print(f"  End: {report['backtest_period']['end']}")
        print(f"  Duration: {report['backtest_period']['duration_days']} days")
        
        # Strategy
        print(f"\nStrategy: {report['strategy'].upper()}")
        print(f"Mode: {report['mode'].upper()}")
        
        # Capital
        print(f"\nCapital:")
        print(f"  Initial: ${report['capital']['initial']:.2f}")
        print(f"  Final: ${report['capital']['final']:.2f}")
        print(f"  Total Return: ${report['capital']['total_return']:.2f} ({report['capital']['total_return_pct']:.2f}%)")
        
        # Performance
        perf = report['performance']
        print(f"\nPerformance Metrics:")
        print(f"  Win Rate: {perf['win_rate']['win_rate']:.1f}%")
        print(f"  Total P&L: ${perf['pnl']['total_pnl']:.2f}")
        print(f"  Sharpe Ratio: {perf['risk_metrics']['sharpe_ratio']:.3f}")
        print(f"  Max Drawdown: {perf['risk_metrics']['max_drawdown']:.2f}%")
        
        # Trade Stats
        print(f"\nTrade Statistics:")
        print(f"  Total Trades: {report['trade_stats']['total_trades']}")
        print(f"  Avg Duration: {report['trade_stats']['avg_trade_duration']}")
        print(f"  Best Trade: {report['trade_stats']['best_trade_pct']:.2f}%")
        print(f"  Worst Trade: {report['trade_stats']['worst_trade_pct']:.2f}%")
        print(f"  Avg Return: {report['trade_stats']['avg_return_pct']:.2f}%")
        
        # Streaks
        print(f"\nStreaks:")
        print(f"  Max Win Streak: {perf['streaks']['max_win_streak']}")
        print(f"  Max Loss Streak: {perf['streaks']['max_loss_streak']}")
        
        print("\n" + "=" * 70)
    
    def run_backtest(self, days: int = 30, strategy: str = 'rule_based', 
                    mode: str = 'swing') -> Dict:
        """
        Run complete backtest: load data, simulate, generate report
        
        Args:
            days: Days of historical data
            strategy: Trading strategy
            mode: Trading mode
            
        Returns:
            Complete backtest results with report
        """
        logger.info(f"Running backtest: {days} days, {strategy} strategy, {mode} mode")
        
        # Load data
        data = self.load_historical_data(days=days)
        
        if data is None:
            logger.error("Failed to load historical data")
            return None
        
        # Simulate trading
        results = self.simulate_trading(data, strategy=strategy, mode=mode)
        
        if results is None:
            logger.error("Simulation failed")
            return None
        
        # Generate report
        report = self.generate_backtest_report(results)
        
        # Print to console
        self.print_report(report)
        
        return {
            'results': results,
            'report': report
        }
