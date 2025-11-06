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
    def calculate_vwap(df):
        """
        Расчёт VWAP (Volume Weighted Average Price) с защитой от NaN
        
        ✅ ИСПРАВЛЕНО: Добавлена защита от деления на 0 и проверка на NaN
        """
        try:
            if df is None or len(df) == 0:
                logger.warning("VWAP: DataFrame is empty")
                return None
            
            # Проверка наличия необходимых колонок
            required_cols = ['high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                logger.warning("VWAP: Missing required columns")
                return None
            
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            cum_tp_vol = (typical_price * df['volume']).cumsum()
            cum_vol = df['volume'].cumsum()
            
            # ✅ Защита от деления на 0
            final_vol = cum_vol.iloc[-1]
            if final_vol == 0 or pd.isna(final_vol):
                logger.warning("VWAP: Cumulative volume is zero or NaN")
                return None
            
            # Вычисляем VWAP без replace (чтобы избежать NaN)
            vwap_series = cum_tp_vol / cum_vol
            result = float(vwap_series.iloc[-1])
            
            # ✅ Проверка на NaN и Infinity
            if not np.isfinite(result):
                logger.warning(f"VWAP returned invalid value: {result}")
                return None
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            return None

    @staticmethod
    def orderbook_imbalance(orderbook):
        """
        Дисбаланс стакана: (Σbid_vol − Σask_vol) / (Σbid_vol + Σask_vol)
        Возвращает 0.0 если данных недостаточно
        """
        try:
            if not orderbook or not orderbook.get('bids') or not orderbook.get('asks'):
                return 0.0
            
            bid_vol = sum(b[1] for b in orderbook['bids'])
            ask_vol = sum(a[1] for a in orderbook['asks'])
            total = bid_vol + ask_vol
            
            if total == 0:
                return 0.0
            
            imbalance = float((bid_vol - ask_vol) / total)
            
            # Проверка на валидность
            if not np.isfinite(imbalance):
                return 0.0
            
            return imbalance
            
        except Exception as e:
            logger.error(f"Error calculating orderbook imbalance: {e}")
            return 0.0

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
    def calculate_all_indicators(df, orderbook=None, mode='swing'):
        """
        Рассчитывает все индикаторы и возвращает единый словарь
        
        Args:
            df: DataFrame с OHLCV данными
            orderbook: dict стакан ордеров (опционально)
            mode: str режим работы ('swing' или 'day')
            
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

            # ✅ VWAP (исправленный - может вернуть None)
            vwap = TechnicalIndicators.calculate_vwap(df)

            # Orderbook imbalance (безопасный - всегда возвращает число)
            ob_imbalance = TechnicalIndicators.orderbook_imbalance(orderbook) if orderbook else 0.0
            
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
                'atr': atr,
                'vwap': vwap,  # ✅ Может быть None - это нормально!
                'orderbook_imbalance': ob_imbalance
            }
            
            # Добавляем индикаторы дейтрейдинга если нужно
            if mode == 'day':
                day_indicators = TechnicalIndicators.calculate_day_trading_indicators(df, orderbook)
                if day_indicators:
                    indicators.update({
                        'day_trading': day_indicators,
                        'is_valid_for_daytrading': TechnicalIndicators.validate_day_trading_conditions(indicators, day_indicators)[0]
                    })
            
            logger.info(f"Indicators calculated for {mode} mode: RSI={rsi:.2f}, MACD crossover={macd_data['crossover']}, VWAP={'OK' if vwap else 'None'}")
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}", exc_info=True)
            return None
    
    @staticmethod
    def calculate_day_trading_indicators(df, orderbook=None):
        """
        Специализированные индикаторы для дейтрейдинга
        
        Args:
            df: DataFrame с OHLCV данными минутного таймфрейма
            orderbook: Актуальный стакан заявок
            
        Returns:
            dict: Индикаторы для дейтрейдинга
        """
        try:
            day_config = config.DAY_TRADING_CONFIG
            
            # Быстрые и медленные MA
            fast_ma = df['close'].ewm(span=day_config['fast_ma']).mean()
            slow_ma = df['close'].ewm(span=day_config['slow_ma']).mean()
            
            # Определение тренда
            trend = 'up' if fast_ma.iloc[-1] > slow_ma.iloc[-1] else 'down'
            trend_strength = abs(fast_ma.iloc[-1] - slow_ma.iloc[-1]) / slow_ma.iloc[-1] * 100
            
            # Волатильность
            recent_volatility = df['high'].rolling(5).max() / df['low'].rolling(5).min() - 1
            is_volatile = recent_volatility.iloc[-1] > day_config['volatility_threshold']
            
            # Объемный анализ
            volume_ma = df['volume'].rolling(20).mean()
            volume_surge = df['volume'].iloc[-1] / volume_ma.iloc[-1]
            
            # Анализ консолидации
            consolidation_period = day_config['consolidation_period']
            price_range = (df['high'].rolling(consolidation_period).max() - 
                         df['low'].rolling(consolidation_period).min()) / df['close'].rolling(consolidation_period).mean()
            is_consolidating = price_range.iloc[-1] < day_config['volatility_threshold']
            
            # Импульс цены
            price_momentum = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5] * 100
            
            # Спред
            if orderbook:
                best_bid = float(orderbook['bids'][0][0])
                best_ask = float(orderbook['asks'][0][0])
                current_spread = (best_ask - best_bid) / best_bid * 100
            else:
                current_spread = 0
                
            return {
                'trend': trend,
                'trend_strength': trend_strength,
                'is_volatile': is_volatile,
                'volatility_value': recent_volatility.iloc[-1],
                'volume_surge': volume_surge,
                'is_consolidating': is_consolidating,
                'price_momentum': price_momentum,
                'current_spread': current_spread,
                'ma_fast': fast_ma.iloc[-1],
                'ma_slow': slow_ma.iloc[-1],
                'signals': {
                    'ma_cross': 'buy' if (fast_ma.iloc[-1] > slow_ma.iloc[-1] and 
                                        fast_ma.iloc[-2] <= slow_ma.iloc[-2]) else
                              'sell' if (fast_ma.iloc[-1] < slow_ma.iloc[-1] and 
                                       fast_ma.iloc[-2] >= slow_ma.iloc[-2]) else None,
                    'volume_confirmed': volume_surge > day_config['volume_increase_threshold'],
                    'spread_ok': current_spread < day_config['max_spread']
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating day trading indicators: {e}")
            return None
            
    @staticmethod
    def validate_day_trading_conditions(indicators, day_indicators):
        """
        Проверяет условия для дейтрейдинга
        
        Args:
            indicators: общие индикаторы
            day_indicators: специализированные индикаторы дейтрейдинга
            
        Returns:
            tuple: (bool, str) - (подходит ли для дейтрейдинга, причина)
        """
        if not day_indicators:
            return False, "Не удалось рассчитать индикаторы"
            
        day_config = config.DAY_TRADING_CONFIG
        
        # Проверка волатильности
        if not day_indicators['is_volatile']:
            return False, "Недостаточная волатильность"
            
        # Проверка объема
        if not day_indicators['signals']['volume_confirmed']:
            return False, "Недостаточный объем"
            
        # Проверка спреда
        if not day_indicators['signals']['spread_ok']:
            return False, "Слишком большой спред"
            
        # Проверка тренда
        if day_indicators['trend_strength'] < day_config['volatility_threshold']:
            return False, "Слабый тренд"
            
        # Проверка RSI
        if indicators['rsi'] > day_config['rsi_overbought']:
            return False, "Перекупленность по RSI"
        elif indicators['rsi'] < day_config['rsi_oversold']:
            return False, "Перепроданность по RSI"
            
        return True, "Условия подходят для дейтрейдинга"

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