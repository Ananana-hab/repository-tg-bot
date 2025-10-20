import asyncio
import config
import logging
from data_collector import DataCollector
from indicators import TechnicalIndicators
from ml_model import MLPredictor
from telegram_bot import TelegramBot
from database import Database
import time
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BTCPumpDumpBot:
    """Главный класс бота для анализа и прогнозирования BTC"""
    
    def __init__(self):
        self.data_collector = DataCollector()
        self.ml_predictor = MLPredictor()
        self.telegram_bot = TelegramBot(config.TELEGRAM_BOT_TOKEN)
        self.db = Database()
        
        self.last_signal = None
        self.last_signal_time = None
        
        logger.info("BTCPumpDumpBot initialized")
    
    async def analyze_market(self):
        """
        Основная функция анализа рынка
        
        Returns:
            dict: Результаты анализа
        """
        try:
            logger.info("=" * 50)
            logger.info("Starting market analysis...")
            
            # 1. Собираем данные
            market_data = self.data_collector.get_market_data()
            if not market_data:
                logger.error("Failed to collect market data")
                return None
            
            # 2. Рассчитываем индикаторы
            indicators = TechnicalIndicators.calculate_all_indicators(market_data['df'])
            if not indicators:
                logger.error("Failed to calculate indicators")
                return None
            
            # Добавляем fear & greed к индикаторам
            indicators['fear_greed'] = market_data['fear_greed']
            
            # 3. Делаем прогноз
            prediction = self.ml_predictor.predict(indicators, market_data)
            
            # 4. Определяем силу сигнала
            signal_strength = TechnicalIndicators.get_signal_strength(
                indicators,
                market_data['price_change_1h']
            )
            
            # 5. Сохраняем данные в БД
            self.db.save_price_data(
                market_data['current_price'],
                market_data['current_volume'],
                indicators
            )
            
            result = {
                'market_data': market_data,
                'indicators': indicators,
                'prediction': prediction,
                'signal_strength': signal_strength,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Analysis complete: {prediction['signal']} ({prediction['probability']:.2%})")
            logger.info(f"Current price: ${market_data['current_price']:,.2f}")
            logger.info(f"RSI: {indicators['rsi']:.2f}, MACD crossover: {indicators['macd_crossover']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in market analysis: {e}", exc_info=True)
            return None
    
    async def check_and_send_signal(self, analysis_result):
        """
        Проверяет условия и отправляет сигнал пользователям
        
        Args:
            analysis_result: результат анализа рынка
        """
        if not analysis_result:
            return
        
        prediction = analysis_result['prediction']
        
        # Проверяем, нужно ли отправлять сигнал
        if not self.ml_predictor.should_send_signal(prediction):
            logger.info(f"Signal not strong enough: {prediction['signal']} ({prediction['probability']:.2%})")
            return
        
        # Проверяем, не отправляли ли мы похожий сигнал недавно (во избежание спама)
        current_time = time.time()
        if self.last_signal and self.last_signal_time:
            time_diff = current_time - self.last_signal_time
            
            # Если прошло меньше 30 минут и сигнал тот же - не отправляем
            if time_diff < 1800 and self.last_signal == prediction['signal']:
                logger.info(f"Same signal sent recently ({time_diff/60:.1f} min ago), skipping")
                return
        
        # Отправляем сигнал
        logger.info(f"🚨 Sending {prediction['signal']} signal to users!")
        
        await self.telegram_bot.send_signal_to_users(
            prediction,
            analysis_result['market_data'],
            analysis_result['indicators']
        )
        
        # Обновляем последний сигнал
        self.last_signal = prediction['signal']
        self.last_signal_time = current_time
    
    async def monitoring_loop(self):
        """
        Основной цикл мониторинга рынка
        Запускается параллельно с Telegram ботом
        """
        logger.info("Starting monitoring loop...")
        
        while True:
            try:
                # Анализируем рынок
                analysis_result = await self.analyze_market()
                
                # Проверяем и отправляем сигналы
                await self.check_and_send_signal(analysis_result)
                
                # Ждём следующей проверки
                logger.info(f"Waiting {config.CHECK_INTERVAL} seconds until next check...")
                await asyncio.sleep(config.CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Monitoring loop stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                # Ждём перед повтором в случае ошибки
                await asyncio.sleep(60)
    
    async def start_telegram_bot(self):
        """Запускает Telegram бота"""
        logger.info("Starting Telegram bot...")
        
        from telegram.ext import Application
        self.telegram_bot.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        self.telegram_bot.setup_handlers()
        
        # Запускаем polling
        await self.telegram_bot.app.initialize()
        await self.telegram_bot.app.start()
        await self.telegram_bot.app.updater.start_polling()
        
        logger.info("Telegram bot started and polling...")
    
    async def run(self):
        """
        Запускает бота полностью
        Одновременно работают:
        1. Telegram bot (обрабатывает команды пользователей)
        2. Monitoring loop (анализирует рынок и шлёт сигналы)
        """
        logger.info("=" * 50)
        logger.info("Starting BTC Pump/Dump Bot")
        logger.info(f"Symbol: {config.SYMBOL}")
        logger.info(f"Timeframe: {config.TIMEFRAME}")
        logger.info(f"Check interval: {config.CHECK_INTERVAL}s")
        logger.info("=" * 50)
        
        try:
            # Создаём задачи для параллельного выполнения
            bot_task = asyncio.create_task(self.start_telegram_bot())
            monitor_task = asyncio.create_task(self.monitoring_loop())
            
            # Ждём выполнения обеих задач
            await asyncio.gather(bot_task, monitor_task)
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            logger.info("Shutting down bot...")
            if self.telegram_bot.app:
                await self.telegram_bot.app.stop()

def main():
    """Точка входа в программу"""
    
    # Проверяем наличие токена
    if config.TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("=" * 50)
        print("⚠️  ОШИБКА: Telegram Bot Token не настроен!")
        print("=" * 50)
        print("\nИнструкция:")
        print("1. Перейди к @BotFather в Telegram")
        print("2. Создай нового бота командой /newbot")
        print("3. Скопируй полученный токен")
        print("4. Открой файл .env в корне проекта")
        print("5. Замени YOUR_TOKEN_HERE на свой токен")
        print("=" * 50)
        return
    
    # Создаём и запускаем бота
    bot = BTCPumpDumpBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped. Goodbye!")

if __name__ == '__main__':
    main()