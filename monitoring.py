"""
Модуль мониторинга и алертов для бота
Проверяет работоспособность и отправляет уведомления при проблемах
"""
import asyncio
import logging
import requests
from datetime import datetime
from telegram import Bot
import config

logger = logging.getLogger(__name__)

class BotMonitor:
    """Мониторинг работоспособности бота"""
    
    def __init__(self, healthcheck_url='http://localhost:8080', alert_chat_id=None):
        self.healthcheck_url = healthcheck_url
        self.alert_chat_id = alert_chat_id or config.TELEGRAM_BOT_TOKEN.split(':')[0]  # fallback to bot owner
        self.bot = None
        self.consecutive_failures = 0
        self.max_failures = 3  # Алерт после 3 неудач подряд
        self.last_alert_time = None
        self.alert_cooldown = 1800  # 30 минут между алертами
        
        if alert_chat_id:
            try:
                self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
            except Exception as e:
                logger.error(f"Failed to initialize alert bot: {e}")
    
    async def check_health(self):
        """Проверить /health эндпоинт"""
        try:
            response = requests.get(f"{self.healthcheck_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    async def check_ready(self):
        """Проверить /ready эндпоинт"""
        try:
            response = requests.get(f"{self.healthcheck_url}/ready", timeout=5)
            if response.status_code == 200:
                return True, "ready"
            else:
                data = response.json()
                return False, data.get('reason', 'unknown')
        except Exception as e:
            logger.warning(f"Readiness check failed: {e}")
            return False, str(e)
    
    async def get_metrics(self):
        """Получить метрики бота"""
        try:
            response = requests.get(f"{self.healthcheck_url}/metrics", timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.warning(f"Failed to get metrics: {e}")
            return None
    
    async def send_alert(self, message):
        """Отправить алерт в Telegram"""
        if not self.bot or not self.alert_chat_id:
            logger.warning(f"Alert (no Telegram): {message}")
            return
        
        # Проверка cooldown
        if self.last_alert_time:
            elapsed = (datetime.now() - self.last_alert_time).total_seconds()
            if elapsed < self.alert_cooldown:
                logger.info(f"Alert suppressed (cooldown): {message}")
                return
        
        try:
            alert_text = f"🚨 <b>BOT ALERT</b>\n\n{message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            await self.bot.send_message(
                chat_id=self.alert_chat_id,
                text=alert_text,
                parse_mode='HTML'
            )
            self.last_alert_time = datetime.now()
            logger.info(f"Alert sent: {message}")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    async def run_checks(self):
        """Выполнить все проверки"""
        # Проверка health
        is_healthy = await self.check_health()
        if not is_healthy:
            self.consecutive_failures += 1
            logger.warning(f"Health check failed (failures: {self.consecutive_failures})")
            
            if self.consecutive_failures >= self.max_failures:
                await self.send_alert(
                    f"❌ Bot is not responding to health checks!\n"
                    f"Consecutive failures: {self.consecutive_failures}"
                )
            return
        
        # Проверка readiness
        is_ready, reason = await self.check_ready()
        if not is_ready:
            self.consecutive_failures += 1
            logger.warning(f"Readiness check failed: {reason} (failures: {self.consecutive_failures})")
            
            if self.consecutive_failures >= self.max_failures:
                await self.send_alert(
                    f"⚠️ Bot is not ready!\n"
                    f"Reason: {reason}\n"
                    f"Consecutive failures: {self.consecutive_failures}"
                )
            return
        
        # Получение метрик
        metrics = await self.get_metrics()
        if metrics:
            # Проверка использования памяти (> 500 MB)
            memory_mb = metrics.get('system', {}).get('memory_mb', 0)
            if memory_mb > 500:
                await self.send_alert(
                    f"⚠️ High memory usage!\n"
                    f"Memory: {memory_mb:.2f} MB"
                )
            
            # Проверка ошибок (> 10 за период)
            errors = metrics.get('errors_count', 0)
            if errors > 10:
                await self.send_alert(
                    f"⚠️ High error rate!\n"
                    f"Errors: {errors}"
                )
            
            logger.info(
                f"✅ Monitor check passed. "
                f"Uptime: {metrics['uptime_seconds']}s, "
                f"Analyses: {metrics['total_analyses']}, "
                f"Signals: {metrics['total_signals_sent']}"
            )
        
        # Сброс счётчика неудач
        if self.consecutive_failures > 0:
            logger.info("Bot recovered!")
            await self.send_alert("✅ Bot has recovered and is operating normally.")
        self.consecutive_failures = 0
    
    async def monitor_loop(self, interval=300):
        """
        Основной цикл мониторинга
        
        Args:
            interval: интервал проверок в секундах (по умолчанию 5 минут)
        """
        logger.info(f"Starting monitoring loop (interval: {interval}s)")
        
        while True:
            try:
                await self.run_checks()
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
            
            await asyncio.sleep(interval)


async def main():
    """Запуск мониторинга как отдельного процесса"""
    # Получить ALERT_TELEGRAM_CHAT_ID из переменных окружения
    alert_chat_id = config.ALERT_TELEGRAM_CHAT_ID if hasattr(config, 'ALERT_TELEGRAM_CHAT_ID') else None
    
    monitor = BotMonitor(
        healthcheck_url='http://localhost:8080',
        alert_chat_id=alert_chat_id
    )
    
    await monitor.monitor_loop(interval=300)  # Проверка каждые 5 минут


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
