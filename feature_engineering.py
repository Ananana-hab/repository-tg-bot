"""
Feature Engineering Module
Создание продвинутых признаков для ML модели
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Класс для создания продвинутых признаков"""
    
    @staticmethod
    def add_price_features(df):
        """
        Добавляет признаки на основе цены
        
        Args:
            df: DataFrame с колонками [open, high, low, close, volume]
            
        Returns:
            dict с признаками
        """
        features = {}
        
        try:
            close = df['close']
            
            # Simple Moving Averages
            features['price_sma_5'] = close.rolling(window=5).mean().iloc[-1] if len(df) >= 5 else close.iloc[-1]
            features['price_sma_20'] = close.rolling(window=20).mean().iloc[-1] if len(df) >= 20 else close.iloc[-1]
            features['price_sma_50'] = close.rolling(window=50).mean().iloc[-1] if len(df) >= 50 else close.iloc[-1]
            
            # Distance from SMAs (normalized)
            current_price = close.iloc[-1]
            features['price_dist_sma_5'] = ((current_price - features['price_sma_5']) / current_price) * 100 if features['price_sma_5'] > 0 else 0
            features['price_dist_sma_20'] = ((current_price - features['price_sma_20']) / current_price) * 100 if features['price_sma_20'] > 0 else 0
            
            # Price volatility (rolling std)
            features['price_volatility_5'] = close.rolling(window=5).std().iloc[-1] if len(df) >= 5 else 0
            features['price_volatility_20'] = close.rolling(window=20).std().iloc[-1] if len(df) >= 20 else 0
            
        except Exception as e:
            logger.error(f"Error in add_price_features: {e}")
            # Return default values
            features = {
                'price_sma_5': 0, 'price_sma_20': 0, 'price_sma_50': 0,
                'price_dist_sma_5': 0, 'price_dist_sma_20': 0,
                'price_volatility_5': 0, 'price_volatility_20': 0
            }
        
        return features
    
    @staticmethod
    def add_volume_features(df):
        """Добавляет признаки на основе объема"""
        features = {}
        
        try:
            volume = df['volume']
            
            # Volume SMAs
            features['volume_sma_5'] = volume.rolling(window=5).mean().iloc[-1] if len(df) >= 5 else volume.iloc[-1]
            features['volume_sma_20'] = volume.rolling(window=20).mean().iloc[-1] if len(df) >= 20 else volume.iloc[-1]
            
            # Volume ratio to SMA
            current_volume = volume.iloc[-1]
            features['volume_sma_ratio_5'] = current_volume / features['volume_sma_5'] if features['volume_sma_5'] > 0 else 1.0
            features['volume_sma_ratio_20'] = current_volume / features['volume_sma_20'] if features['volume_sma_20'] > 0 else 1.0
            
            # Volume spike count (last 10 periods)
            if len(df) >= 10:
                recent_volume = volume.iloc[-10:]
                avg_volume = recent_volume.mean()
                features['volume_spike_count'] = sum(recent_volume > avg_volume * 2)
            else:
                features['volume_spike_count'] = 0
            
            # Volume trend (increasing/decreasing)
            if len(df) >= 5:
                volume_trend = volume.iloc[-5:].diff().mean()
                features['volume_trend'] = 1 if volume_trend > 0 else -1 if volume_trend < 0 else 0
            else:
                features['volume_trend'] = 0
                
        except Exception as e:
            logger.error(f"Error in add_volume_features: {e}")
            features = {
                'volume_sma_5': 0, 'volume_sma_20': 0,
                'volume_sma_ratio_5': 1.0, 'volume_sma_ratio_20': 1.0,
                'volume_spike_count': 0, 'volume_trend': 0
            }
        
        return features
    
    @staticmethod
    def add_momentum_features(df):
        """Добавляет признаки импульса"""
        features = {}
        
        try:
            close = df['close']
            
            # Rate of Change (ROC)
            if len(df) >= 5:
                features['roc_5'] = ((close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]) * 100
            else:
                features['roc_5'] = 0
            
            if len(df) >= 10:
                features['roc_10'] = ((close.iloc[-1] - close.iloc[-10]) / close.iloc[-10]) * 100
            else:
                features['roc_10'] = 0
            
            if len(df) >= 20:
                features['roc_20'] = ((close.iloc[-1] - close.iloc[-20]) / close.iloc[-20]) * 100
            else:
                features['roc_20'] = 0
            
            # Momentum acceleration (change in ROC)
            if len(df) >= 10:
                roc_current = features['roc_5']
                close_5_ago = close.iloc[-5] if len(df) >= 10 else close.iloc[-1]
                close_10_ago = close.iloc[-10] if len(df) >= 10 else close.iloc[-1]
                roc_previous = ((close_5_ago - close_10_ago) / close_10_ago) * 100 if close_10_ago > 0 else 0
                features['momentum_acceleration'] = roc_current - roc_previous
            else:
                features['momentum_acceleration'] = 0
            
            # Trend strength (consistency of direction)
            if len(df) >= 10:
                recent_changes = close.iloc[-10:].diff()
                positive_count = sum(recent_changes > 0)
                features['trend_strength'] = (positive_count / 9) * 2 - 1  # -1 to 1
            else:
                features['trend_strength'] = 0
                
        except Exception as e:
            logger.error(f"Error in add_momentum_features: {e}")
            features = {
                'roc_5': 0, 'roc_10': 0, 'roc_20': 0,
                'momentum_acceleration': 0, 'trend_strength': 0
            }
        
        return features
    
    @staticmethod
    def add_volatility_features(df, indicators):
        """Добавляет признаки волатильности"""
        features = {}
        
        try:
            close = df['close']
            
            # ATR normalized by price
            atr = indicators.get('atr', 0)
            current_price = close.iloc[-1]
            features['atr_normalized'] = (atr / current_price) * 100 if current_price > 0 else 0
            
            # Bollinger Bands width
            bb_upper = indicators.get('bb_upper', 0)
            bb_lower = indicators.get('bb_lower', 0)
            features['bollinger_width'] = ((bb_upper - bb_lower) / current_price) * 100 if current_price > 0 else 0
            
            # Volatility regime (low/medium/high)
            if len(df) >= 20:
                volatility = close.rolling(window=20).std().iloc[-1]
                avg_volatility = close.rolling(window=20).std().mean()
                
                if volatility < avg_volatility * 0.7:
                    features['volatility_regime'] = -1  # Low
                elif volatility > avg_volatility * 1.3:
                    features['volatility_regime'] = 1   # High
                else:
                    features['volatility_regime'] = 0   # Medium
            else:
                features['volatility_regime'] = 0
            
            # Price range (high - low) normalized
            if len(df) >= 1:
                high = df['high'].iloc[-1]
                low = df['low'].iloc[-1]
                features['price_range_normalized'] = ((high - low) / current_price) * 100 if current_price > 0 else 0
            else:
                features['price_range_normalized'] = 0
                
        except Exception as e:
            logger.error(f"Error in add_volatility_features: {e}")
            features = {
                'atr_normalized': 0, 'bollinger_width': 0,
                'volatility_regime': 0, 'price_range_normalized': 0
            }
        
        return features
    
    @staticmethod
    def add_market_structure_features(df):
        """Добавляет признаки рыночной структуры"""
        features = {}
        
        try:
            close = df['close']
            high = df['high']
            low = df['low']
            
            # Support/Resistance distance
            if len(df) >= 20:
                recent_high = high.iloc[-20:].max()
                recent_low = low.iloc[-20:].min()
                current_price = close.iloc[-1]
                
                features['distance_to_resistance'] = ((recent_high - current_price) / current_price) * 100 if current_price > 0 else 0
                features['distance_to_support'] = ((current_price - recent_low) / current_price) * 100 if current_price > 0 else 0
            else:
                features['distance_to_resistance'] = 0
                features['distance_to_support'] = 0
            
            # Higher highs / Lower lows pattern
            if len(df) >= 10:
                highs = high.iloc[-10:]
                lows = low.iloc[-10:]
                
                higher_highs = sum(highs.diff() > 0)
                lower_lows = sum(lows.diff() < 0)
                
                features['higher_highs_count'] = higher_highs
                features['lower_lows_count'] = lower_lows
            else:
                features['higher_highs_count'] = 0
                features['lower_lows_count'] = 0
                
        except Exception as e:
            logger.error(f"Error in add_market_structure_features: {e}")
            features = {
                'distance_to_resistance': 0, 'distance_to_support': 0,
                'higher_highs_count': 0, 'lower_lows_count': 0
            }
        
        return features
    
    @staticmethod
    def engineer_all_features(df, indicators, market_data):
        """
        Создает все продвинутые признаки
        
        Args:
            df: DataFrame с OHLCV данными
            indicators: dict с базовыми индикаторами
            market_data: dict с рыночными данными
            
        Returns:
            dict со всеми признаками (35+)
        """
        all_features = {}
        
        try:
            # Price features (7)
            all_features.update(FeatureEngineer.add_price_features(df))
            
            # Volume features (6)
            all_features.update(FeatureEngineer.add_volume_features(df))
            
            # Momentum features (5)
            all_features.update(FeatureEngineer.add_momentum_features(df))
            
            # Volatility features (4)
            all_features.update(FeatureEngineer.add_volatility_features(df, indicators))
            
            # Market structure features (4)
            all_features.update(FeatureEngineer.add_market_structure_features(df))
            
            # Add original indicators (базовые признаки)
            all_features.update({
                'rsi': indicators.get('rsi', 50),
                'macd': indicators.get('macd', 0),
                'bb_position_above': 1 if indicators.get('bb_position') == 'above_upper' else 0,
                'bb_position_below': 1 if indicators.get('bb_position') == 'below_lower' else 0,
                'ema_cross': 1 if indicators.get('ema_200', 0) > 0 and indicators.get('ema_50', 0) > indicators.get('ema_200', 0) else 0,
                'fear_greed': market_data.get('fear_greed', 50),
                'orderbook_imbalance': indicators.get('orderbook_imbalance', 0),
                'oi_change_1h': market_data.get('oi_change_1h', 0),
                'oi_change_4h': market_data.get('oi_change_4h', 0),
            })
            
            logger.debug(f"Engineered {len(all_features)} features")
            
        except Exception as e:
            logger.error(f"Error in engineer_all_features: {e}")
        
        return all_features


def test_feature_engineering():
    """Тест создания признаков"""
    import pandas as pd
    
    # Создаем тестовые данные
    df = pd.DataFrame({
        'open': [50000 + i*10 for i in range(100)],
        'high': [50100 + i*10 for i in range(100)],
        'low': [49900 + i*10 for i in range(100)],
        'close': [50000 + i*10 for i in range(100)],
        'volume': [1000 + i for i in range(100)]
    })
    
    indicators = {
        'rsi': 55,
        'macd': 10,
        'atr': 100,
        'bb_upper': 51000,
        'bb_lower': 49000,
        'bb_position': 'middle'
    }
    
    market_data = {
        'fear_greed': 60,
        'oi_change_1h': 2.5,
        'oi_change_4h': 5.0
    }
    
    features = FeatureEngineer.engineer_all_features(df, indicators, market_data)
    
    print(f"Total features: {len(features)}")
    print("\nFeatures:")
    for key, value in sorted(features.items()):
        print(f"  {key:30s}: {value:.4f}" if isinstance(value, (int, float)) else f"  {key:30s}: {value}")


if __name__ == '__main__':
    test_feature_engineering()
