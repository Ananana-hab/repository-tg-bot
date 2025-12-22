"""
Performance Metrics Module
Calculates trading performance metrics for the BTC bot
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Calculate trading performance metrics"""
    
    def __init__(self):
        self.risk_free_rate = 0.04  # 4% annual risk-free rate (can be configured)
    
    def calculate_win_rate(self, signals: pd.DataFrame) -> Dict:
        """
        Calculate win rate from signals
        
        Args:
            signals: DataFrame with columns: signal_type, price, result_price, actual_result
            
        Returns:
            dict: {
                'total_signals': int,
                'wins': int,
                'losses': int,
                'win_rate': float (0-100),
                'pump_win_rate': float,
                'dump_win_rate': float
            }
        """
        if signals is None or len(signals) == 0:
            return {
                'total_signals': 0,
                'completed_signals': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'pump_win_rate': 0.0,
                'dump_win_rate': 0.0
            }
        
        # Filter for signals with results
        completed = signals[signals['actual_result'].notna()].copy()
        
        if len(completed) == 0:
            return {
                'total_signals': len(signals),
                'completed_signals': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'pump_win_rate': 0.0,
                'dump_win_rate': 0.0
            }
        
        # Calculate wins
        wins = len(completed[completed['actual_result'] == 'correct'])
        losses = len(completed[completed['actual_result'] == 'incorrect'])
        win_rate = (wins / len(completed)) * 100 if len(completed) > 0 else 0
        
        # By signal type
        pump_signals = completed[completed['signal_type'] == 'PUMP']
        dump_signals = completed[completed['signal_type'] == 'DUMP']
        
        pump_wins = len(pump_signals[pump_signals['actual_result'] == 'correct'])
        dump_wins = len(dump_signals[dump_signals['actual_result'] == 'correct'])
        
        pump_win_rate = (pump_wins / len(pump_signals)) * 100 if len(pump_signals) > 0 else 0
        dump_win_rate = (dump_wins / len(dump_signals)) * 100 if len(dump_signals) > 0 else 0
        
        return {
            'total_signals': len(signals),
            'completed_signals': len(completed),
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 2),
            'pump_win_rate': round(pump_win_rate, 2),
            'dump_win_rate': round(dump_win_rate, 2)
        }
    
    def calculate_pnl(self, signals: pd.DataFrame, initial_capital: float = 1000.0, 
                      position_size_pct: float = 0.1) -> Dict:
        """
        Calculate Profit & Loss from signals
        
        Args:
            signals: DataFrame with signal data
            initial_capital: Starting capital (default 1000 USD)
            position_size_pct: Position size as percentage of capital (default 10%)
            
        Returns:
            dict: {
                'total_pnl': float,
                'total_pnl_pct': float,
                'avg_pnl_per_signal': float,
                'best_trade': float,
                'worst_trade': float,
                'profitable_trades': int,
                'losing_trades': int
            }
        """
        if signals is None or len(signals) == 0:
            return self._empty_pnl_result()
        
        # Filter for completed signals with result prices
        completed = signals[
            (signals['result_price'].notna()) & 
            (signals['price'].notna())
        ].copy()
        
        if len(completed) == 0:
            return self._empty_pnl_result()
        
        # Calculate P&L for each signal
        pnl_list = []
        for _, signal in completed.iterrows():
            pnl = self._calculate_signal_pnl(
                signal['signal_type'],
                signal['price'],
                signal['result_price'],
                initial_capital * position_size_pct
            )
            pnl_list.append(pnl)
        
        completed['pnl'] = pnl_list
        
        # Calculate metrics
        total_pnl = sum(pnl_list)
        total_pnl_pct = (total_pnl / initial_capital) * 100
        avg_pnl = np.mean(pnl_list) if len(pnl_list) > 0 else 0
        best_trade = max(pnl_list) if len(pnl_list) > 0 else 0
        worst_trade = min(pnl_list) if len(pnl_list) > 0 else 0
        profitable = len([p for p in pnl_list if p > 0])
        losing = len([p for p in pnl_list if p < 0])
        
        return {
            'total_pnl': round(total_pnl, 2),
            'total_pnl_pct': round(total_pnl_pct, 2),
            'avg_pnl_per_signal': round(avg_pnl, 2),
            'best_trade': round(best_trade, 2),
            'worst_trade': round(worst_trade, 2),
            'profitable_trades': profitable,
            'losing_trades': losing,
            'signals_analyzed': len(completed)
        }
    
    def calculate_sharpe_ratio(self, returns: List[float], 
                               periods_per_year: int = 365) -> float:
        """
        Calculate Sharpe Ratio
        
        Args:
            returns: List of returns (as decimals, e.g., 0.05 for 5%)
            periods_per_year: Number of periods in a year (365 for daily)
            
        Returns:
            float: Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        
        # Calculate excess returns
        avg_return = np.mean(returns_array)
        std_return = np.std(returns_array, ddof=1)
        
        if std_return == 0:
            return 0.0
        
        # Annualized metrics
        annual_return = avg_return * periods_per_year
        annual_std = std_return * np.sqrt(periods_per_year)
        annual_rf = self.risk_free_rate
        
        sharpe = (annual_return - annual_rf) / annual_std
        
        return round(sharpe, 3)
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> Dict:
        """
        Calculate Maximum Drawdown
        
        Args:
            equity_curve: List of equity values over time
            
        Returns:
            dict: {
                'max_drawdown': float (percentage),
                'max_drawdown_duration': int (periods),
                'peak_value': float,
                'trough_value': float
            }
        """
        if not equity_curve or len(equity_curve) < 2:
            return {
                'max_drawdown': 0.0,
                'max_drawdown_duration': 0,
                'peak_value': 0.0,
                'trough_value': 0.0
            }
        
        equity = np.array(equity_curve)
        
        # Calculate running maximum
        running_max = np.maximum.accumulate(equity)
        
        # Calculate drawdown
        drawdown = (equity - running_max) / running_max * 100
        
        max_dd = np.min(drawdown)
        max_dd_idx = np.argmin(drawdown)
        
        # Find peak before max drawdown
        peak_idx = np.argmax(equity[:max_dd_idx+1]) if max_dd_idx > 0 else 0
        
        peak_value = equity[peak_idx]
        trough_value = equity[max_dd_idx]
        dd_duration = max_dd_idx - peak_idx
        
        return {
            'max_drawdown': round(abs(max_dd), 2),
            'max_drawdown_duration': int(dd_duration),
            'peak_value': round(peak_value, 2),
            'trough_value': round(trough_value, 2)
        }
    
    def calculate_win_loss_streaks(self, signals: pd.DataFrame) -> Dict:
        """
        Calculate win/loss streaks
        
        Args:
            signals: DataFrame with actual_result column
            
        Returns:
            dict: {
                'max_win_streak': int,
                'max_loss_streak': int,
                'current_streak': int (positive for wins, negative for losses)
            }
        """
        if signals is None or len(signals) == 0:
            return {
                'max_win_streak': 0,
                'max_loss_streak': 0,
                'current_streak': 0
            }
        
        # Filter completed signals
        completed = signals[signals['actual_result'].notna()].copy()
        
        if len(completed) == 0:
            return {
                'max_win_streak': 0,
                'max_loss_streak': 0,
                'current_streak': 0
            }
        
        # Sort by timestamp
        completed = completed.sort_values('timestamp')
        
        # Convert to win/loss sequence
        is_win = (completed['actual_result'] == 'correct').astype(int)
        
        max_win = 0
        max_loss = 0
        current = 0
        current_type = None
        
        for win in is_win:
            if win == 1:  # Win
                if current_type == 'win':
                    current += 1
                else:
                    current = 1
                    current_type = 'win'
                max_win = max(max_win, current)
            else:  # Loss
                if current_type == 'loss':
                    current += 1
                else:
                    current = 1
                    current_type = 'loss'
                max_loss = max(max_loss, current)
        
        # Current streak (positive = wins, negative = losses)
        current_streak = current if current_type == 'win' else -current
        
        return {
            'max_win_streak': max_win,
            'max_loss_streak': max_loss,
            'current_streak': current_streak
        }
    
    def generate_performance_report(self, signals: pd.DataFrame, 
                                   initial_capital: float = 1000.0) -> Dict:
        """
        Generate comprehensive performance report
        
        Args:
            signals: DataFrame with signal data
            initial_capital: Starting capital
            
        Returns:
            dict: Complete performance metrics
        """
        logger.info("Generating performance report...")
        
        # Calculate all metrics
        win_rate_data = self.calculate_win_rate(signals)
        pnl_data = self.calculate_pnl(signals, initial_capital)
        streaks = self.calculate_win_loss_streaks(signals)
        
        # Calculate equity curve for drawdown and Sharpe
        equity_curve = self._build_equity_curve(signals, initial_capital)
        
        if len(equity_curve) > 1:
            # Calculate returns from equity curve
            returns = [
                (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                for i in range(1, len(equity_curve))
            ]
            sharpe = self.calculate_sharpe_ratio(returns)
            drawdown_data = self.calculate_max_drawdown(equity_curve)
        else:
            sharpe = 0.0
            drawdown_data = {
                'max_drawdown': 0.0,
                'max_drawdown_duration': 0,
                'peak_value': initial_capital,
                'trough_value': initial_capital
            }
        
        report = {
            'summary': {
                'total_signals': win_rate_data['total_signals'],
                'completed_signals': win_rate_data['completed_signals'],
                'initial_capital': initial_capital,
                'final_capital': equity_curve[-1] if equity_curve else initial_capital,
            },
            'win_rate': win_rate_data,
            'pnl': pnl_data,
            'risk_metrics': {
                'sharpe_ratio': sharpe,
                **drawdown_data
            },
            'streaks': streaks,
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"Performance report generated: Win Rate={win_rate_data['win_rate']:.1f}%, "
                   f"Total P&L={pnl_data['total_pnl']:.2f}, Sharpe={sharpe:.2f}")
        
        return report
    
    def _calculate_signal_pnl(self, signal_type: str, entry_price: float, 
                              exit_price: float, position_size: float) -> float:
        """Calculate P&L for a single signal"""
        if signal_type == 'PUMP':
            # Long position: profit if price goes up
            return_pct = (exit_price - entry_price) / entry_price
        else:  # DUMP
            # Short position: profit if price goes down
            return_pct = (entry_price - exit_price) / entry_price
        
        return position_size * return_pct
    
    def _build_equity_curve(self, signals: pd.DataFrame, 
                           initial_capital: float) -> List[float]:
        """Build equity curve from signals"""
        if signals is None or len(signals) == 0:
            return [initial_capital]
        
        # Filter and sort completed signals
        completed = signals[
            (signals['result_price'].notna()) & 
            (signals['price'].notna())
        ].copy()
        
        if len(completed) == 0:
            return [initial_capital]
        
        completed = completed.sort_values('timestamp')
        
        equity = [initial_capital]
        position_size_pct = 0.1  # 10% of capital per trade
        
        for _, signal in completed.iterrows():
            current_capital = equity[-1]
            position_size = current_capital * position_size_pct
            
            pnl = self._calculate_signal_pnl(
                signal['signal_type'],
                signal['price'],
                signal['result_price'],
                position_size
            )
            
            new_capital = current_capital + pnl
            equity.append(new_capital)
        
        return equity
    
    def _empty_pnl_result(self) -> Dict:
        """Return empty P&L result structure"""
        return {
            'total_pnl': 0.0,
            'total_pnl_pct': 0.0,
            'avg_pnl_per_signal': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
            'profitable_trades': 0,
            'losing_trades': 0,
            'signals_analyzed': 0
        }
