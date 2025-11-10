import ccxt
import requests
import config
import logging
from datetime import datetime, timedelta
import pandas as pd

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class DataCollector:
    def __init__(self):
        # Инициализируем Binance без API ключей (публичные данные)
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
        })
        # Кэш для FNG
        self._fng_cache = {'value': None, 'ts': None}
        # Кэш для Open Interest (обновляется каждые 5 минут)
        self._oi_cache = {'value': None, 'ts': None, 'history': []}
        
    def get_current_price(self):
        """Получает текущую цену BTC/USDT"""
        try:
            ticker = self.exchange.fetch_ticker(config.SYMBOL)
            return {
                'price': ticker['last'],
                'volume': ticker['quoteVolume'],
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.error(f"Error fetching price: {e}")
            return None
    
    def get_ohlcv_data(self, timeframe='5m', limit=100):
        """
        Получает OHLCV данные (Open, High, Low, Close, Volume)
        
        Args:
            timeframe: Таймфрейм ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: Количество свечей
        
        Returns:
            DataFrame с колонками: timestamp, open, high, low, close, volume
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                config.SYMBOL,
                timeframe=timeframe,
                limit=limit
            )
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            logger.info(f"Fetched {len(df)} candles for {config.SYMBOL} ({timeframe})")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV data: {e}")
            return None
    
    def get_orderbook(self, limit=20):
        """Получает стакан ордеров (bid/ask)"""
        try:
            orderbook = self.exchange.fetch_order_book(config.SYMBOL, limit)
            
            return {
                'bids': orderbook['bids'],  # Заявки на покупку
                'asks': orderbook['asks'],  # Заявки на продажу
                'bid_volume': sum([bid[1] for bid in orderbook['bids']]),
                'ask_volume': sum([ask[1] for ask in orderbook['asks']])
            }
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return None
    
    def get_fear_greed_index(self):
        """
        Получает Fear & Greed Index из Alternative.me API с кэшированием
        
        Returns:
            int: Значение от 0 (Extreme Fear) до 100 (Extreme Greed)
        """
        try:
            now = datetime.now()
            # Кэш TTL 5 минут
            if self._fng_cache['ts'] and (now - self._fng_cache['ts']).seconds < 300:
                logger.debug(f"Using cached F&G: {self._fng_cache['value']}")
                return self._fng_cache['value']

            # Ретраи через Session + HTTPAdapter
            session = requests.Session()
            try:
                adapter = requests.adapters.HTTPAdapter(max_retries=3)
                session.mount('https://', adapter)
                session.mount('http://', adapter)
            except Exception:
                pass

            response = session.get(config.FEAR_GREED_API, timeout=5)
            data = response.json()
            
            value = None
            if data and 'data' in data and len(data['data']) > 0:
                value = int(data['data'][0]['value'])
                classification = data['data'][0]['value_classification']
                logger.info(f"Fear & Greed Index: {value} ({classification})")

            if value is None:
                # fallback значение
                value = 50
                logger.warning("F&G returned None, using default: 50")

            self._fng_cache = {'value': value, 'ts': now}
            return value
            
        except Exception as e:
            logger.error(f"Error fetching Fear & Greed Index: {e}")
            # Возвращаем кэш или дефолт
            cached_value = self._fng_cache['value']
            if cached_value is not None:
                logger.warning(f"Using cached F&G value: {cached_value}")
                return cached_value
            else:
                logger.warning("No cache available, using default: 50")
                return 50
    
    def get_24h_stats(self):
        """Получает статистику за 24 часа"""
        try:
            ticker = self.exchange.fetch_ticker(config.SYMBOL)
            
            return {
                'price_change_24h': ticker.get('percentage', 0),
                'high_24h': ticker.get('high', 0),
                'low_24h': ticker.get('low', 0),
                'volume_24h': ticker.get('quoteVolume', 0)
            }
        except Exception as e:
            logger.error(f"Error fetching 24h stats: {e}")
            return None
    
    def get_open_interest(self):
        """
        Получает текущий Open Interest для BTC/USDT фьючерсов
        с кэшированием и историей изменений
        
        Returns:
            dict: {
                'value': текущее значение OI,
                'change_5m': изменение за 5 минут (%),
                'change_1h': изменение за 1 час (%),
                'change_4h': изменение за 4 часа (%)
            }
        """
        try:
            now = datetime.now()
            
            # Запрашиваем текущий OI (всегда свежий)
            url = 'https://fapi.binance.com/fapi/v1/openInterest'
            params = {'symbol': 'BTCUSDT'}
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code != 200:
                logger.error(f"OI API error: {response.status_code}")
                return self._get_cached_oi_or_default()
            
            data = response.json()
            current_oi = float(data['openInterest'])
            
            # Обновляем историю (храним последние 60 записей = ~5 часов при проверке каждые 5 мин)
            self._oi_cache['history'].append({
                'value': current_oi,
                'timestamp': now
            })
            
            # Обрезаем историю до 60 записей
            if len(self._oi_cache['history']) > 60:
                self._oi_cache['history'] = self._oi_cache['history'][-60:]
            
            # Вычисляем изменения
            change_5m = self._calculate_oi_change(minutes=5)
            change_1h = self._calculate_oi_change(minutes=60)
            change_4h = self._calculate_oi_change(minutes=240)
            
            result = {
                'value': current_oi,
                'change_5m': change_5m,
                'change_1h': change_1h,
                'change_4h': change_4h,
                'timestamp': now
            }
            
            # Обновляем кэш
            self._oi_cache['value'] = result
            self._oi_cache['ts'] = now
            
            logger.info(
                f"Open Interest: {current_oi:,.0f} | "
                f"5m: {change_5m:+.2f}% | 1h: {change_1h:+.2f}% | 4h: {change_4h:+.2f}%"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching Open Interest: {e}")
            return self._get_cached_oi_or_default()
    
    def _calculate_oi_change(self, minutes):
        """Вычисляет изменение OI за указанный период"""
        try:
            history = self._oi_cache['history']
            if len(history) < 2:
                return 0.0
            
            now = datetime.now()
            target_time = now - timedelta(minutes=minutes)
            
            # Находим ближайшую запись к целевому времени
            closest = min(
                history,
                key=lambda x: abs((x['timestamp'] - target_time).total_seconds())
            )
            
            current_oi = history[-1]['value']
            past_oi = closest['value']
            
            if past_oi == 0:
                return 0.0
            
            change = ((current_oi - past_oi) / past_oi) * 100
            return round(change, 2)
            
        except Exception as e:
            logger.debug(f"Error calculating OI change: {e}")
            return 0.0
    
    def _get_cached_oi_or_default(self):
        """Возвращает кэшированный OI или дефолтные значения"""
        if self._oi_cache['value']:
            logger.warning("Using cached OI value")
            return self._oi_cache['value']
        else:
            logger.warning("No OI cache available, returning defaults")
            return {
                'value': 0,
                'change_5m': 0.0,
                'change_1h': 0.0,
                'change_4h': 0.0,
                'timestamp': datetime.now()
            }
    
    def calculate_price_change(self, df, periods=12):
        """
        Рассчитывает изменение цены за N периодов
        
        Args:
            df: DataFrame с ценами
            periods: Количество периодов назад
            
        Returns:
            float: Процент изменения цены
        """
        if df is None or len(df) < periods:
            logger.warning(f"Not enough data for price change calculation: {len(df) if df is not None else 0} < {periods}")
            return 0
        
        current_price = df['close'].iloc[-1]
        past_price = df['close'].iloc[-periods]
        
        if past_price == 0:
            logger.warning("Past price is 0, cannot calculate change")
            return 0
        
        change = ((current_price - past_price) / past_price) * 100
        return round(change, 2)
    
    def get_market_data(self, timeframe=None, limit=None):
        """
        Собирает все необходимые данные для анализа
        
        ✅ ИСПРАВЛЕНО: Динамический расчёт периодов в зависимости от таймфрейма
        
        Args:
            timeframe: Таймфрейм свечей (опционально, берётся из config)
            limit: Количество свечей (опционально, по умолчанию 100)
        
        Returns:
            dict: Полный набор данных для ML модели
        """
        logger.info("Collecting market data...")
        
        # Используем переданный таймфрейм или из config
        tf = timeframe or config.TIMEFRAME
        lm = limit or 100
        
        # ✅ Динамический расчёт периодов в зависимости от таймфрейма
        timeframe_minutes = {
            '1m': 1,
            '3m': 3,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '2h': 120,
            '4h': 240,
            '1d': 1440
        }
        
        tf_min = timeframe_minutes.get(tf, 5)  # Default 5m если неизвестный
        
        # Рассчитываем периоды для 1h и 4h
        periods_1h = max(1, 60 // tf_min)   # Защита от деления на 0
        periods_4h = max(1, 240 // tf_min)
        
        logger.info(f"Timeframe: {tf} ({tf_min} min), Periods: 1h={periods_1h}, 4h={periods_4h}")
        
        # Получаем OHLCV данные
        df = self.get_ohlcv_data(timeframe=tf, limit=lm)
        if df is None:
            logger.error("Failed to fetch OHLCV data")
            return None
        
        # Текущая цена и объем
        current = self.get_current_price()
        if current is None:
            logger.error("Failed to fetch current price")
            return None
        
        # Fear & Greed Index (с кэшем)
        fear_greed = self.get_fear_greed_index()
        
        # 24h статистика
        stats_24h = self.get_24h_stats()
        
        # Orderbook
        orderbook = self.get_orderbook()
        
        # ✅ Open Interest (НОВОЕ!)
        open_interest = self.get_open_interest()
        
        # ✅ Изменение цены с правильными периодами
        price_change_1h = self.calculate_price_change(df, periods=periods_1h)
        price_change_4h = self.calculate_price_change(df, periods=periods_4h)
        
        market_data = {
            'df': df,
            'current_price': current['price'],
            'current_volume': current['volume'],
            'timestamp': current['timestamp'],
            'fear_greed': fear_greed,
            'price_change_1h': price_change_1h,
            'price_change_4h': price_change_4h,
            'stats_24h': stats_24h,
            'orderbook': orderbook,
            # ✅ НОВОЕ: Open Interest
            'open_interest': open_interest['value'],
            'oi_change_5m': open_interest['change_5m'],
            'oi_change_1h': open_interest['change_1h'],
            'oi_change_4h': open_interest['change_4h'],
            # ✅ Метаданные для отладки
            'timeframe': tf,
            'timeframe_minutes': tf_min,
            'periods_1h': periods_1h,
            'periods_4h': periods_4h
        }
        
        logger.info(f"Market data collected: Price=${current['price']:,.2f}, "
                    f"Change 1h={price_change_1h}% ({periods_1h} periods), "
                    f"Change 4h={price_change_4h}% ({periods_4h} periods)")
        
        return market_data