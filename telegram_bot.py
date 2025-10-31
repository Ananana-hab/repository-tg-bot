from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import config
import logging
from database import Database
from datetime import datetime

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.db = Database()
        self.app = None
        
        # Хранилище пользовательских настроек (временно в памяти)
        self.user_settings = {}
        
    def get_user_settings(self, user_id):
        """Получает настройки пользователя или создаёт дефолтные"""
        if user_id not in self.user_settings:
            self.user_settings[user_id] = {
                'notifications': True,
                'min_probability': 70,
                'signal_types': ['PUMP', 'DUMP']  # Какие сигналы показывать
            }
        return self.user_settings[user_id]
    
    def update_user_setting(self, user_id, key, value):
        """Обновляет настройку пользователя"""
        settings = self.get_user_settings(user_id)
        settings[key] = value
        self.user_settings[user_id] = settings
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Сохраняем пользователя в БД
        self.db.add_user(user.id, user.username, user.first_name)
        
        welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот для анализа Bitcoin и прогнозирования PUMP/DUMP движений.

🤖 Что я умею:
- Анализировать BTC в режиме реального времени
- Рассчитывать вероятность роста/падения
- Отправлять сигналы с высокой точностью
- Показывать технические индикаторы

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
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status - показывает текущий анализ"""
        message = update.message if update.message else update.callback_query.message
        
        await message.reply_text("🔄 Анализирую рынок, подождите...")
        
        # TODO: Здесь будет вызов реального анализа из main.py
        status_text = f"""
📊 BTC/USDT Анализ

💰 Цена: $107,450
📈 Изменение 1h: +0.5%
📊 Изменение 4h: +1.2%

🔍 Индикаторы:
- RSI (14): 68 📈
- MACD: Бычий тренд
- Bollinger: Внутри диапазона
- Объём: +25% выше среднего

🎯 Прогноз: NEUTRAL
Вероятность: 55%
Confidence: LOW

