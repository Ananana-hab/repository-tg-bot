"""
Telegram Bot Integration Patch
Apply this patch to telegram_bot.py to enable performance metrics
"""

# Add to imports at the top of telegram_bot.py (after line 7):
# from telegram_commands_enhanced import stats_command_enhanced, performance_command

# Replace the stats_command method (lines 185-231) with:
# stats_command = stats_command_enhanced

#  Add new command handler in setup_handlers method (after line 742):
# self.app.add_handler(CommandHandler('performance', performance_command))

# Update help command text (line 112) to include:
# /performance - Детальная статистика

# Update start command welcome text (line 112) to include:
# /performance - Детальный анализ производительности


print("""
To integrate performance metrics into Telegram bot:

1. Open d:\\btc_pump_dump_bot\\repository-tg-bot\\telegram_bot.py

2. Add import at top (after line 7):
   from telegram_commands_enhanced import stats_command_enhanced, performance_command

3. Replace stats_command method with enhanced version (line 185):
   # Comment out or delete lines 185-231
   # Then add:
   stats_command = stats_command_enhanced

4. Add performance_command to the class:
   performance_command = performance_command

5. Update setup_handlers (around line 746):
   self.app.add_handler(CommandHandler('performance', performance_command))

6. Update help text (line 282) to include:
   /performance - Детальный анализ

Alternatively, run the automated integration script:
   python integrate_telegram_metrics.py
""")
