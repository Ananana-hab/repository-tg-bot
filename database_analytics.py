"""
Database Analytics Extensions
Provides additional database methods for performance analysis and backtesting
"""
import pandas as pd
import logging
from datetime import datetime
from database import Database

logger = logging.getLogger(__name__)


class DatabaseAnalytics(Database):
    """
    Extension class for Database with analytics methods
    Inherits all methods from Database and adds analytics capabilities
    """
    
    def get_signals_for_analysis(self, days=30, signal_type=None):
        """
        Получает сигналы с ценовыми данными для анализа производительности
        
        Args:
            days: количество дней истории
            signal_type: фильтр по типу сигнала ('PUMP', 'DUMP' или None для всех)
            
        Returns:
            pandas DataFrame с колонками: id, timestamp, signal_type, probability, 
            price, confidence, actual_result, result_price, result_timestamp
        """
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT 
                        id, timestamp, signal_type, probability, price, 
                        confidence, actual_result, result_price, result_timestamp
                    FROM signals
                    WHERE timestamp >= datetime('now', ?)
                """
                
                params = [f'-{days} days']
                
                if signal_type:
                    query += " AND signal_type = ?"
                    params.append(signal_type)
                
                query += " ORDER BY timestamp ASC"
                
                df = pd.read_sql_query(query, conn, params=params)
                
                # Convert timestamp columns to datetime
                if len(df) > 0:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    if 'result_timestamp' in df.columns:
                        df['result_timestamp'] = pd.to_datetime(df['result_timestamp'])
                
                logger.info(f"Retrieved {len(df)} signals for analysis")
                return df
                
        except Exception as e:
            logger.error(f"Error getting signals for analysis: {e}")
            return None
    
    def get_historical_prices(self, start_date=None, end_date=None, limit=1000):
        """
        Получает исторические цены для бэктестинга
        
        Args:
            start_date: начальная дата (datetime или строка)
            end_date: конечная дата (datetime или строка)
            limit: максимальное количество записей
            
        Returns:
            pandas DataFrame с колонками: timestamp, price, volume, и индикаторы
        """
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT 
                        timestamp, price, volume, rsi, macd, macd_signal,
                        bb_upper, bb_lower, fear_greed_index
                    FROM price_data
                    WHERE 1=1
                """
                
                params = []
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(str(start_date))
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(str(end_date))
                
                query += " ORDER BY timestamp ASC LIMIT ?"
                params.append(limit)
                
                df = pd.read_sql_query(query, conn, params=params)
                
                if len(df) > 0:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                logger.info(f"Retrieved {len(df)} historical price records")
                return df
                
        except Exception as e:
            logger.error(f"Error getting historical prices: {e}")
            return None
    
    def get_equity_curve(self, days=30, initial_capital=1000.0):
        """
        Рассчитывает кривую капитала на основе результатов сигналов
        
        Args:
            days: количество дней истории
            initial_capital: начальный капитал
            
        Returns:
            pandas DataFrame с колонками: timestamp, equity, signal_type, pnl
        """
        try:
            signals_df = self.get_signals_for_analysis(days=days)
            
            if signals_df is None or len(signals_df) == 0:
                logger.warning("No signals found for equity curve calculation")
                return None
            
            # Filter completed signals with result prices
            completed = signals_df[
                (signals_df['result_price'].notna()) & 
                (signals_df['price'].notna())
            ].copy()
            
            if len(completed) == 0:
                logger.warning("No completed signals found")
                return None
            
            # Calculate P&L for each signal
            position_size_pct = 0.1  # 10% per trade
            equity = initial_capital
            equity_curve = []
            
            for _, signal in completed.iterrows():
                position_size = equity * position_size_pct
                
                # Calculate P&L
                if signal['signal_type'] == 'PUMP':
                    return_pct = (signal['result_price'] - signal['price']) / signal['price']
                else:  # DUMP
                    return_pct = (signal['price'] - signal['result_price']) / signal['price']
                
                pnl = position_size * return_pct
                equity += pnl
                
                equity_curve.append({
                    'timestamp': signal['timestamp'],
                    'equity': equity,
                    'signal_type': signal['signal_type'],
                    'pnl': pnl
                })
            
            equity_df = pd.DataFrame(equity_curve)
            logger.info(f"Generated equity curve with {len(equity_df)} points")
            
            return equity_df
            
        except Exception as e:
            logger.error(f"Error calculating equity curve: {e}")
            return None
