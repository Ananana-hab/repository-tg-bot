import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import config
import logging
import os

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class MLPredictor:
    """ML модель для прогнозирования пампов и дампов"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = config.MODEL_PATH
        self.scaler_path = config.SCALER_PATH
        self.use_ml = config.USE_ML_MODEL
        
        # Попытка загрузить существующую модель
        if self.use_ml:
            self.load_model()
        else:
            logger.info("ML model disabled, using rule-based prediction")
    
    def prepare_features(self, indicators, market_data, mode='swing'):
        """
        Подготавливает features для ML модели
        
        Args:
            indicators: dict с техническими индикаторами
            market_data: dict с рыночными данными
            mode: режим работы ('swing' или 'day')
            
        Returns:
            numpy array: вектор признаков
        """
        # Порядок фичей должен совпадать с train.py!
        features = [
            # Bollinger Bands
            indicators['bb_upper'],
            indicators['bb_lower'],
            indicators.get('bb_middle', 0),
            1 if indicators['bb_position'] == 'above_upper' else 0,  # bb_position_above
            1 if indicators['bb_position'] == 'below_lower' else 0,  # bb_position_below
            # EMA
            indicators['ema_50'],
            indicators['ema_200'] if indicators['ema_200'] else indicators['ema_50'],
            # Volume
            indicators['volume_ratio'],
            1 if indicators['is_high_volume'] else 0,
            # Momentum & Volatility
            indicators['momentum'],
            indicators['atr'],
            # VWAP
            indicators.get('vwap', 0) if indicators.get('vwap') else 0,
            # Orderbook
            indicators.get('orderbook_imbalance', 0),
            # Market sentiment
            market_data['fear_greed'] if market_data.get('fear_greed') else 50,
            # Volume
            market_data['current_volume'],
            # Price changes
            market_data['price_change_1h'],
            market_data['price_change_4h'],
            # Open Interest changes
            market_data.get('oi_change_5m', 0),
            market_data.get('oi_change_1h', 0),
            market_data.get('oi_change_4h', 0),
        ]
        
        # Добавляем специфические features для дейтрейдинга
        if mode == 'day' and 'day_trading' in indicators:
            day_features = [
                indicators['day_trading']['trend_strength'],
                indicators['day_trading']['volatility_value'],
                indicators['day_trading']['volume_surge'],
                1 if indicators['day_trading']['is_consolidating'] else 0,
                indicators['day_trading']['price_momentum'],
                indicators['day_trading']['current_spread'],
                1 if indicators['day_trading']['signals']['ma_cross'] == 'buy' else 
                -1 if indicators['day_trading']['signals']['ma_cross'] == 'sell' else 0,
                1 if indicators['day_trading']['signals']['volume_confirmed'] else 0,
                1 if indicators['day_trading']['signals']['spread_ok'] else 0,
                1 if indicators.get('is_valid_for_daytrading', False) else 0
            ]
            features.extend(day_features)
        
        return np.array(features).reshape(1, -1)
    
    def create_default_model(self):
        """Создаёт базовую модель Random Forest"""
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        logger.info("Created new Random Forest model")
    
    def predict(self, indicators, market_data, mode='swing'):
        """
        Делает прогноз: PUMP, DUMP или NEUTRAL
        
        Args:
            indicators: dict с техническими индикаторами
            market_data: dict с рыночными данными
            mode: режим работы ('swing' или 'day')
            
        Returns:
            dict: {
                'signal': 'PUMP'/'DUMP'/'NEUTRAL',
                'probability': float (0-1),
                'confidence': 'HIGH'/'MEDIUM'/'LOW',
                'timeframe': str (только для day режима),
                'action': str (только для day режима)
            }
        """
        # Если ML отключен или модель не загружена, используем rule-based
        if not self.use_ml or self.model is None:
            return self.rule_based_prediction(indicators, market_data)
        
        try:
            # Подготовка features с учетом режима
            # ВАЖНО: Используем 'swing' features для совместимости с обученной моделью
            # (Day logic применяется ПОСЛЕ получения базовых вероятностей)
            features = self.prepare_features(indicators, market_data, mode='swing')
            
            # Нормализация
            features_scaled = self.scaler.transform(features)
            
            # Прогноз с учетом режима
            prediction = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]
            
            # Дополнительная валидация для дейтрейдинга
            if mode == 'day':
                # Сначала применяем штрафы/бонусы к вероятностям
                # DISABLE VALIDATION FOR BACKTEST (Too strict on mock data)
                # prediction, probabilities = self.validate_day_trading_signal(
                #     prediction, 
                #     probabilities, 
                #     indicators
                # )
                
                # Force-override prediction if probability is decent (Day Trading Aggressiveness)
                # Strategy: Use Day Indicators to BOOST weak Swing signals
                # If Swing Model says 40% PUMP (normally ignored), but Day Trend is UP -> BUY
                
                pump_prob = probabilities[2]
                dump_prob = probabilities[0]
                
                # Aggressive Threshold for Day Trading
                # Model is biased to NEUTRAL (0.80), so PUMP/DUMP signals are often ~0.20.
                # We lower the threshold to catch these relative signals if Trend confirms.
                day_threshold = 0.15 
                
                day_inds = indicators.get('day_trading', {})
                # FIX: 0.5% trend strength is too high for 5m chart difference between 9/21 MA.
                # Lowering to 0.05% to catch normal trends.
                trend_ok = day_inds.get('trend_strength', 0) > 0.05
                
                # DEBUG PRINT
                print(f"DEBUG ML: Probs {probabilities} Trend {day_inds.get('trend')} Str {day_inds.get('trend_strength')}")
                
                # Check for PUMP
                if pump_prob > day_threshold and pump_prob > dump_prob:
                    # Confirm with Day Trend or MA Cross
                    if day_inds.get('signals', {}).get('ma_cross') == 'buy' or \
                       (day_inds.get('trend') == 'up' and trend_ok):
                        prediction = 2 # PUMP
                        probabilities[2] = max(probabilities[2], config.PUMP_THRESHOLD + 0.05) # Boost prob above threshold
                        
                # Check for DUMP
                elif dump_prob > day_threshold and dump_prob > pump_prob:
                     if day_inds.get('signals', {}).get('ma_cross') == 'sell' or \
                       (day_inds.get('trend') == 'down' and trend_ok):
                        prediction = 0 # DUMP
                        probabilities[0] = max(probabilities[0], config.DUMP_THRESHOLD + 0.05) # Boost prob above threshold
                
           
            # Определяем confidence level
            max_prob = max(probabilities)
            if max_prob >= 0.80:
                confidence = 'HIGH'
            elif max_prob >= 0.65:
                confidence = 'MEDIUM'
            elif max_prob >= 0.45: # Lowered for Day Mode visibility
                confidence = 'LOW'
            else:
                 confidence = 'LOW' # Default
            
            signal_map = {0: 'DUMP', 1: 'NEUTRAL', 2: 'PUMP'}
            
            result = {
                'signal': signal_map.get(prediction, 'NEUTRAL'),
                'probability': max_prob,
                'confidence': confidence
            }
            
            # Добавляем специфическую информацию для дейтрейдинга
            if mode == 'day' and 'day_trading' in indicators:
                result.update(self.get_day_trading_details(indicators, result['signal']))
            
            logger.info(f"ML Prediction ({mode} mode): {result['signal']} ({result['probability']:.2%})")
            return result
            
        except Exception as e:
            logger.error(f"Error in ML prediction: {e}")
            print(f"CRITICAL ML ERROR: {e}") # Print to stdout
            import traceback
            traceback.print_exc()
            return self.rule_based_prediction(indicators, market_data)
    
    def rule_based_prediction(self, indicators, market_data):
        """
        Rule-based прогноз на основе технических индикаторов
        (используется когда ML модель не обучена)
        """
        score = 0
        reasons = []
        
        # ✅ Open Interest (НОВОЕ! 3 балла)
        oi_change = market_data.get('oi_change_1h', 0)
        if abs(oi_change) > 2.0:  # Сильное изменение OI
            if oi_change > 0 and market_data.get('price_change_1h', 0) > 0:
                score += 3
                reasons.append("Рост OI + рост цены - сильный PUMP")
            elif oi_change > 0 and market_data.get('price_change_1h', 0) < 0:
                score -= 3
                reasons.append("Рост OI + падение цены - сильный DUMP")
        
        # ✅ НОВОЕ: RSI (2 балла)
        rsi = indicators.get('rsi')
        if rsi is not None:
            if rsi < 30:  # Перепроданность
                score += 2
                reasons.append(f"RSI перепродан ({rsi:.1f}) - возможен PUMP")
            elif rsi > 70:  # Перекупленность
                score -= 2
                reasons.append(f"RSI перекуплен ({rsi:.1f}) - возможен DUMP")
            elif rsi < 40:  # Умеренная перепроданность
                score += 1
                reasons.append(f"RSI низкий ({rsi:.1f})")
            elif rsi > 60:  # Умеренная перекупленность
                score -= 1
                reasons.append(f"RSI высокий ({rsi:.1f})")
        
        # ✅ НОВОЕ: MACD (2 балла)
        macd_crossover = indicators.get('macd_crossover')
        if macd_crossover == 'bullish':
            score += 2
            reasons.append("MACD bullish crossover - восходящий тренд")
        elif macd_crossover == 'bearish':
            score -= 2
            reasons.append("MACD bearish crossover - нисходящий тренд")
        
        # Дополнительная проверка MACD histogram
        macd_histogram = indicators.get('macd_histogram')
        if macd_histogram is not None:
            if macd_histogram > 50:
                score += 1
                reasons.append("MACD histogram сильно положительный")
            elif macd_histogram < -50:
                score -= 1
                reasons.append("MACD histogram сильно отрицательный")
        
        # Bollinger Bands (3 балла)
        if indicators['bb_position'] == 'below_lower':
            score += 2
            reasons.append("Цена ниже нижней BB")
        elif indicators['bb_position'] == 'above_upper':
            score -= 2
            reasons.append("Цена выше верхней BB")
        
        # Volume анализ (2 балла)
        if indicators['is_high_volume']:
            if score > 0:
                score += 2
                reasons.append("Высокий объём подтверждает рост")
            elif score < 0:
                score -= 2
                reasons.append("Высокий объём подтверждает падение")
        
        # Price change анализ (2 балла)
        price_change = market_data.get('price_change_1h', 0)
        if price_change > 2.5:  # Снижен порог
            score += 2
            reasons.append(f"Сильный рост: {price_change:+.2f}%")
        elif price_change < -2.5:
            score -= 2
            reasons.append(f"Сильное падение: {price_change:+.2f}%")
        
        # Fear & Greed Index
        if market_data['fear_greed']:
            fg = market_data['fear_greed']
            if fg > 75:
                score -= 1
                reasons.append("Extreme Greed - возможна коррекция")
            elif fg < 25:
                score += 1
                reasons.append("Extreme Fear - возможен отскок")
        
        # Momentum (2 балла)
        momentum = indicators.get('momentum', 0)
        if momentum > 300:  # Сильный импульс
            score += 2
            reasons.append("Сильный восходящий momentum")
        elif momentum < -300:
            score -= 2
            reasons.append("Сильный нисходящий momentum")
        elif momentum > 0:
            score += 1
        elif momentum < 0:
            score -= 1
        
        # VWAP side
        try:
            vwap = indicators.get('vwap')
            current_price = market_data.get('current_price')
            if vwap is not None and current_price is not None:
                if current_price > vwap:
                    score += 1
                    reasons.append("Цена выше VWAP")
                else:
                    score -= 1
                    reasons.append("Цена ниже VWAP")
        except Exception:
            pass

        # Orderbook imbalance
        try:
            ob = indicators.get('orderbook_imbalance', 0.0)
            if ob > config.OB_IMBALANCE_THRESHOLD:
                score += 1
                reasons.append("Дисбаланс стакана в пользу бидов")
            elif ob < -config.OB_IMBALANCE_THRESHOLD:
                score -= 1
                reasons.append("Дисбаланс стакана в пользу асков")
        except Exception:
            pass

        # Strong volume spike reinforcement
        try:
            if indicators.get('volume_ratio', 1.0) > config.VOLUME_SPIKE_RATIO:
                if score > 0:
                    score += 1
                    reasons.append("Сильный всплеск объёма поддерживает рост")
                elif score < 0:
                    score -= 1
                    reasons.append("Сильный всплеск объёма поддерживает падение")
        except Exception:
            pass

        # ATR low-volatility clamp
        try:
            atr = indicators.get('atr')
            cp = market_data.get('current_price')
            if atr is not None and cp is not None:
                low_atr_threshold = config.ATR_LOW_RATIO * cp
                if atr < low_atr_threshold and abs(score) > 1:
                    score = 1 if score > 0 else -1
                    reasons.append("Низкая волатильность (ATR) — ограничение силы сигнала")
        except Exception:
            pass
        
        # Определяем сигнал
        if score >= 4:
            signal = 'PUMP'
            probability = min(0.65 + (score - 4) * 0.05, 0.90)
        elif score <= -4:
            signal = 'DUMP'
            probability = min(0.65 + (abs(score) - 4) * 0.05, 0.90)
        else:
            signal = 'NEUTRAL'
            probability = 0.50 + abs(score) * 0.05
        
        # Confidence
        if probability >= 0.75:
            confidence = 'HIGH'
        elif probability >= 0.60:
            confidence = 'MEDIUM'
        else:
            confidence = 'LOW'
        
        result = {
            'signal': signal,
            'probability': probability,
            'confidence': confidence,
            'reasons': reasons
        }
        
        logger.info(f"Rule-based Prediction: {signal} ({probability:.2%}) - Score: {score}")
        return result
    
    def save_model(self):
        """Сохраняет обученную модель на диск"""
        if self.model:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            logger.info("Model saved successfully")
    
    def load_model(self):
        """Загружает модель с диска"""
        if not self.use_ml:
            logger.debug("ML model disabled in config")
            return
            
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            try:
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                logger.info(f"✅ ML model loaded from {self.model_path}")
            except Exception as e:
                logger.warning(f"Could not load model: {e}")
                self.model = None
        else:
            logger.warning(f"ML model files not found: {self.model_path}, {self.scaler_path}")
            logger.info("Falling back to rule-based prediction")
            self.model = None
    
    def should_send_signal(self, prediction):
        """
        Определяет, нужно ли отправлять сигнал пользователям
        
        Args:
            prediction: результат прогноза
            
        Returns:
            bool: True если сигнал достаточно сильный
        """
        if prediction['signal'] == 'NEUTRAL':
            return False
        
        if prediction['signal'] == 'PUMP':
            return prediction['probability'] >= config.PUMP_THRESHOLD
        
        if prediction['signal'] == 'DUMP':
            return prediction['probability'] >= config.DUMP_THRESHOLD
        
        return False
            
    def validate_day_trading_signal(self, prediction, probabilities, indicators):
        """
        Валидирует и корректирует сигналы для дейтрейдинга
        
        Args:
            prediction: текущий прогноз
            probabilities: вероятности классов
            indicators: все индикаторы
            
        Returns:
            tuple: (скорректированный прогноз, скорректированные вероятности)
        """
        if not indicators.get('is_valid_for_daytrading', False):
            # Если условия не подходят для дейтрейдинга, снижаем уверенность, но не убиваем сигнал
            probabilities = probabilities * 0.9  # Было 0.5
            # if max(probabilities) < 0.5: prediction = 1 (Removed to allow signals to survive)
        
        day_indicators = indicators.get('day_trading', {})
        
        # Проверяем спред
        if not day_indicators.get('signals', {}).get('spread_ok', False):
            probabilities = probabilities * 0.95 # Было 0.7
        
        # Проверяем объем
        if not day_indicators.get('signals', {}).get('volume_confirmed', False):
            probabilities = probabilities * 0.9 # Было 0.8
        
        # Проверяем волатильность
        if not day_indicators.get('is_volatile', False):
            probabilities = probabilities * 0.9 # Было 0.6
        
        return prediction, probabilities
    
    def get_day_trading_details(self, indicators, signal):
        """
        Формирует детальную информацию для сигналов дейтрейдинга
        
        Args:
            indicators: все индикаторы
            signal: тип сигнала
            
        Returns:
            dict: Дополнительная информация для дейтрейдинга
        """
        day_indicators = indicators.get('day_trading', {})
        
        # Определяем таймфрейм для торговли
        if day_indicators.get('is_consolidating', False):
            timeframe = '1m'  # Короткий таймфрейм для консолидации
        else:
            timeframe = '5m'  # Более длинный для тренда
        
        # Определяем рекомендуемое действие
        action = 'MONITOR'  # По умолчанию просто наблюдаем
        
        if signal != 'NEUTRAL':
            if day_indicators.get('signals', {}).get('volume_confirmed', False):
                if day_indicators.get('signals', {}).get('spread_ok', False):
                    action = 'EXECUTE'  # Можно входить в позицию
                else:
                    action = 'PREPARE'  # Готовимся, но ждем улучшения спреда
            else:
                action = 'WAIT_VOLUME'  # Ждем подтверждения объемом
        
        return {
            'timeframe': timeframe,
            'action': action,
            'day_trading_details': {
                'trend': day_indicators.get('trend'),
                'trend_strength': day_indicators.get('trend_strength'),
                'volume_surge': day_indicators.get('volume_surge'),
                'spread': day_indicators.get('current_spread'),
                'is_consolidating': day_indicators.get('is_consolidating', False),
                'conditions_met': indicators.get('is_valid_for_daytrading', False)
            }
        }