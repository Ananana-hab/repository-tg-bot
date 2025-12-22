import ccxt.async_support as ccxt
from ccxt.base.errors import RateLimitExceeded, NetworkError, ExchangeError, RequestTimeout
import aiohttp
import asyncio
import config
import logging
from datetime import datetime, timedelta
import pandas as pd
import time

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class DataCollector:
    def __init__(self):
        # Инициализируем Async Binance без API ключей (публичные данные)
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
        })
        # Кэш для FNG
        self._fng_cache = {'value': None, 'ts': None}
        # Кэш для Open Interest
        self._oi_cache = {'value': None, 'ts': None, 'history': []}
        
    async def close(self):
        """Закрывает соединение с биржей"""
        await self.exchange.close()
        
    async def get_current_price(self):
        """Получает текущую цену BTC/USDT асинхронно"""
        try:
            ticker = await self.exchange.fetch_ticker(config.SYMBOL)
            return {
                'price': float(ticker['last']),
                'volume': float(ticker['quoteVolume']),
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.error(f"Error fetching price: {e}")
            return None
    
    async def get_ohlcv_data(self, timeframe='5m', limit=100):
        """
        Получает OHLCV данные асинхронно
        """
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                ohlcv = await self.exchange.fetch_ohlcv(config.SYMBOL, timeframe, limit=limit)
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                # Приводим к типам (на всякий случай)
                cols = ['open', 'high', 'low', 'close', 'volume']
                df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
                
                return df
                
            except (NetworkError, RequestTimeout) as e:
                logger.warning(f"Network error fetching OHLCV (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error("Max retries exceeded for OHLCV")
                    return None
            except Exception as e:
                logger.error(f"Error fetching OHLCV: {e}")
                return None
    
    async def get_order_book(self, limit=20):
        """Получает стакан заявок асинхронно"""
        try:
            orderbook = await self.exchange.fetch_order_book(config.SYMBOL, limit)
            # Возвращаем в том же формате, что и раньше, для совместимости?
            # Или просто сырой, но старый код ожидал dict['bids']... ccxt возвращает dict с bids/asks
            return orderbook
        except Exception as e:
            logger.error(f"Error fetching order book: {e}")
            return None
            
    async def get_fear_greed_index(self):
        """Получает индекс страха и жадности (Alternative.me API) асинхронно"""
        # Проверяем кэш (TTL 1 час)
        now = datetime.now()
        if (self._fng_cache['value'] is not None and 
            self._fng_cache['ts'] is not None and 
            (now - self._fng_cache['ts']).total_seconds() < 3600):
            return self._fng_cache['value']

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(config.FEAR_GREED_API, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and 'data' in data and len(data['data']) > 0:
                            value = int(data['data'][0]['value'])
                            self._fng_cache = {'value': value, 'ts': now}
                            logger.info(f"Fear & Greed Index updated: {value}")
                            return value
                        
            return self._fng_cache['value'] if self._fng_cache['value'] else 50
        except Exception as e:
            logger.error(f"Error fetching Fear & Greed Index: {e}")
            return self._fng_cache['value'] if self._fng_cache['value'] else 50

    async def get_open_interest(self):
        """Получает Open Interest асинхронно (с кэшированием)"""
        now = datetime.now()
        # Кэш на 5 минут
        if (self._oi_cache['value'] is not None and 
            self._oi_cache['ts'] is not None and 
            (now - self._oi_cache['ts']).total_seconds() < 300):
             return self._oi_cache['value']
             
        try:
            # Прямой запрос к binance api для фьючерсов
            url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={config.SYMBOL.replace('/', '')}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        current_oi = float(data['openInterest'])
                        
                        # Сохраняем историю
                        self._oi_cache['history'].append({'timestamp': now, 'value': current_oi})
                        cutoff = now - timedelta(hours=5)
                        self._oi_cache['history'] = [x for x in self._oi_cache['history'] if x['timestamp'] > cutoff]
                        
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
                        
                        self._oi_cache['value'] = result
                        self._oi_cache['ts'] = now
                        
                        logger.info(f"Open Interest updated: {current_oi}")
                        return result
                    
            return self._get_cached_oi_or_default()
            
        except Exception as e:
            logger.debug(f"Could not fetch Open Interest: {e}")
            return self._get_cached_oi_or_default()

    def _calculate_oi_change(self, minutes):
        """Вычисляет изменение OI за указанный период (синхронно, чистая логика)"""
        try:
            history = self._oi_cache['history']
            if len(history) < 2:
                return 0.0
            
            now = datetime.now()
            target_time = now - timedelta(minutes=minutes)
            
            closest = min(history, key=lambda x: abs((x['timestamp'] - target_time).total_seconds()))
            
            current_oi = history[-1]['value']
            past_oi = closest['value']
            
            if past_oi == 0: return 0.0
            return round(((current_oi - past_oi) / past_oi) * 100, 2)
            
        except Exception:
            return 0.0

    def _get_cached_oi_or_default(self):
        if self._oi_cache['value']: return self._oi_cache['value']
        return {'value': 0, 'change_5m': 0, 'change_1h': 0, 'change_4h': 0}

    def calculate_price_change(self, df, periods=12):
        if df is None or len(df) < periods: return 0
        current = df['close'].iloc[-1]
        past = df['close'].iloc[-periods]
        if past == 0: return 0
        return round(((current - past) / past) * 100, 2)

    async def get_24h_stats(self):
        """Получает статистику за 24 часа"""
        try:
            ticker = await self.exchange.fetch_ticker(config.SYMBOL)
            return {
                'price_change_24h': ticker.get('percentage', 0),
                'high_24h': ticker.get('high', 0),
                'low_24h': ticker.get('low', 0),
                'volume_24h': ticker.get('quoteVolume', 0)
            }
        except Exception as e:
            logger.error(f"Error fetching 24h stats: {e}")
            return None

    async def get_market_data(self, timeframe=None, limit=None):
        """
        Собирает ВСЕ данные для анализа в одну структуру асинхронно
        """
        logger.info("Collecting market data...")
        
        tf = timeframe or config.TIMEFRAME
        lm = limit or 100
        
        try:
            # Параллельный запуск независимых задач
            # 1. Основные
            ohlcv_task = asyncio.create_task(self.get_ohlcv_data(timeframe=tf, limit=lm))
            price_task = asyncio.create_task(self.get_current_price())
            ob_task = asyncio.create_task(self.get_order_book())
            fg_task = asyncio.create_task(self.get_fear_greed_index())
            oi_task = asyncio.create_task(self.get_open_interest())
            stats_task = asyncio.create_task(self.get_24h_stats())
            
            # Ожидание
            df = await ohlcv_task
            current = await price_task
            orderbook = await ob_task
            fear_greed = await fg_task
            open_interest = await oi_task
            stats_24h = await stats_task
            
            if df is None or df.empty:
                logger.error("Failed to get OHLCV data")
                return None
                
            if current is None:
                current = {
                    'price': df['close'].iloc[-1],
                    'volume': df['volume'].iloc[-1],
                    'timestamp': df['timestamp'].iloc[-1]
                }
            
            # Расчеты (CPU bound часть - очень быстрая, можно оставить синхронно)
            # Периоды
            timeframe_minutes = {'1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30, '1h': 60, '4h': 240, '1d': 1440}
            tf_min = timeframe_minutes.get(tf, 5)
            periods_1h = max(1, 60 // tf_min)
            periods_4h = max(1, 240 // tf_min)
            
            price_change_1h = self.calculate_price_change(df, periods=periods_1h)
            price_change_4h = self.calculate_price_change(df, periods=periods_4h)
            
            # Volume ratio
            try:
                avg_volume = df['volume'].rolling(window=config.VOLUME_MA_PERIOD).mean().iloc[-1]
                current_vol = float(df['volume'].iloc[-1])
                volume_ratio = (current_vol / avg_volume) if avg_volume > 0 else 1.0
                volume_change_pct = (volume_ratio - 1.0) * 100.0
            except:
                volume_ratio = 1.0
                volume_change_pct = 0.0
            
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
                'open_interest': open_interest['value'],
                'oi_change_5m': open_interest['change_5m'],
                'oi_change_1h': open_interest['change_1h'],
                'oi_change_4h': open_interest['change_4h'],
                'volume_ratio': volume_ratio,
                'volume_change_pct': round(volume_change_pct, 1),
                'timeframe': tf,
                'timeframe_minutes': tf_min,
                'periods_1h': periods_1h,
                'periods_4h': periods_4h
            }
            
            logger.info(f"Market data collected: Price=${current['price']:.2f}, F&G={fear_greed}")
            return market_data
            
        except Exception as e:
            logger.error(f"Critical error in get_market_data: {e}")
            import traceback
            traceback.print_exc()
            return None