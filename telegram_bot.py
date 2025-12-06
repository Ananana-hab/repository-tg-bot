from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import config
import logging
from database import Database
from datetime import datetime
import asyncio

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token, main_bot=None):  # ✅ ИСПРАВЛЕНО: Добавлен main_bot
        self.token = token
        self.db = Database()
        self.app = None
        self.main_bot = main_bot  # Ссылка на главный бот
        
        # Хранилище пользовательских настроек (временно в памяти)
        self.user_settings = {}
        
    def get_user_settings(self, user_id):
        """Получает настройки пользователя или создаёт дефолтные"""
        if user_id not in self.user_settings:
            self.user_settings[user_id] = {
                'notifications': True,
                'min_probability': 70,
                'signal_types': ['PUMP', 'DUMP'],
                'mode': 'swing'  # 'swing' | 'day'
            }
        return self.user_settings[user_id]
    
    def update_user_setting(self, user_id, key, value):
        """Обновляет настройку пользователя"""
        settings = self.get_user_settings(user_id)
        settings[key] = value
        self.user_settings[user_id] = settings
    
    def _get_bb_status(self, indicators):
        """Определяет статус Bollinger Bands"""
        try:
            bb_upper = indicators.get('bollinger_upper')
            bb_lower = indicators.get('bollinger_lower')
            bb_middle = indicators.get('bollinger_middle')
            
            if bb_upper and bb_lower and bb_middle:
                return "Внутри диапазона"
            return "N/A"
        except:
            return "N/A"
    
    def _get_volume_status(self, indicators):
        """Определяет статус объёма"""
        try:
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:
                return f"+{(volume_ratio-1)*100:.0f}% выше среднего"
            elif volume_ratio < 0.7:
                return f"{(1-volume_ratio)*100:.0f}% ниже среднего"
            else:
                return "Средний"
        except:
            return "N/A"

    async def send_with_retry(self, chat_id, text, reply_markup=None, max_retries=3):
        """
        Отправляет сообщение с поддержкой повторных попыток
        
        Args:
            chat_id: ID чата
            text: текст сообщения
            reply_markup: разметка клавиатуры (опционально)
            max_retries: максимальное количество попыток
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                # Используем существующий Application вместо создания нового
                if self.app and self.app.bot:
                    return await self.app.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                else:
                    # Fallback: создаём временный Application если основной не инициализирован
                    async with Application.builder().token(self.token).build() as app:
                        return await app.bot.send_message(
                            chat_id=chat_id,
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue
                logger.error(f"Failed to send message after {max_retries} attempts: {e}")
                raise last_error
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Сохраняем пользователя в БД
        self.db.add_user(user.id, user.username, user.first_name)
        
        welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот для анализа Bitcoin и прогнозирования PUMP/DUMP движений.

🤖 Что я умею:
• Анализировать BTC в режиме реального времени
• Рассчитывать вероятность роста/падения
• Отправлять сигналы с высокой точностью
• Показывать технические индикаторы

📊 Команды:
/status - Текущий анализ BTC
/stats - Статистика и точность
/subscribe - Включить уведомления
/unsubscribe - Отключить уведомления
/settings - Настройки
/help - Помощь

⚠️ Disclaimer: Это не финансовый совет. Торгуйте на свой риск!
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 Текущий статус", callback_data='cmd_status')],
            [InlineKeyboardButton("🔔 Подписаться на сигналы", callback_data='cmd_subscribe')],
            [InlineKeyboardButton("📈 Статистика", callback_data='cmd_stats')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_with_retry(chat_id=update.message.chat_id, text=welcome_text, reply_markup=reply_markup)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status - показывает текущий анализ"""
        message = update.message if update.message else update.callback_query.message
        
        await self.send_with_retry(chat_id=message.chat_id, text="🔄 Анализирую рынок, подождите...")
        
        try:
            # Получаем реальный анализ рынка
            if self.main_bot:
                # Определяем текущий режим
                async with self.main_bot._mode_lock:
                    mode = self.main_bot.current_mode
                
                # Выполняем анализ
                analysis = await self.main_bot.analyze_market_with_mode(mode)
                
                if analysis:
                    market_data = analysis['market_data']
                    indicators = analysis['indicators']
                    prediction = analysis['prediction']
                    
                    # Форматируем сообщение с реальными данными
                    direction = '↗️' if market_data.get('price_change_1h', 0) > 0 else '↘️'
                    signal_emoji = '🚀' if prediction['signal'] == 'PUMP' else '📉' if prediction['signal'] == 'DUMP' else '↔️'
                    
                    status_text = f"""
📊 BTC/USDT | {mode.upper()}
━━━━━━━━━━━━━━━━

💰 Цена: ${market_data['current_price']:,.2f}
{direction} 1ч: {market_data.get('price_change_1h', 0):+.2f}%
{direction} 4ч: {market_data.get('price_change_4h', 0):+.2f}%
📉 24ч: {market_data.get('stats_24h', {}).get('price_change_24h', 0):+.2f}%

📊 АКТИВНОСТЬ:
• Объём: {self._get_volume_status(indicators)}
• Bollinger: {self._get_bb_status(indicators)}
• Momentum: {'Растёт' if indicators.get('momentum', 0) > 0 else 'Падает'}

{signal_emoji} ПРОГНОЗ: {prediction['signal']}
🎯 Уверенность: {prediction['confidence']} ({prediction['probability']*100:.0f}%)

⏰ {datetime.utcnow().strftime('%H:%M:%S UTC')}
                    """
                else:
                    status_text = "⚠️ Не удалось получить данные анализа. Попробуйте позже."
            else:
                status_text = "⚠️ Анализатор недоступен. Попробуйте позже."
                
        except Exception as e:
            logger.error(f"Error in status_command: {e}", exc_info=True)
            status_text = "❌ Ошибка при анализе рынка. Попробуйте позже."
        
        await self.send_with_retry(chat_id=message.chat_id, text=status_text)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику сигналов"""
        try:
            message = update.message if update.message else update.callback_query.message
            
            # Получаем статистику из БД
            stats = self.db.get_signals_stats(days=30)
            if not stats:
                await self.send_with_retry(
                    chat_id=message.chat_id,
                    text="⚠️ Ошибка получения статистики"
                )
                return

            total_signals = sum(s['count'] for s in stats.values())
            if total_signals == 0:
                await self.send_with_retry(
                    chat_id=message.chat_id,
                    text="📊 Статистика пока недоступна - нет сигналов за последние 30 дней"
                )
                return

            stats_text = "📊 Статистика сигналов за месяц:\n\n"
            
            for signal_type, data in stats.items():
                count = data['count']
                if count > 0:
                    avg_prob = data['avg_probability']
                    high_conf = data['high_confidence']
                    
                    stats_text += f"{signal_type} сигналы:\n"
                    stats_text += f"• Количество: {count}\n"
                    stats_text += f"• Средняя вероятность: {avg_prob:.1%}\n"
                    stats_text += f"• Высокая уверенность: {high_conf:.1f}%\n"
                    stats_text += "\n"

            stats_text += f"📈 Всего сигналов: {total_signals}\n"
            stats_text += f"⏰ {datetime.utcnow().strftime('%H:%M:%S UTC')}"

            await self.send_with_retry(chat_id=message.chat_id, text=stats_text)

        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await self.send_with_retry(
                chat_id=message.chat_id,
                text="❌ Произошла ошибка при получении статистики"
            )
    
    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подписывает пользователя на уведомления"""
        message = update.message if update.message else update.callback_query.message
        user_id = update.effective_user.id
        
        # Обновляем настройки
        settings = self.get_user_settings(user_id)
        if settings['notifications']:
            text = "❗️ Вы уже подписаны на уведомления"
        else:
            settings['notifications'] = True
            self.user_settings[user_id] = settings
            text = """
✅ Вы успешно подписались на уведомления!

Теперь вы будете получать:
• PUMP/DUMP сигналы
• Важные новости
• Технический анализ

Используйте /settings для настройки параметров
"""
        await self.send_with_retry(chat_id=message.chat_id, text=text)
    
    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отписывает пользователя от уведомлений"""
        message = update.message if update.message else update.callback_query.message
        user_id = update.effective_user.id
        
        settings = self.get_user_settings(user_id)
        if not settings['notifications']:
            text = "❗️ Вы уже отписаны от уведомлений"
        else:
            settings['notifications'] = False
            self.user_settings[user_id] = settings
            text = "✅ Вы успешно отписались от уведомлений"
            
        await self.send_with_retry(chat_id=message.chat_id, text=text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает справку по боту"""
        help_text = """
🤖 Помощь по использованию бота

📊 Основные команды:
/start - Перезапустить бота
/status - Текущий анализ BTC
/stats - Статистика сигналов
/subscribe - Включить уведомления
/unsubscribe - Отключить уведомления 
/settings - Настройки уведомлений
/help - Это сообщение

⚙️ Настройки (/settings):
• Включение/отключение уведомлений
• Минимальная вероятность сигнала
• Выбор типов сигналов (PUMP/DUMP)
• Выбор режима (Swing/Day)

💡 Совет:
Используйте настройки для фильтрации 
сигналов под вашу стратегию

⚠️ Внимание:
Бот использует технический анализ и ML.
Все сигналы носят рекомендательный характер.
Торгуйте с умом и на свой страх и риск!
"""
        await self.send_with_retry(chat_id=update.message.chat_id, text=help_text)
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню настроек"""
        if isinstance(update, Update):
            message = update.message if update.message else update.callback_query.message
            user_id = update.effective_user.id
        else:
            # Если вызвано из callback
            message = update.message
            user_id = update.from_user.id
            
        settings = self.get_user_settings(user_id)
        notifications = "✅" if settings['notifications'] else "❌"
        min_prob = settings['min_probability']
        signal_types = ", ".join(settings['signal_types'])
        mode = settings.get('mode', 'swing').upper()
        
        text = f"""
