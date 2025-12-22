"""
Automated Telegram Bot Integration Script
Integrates performance metrics into telegram_bot.py
"""
import re


def integrate_performance_metrics():
    """Автоматически интегрирует performance metrics в telegram_bot.py"""
    
    telegram_bot_path = "d:\\btc_pump_dump_bot\\repository-tg-bot\\telegram_bot.py"
    
    print("Reading telegram_bot.py...")
    
    try:
        with open(telegram_bot_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Backup original file
        with open(telegram_bot_path + ".backup", 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Backup created: telegram_bot.py.backup")
        
        # 1. Add import
        if "from telegram_commands_enhanced import" not in content:
            import_line = "from telegram_commands_enhanced import stats_command_enhanced, performance_command\n"
            content = content.replace(
                "import asyncio\r\n",
                f"import asyncio\r\n{import_line}"
            )
            print("✅ Added enhanced commands import")
        
        # 2. Replace stats_command method
        # Find the method and replace it
        stats_pattern = r"    async def stats_command\(self.*?\n(?:.*?\n)*?            \)\r?\n"
        if re.search(stats_pattern, content):
            content = re.sub(
                stats_pattern,
                "    # Enhanced stats command from telegram_commands_enhanced.py\n    stats_command = stats_command_enhanced\n",
                content,
                count=1
            )
            print("✅ Replaced stats_command method")
        
        # 3. Add performance_command reference in class
        if "performance_command = performance_command" not in content:
            # Add after stats_command
            content = content.replace(
                "    stats_command = stats_command_enhanced\n",
                "    stats_command = stats_command_enhanced\n    performance_command = performance_command\n"
            )
            print("✅ Added performance_command reference")
        
        # 4. Add handler in setup_handlers
        if "CommandHandler('performance'" not in content:
            content = content.replace(
                "self.app.add_handler(CommandHandler('help', self.help_command))",
                "self.app.add_handler(CommandHandler('help', self.help_command))\n        self.app.add_handler(CommandHandler('performance', self.performance_command))"
            )
            print("✅ Added performance command handler")
        
        # 5. Update help text
        if "/performance" not in content:
            content = content.replace(
                "/help - Помощь",
                "/performance - Детальный анализ\\n/help - Помощь"
            )
            print("✅ Updated help text")
        
        # Write updated content
        with open(telegram_bot_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("\n" + "=" * 70)
        print("✅ INTEGRATION COMPLETE!")
        print("=" * 70)
        print("\nUpdated telegram_bot.py with:")
        print("  • Enhanced /stats command with performance metrics")
        print("  • New /performance command for detailed analysis")
        print("\nTo test:")
        print("  1. Restart the bot")
        print("  2. Send /stats to see enhanced statistics")
        print("  3. Send /performance for detailed analysis")
        print("\nOriginal file backed up to: telegram_bot.py.backup")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ File not found: {telegram_bot_path}")
        print("Make sure the bot is in the correct directory")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    print("=" * 70)
    print("TELEGRAM BOT PERFORMANCE METRICS INTEGRATION")
    print("=" * 70)
    print()
    
    success = integrate_performance_metrics()
    
    if not success:
        print("\n⚠️ Integration failed. Please integrate manually using:")
        print("telegram_integration_readme.py")