⏰ Обновлено: {datetime.now().strftime('%H:%M:%S UTC')}
"""
        
        keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data='cmd_status')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(status_text, reply_markup=reply_markup)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику точности сигналов"""
        message = update.message if update.message else update.callback_query.message
        
        accuracy = self.db.get_signal_accuracy(days=7)
        
        if not accuracy:
            stats_text = """
📊 Статистика за последние 7 дней

Пока недостаточно данных для расчёта точности.
Бот только начал работу! 🚀

Подпишись на сигналы: /subscribe
"""
        else:
            pump_acc = accuracy.get('PUMP', 0)
            dump_acc = accuracy.get('DUMP', 0)
            
            stats_text = f"""
📊 Статистика за последние 7 дней

🚀 PUMP сигналы: {pump_acc:.1f}% точность
📉 DUMP сигналы: {dump_acc:.1f}% точность

Общая точность: {(pump_acc + dump_acc) / 2:.1f}%

⏰ Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
        
        keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data='cmd_stats')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(stats_text, reply_markup=reply_markup)
    
    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подписка на уведомления"""
        message = update.message if hasattr(update, 'message') and update.message else update.callback_query.message
        user_id = update.effective_user.id if hasattr(update, 'effective_user') and update.effective_user else update.from_user.id
        
        self.db.update_subscription(user_id, True)
        self.update_user_setting(user_id, 'notifications', True)
        
        await message.reply_text(
            "✅ Вы подписаны на сигналы!\n\n"
            "Вы будете получать уведомления когда:\n"
            "• Обнаружен сильный сигнал PUMP/DUMP\n"
            "• Вероятность выше 70%\n"
            "• Confidence уровень HIGH или MEDIUM\n\n"
            "Используйте /unsubscribe чтобы отписаться.\n"
            "Настройте параметры: /settings"
        )
    
    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отписка от уведомлений"""
        message = update.message if hasattr(update, 'message') and update.message else update.callback_query.message
        user_id = update.effective_user.id if hasattr(update, 'effective_user') and update.effective_user else update.from_user.id
        
        self.db.update_subscription(user_id, False)
        self.update_user_setting(user_id, 'notifications', False)
        
        await message.reply_text(
            "❌ Вы отписались от сигналов.\n\n"
            "Используйте /subscribe чтобы подписаться снова."
        )
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Настройки пользователя"""
        message = update.message if hasattr(update, 'message') and update.message else update.callback_query.message
        user_id = update.effective_user.id if hasattr(update, 'effective_user') and update.effective_user else update.from_user.id
        
        settings = self.get_user_settings(user_id)
        
        notif_status = "ВКЛ ✅" if settings['notifications'] else "ВЫКЛ ❌"
        signal_types_text = ", ".join(settings['signal_types']) if settings['signal_types'] else "Нет"
        
        settings_text = f"""
⚙️ Настройки бота

🔔 Уведомления: {notif_status}
📊 Минимальная вероятность: {settings['min_probability']}%
🎯 Типы сигналов: {signal_types_text}

Нажмите на кнопку чтобы изменить:
"""
        
        keyboard = [
            [InlineKeyboardButton(f"🔔 Уведомления: {notif_status}", callback_data='toggle_notifications')],
            [InlineKeyboardButton(f"📊 Мин. вероятность: {settings['min_probability']}%", callback_data='set_threshold')],
            [InlineKeyboardButton(f"🎯 Типы сигналов: {signal_types_text}", callback_data='signal_types')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(settings_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Помощь и информация"""
        help_text = """
❓ Помощь по боту

📊 Что означают сигналы:

🚀 PUMP - Прогноз роста цены
- HIGH confidence: 80%+ вероятность
- MEDIUM confidence: 65-80% вероятность
- LOW confidence: менее 65%

📉 DUMP - Прогноз падения цены
- Аналогично PUMP сигналам

⚪️ NEUTRAL - Нет четкого тренда
- Боковое движение или неопределённость

🔍 Индикаторы:
- RSI - индекс относительной силы
- MACD - схождение/расхождение средних
- Bollinger Bands - полосы Боллинджера
- Volume - анализ объёмов
- Fear & Greed - индекс страха и жадности

⚠️ Важно:
- Это не финансовый совет
- Всегда проводите свой анализ
- Используйте стоп-лоссы
- Не вкладывайте больше, чем можете потерять

📞 Контакты:
Если нашли баг или есть предложения - напишите разработчику.
"""
        
        await update.message.reply_text(help_text)
    
    async def handle_toggle_notifications(self, query, user_id):
        """Обработчик переключения уведомлений"""
        settings = self.get_user_settings(user_id)
        settings['notifications'] = not settings['notifications']
        
        # Обновляем в БД
        self.db.update_subscription(user_id, settings['notifications'])
        
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
- Ниже = больше сигналов, но меньше точность
- Выше = меньше сигналов, но выше точность

Рекомендуется: 70%
"""
        
        await query.message.edit_text(text, reply_markup=reply_markup)
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
        
        message = f"""
{signal_emoji} {prediction['signal']} SIGNAL {confidence_emoji}

BTC/USDT
💰 Цена: ${market_data['current_price']:,.2f}
📊 Изменение 1h: {market_data['price_change_1h']:+.2f}%
📈 Изменение 4h: {market_data['price_change_4h']:+.2f}%

🎯 Вероятность: {prediction['probability']:.0%}
🎚️ Confidence: {prediction['confidence']}

🔍 Индикаторы:
- RSI: {indicators['rsi']:.1f} {'📈' if indicators['rsi'] > 50 else '📉'}
- MACD: {indicators['macd_crossover']}
- Volume: {'+' if indicators['is_high_volume'] else ''}{(indicators['volume_ratio'] - 1) * 100:.0f}% от среднего
- Fear & Greed: {market_data.get('fear_greed', 'N/A')}

⏰ {datetime.now().strftime('%H:%M:%S UTC')}

⚠️ Это не финансовый совет!
"""
        
        # Отправляем пользователям с учётом их настроек
        sent_count = 0
        for user_id in users:
            try:
                # Проверяем настройки пользователя
                settings = self.get_user_settings(user_id)
                
                # Пропускаем если уведомления выключены
                if not settings.get('notifications', True):
                    continue
                
                # Пропускаем если вероятность ниже порога
                min_prob = settings.get('min_probability', 70)
                if prediction['probability'] * 100 < min_prob:
                    continue
                
                # Пропускаем если тип сигнала не выбран
                signal_types = settings.get('signal_types', ['PUMP', 'DUMP'])
                if prediction['signal'] not in signal_types:
                    continue
                
                await self.app.bot.send_message(chat_id=user_id, text=message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
        
        logger.info(f"Signal sent to {sent_count}/{len(users)} users")
        
        # Сохраняем сигнал в БД
        self.db.save_signal(
            prediction['signal'],
            prediction['probability'],
            market_data['current_price'],
            prediction['confidence']
        )
    
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