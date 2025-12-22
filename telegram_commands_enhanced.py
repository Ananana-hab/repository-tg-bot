import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
import pandas as pd
from database_analytics import DatabaseAnalytics

logger = logging.getLogger(__name__)

# Помощник для форматирования
def format_trend(value, is_pct=False):
    if value is None: return "N/A"
    s = f"{value:+.2f}%" if is_pct else f"{value:.2f}"
    if value > 0: return f"🟢 {s}"
    if value < 0: return f"🔴 {s}"
    return f"⚪ {s}"

async def stats_command_enhanced(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает расширенную статистику сигналов
    """
    message = update.message if update.message else update.callback_query.message
    
    analytics = DatabaseAnalytics()
    
    # 1. Получаем общую статистику сигналов за 30 дней
    stats = analytics.get_signals_stats(days=30)
    
    # 2. Получаем точность (если есть проверенные сигналы)
    accuracy = analytics.get_signal_accuracy(days=30)
    
    if not stats:
        await self.send_with_retry(message.chat_id, "ℹ️ Нет данных для статистики за последние 30 дней.")
        return

    # Формируем сообщение
    total_pump = stats.get('PUMP', {}).get('count', 0)
    total_dump = stats.get('DUMP', {}).get('count', 0)
    
    pump_acc = accuracy.get('PUMP', 0)
    dump_acc = accuracy.get('DUMP', 0)
    
    avg_conf_pump = stats.get('PUMP', {}).get('high_confidence', 0)
    avg_conf_dump = stats.get('DUMP', {}).get('high_confidence', 0)

    text = f"""
📊 СТАТИСТИКА СИГНАЛОВ (30 дней)
━━━━━━━━━━━━━━━━

🚀 PUMP СИГНАЛЫ:
• Всего: {total_pump}
• Точность: {pump_acc:.1f}%
• Высокая уверенность: {avg_conf_pump:.0f}%

📉 DUMP СИГНАЛЫ:
• Всего: {total_dump}
• Точность: {dump_acc:.1f}%
• Высокая уверенность: {avg_conf_dump:.0f}%

🤖 ОБЩАЯ ТОЧНОСТЬ: {(pump_acc + dump_acc)/2:.1f}%
━━━━━━━━━━━━━━━━
ℹ️ Точность рассчитывается на основе движения цены после сигнала.
"""
    await self.send_with_retry(message.chat_id, text)

async def performance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Анализ производительности и Equity Curve (симуляция)
    """
    message = update.message if update.message else update.callback_query.message
    analytics = DatabaseAnalytics()
    
    equity_df = analytics.get_equity_curve(days=30, initial_capital=1000)
    
    if equity_df is None or equity_df.empty:
        await self.send_with_retry(message.chat_id, "ℹ️ Недостаточно данных для расчета кривой капитала.")
        return

    # Считаем итоговый PnL
    start_cap = 1000
    end_cap = equity_df.iloc[-1]['equity']
    total_pnl = end_cap - start_cap
    total_pnl_pct = (total_pnl / start_cap) * 100
    
    best_trade = equity_df['pnl'].max()
    worst_trade = equity_df['pnl'].min()
    
    text = f"""
📈 ПРОИЗВОДИТЕЛЬНОСТЬ (Paper Trading)
━━━━━━━━━━━━━━━━
Начальный капитал: $1,000

💰 Текущий капитал: ${end_cap:,.2f}
📊 PnL: {format_trend(total_pnl_pct, is_pct=True)} (${total_pnl:.2f})

🏆 Лучшая сделка: +${best_trade:.2f}
💀 Худшая сделка: ${worst_trade:.2f}
━━━━━━━━━━━━━━━━
ℹ️ Симуляция: вход 10% от депозита на каждый сигнал.
"""
    await self.send_with_retry(message.chat_id, text)

async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Генерирует CSV отчет (упрощенная версия)
    """
    message = update.message if update.message else update.callback_query.message
    await self.send_with_retry(message.chat_id, "📝 Генерация полных отчетов скоро будет доступна.")

async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запускает ручной анализ рынка прямо сейчас
    """
    message = update.message if update.message else update.callback_query.message
    
    if not self.main_bot:
        await self.send_with_retry(message.chat_id, "❌ Ошибка: нет связи с аналитическим ядром.")
        return
        
    await self.send_with_retry(message.chat_id, "🔄 Запускаю глубокий анализ рынка...")
    
    try:
        # Используем текущий режим бота для анализа
        async with self.main_bot._mode_lock:
             mode = self.main_bot.current_mode
             
        result = await self.main_bot.analyze_market_with_mode(mode)
        
        if not result:
            await self.send_with_retry(message.chat_id, "⚠️ Не удалось получить данные. Попробуйте позже.")
            return

        market_data = result['market_data']
        prediction = result['prediction']
        indicators = result['indicators']

        # Формируем расширенный отчет
        signal_icon = "🚀" if prediction['signal'] == 'PUMP' else "📉" if prediction['signal'] == 'DUMP' else "⚖️"
        
        text = f"""
🔎 РУЧНОЙ АНАЛИЗ | {datetime.now().strftime('%H:%M')}
━━━━━━━━━━━━━━━━
Цена: ${market_data['current_price']:,.2f}

🧠 ML ПРОГНОЗ:
Сигнал: {signal_icon} {prediction['signal']}
Вероятность: {prediction['probability']:.1%} ({prediction.get('confidence', 'N/A')})

📊 ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ:
• RSI: {indicators.get('rsi', 0):.1f}
• MACD: {indicators.get('macd', 0):.2f}
• Объём: {indicators.get('volume_ratio', 1.0):.2f}x
• Bollinger: {indicators.get('bb_position', 'inside')}

🌪 НАСТРОЕНИЕ РЫНКА:
• Fear & Greed: {market_data.get('fear_greed', 50)}
• Open Interest (1h): {format_trend(market_data.get('oi_change_1h', 0), is_pct=True)}

━━━━━━━━━━━━━━━━
"""
        await self.send_with_retry(message.chat_id, text)
        
    except Exception as e:
        logger.error(f"Manual analysis failed: {e}")
        await self.send_with_retry(message.chat_id, "❌ Ошибка при выполнении анализа.")

async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает историю последних сигналов
    """
    message = update.message if update.message else update.callback_query.message
    analytics = DatabaseAnalytics()
    
    # Получаем последние 10 сигналов
    df = analytics.get_signals_for_analysis(days=7)
    
    if df is None or len(df) == 0:
        await self.send_with_retry(message.chat_id, "📭 История сигналов пуста.")
        return
        
    # Берем последние 10
    recent = df.tail(10).iloc[::-1] # Разворачиваем (новые сверху)
    
    text = "📜 ИСТОРИЯ СИГНАЛОВ (Последние 10):\n\n"
    
    for _, row in recent.iterrows():
        icon = "🟢" if row['signal_type'] == 'PUMP' else "🔴"
        date_str = pd.to_datetime(row['timestamp']).strftime('%d.%m %H:%M')
        price = row['price']
        
        # Если есть результат
        result_str = ""
        if pd.notna(row.get('actual_result')):
             res_icon = "✅" if row['actual_result'] == 'correct' else "❌"
             result_str = f"| {res_icon}"
        
        text += f"{icon} {date_str} | ${price:,.0f} {result_str}\n"

    text += "\nИспользуйте /stats для полной статистики."
    await self.send_with_retry(message.chat_id, text)
