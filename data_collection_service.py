"""
Data Collection Service
Автоматический сбор рыночных данных каждые 5 минут для ML обучения
"""

import asyncio
import logging
from datetime import datetime
import config
from database import Database
from data_collector import DataCollector
from indicators import TechnicalIndicators

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)


class DataCollectionService:
    """Сервис для непрерывного сбора рыночных данных"""
    
    def __init__(self):
        self.db = Database()
        self.data_collector = DataCollector()
        self.is_running = False
        
    async def collect_and_save(self):
        """Собирает данные и сохраняет в БД"""
        try:
            # Получаем рыночные данные
            market_data = self.data_collector.get_market_data()
            
            if not market_data or market_data.get('df') is None:
                logger.warning("Failed to collect market data")
                return False
            
            # Рассчитываем индикаторы
            df = market_data['df']
            orderbook = market_data.get('orderbook')
            
            indicators = TechnicalIndicators.calculate_all_indicators(
                df, 
                orderbook=orderbook,
                mode=config.TRADING_MODE
            )
            
            if not indicators:
                logger.warning("Failed to calculate indicators")
                return False
            
            # Добавляем volume_ma в market_data
            if len(df) >= config.VOLUME_MA_PERIOD:
                volume_ma = df['volume'].rolling(window=config.VOLUME_MA_PERIOD).mean().iloc[-1]
                market_data['volume_ma'] = float(volume_ma)
            else:
                market_data['volume_ma'] = 0
            
            # Сохраняем снимок
            self.db.save_market_snapshot(indicators, market_data)
            
            logger.info(f"Market snapshot collected: ${market_data['current_price']:,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error in collect_and_save: {e}")
            return False
    
    async def update_labels_task(self):
        """Периодически обновляет метки для старых записей"""
        while self.is_running:
            try:
                # Обновляем метки каждый час
                await asyncio.sleep(3600)  # 1 час
                
                logger.info("Updating future prices and labels...")
                self.db.update_future_prices(hours_ago=1)
                
                # Показываем статистику
                stats = self.db.get_snapshot_stats()
                if stats:
                    logger.info(
                        f"Snapshot stats: Total={stats['total']}, "
                        f"Labeled={stats['labeled']}, "
                        f"PUMP={stats['pump_count']}, "
                        f"DUMP={stats['dump_count']}, "
                        f"NEUTRAL={stats['neutral_count']}"
                    )
                
            except Exception as e:
                logger.error(f"Error in update_labels_task: {e}")
    
    async def collection_loop(self):
        """Основной цикл сбора данных"""
        logger.info("Data collection service started")
        self.is_running = True
        
        # Запускаем задачу обновления меток
        asyncio.create_task(self.update_labels_task())
        
        while self.is_running:
            try:
                # Собираем данные
                success = await self.collect_and_save()
                
                if success:
                    logger.debug("Data collection cycle completed")
                else:
                    logger.warning("Data collection cycle failed")
                
                # Ждем 5 минут (300 секунд)
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                # При ошибке ждем меньше перед повтором
                await asyncio.sleep(60)
    
    def stop(self):
        """Останавливает сервис"""
        logger.info("Stopping data collection service...")
        self.is_running = False


async def main():
    """Тестовый запуск сервиса"""
    service = DataCollectionService()
    
    try:
        await service.collection_loop()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        service.stop()


if __name__ == '__main__':
    asyncio.run(main())
