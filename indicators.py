import pandas as pd
import numpy as np
import config
import logging

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Класс для расчёта технических индикаторов"""
    
    @staticmethod
    def calculate_rsi(df, period=14):
        """
        Расчёт RSI (Relative Strength Index)
        
        RSI > 70 = Перекупленность (возможен дамп)
        RSI < 30 = Перепроданность (возможен памп)
        """
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
    
    @staticmethod
    def calculate_macd(df, fast=12, slow=26, signal=9):
        """
        Расчёт MACD (Moving Average Convergence Divergence)
        
        Bullish: MACD пересекает signal line снизу вверх
        Bearish: MACD пересекает signal line сверху вниз
        """
        exp1 = df['close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=slow, adjust=False).mean()
        
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        
        return {
            'macd': macd.iloc[-1],
            'signal': signal_line.iloc[-1],
            'histogram': histogram.iloc[-1],
            'crossover': 'bullish' if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0 else
                        'bearish' if histogram.iloc[-1] < 0 and histogram.iloc[-2] >= 0 else 'none'
        }
    
    @staticmethod
    def calculate_bollinger_bands(df, period=20, std_dev=2):
        """
        Расчёт Bollinger Bands
        
        Price > Upper Band = Перекупленность
        Price < Lower Band = Перепроданность
        """
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        current_price = df['close'].iloc[-1]
        
        return {
            'upper': upper_band.iloc[-1],
            'middle': sma.iloc[-1],
            'lower': lower_band.iloc[-1],
            'position': 'above_upper' if current_price > upper_band.iloc[-1] else
                       'below_lower' if current_price < lower_band.iloc[-1] else 'inside'
        }
    
    @staticmethod
    def calculate_ema(df, period):
        """Расчёт Exponential Moving Average"""
        return df['close'].ewm(span=period, adjust=False).mean().iloc[-1]
    
    @staticmethod
    def calculate_volume_analysis(df, period=20):
        """
        Анализ объёма торгов
        
        Returns:
            dict: Средний объём и отклонение текущего объёма
        """
        avg_volume = df['volume'].rolling(window=period).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]
        
        volume_ratio = (current_volume / avg_volume) if avg_volume > 0 else 1
        
        return {
            'avg_volume': avg_volume,
            'current_volume': current_volume,
            'volume_ratio': volume_ratio,
            'is_high': volume_ratio > 1.5  # Объём выше среднего на 50%+
        }
    
    @staticmethod
    def calculate_momentum(df, period=10):
        """
        Расчёт Momentum
        
        Положительный momentum = восходящий тренд
        Отрицательный momentum = нисходящий тренд
        """
        momentum = df['close'].iloc[-1] - df['close'].iloc[-period]
        return momentum
    
    @staticmethod
    def calculate_atr(df, period=14):
        """
        Расчёт ATR (Average True Range) - волатильность
        
        Высокий ATR = высокая волатильность
        """
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        
        atr = true_range.rolling(window=period).mean().iloc[-1]
        return atr
    
    @staticmethod
    def calculate_all_indicators(df):
        """
        Рассчитывает все индикаторы и возвращает единый словарь
        
        Args:
            df: DataFrame с OHLCV данными
            
        Returns:
            dict: Все рассчитанные индикаторы
        """
        if df is None or len(df) < 50:
            logger.warning("Not enough data to calculate indicators")
            return None
        
        try:
            # RSI
            rsi = TechnicalIndicators.calculate_rsi(df, config.RSI_PERIOD)
            
            # MACD
            macd_data = TechnicalIndicators.calculate_macd(
                df,
                config.MACD_FAST,
                config.MACD_SLOW,
                config.MACD_SIGNAL
            )
            
            # Bollinger Bands
            bb_data = TechnicalIndicators.calculate_bollinger_bands(df, config.BOLLINGER_PERIOD)
            
            # EMA
            ema_50 = TechnicalIndicators.calculate_ema(df, 50)
            ema_200 = TechnicalIndicators.calculate_ema(df, 200) if len(df) >= 200 else None
            
            # Volume Analysis
            volume_data = TechnicalIndicators.calculate_volume_analysis(df, config.VOLUME_MA_PERIOD)
            
            # Momentum
            momentum = TechnicalIndicators.calculate_momentum(df, 10)
            
            # ATR
            atr = TechnicalIndicators.calculate_atr(df, 14)
            
            indicators = {
                'rsi': rsi,
                'macd': macd_data['macd'],
                'macd_signal': macd_data['signal'],
                'macd_histogram': macd_data['histogram'],
                'macd_crossover': macd_data['crossover'],
                'bb_upper': bb_data['upper'],
                'bb_middle': bb_data['middle'],
                'bb_lower': bb_data['lower'],
                'bb_position': bb_data['position'],
                'ema_50': ema_50,
                'ema_200': ema_200,
                'volume_ratio': volume_data['volume_ratio'],
                'is_high_volume': volume_data['is_high'],
                'momentum': momentum,
                'atr': atr
            }
            
            logger.info(f"Indicators calculated: RSI={rsi:.2f}, MACD crossover={macd_data['crossover']}")
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return None
    
    @staticmethod
    def get_signal_strength(indicators, price_change):
        """
        Определяет силу сигнала на основе индикаторов
        
        Returns:
            str: 'STRONG', 'MEDIUM', 'WEAK'
        """
        score = 0
        
        # RSI
        if indicators['rsi'] > 70:
            score += 2  # Сильный сигнал дампа
        elif indicators['rsi'] < 30:
            score += 2  # Сильный сигнал пампа
        elif 60 < indicators['rsi'] < 70 or 30 < indicators['rsi'] < 40:
            score += 1  # Средний сигнал
        
        # MACD Crossover
        if indicators['macd_crossover'] in ['bullish', 'bearish']:
            score += 2
        
        # Bollinger Bands
        if indicators['bb_position'] in ['above_upper', 'below_lower']:
            score += 2
        
        # Volume
        if indicators['is_high_volume']:
            score += 1
        
        # Price change
        if abs(price_change) > 5:
            score += 2
        elif abs(price_change) > 3:
            score += 1
        
        if score >= 6:
            return 'STRONG'
        elif score >= 4:
            return 'MEDIUM'
        else:
            return 'WEAK'