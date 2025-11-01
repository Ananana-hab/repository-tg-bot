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
        self.model_path = 'btc_model.pkl'
        self.scaler_path = 'scaler.pkl'
        
        # Попытка загрузить существующую модель
        self.load_model()
    
    def prepare_features(self, indicators, market_data):
        """
        Подготавливает features для ML модели
        
        Args:
            indicators: dict с техническими индикаторами
            market_data: dict с рыночными данными
            
        Returns:
            numpy array: вектор признаков
        """
        features = [
            indicators['rsi'],
            indicators['macd'],
            indicators['macd_signal'],
            indicators['macd_histogram'],
            1 if indicators['macd_crossover'] == 'bullish' else -1 if indicators['macd_crossover'] == 'bearish' else 0,
            indicators['bb_upper'],
            indicators['bb_lower'],
            1 if indicators['bb_position'] == 'above_upper' else -1 if indicators['bb_position'] == 'below_lower' else 0,
            indicators['ema_50'],
            indicators['ema_200'] if indicators['ema_200'] else indicators['ema_50'],
            indicators['volume_ratio'],
            1 if indicators['is_high_volume'] else 0,
            indicators['momentum'],
            indicators['atr'],
            market_data['price_change_1h'],
            market_data['price_change_4h'],
            market_data['fear_greed'] if market_data['fear_greed'] else 50,
            market_data['current_volume']
        ]
        
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
    
    def predict(self, indicators, market_data):
        """
        Делает прогноз: PUMP, DUMP или NEUTRAL
        
        Returns:
            dict: {
                'signal': 'PUMP'/'DUMP'/'NEUTRAL',
                'probability': float (0-1),
                'confidence': 'HIGH'/'MEDIUM'/'LOW'
            }
        """
        # Если модель не обучена, используем rule-based подход
        if self.model is None:
            return self.rule_based_prediction(indicators, market_data)
        
        try:
            # Подготовка features
            features = self.prepare_features(indicators, market_data)
            
            # Нормализация
            features_scaled = self.scaler.transform(features)
            
            # Прогноз
            prediction = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]
            
            # Определяем confidence level
            max_prob = max(probabilities)
            if max_prob >= 0.80:
                confidence = 'HIGH'
            elif max_prob >= 0.65:
                confidence = 'MEDIUM'
            else:
                confidence = 'LOW'
            
            signal_map = {0: 'DUMP', 1: 'NEUTRAL', 2: 'PUMP'}
            
            result = {
                'signal': signal_map[prediction],
                'probability': max_prob,
                'confidence': confidence
            }
            
            logger.info(f"ML Prediction: {result['signal']} ({result['probability']:.2%})")
            return result
            
        except Exception as e:
            logger.error(f"Error in ML prediction: {e}")
            return self.rule_based_prediction(indicators, market_data)
    
    def rule_based_prediction(self, indicators, market_data):
        """
        Rule-based прогноз на основе технических индикаторов
        (используется когда ML модель не обучена)
        """
        score = 0
        reasons = []
        
        # RSI анализ
        if indicators['rsi'] > 70:
            score -= 2
            reasons.append("RSI перекупленность")
        elif indicators['rsi'] < 30:
            score += 2
            reasons.append("RSI перепроданность")
        elif indicators['rsi'] > 60:
            score -= 1
        elif indicators['rsi'] < 40:
            score += 1
        
        # MACD анализ
        if indicators['macd_crossover'] == 'bullish':
            score += 2
            reasons.append("MACD бычий кроссовер")
        elif indicators['macd_crossover'] == 'bearish':
            score -= 2
            reasons.append("MACD медвежий кроссовер")
        
        # Bollinger Bands
        if indicators['bb_position'] == 'below_lower':
            score += 2
            reasons.append("Цена ниже нижней BB")
        elif indicators['bb_position'] == 'above_upper':
            score -= 2
            reasons.append("Цена выше верхней BB")
        
        # Volume анализ
        if indicators['is_high_volume']:
            if score > 0:
                score += 1
                reasons.append("Высокий объём подтверждает рост")
            elif score < 0:
                score -= 1
                reasons.append("Высокий объём подтверждает падение")
        
        # Price change анализ
        price_change = market_data['price_change_1h']
        if price_change > 3:
            score += 1
        elif price_change < -3:
            score -= 1
        
        # Fear & Greed Index
        if market_data['fear_greed']:
            fg = market_data['fear_greed']
            if fg > 75:
                score -= 1
                reasons.append("Extreme Greed - возможна коррекция")
            elif fg < 25:
                score += 1
                reasons.append("Extreme Fear - возможен отскок")
        
        # Momentum
        if indicators['momentum'] > 0:
            score += 1
        else:
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
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            try:
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load model: {e}")
                self.model = None
        else:
            logger.info("No trained model found, using rule-based approach")
    
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