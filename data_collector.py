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
            
            logger.info(f"Fetched {len(df)} candles for {config.SYMBOL}")
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
        Получает Fear & Greed Index из Alternative.me API
        
        Returns:
            int: Значение от 0 (Extreme Fear) до 100 (Extreme Greed)
        """
        try:
            now = datetime.now()
            # Кэш TTL 5 минут
            if self._fng_cache['ts'] and (now - self._fng_cache['ts']).seconds < 300:
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

            self._fng_cache = {'value': value, 'ts': now}
            return value
            
        except Exception as e:
            logger.error(f"Error fetching Fear & Greed Index: {e}")
            # Возвращаем кэш или дефолт
            return self._fng_cache['value'] if self._fng_cache['value'] is not None else 50
    
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
            return 0
        
        current_price = df['close'].iloc[-1]
        past_price = df['close'].iloc[-periods]
        
        change = ((current_price - past_price) / past_price) * 100
        return round(change, 2)
    
    def get_market_data(self, timeframe=None, limit=None):
        """
        Собирает все необходимые данные для анализа
        
        Returns:
            dict: Полный набор данных для ML модели
        """
        logger.info("Collecting market data...")
        
        # Получаем OHLCV данные
        tf = timeframe or config.TIMEFRAME
        lm = limit or 100
        df = self.get_ohlcv_data(timeframe=tf, limit=lm)
        if df is None:
            return None
        
        # Текущая цена и объем
        current = self.get_current_price()
        if current is None:
            return None
        
        # Fear & Greed Index
        fear_greed = self.get_fear_greed_index()
        
        # 24h статистика
        stats_24h = self.get_24h_stats()
        
        # Orderbook
        orderbook = self.get_orderbook()
        
        # Изменение цены
        price_change_1h = self.calculate_price_change(df, periods=12)  # 12 * 5min = 1h
        price_change_4h = self.calculate_price_change(df, periods=48)  # 48 * 5min = 4h
        
        market_data = {
            'df': df,
            'current_price': current['price'],
            'current_volume': current['volume'],
            'timestamp': current['timestamp'],
            'fear_greed': fear_greed,
            'price_change_1h': price_change_1h,
            'price_change_4h': price_change_4h,
            'stats_24h': stats_24h,
            'orderbook': orderbook
        }
        
        logger.info(f"Market data collected: Price=${current['price']:.2f}, Change 1h={price_change_1h}%")
        return market_data