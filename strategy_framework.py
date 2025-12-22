"""
Strategy Framework
Defines abstract base class for trading strategies and concrete implementations.
Enables standardized signal generation for backtesting and live trading.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
from ml_model import MLPredictor
import logging

logger = logging.getLogger(__name__)

class Strategy(ABC):
    """Abstract base class for trading strategies"""
    
    def __init__(self, name: str):
        self.name = name
        
    @abstractmethod
    def generate_signal(self, row: pd.Series, indicators: Dict[str, Any], mode: str = 'swing') -> Dict[str, Any]:
        """
        Generate trading signal based on market data
        
        Args:
            row: DataFrame row containing price and other raw data
            indicators: Dictionary of calculated technical indicators
            
        Returns:
            Dict containing:
            - signal: 'PUMP', 'DUMP', 'NEUTRAL'
            - confidence: float (0-1)
            - probability: float (0-1)
            - meta: dict with additional info
        """
        pass

class RuleBasedStrategy(Strategy):
    """
    Standard rule-based strategy using RSI, MACD, and Bollinger Bands.
    """
    
    def __init__(self, **kwargs):
        super().__init__("Rule-Based")
        # Default parameters
        self.params = {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'rsi_score': 2,
            'macd_score': 2,
            'bb_score': 2,
            'volume_score': 2,
            'oi_threshold': 2.0,
            'oi_score': 3,
            'score_threshold': 4
        }
        # Update with provided kwargs
        self.params.update(kwargs)
        
    def generate_signal(self, row: pd.Series, indicators: Dict[str, Any] = None, mode: str = 'swing') -> Dict[str, Any]:
        if indicators is None:
            indicators = {} 
        
        # Prepare data
        if not indicators and isinstance(row, pd.Series):
             indicators = {
                'rsi': row.get('rsi', 50),
                'macd': row.get('macd', 0),
                'macd_signal': row.get('macd_signal', 0),
                'bb_upper': row.get('bb_upper', 0),
                'bb_lower': row.get('bb_lower', 0),
                'volume_ratio': row.get('volume_ratio', 1.0),
                'is_high_volume': row.get('is_high_volume', False),
                'macd_crossover': row.get('macd_crossover', 'none'),
                'bb_position': row.get('bb_position', 'inside')
             }

        market_data = {
            'current_price': row.get('price', 0),
            'price_change_1h': row.get('price_change_1h', 0),
            'oi_change_1h': row.get('oi_change_1h', 0)
        }
        
        # --- Logic Implementation (Independent of MLPredictor) ---
        score = 0
        reasons = []
        p = self.params
        
        # 1. Open Interest
        oi_change = market_data.get('oi_change_1h', 0)
        if abs(oi_change) > p['oi_threshold']:
            if oi_change > 0 and market_data.get('price_change_1h', 0) > 0:
                score += p['oi_score']
                reasons.append("High OI + Price Up")
            elif oi_change > 0 and market_data.get('price_change_1h', 0) < 0:
                score -= p['oi_score']
                reasons.append("High OI + Price Down")
                
        # 2. RSI
        rsi = indicators.get('rsi')
        if rsi is not None:
            if rsi < p['rsi_oversold']:
                score += p['rsi_score']
                reasons.append(f"RSI Oversold ({rsi:.1f})")
            elif rsi > p['rsi_overbought']:
                score -= p['rsi_score']
                reasons.append(f"RSI Overbought ({rsi:.1f})")
                
        # 3. MACD
        macd_crossover = indicators.get('macd_crossover')
        if macd_crossover == 'bullish':
            score += p['macd_score']
            reasons.append("MACD Bullish")
        elif macd_crossover == 'bearish':
            score -= p['macd_score']
            reasons.append("MACD Bearish")
            
        # 4. Bollinger Bands
        bb_pos = indicators.get('bb_position', 'inside')
        if bb_pos == 'below_lower':
            score += p['bb_score']
            reasons.append("Below Lower BB")
        elif bb_pos == 'above_upper':
            score -= p['bb_score']
            reasons.append("Above Upper BB")
         
        # 5. Volume
        if indicators.get('is_high_volume', False):
            if score > 0:
                score += p['volume_score']
                reasons.append("High Volume Confirmation")
            elif score < 0:
                score -= p['volume_score']
                reasons.append("High Volume Confirmation")

        # Determine Signal
        threshold = p['score_threshold']
        
        if score >= threshold:
            signal = 'PUMP'
            # Dynamic probability based on score
            prob = 0.7 + (min(score - threshold, 5) / 20) 
        elif score <= -threshold:
            signal = 'DUMP'
            prob = 0.7 + (min(abs(score) - threshold, 5) / 20)
        else:
            signal = 'NEUTRAL'
            prob = 0.5
            
        prob = min(prob, 0.99)
        
        confidence = 'LOW'
        if prob > 0.8: confidence = 'HIGH'
        elif prob > 0.6: confidence = 'MEDIUM'
        
        return {
            'signal': signal,
            'confidence': confidence,
            'probability': prob,
            'score': score,
            'reasons': reasons
        }

class MLStrategy(Strategy):
    """
    Machine Learning strategy using trained models.
    """
    
    def __init__(self):
        super().__init__("ML-Model")
        self.predictor = MLPredictor()
        
    def generate_signal(self, row: pd.Series, indicators: Dict[str, Any], mode: str = 'swing') -> Dict[str, Any]:
        # Placeholder for actual ML prediction when model is ready
        # Currently MLPredictor.predict uses rule-based as fallback if no model
        
        market_data = {
            'current_price': row.get('price', 0),
            'current_volume': row.get('volume', 0), # FIX: ML needs volume
            'fear_greed': row.get('fear_greed_index', 50),
            'price_change_1h': row.get('price_change_1h', 0),
            'price_change_4h': row.get('price_change_4h', 0), # Added for completeness
            'oi_change_1h': row.get('oi_change_1h', 0)
        }
        
        # We use 'predict' which handles model loading/fallback
        return self.predictor.predict(indicators, market_data, mode=mode)

class StrategyFactory:
    """Factory to create strategies"""
    
    @staticmethod
    def get_strategy(strategy_type: str, **kwargs) -> Strategy:
        if strategy_type.lower() == 'rule_based':
            return RuleBasedStrategy(**kwargs)
        elif strategy_type.lower() == 'ml':
            return MLStrategy()
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
