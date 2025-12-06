"""
Dataset Builder для ML модели
Собирает обучающие данные из price_data с авторазметкой
"""
import pandas as pd
import numpy as np
from database import Database
from indicators import TechnicalIndicators
from data_collector import DataCollector
import config
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)


class DatasetBuilder:
    """Строит обучающий датасет из исторических данных"""
    
    def __init__(self):
        self.db = Database()
        self.data_collector = DataCollector()
        
    def get_historical_data(self, days: int = 90) -> Optional[pd.DataFrame]:
        """
        Получает исторические данные из БД
        
        Args:
            days: количество дней истории
            
        Returns:
            DataFrame с колонками: timestamp, price, volume, bb_upper, bb_lower, fear_greed_index
        """
        try:
            conn = self.db.get_connection()
            query = f"""
                SELECT timestamp, price, volume, bb_upper, bb_lower, fear_greed_index
                FROM price_data
                WHERE timestamp >= datetime('now', '-{days} days')
                ORDER BY timestamp ASC
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if len(df) == 0:
                logger.warning(f"No historical data found for last {days} days")
                return None
                
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            logger.info(f"Loaded {len(df)} historical records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}", exc_info=True)
            return None
    
    def calculate_indicators_for_row(self, df: pd.DataFrame, idx: int, window: int = 100) -> Optional[Dict]:
        """
        Рассчитывает индикаторы для конкретной строки
        
        Args:
            df: DataFrame с историческими данными
            idx: индекс строки
            window: размер окна для расчёта индикаторов
            
        Returns:
            dict с индикаторами или None
        """
        if idx < window:
            return None
            
        try:
            # Берём окно данных до текущего момента
            window_df = df.iloc[max(0, idx - window):idx + 1].copy()
            
            if len(window_df) < 50:
                return None
            
            # Создаём OHLCV DataFrame (упрощённо, используем price как close)
            ohlcv_df = pd.DataFrame({
                'timestamp': window_df['timestamp'].values,
                'open': window_df['price'].values,
                'high': window_df['price'].values,
                'low': window_df['price'].values,
                'close': window_df['price'].values,
                'volume': window_df['volume'].values
            })
            
            # Рассчитываем индикаторы
            indicators = TechnicalIndicators.calculate_all_indicators(
                ohlcv_df,
                orderbook=None,
                mode='swing'
            )
            
            if not indicators:
                return None
                
            return indicators
            
        except Exception as e:
            logger.debug(f"Error calculating indicators for row {idx}: {e}")
            return None
    
    def label_sample(self, df: pd.DataFrame, idx: int, horizon_minutes: int = 60, 
                    pump_threshold: float = 2.5, dump_threshold: float = -2.5) -> Optional[str]:
        """
        Авторазметка: определяет метку на основе будущего изменения цены
        
        Args:
            df: DataFrame с данными
            idx: текущий индекс
            horizon_minutes: горизонт прогноза в минутах
            pump_threshold: порог для PUMP (%)
            dump_threshold: порог для DUMP (%)
            
        Returns:
            'PUMP', 'DUMP' или 'NEUTRAL'
        """
        if idx >= len(df) - 1:
            return None
            
        current_price = df.iloc[idx]['price']
        current_time = df.iloc[idx]['timestamp']
        
        # Находим цену через horizon_minutes
        target_time = current_time + timedelta(minutes=horizon_minutes)
        
        # Ищем ближайшую запись после target_time
        future_df = df[df['timestamp'] > target_time]
        if len(future_df) == 0:
            return None
            
        future_price = future_df.iloc[0]['price']
        
        # Рассчитываем изменение в %
        price_change = ((future_price - current_price) / current_price) * 100
        
        # Разметка
        if price_change >= pump_threshold:
            return 'PUMP'
        elif price_change <= dump_threshold:
            return 'DUMP'
        else:
            return 'NEUTRAL'
    
    def build_dataset(self, days: int = 90, horizon_minutes: int = 60,
                     pump_threshold: float = 2.5, dump_threshold: float = -2.5,
                     min_samples_per_class: int = 100) -> Optional[pd.DataFrame]:
        """
        Строит полный обучающий датасет
        
        Args:
            days: количество дней истории
            horizon_minutes: горизонт прогноза
            pump_threshold: порог для PUMP
            dump_threshold: порог для DUMP
            min_samples_per_class: минимальное количество примеров на класс
            
        Returns:
            DataFrame с фичами и метками
        """
        logger.info(f"Building dataset: {days} days, horizon={horizon_minutes}min")
        
        # Загружаем исторические данные
        df = self.get_historical_data(days)
        if df is None or len(df) < 200:
            logger.error("Not enough historical data")
            return None
        
        samples = []
        window = 100
        
        # Обрабатываем каждую строку (с шагом для ускорения)
        step = max(1, len(df) // 10000)  # Обрабатываем максимум 10k примеров
        
        for idx in range(window, len(df) - horizon_minutes, step):
            try:
                # Рассчитываем индикаторы
                indicators = self.calculate_indicators_for_row(df, idx, window)
                if not indicators:
                    continue
                
                # Размечаем
                label = self.label_sample(df, idx, horizon_minutes, pump_threshold, dump_threshold)
                if not label:
                    continue
                
                # Формируем фичи (как в prepare_features, но без market_data)
                features = {
                    'bb_upper': indicators.get('bb_upper', 0),
                    'bb_lower': indicators.get('bb_lower', 0),
                    'bb_middle': indicators.get('bb_middle', 0),
                    'bb_position_above': 1 if indicators.get('bb_position') == 'above_upper' else 0,
                    'bb_position_below': 1 if indicators.get('bb_position') == 'below_lower' else 0,
                    'ema_50': indicators.get('ema_50', 0),
                    'ema_200': indicators.get('ema_200', indicators.get('ema_50', 0)),
                    'volume_ratio': indicators.get('volume_ratio', 1.0),
                    'is_high_volume': 1 if indicators.get('is_high_volume') else 0,
                    'momentum': indicators.get('momentum', 0),
                    'atr': indicators.get('atr', 0),
                    'vwap': indicators.get('vwap', 0) if indicators.get('vwap') else 0,
                    'orderbook_imbalance': indicators.get('orderbook_imbalance', 0),
                    'fear_greed': df.iloc[idx]['fear_greed_index'] if pd.notna(df.iloc[idx]['fear_greed_index']) else 50,
                    'current_volume': df.iloc[idx]['volume'],
                    'current_price': df.iloc[idx]['price'],
                    'timestamp': df.iloc[idx]['timestamp'],
                    'label': label
                }
                
                # Добавляем price changes (нужно рассчитать из истории)
                if idx >= 12:  # 1h для 5m свечей
                    price_1h_ago = df.iloc[max(0, idx - 12)]['price']
                    price_change_1h = ((df.iloc[idx]['price'] - price_1h_ago) / price_1h_ago) * 100
                    features['price_change_1h'] = price_change_1h
                else:
                    features['price_change_1h'] = 0
                    
                if idx >= 48:  # 4h для 5m свечей
                    price_4h_ago = df.iloc[max(0, idx - 48)]['price']
                    price_change_4h = ((df.iloc[idx]['price'] - price_4h_ago) / price_4h_ago) * 100
                    features['price_change_4h'] = price_change_4h
                else:
                    features['price_change_4h'] = 0
                
                # OI changes (если нет в БД, ставим 0)
                features['oi_change_5m'] = 0
                features['oi_change_1h'] = 0
                features['oi_change_4h'] = 0
                
                samples.append(features)
                
            except Exception as e:
                logger.debug(f"Error processing row {idx}: {e}")
                continue
        
        if len(samples) == 0:
            logger.error("No samples generated")
            return None
        
        dataset_df = pd.DataFrame(samples)
        
        # Проверяем баланс классов
        label_counts = dataset_df['label'].value_counts()
        logger.info(f"Dataset built: {len(dataset_df)} samples")
        logger.info(f"Label distribution:\n{label_counts}")
        
        # Проверяем минимальное количество примеров
        for label in ['PUMP', 'DUMP', 'NEUTRAL']:
            count = label_counts.get(label, 0)
            if count < min_samples_per_class:
                logger.warning(f"Class {label} has only {count} samples (min: {min_samples_per_class})")
        
        return dataset_df
    
    def save_dataset(self, dataset_df: pd.DataFrame, filepath: str = 'training_dataset.parquet'):
        """Сохраняет датасет в файл"""
        try:
            dataset_df.to_parquet(filepath, index=False)
            logger.info(f"Dataset saved to {filepath}: {len(dataset_df)} samples")
        except Exception as e:
            logger.error(f"Error saving dataset: {e}")
            # Fallback to CSV
            dataset_df.to_csv(filepath.replace('.parquet', '.csv'), index=False)
            logger.info(f"Dataset saved to CSV: {filepath.replace('.parquet', '.csv')}")


if __name__ == '__main__':
    builder = DatasetBuilder()
    dataset = builder.build_dataset(days=90, horizon_minutes=60, pump_threshold=2.5, dump_threshold=-2.5)
    if dataset is not None:
        builder.save_dataset(dataset)
        print(f"\n✅ Dataset ready: {len(dataset)} samples")
        print(dataset['label'].value_counts())
    else:
        print("❌ Failed to build dataset")