⚙️ Настройки

🔔 Уведомления: {notifications}
🎯 Мин. вероятность: {min_prob}%
📊 Типы сигналов: {signal_types}
📈 Режим: {mode}

Выберите параметр для изменения:
"""
        
        keyboard = [
            [InlineKeyboardButton(f"🔔 Уведомления ({notifications})", callback_data='toggle_notifications')],
            [InlineKeyboardButton(f"🎯 Мин. вероятность ({min_prob}%)", callback_data='set_threshold')],
            [InlineKeyboardButton("📊 Типы сигналов", callback_data='signal_types')],
            [InlineKeyboardButton(f"📈 Режим ({mode})", callback_data='toggle_mode')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            if isinstance(update, Update):
                await message.reply_text(text, reply_markup=reply_markup)
            else:
                await message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error in settings_command: {e}")
            await message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def handle_toggle_notifications(self, query, user_id):
        """Переключает статус уведомлений"""
        settings = self.get_user_settings(user_id)
        settings['notifications'] = not settings['notifications']
        self.user_settings[user_id] = settings
        
        status = "включены ✅" if settings['notifications'] else "отключены ❌"
        await query.answer(f"Уведомления {status}")
        
        # Обновляем сообщение с настройками
        await self.settings_command(query, None)
    
    async def handle_set_threshold(self, query, user_id):
        """Обработчик изменения минимальной вероятности"""
        settings = self.get_user_settings(user_id)
        
        keyboard = [
            [
                InlineKeyboardButton("60%", callback_data='threshold_60'),
                InlineKeyboardButton("65%", callback_data='threshold_65'),
                InlineKeyboardButton("70%", callback_data='threshold_70'),
            ],
            [
                InlineKeyboardButton("75%", callback_data='threshold_75'),
                InlineKeyboardButton("80%", callback_data='threshold_80'),
                InlineKeyboardButton("85%", callback_data='threshold_85'),
            ],
            [InlineKeyboardButton("« Назад", callback_data='cmd_settings')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📊 Минимальная вероятность сигнала

Текущее значение: {settings['min_probability']}%

Выберите новое значение:
• Ниже = больше сигналов, но меньше точность
• Выше = меньше сигналов, но выше точность

Рекомендуется: 70%
"""
        
        await self.send_with_retry(chat_id=query.message.chat_id, text=text, reply_markup=reply_markup)
        await query.answer()
    
    async def handle_threshold_change(self, query, user_id, value):
        """Обработчик изменения конкретного значения порога"""
        self.update_user_setting(user_id, 'min_probability', value)
        
        await query.answer(f"Минимальная вероятность установлена: {value}%")
        
        # Возвращаемся к настройкам
        await self.settings_command(query, None)
        
    async def handle_signal_types(self, query, user_id):
        """Обработчик выбора типов сигналов"""
        settings = self.get_user_settings(user_id)
        signal_types = settings['signal_types']
        
        keyboard = [
            [
                InlineKeyboardButton(
                    f"🚀 PUMP {'✅' if 'PUMP' in signal_types else '❌'}", 
                    callback_data='toggle_pump'
                ),
            ],
            [
                InlineKeyboardButton(
                    f"📉 DUMP {'✅' if 'DUMP' in signal_types else '❌'}", 
                    callback_data='toggle_dump'
                ),
            ],
            [InlineKeyboardButton("« Назад", callback_data='cmd_settings')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        active_signals = ", ".join(signal_types) if signal_types else "Нет активных"
        
        text = f"""
🎯 Типы сигналов

Активные: {active_signals}

Выберите какие сигналы вы хотите получать:
"""
        
        await query.message.edit_text(text, reply_markup=reply_markup)
        await query.answer()

    async def handle_toggle_signal_type(self, query, user_id, signal_type):
        """Переключает тип сигнала (PUMP/DUMP)"""
        settings = self.get_user_settings(user_id)
        signal_types = settings['signal_types']
        
        if signal_type in signal_types:
            signal_types.remove(signal_type)
            status = "отключен"
        else:
            signal_types.append(signal_type)
            status = "включен"
        
        self.update_user_setting(user_id, 'signal_types', signal_types)
        
        await query.answer(f"{signal_type} сигналы {status}")
        
        # Обновляем меню выбора типов
        await self.handle_signal_types(query, user_id)

    async def handle_toggle_mode(self, query, user_id):
        """Переключает режим анализа между swing и day trading"""
        settings = self.get_user_settings(user_id)
        current_mode = settings.get('mode', 'swing')
        new_mode = 'day' if current_mode == 'swing' else 'swing'
        
        # Обновляем локальную настройку пользователя
        self.update_user_setting(user_id, 'mode', new_mode)
        
        # Обновляем глобальный режим бота (если есть ссылка)
        if self.main_bot:
            try:
                success = self.main_bot.set_trading_mode(new_mode)
                if success:
                    await query.answer(f"✅ Режим изменён: {new_mode.upper()}")
                    logger.info(f"User {user_id} changed mode to {new_mode}")
                else:
                    await query.answer("⚠️ Ошибка изменения режима")
                    logger.error(f"Failed to change mode for user {user_id}")
            except Exception as e:
                logger.error(f"Error changing mode: {e}")
                await query.answer("⚠️ Произошла ошибка")
        else:
            await query.answer(f"Режим: {new_mode.upper()} (только отображение)")
            logger.warning("main_bot not set, mode change is local only")
        
        # Обновляем меню настроек
        await self.settings_command(query, None)
        
    def format_day_trading_message(self, signal_data, market_data):
        """
        Форматирует сообщение для дейтрейдинга с учетом специфики
        """
        day_details = signal_data.get('day_trading_details', {})
        
        # Определяем эмодзи
        signal_emoji = '🚀' if signal_data['signal'] == 'PUMP' else '📉' if signal_data['signal'] == 'DUMP' else '⚡'
        direction = '↗️' if signal_data['signal'] == 'PUMP' else '↘️' if signal_data['signal'] == 'DUMP' else '↔️'
        
        # Сила сигнала (8-10 = HIGH, 6-7 = MEDIUM)
        strength = int(signal_data['probability'] * 10)
        
        message = f"""
{signal_emoji} ИМПУЛЬС | DAY TRADING
━━━━━━━━━━━━━━━━

💰 BTC/USDT
${market_data['current_price']:,.2f} {direction} {market_data['price_change_1h']:+.2f}% (1ч)

🔥 ДЕТЕКЦИЯ:
✅ Изменение за 1ч: {market_data['price_change_1h']:+.2f}%
✅ Объём: {day_details.get('volume_surge', 1.0):.1f}x от среднего
✅ Open Interest: {market_data.get('oi_change_5m', 0):+.2f}% (5м)
✅ Тренд: {day_details.get('trend', 'unknown').upper()}

🎯 СИЛА СИГНАЛА: {strength}/10
⚡ УВЕРЕННОСТЬ: {signal_data['confidence']}

⏱ Актуально: 2-15 минут
⚠️ Быстрая реакция обязательна!
⏰ {datetime.utcnow().strftime('%H:%M:%S UTC')}
"""
        return message

    def format_swing_message(self, signal_data, market_data):
        """
        Форматирует сообщение для свинг-трейдинга
        """
        # Определяем эмодзи
        signal_emoji = '🚀' if signal_data['signal'] == 'PUMP' else '📉' if signal_data['signal'] == 'DUMP' else '🔔'
        direction = '↗️' if signal_data['signal'] == 'PUMP' else '↘️' if signal_data['signal'] == 'DUMP' else '↔️'
        signal_name = 'РОСТ' if signal_data['signal'] == 'PUMP' else 'ПАДЕНИЕ' if signal_data['signal'] == 'DUMP' else 'СИГНАЛ'
        
        # Вычисляем уверенность
        confidence_text = 'ВЫСОКАЯ' if signal_data['confidence'] == 'HIGH' else 'СРЕДНЯЯ' if signal_data['confidence'] == 'MEDIUM' else 'НИЗКАЯ'
        confidence_pct = int(signal_data['probability'] * 100)
        
        return f"""
{signal_emoji} {signal_name} | SWING
━━━━━━━━━━━━━━━━

💰 BTC/USDT
${market_data['current_price']:,.2f} {direction} {market_data.get('price_change_1h', 0):+.2f}% (1ч)

📊 СИГНАЛЫ:
✅ Изменение 1ч: {market_data.get('price_change_1h', 0):+.2f}%
✅ Изменение 4ч: {market_data.get('price_change_4h', 0):+.2f}%
✅ Объём: {market_data.get('volume_change_pct', 0):+.1f}% от среднего
✅ Open Interest: {market_data.get('oi_change_4h', 0):+.2f}% (4ч)

🎯 УВЕРЕННОСТЬ: {confidence_text} ({confidence_pct}%)
⏱ Таймфрейм: 4-24 часа

⚠️ Это анализ, не совет
⏰ {datetime.utcnow().strftime('%H:%M:%S UTC')}
"""

    async def send_signal_notification(self, user_id, signal_data, market_data):
        """
        Отправляет уведомление о сигнале с учетом режима торговли
        
        Args:
            user_id: ID пользователя
            signal_data: dict с данными сигнала
            market_data: dict с рыночными данными
        """
        try:
            # Проверяем настройки пользователя
            settings = self.get_user_settings(user_id)
            
            if not settings.get('notifications', True):
                return
            
            # Проверяем подходит ли сигнал под настройки пользователя
            if signal_data['probability'] * 100 < settings['min_probability']:
                return
                
            if signal_data['signal'] not in settings['signal_types']:
                return
            
            # Форматируем сообщение в зависимости от режима
            mode = settings.get('mode', 'swing')
            if mode == 'day':
                message = self.format_day_trading_message(signal_data, market_data)
            else:
                message = self.format_swing_message(signal_data, market_data)
            
            # Отправляем сообщение с механизмом повторных попыток
            await self.send_with_retry(chat_id=user_id, text=message)
            
        except Exception as e:
            logger.error(f"Error sending signal to user {user_id}: {e}")
    
    async def send_signal_to_users(self, prediction, market_data, indicators):
        """
        Отправляет сигнал всем подписанным пользователям с учётом их настроек
        
        Args:
            prediction: результат ML прогноза
            market_data: данные рынка
            indicators: технические индикаторы
        """
        users = self.db.get_subscribed_users()
        
        if not users:
            logger.info("No subscribed users to send signal")
            return
        
        # Формируем сообщение
        signal_emoji = "🚀" if prediction['signal'] == 'PUMP' else "📉"
        confidence_emoji = "🔥" if prediction['confidence'] == 'HIGH' else "⚡" if prediction['confidence'] == 'MEDIUM' else "💡"
        
        # Определяем направление
        direction = '↗️' if prediction['signal'] == 'PUMP' else '↘️' if prediction['signal'] == 'DUMP' else '↔️'
        signal_name = 'РОСТ' if prediction['signal'] == 'PUMP' else 'ПАДЕНИЕ' if prediction['signal'] == 'DUMP' else 'СИГНАЛ'
        
        message = f"""
{signal_emoji} {signal_name} {confidence_emoji}

💰 BTC/USDT
${market_data['current_price']:,.2f} {direction} {market_data['price_change_1h']:+.2f}% (1ч)

📊 АНАЛИЗ:
✅ Изменение 1ч: {market_data['price_change_1h']:+.2f}%
✅ Изменение 4ч: {market_data['price_change_4h']:+.2f}%
✅ Объём: {'+' if indicators['is_high_volume'] else ''}{(indicators['volume_ratio'] - 1) * 100:.0f}% от среднего
✅ Open Interest: {market_data.get('oi_change_1h', 0):+.2f}% (1ч)

🎯 УВЕРЕННОСТЬ: {prediction['confidence']} ({prediction['probability']:.0%})

⚠️ Это анализ, не совет!
⏰ {datetime.utcnow().strftime('%H:%M:%S UTC')}
"""
        
        # Отправляем пользователям с учётом их настроек (троттлинг и батчинг)
        sem = asyncio.Semaphore(config.TELEGRAM_QPS)  # ограничение сообщений/сек
        tasks = []
        sent_counter = {'count': 0}

        async def _safe_send(uid, txt):
            async with sem:
                try:
                    # Используем механизм повторных попыток
                    await self.send_with_retry(chat_id=uid, text=txt)
                    sent_counter['count'] += 1
                except Exception as e:
                    logger.error(f"Failed to send message to user {uid} after retries: {e}")

        for user_id in users:
            # Проверяем настройки пользователя
            settings = self.get_user_settings(user_id)
            if not settings.get('notifications', True):
                continue
            min_prob = settings.get('min_probability', 70)
            if prediction['probability'] * 100 < min_prob:
                continue
            signal_types = settings.get('signal_types', ['PUMP', 'DUMP'])
            if prediction['signal'] not in signal_types:
                continue

            tasks.append(_safe_send(user_id, message))

        # Выполняем задачами батчами, сглаживая пики с повторными попытками
        batch_size = config.TELEGRAM_BATCH_SIZE
        for i in range(0, len(tasks), batch_size):
            try:
                await asyncio.gather(*tasks[i:i + batch_size])
                if i + batch_size < len(tasks):
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in batch {i//batch_size}: {e}")
        
        logger.info(f"Signal sent to {sent_counter['count']}/{len(users)} users")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на inline кнопки"""
        query = update.callback_query
        user_id = update.effective_user.id
        data = query.data
        
        logger.info(f"Button pressed: {data} by user {user_id}")
        
        try:
            # Команды (вызов функций)
            if data == 'cmd_status':
                await query.answer()
                await self.status_command(query, context)
                
            elif data == 'cmd_subscribe':
                await query.answer()
                await self.subscribe_command(query, context)
                
            elif data == 'cmd_stats':
                await query.answer()
                await self.stats_command(query, context)
                
            elif data == 'cmd_settings':
                await query.answer()
                await self.settings_command(query, context)
            
            # Настройки - переключение уведомлений
            elif data == 'toggle_notifications':
                await self.handle_toggle_notifications(query, user_id)
            
            # Настройки - выбор минимальной вероятности
            elif data == 'set_threshold':
                await self.handle_set_threshold(query, user_id)
            
            # Настройки - установка конкретного значения порога
            elif data.startswith('threshold_'):
                value = int(data.split('_')[1])
                await self.handle_threshold_change(query, user_id, value)
            
            # Настройки - выбор типов сигналов
            elif data == 'signal_types':
                await self.handle_signal_types(query, user_id)
            
            # Настройки - переключение режима анализа
            elif data == 'toggle_mode':
                await self.handle_toggle_mode(query, user_id)
            
            # Настройки - переключение PUMP сигналов
            elif data == 'toggle_pump':
                await self.handle_toggle_signal_type(query, user_id, 'PUMP')
            
            # Настройки - переключение DUMP сигналов
            elif data == 'toggle_dump':
                await self.handle_toggle_signal_type(query, user_id, 'DUMP')
            
            else:
                await query.answer("Неизвестная команда")
                logger.warning(f"Unknown callback data: {data}")
                
        except Exception as e:
            logger.error(f"Error in button_callback: {e}", exc_info=True)
            await query.answer("Произошла ошибка. Попробуйте снова.")

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.app.add_handler(CommandHandler('start', self.start_command))
        self.app.add_handler(CommandHandler('status', self.status_command))
        self.app.add_handler(CommandHandler('stats', self.stats_command))
        self.app.add_handler(CommandHandler('subscribe', self.subscribe_command))
        self.app.add_handler(CommandHandler('unsubscribe', self.unsubscribe_command))
        self.app.add_handler(CommandHandler('settings', self.settings_command))
        self.app.add_handler(CommandHandler('help', self.help_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        
        logger.info("Bot handlers configured")
    
    def run(self):
        """Запускает бота"""
        self.app = Application.builder().token(self.token).build()
        self.setup_handlers()
        
        logger.info("Bot started")
        self.app.run_polling()