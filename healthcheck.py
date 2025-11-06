"""
Healthcheck HTTP endpoint для мониторинга бота
Предоставляет эндпоинты для проверки работоспособности
"""
import asyncio
from aiohttp import web
import logging
from datetime import datetime
import psutil
import os

logger = logging.getLogger(__name__)

class HealthCheck:
    """HTTP сервер для healthcheck и метрик"""
    
    def __init__(self, port=8080):
        self.port = port
        self.app = web.Application()
        self.runner = None
        
        # Метрики
        self.start_time = datetime.now()
        self.last_analysis_time = None
        self.is_ready = False
        self.total_analyses = 0
        self.total_signals_sent = 0
        self.errors_count = 0
        
        # Настройка роутов
        self.app.router.add_get('/health', self.health_handler)
        self.app.router.add_get('/ready', self.ready_handler)
        self.app.router.add_get('/metrics', self.metrics_handler)
        self.app.router.add_get('/', self.root_handler)
    
    async def health_handler(self, request):
        """
        Базовая проверка жизнеспособности процесса
        Возвращает 200 OK если процесс работает
        """
        return web.Response(text='OK', status=200)
    
    async def ready_handler(self, request):
        """
        Проверка готовности бота к работе
        Проверяет что анализ рынка выполнялся недавно
        """
        if not self.is_ready:
            return web.json_response(
                {'status': 'not_ready', 'reason': 'Bot is starting up'},
                status=503
            )
        
        # Проверяем что анализ был недавно (< 10 минут)
        if self.last_analysis_time:
            delta = (datetime.now() - self.last_analysis_time).total_seconds()
            if delta > 600:  # 10 минут
                return web.json_response({
                    'status': 'stale',
                    'reason': f'Last analysis {int(delta)}s ago',
                    'last_analysis': self.last_analysis_time.isoformat()
                }, status=503)
        
        return web.json_response({
            'status': 'ready',
            'last_analysis': self.last_analysis_time.isoformat() if self.last_analysis_time else None
        }, status=200)
    
    async def metrics_handler(self, request):
        """
        Возвращает метрики работы бота
        """
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Системные метрики
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent(interval=0.1)
        
        metrics = {
            'uptime_seconds': int(uptime),
            'status': 'ready' if self.is_ready else 'starting',
            'last_analysis': self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            'total_analyses': self.total_analyses,
            'total_signals_sent': self.total_signals_sent,
            'errors_count': self.errors_count,
            'system': {
                'memory_mb': round(memory_mb, 2),
                'cpu_percent': round(cpu_percent, 2),
                'pid': os.getpid()
            }
        }
        
        return web.json_response(metrics, status=200)
    
    async def root_handler(self, request):
        """
        Корневой эндпоинт с информацией о доступных роутах
        """
        info = {
            'service': 'BTC Pump/Dump Bot',
            'version': '1.0.0',
            'endpoints': {
                '/health': 'Health check (liveness probe)',
                '/ready': 'Readiness check',
                '/metrics': 'Bot metrics and statistics',
            }
        }
        return web.json_response(info, status=200)
    
    def update_analysis_time(self):
        """Обновить время последнего анализа"""
        self.last_analysis_time = datetime.now()
        self.total_analyses += 1
    
    def increment_signals(self, count=1):
        """Увеличить счётчик отправленных сигналов"""
        self.total_signals_sent += count
    
    def increment_errors(self):
        """Увеличить счётчик ошибок"""
        self.errors_count += 1
    
    def set_ready(self, ready: bool):
        """Установить статус готовности"""
        self.is_ready = ready
        logger.info(f"Healthcheck ready status: {ready}")
    
    async def start(self):
        """Запустить healthcheck HTTP сервер"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            site = web.TCPSite(self.runner, '0.0.0.0', self.port)
            await site.start()
            logger.info(f"✅ Healthcheck server started on http://0.0.0.0:{self.port}")
            logger.info(f"   Endpoints: /health /ready /metrics")
        except Exception as e:
            logger.error(f"Failed to start healthcheck server: {e}")
            raise
    
    async def stop(self):
        """Остановить healthcheck HTTP сервер"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("Healthcheck server stopped")
