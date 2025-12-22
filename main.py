import asyncio
import config
import logging
from logging.handlers import RotatingFileHandler
from data_collector import DataCollector
from indicators import TechnicalIndicators
from ml_model import MLPredictor
from paper_trader import PaperTrader
from telegram_bot import TelegramBot
from database import Database
from healthcheck import HealthCheck
from utils import validate_config
import time
from datetime import datetime
import random
import signal
import sys

# Настройка логирования для production
file_handler = RotatingFileHandler(
    config.LOG_FILE,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
console_handler = logging.StreamHandler()

log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

file_handler.setFormatter(log_format)
console_handler.setFormatter(log_format)

logging.basicConfig(
    level=config.LOG_LEVEL,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

class BTCPumpDumpBot:
    """Главный класс бота для анализа и прогнозирования BTC"""
    
    def __init__(self):
        self.data_collector = DataCollector()
        self.ml_predictor = MLPredictor()
        self.telegram_bot = TelegramBot(config.TELEGRAM_BOT_TOKEN, main_bot=self)
        self.db = Database()
        self.healthcheck = HealthCheck(port=config.HEALTHCHECK_PORT)
        
        self.last_signal = None
        self.last_signal_time = None
        self.last_signal_price = None  # Для анти-спама по цене
        # Режим анализа: 'swing' | 'day' (читаем из config)
        self.current_mode = config.TRADING_MODE
        self._mode_lock = asyncio.Lock()
        
        # Флаг для graceful shutdown
        self.shutdown_requested = False
        
        # Paper Trading Engine (Phase 3)
        self.paper_trader = PaperTrader(self.db)
        
        logger.info("BTCPumpDumpBot initialized")

    def set_trading_mode(self, mode):
        if mode not in ['swing', 'day']:
            return False
        self.current_mode = mode
        logger.info(f"🔄 Trading mode changed: {mode.upper()}")
        return True
    
    def _get_params_for_mode(self, mode: str):
        """Возвращает параметры сбора данных под режим."""
        if mode == 'day':
            return {'timeframe': config.DAY_TIMEFRAME, 'limit': config.DAY_LIMIT}
        return {'timeframe': config.TIMEFRAME, 'limit': 100}

    async def analyze_market_with_mode(self, mode: str):
        """
        Анализ рынка с параметрами, зависящими от режима
        """
        try:
            params = self._get_params_for_mode(mode)
            logger.info("=" * 50)
            logger.info(f"Starting market analysis (mode={mode})...")
            
            # 1. Собираем данные c учётом режима
            market_data = await self.data_collector.get_market_data(
                timeframe=params['timeframe'],
                limit=params['limit']
            )
            if not market_data:
                logger.error("Failed to collect market data")
                return None
            
            # 2. Рассчитываем индикаторы
            indicators = TechnicalIndicators.calculate_all_indicators(
                market_data['df'],
                orderbook=market_data.get('orderbook'),
                mode=mode
            )
            if not indicators:
                logger.error("Failed to calculate indicators")
                return None
            
            # Добавляем fear & greed к индикаторам
            indicators['fear_greed'] = market_data['fear_greed']
            
            # 3. Делаем прогноз
            prediction = self.ml_predictor.predict(indicators, market_data, mode=mode)
            
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
                'timestamp': datetime.now(),
                'mode': mode
            }
            
            logger.info(f"Analysis complete: {prediction['signal']} ({prediction['probability']:.2%})")
            logger.info(f"Current price: ${market_data['current_price']:,.2f}")
            logger.info(f"BB position: {indicators.get('bb_position', 'N/A')}, Volume ratio: {indicators.get('volume_ratio', 0):.2f}x")
            
            # Обновляем healthcheck метрики
            self.healthcheck.update_analysis_time()
            
            return result
        except Exception as e:
            logger.error(f"Error in market analysis (mode={mode}): {e}", exc_info=True)
            self.healthcheck.increment_errors()
            return None

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
            market_data = await self.data_collector.get_market_data()
            if not market_data:
                logger.error("Failed to collect market data")
                return None
            
            # 2. Рассчитываем индикаторы
            indicators = TechnicalIndicators.calculate_all_indicators(
                market_data['df'],
                orderbook=market_data.get('orderbook'),
                mode='swing'
            )
            if not indicators:
                logger.error("Failed to calculate indicators")
                return None
            
            # Добавляем fear & greed к индикаторам
            indicators['fear_greed'] = market_data['fear_greed']
            
            # 3. Делаем прогноз
            prediction = self.ml_predictor.predict(indicators, market_data, mode='swing')
            
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
            logger.info(f"BB position: {indicators.get('bb_position', 'N/A')}, Volume ratio: {indicators.get('volume_ratio', 0):.2f}x")
            
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
        current_price = analysis_result['market_data']['current_price']
        
        if self.last_signal and self.last_signal_time:
            time_diff = current_time - self.last_signal_time
            
            # Если прошло меньше 30 минут и сигнал тот же - не отправляем
            if time_diff < 1800 and self.last_signal == prediction['signal']:
                logger.info(f"Same signal sent recently ({time_diff/60:.1f} min ago), skipping")
                return
        
        # Анти-спам: проверяем изменение цены (минимум 0.15%)
        if self.last_signal_price:
            price_change_pct = abs(
                (current_price - self.last_signal_price) / self.last_signal_price * 100
            )
            if price_change_pct < 0.15:
                logger.info(
                    f"Price change too small: {price_change_pct:.3f}% "
                    f"(${self.last_signal_price:,.2f} -> ${current_price:,.2f}), skipping signal"
                )
                return
            else:
                logger.info(f"Price changed by {price_change_pct:.3f}%, sending new signal")
        
        # Отправляем сигнал
        logger.info(f"🚨 Sending {prediction['signal']} signal to users!")
        
        # Сохраняем сигнал в БД
        self.db.save_signal(
            signal_type=prediction['signal'],
            probability=prediction['probability'],
            price=analysis_result['market_data']['current_price'],
            confidence=prediction['confidence']
        )

        # ----------------------------------------
        # Paper Trading Trigger
        # ----------------------------------------
        try:
            self.paper_trader.open_position(
                signal_type=prediction['signal'],
                current_price=analysis_result['market_data']['current_price'],
                probability=prediction['probability']
            )
        except Exception as e:
            logger.error(f"Paper Trading Error: {e}")
        
        await self.telegram_bot.send_signal_to_users(
            prediction,
            analysis_result['market_data'],
            analysis_result['indicators']
        )
        
        # Обновляем healthcheck метрики
        users_count = len(self.db.get_subscribed_users())
        self.healthcheck.increment_signals(users_count)
        
        # Обновляем последний сигнал и цену
        self.last_signal = prediction['signal']
        self.last_signal_time = current_time
        self.last_signal_price = current_price
        
        logger.info(
            f"✅ Signal sent: {prediction['signal']} at ${current_price:,.2f} "
            f"({prediction['probability']:.1%} confidence)"
        )
    
    async def monitoring_loop(self):
        """
        Основной цикл мониторинга рынка
        Запускается параллельно с Telegram ботом
        """
        logger.info("Starting monitoring loop...")
        
        while not self.shutdown_requested:
            try:
                # Определяем режим под lock и анализируем рынок
                async with self._mode_lock:
                    mode = self.current_mode
                analysis_result = await self.analyze_market_with_mode(mode)
                
                # Проверяем и отправляем сигналы
                await self.check_and_send_signal(analysis_result)
                
                # Paper Trading: Check exits (SL/TP) every loop
                current_price = analysis_result['market_data']['current_price']
                try:
                    self.paper_trader.update_positions(current_price)
                except Exception as e:
                    logger.error(f"Paper Trader Update Error: {e}")
                
                # Ждём следующей проверки (джиттер, отдельный базовый интервал для day)
                base_interval = config.CHECK_INTERVAL if mode != 'day' else config.DAY_CHECK_INTERVAL
                jitter = random.randint(-3, 3)
                sleep_s = max(5, base_interval + jitter)
                logger.info(f"Waiting {sleep_s} seconds until next check (mode={mode})...")
                
                # Прерываемый sleep для быстрого shutdown
                for _ in range(sleep_s):
                    if self.shutdown_requested:
                        break
                    await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("Monitoring loop stopped by user")
                self.shutdown_requested = True
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                self.healthcheck.increment_errors()
                # Ждём перед повтором в случае ошибки
                await asyncio.sleep(60)
    
    async def start_telegram_bot(self):
        """Запускает Telegram бота"""
        logger.info("Starting Telegram bot...")
        
        from telegram.ext import Application
        self.telegram_bot.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        self.telegram_bot.setup_handlers()
        
        # Запускаем polling (современный async способ)
        await self.telegram_bot.app.initialize()
        await self.telegram_bot.app.start()
        
        # PTB v21+: Application.start_polling(); PTB v20: fallback на updater.start_polling()
        if hasattr(self.telegram_bot.app, 'start_polling'):
            await self.telegram_bot.app.start_polling()
        elif hasattr(self.telegram_bot.app, 'updater') and getattr(self.telegram_bot.app, 'updater'):
            await self.telegram_bot.app.updater.start_polling()
        else:
            logger.error("No polling method available on Application. Please verify PTB version.")
        
        logger.info("Telegram bot started and polling...")
    
    async def run(self):
        """
        Запускает бота полностью
        Одновременно работают:
        1. Healthcheck HTTP server (мониторинг работоспособности)
        2. Telegram bot (обрабатывает команды пользователей)
        3. Monitoring loop (анализирует рынок и шлёт сигналы)
        """
        logger.info("=" * 50)
        logger.info("Starting BTC Pump/Dump Bot")
        logger.info(f"Environment: {config.ENVIRONMENT}")
        logger.info(f"Symbol: {config.SYMBOL}")
        logger.info(f"Timeframe: {config.TIMEFRAME}")
        logger.info(f"Check interval: {config.CHECK_INTERVAL}s")
        logger.info(f"Trading mode: {config.TRADING_MODE}")
        logger.info("=" * 50)
        
        try:
            # 1. Запускаем healthcheck сервер
            await self.healthcheck.start()
            
            # 2. Создаём задачи для параллельного выполнения
            bot_task = asyncio.create_task(self.start_telegram_bot())
            monitor_task = asyncio.create_task(self.monitoring_loop())
            
            # 3. Устанавливаем статус готовности
            self.healthcheck.set_ready(True)
            logger.info("✅ Bot is ready and running!")
            
            # 4. Ждём выполнения задач
            await asyncio.gather(bot_task, monitor_task)
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            self.shutdown_requested = True
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            self.healthcheck.increment_errors()
        finally:
            logger.info("Shutting down bot...")
            self.healthcheck.set_ready(False)
            
            # Graceful shutdown с таймаутом
            try:
                # Останавливаем Telegram бота
                if self.telegram_bot.app:
                    logger.info("Stopping Telegram bot...")
                    await asyncio.wait_for(
                        self.telegram_bot.app.stop(),
                        timeout=config.SHUTDOWN_TIMEOUT
                    )
                
                # Останавливаем healthcheck сервер
                logger.info("Stopping healthcheck server...")
                await self.healthcheck.stop()
                
                # Закрываем соединение с биржей
                if hasattr(self.data_collector, 'close'):
                    await self.data_collector.close()
                
                logger.info("✅ Bot stopped gracefully")
                
            except asyncio.TimeoutError:
                logger.warning("Shutdown timeout exceeded, forcing stop...")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}", exc_info=True)

def main():
    """Точка входа в программу"""
    
    # Валидация конфигурации
    if not validate_config():
        print("❌ Ошибки конфигурации. Исправьте и запустите снова.")
        return
    
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
    
    # Создаём бота
    bot = BTCPumpDumpBot()
    
    # Настройка обработчиков сигналов для graceful shutdown
    def signal_handler(signum, frame):
        """Обработчик SIGTERM и SIGINT для graceful shutdown"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        bot.shutdown_requested = True
    
    # Регистрируем обработчики (SIGTERM для systemd, SIGINT для Ctrl+C)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped. Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()