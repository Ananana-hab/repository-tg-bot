#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Утилита для очистки Telegram webhook и решения конфликтов"""

import requests
import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_webhook():
    """Удаляет webhook из Telegram"""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/deleteWebhook"
    params = {
        'drop_pending_updates': True  # Удаляет все pending updates
    }
    
    logger.info("Clearing Telegram webhook...")
    response = requests.post(url, params=params)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            logger.info("OK: Webhook cleared successfully")
            return True
        else:
            logger.error(f"ERROR: Failed to clear webhook: {result}")
            return False
    else:
        logger.error(f"ERROR: HTTP error: {response.status_code}")
        return False

def get_webhook_info():
    """Получает информацию о текущем webhook"""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    
    logger.info("Getting webhook info...")
    response = requests.get(url)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            info = result.get('result', {})
            logger.info(f"Webhook URL: {info.get('url', 'None')}")
            logger.info(f"Pending updates: {info.get('pending_update_count', 0)}")
            logger.info(f"Last error: {info.get('last_error_message', 'None')}")
            return info
    
    return None

def get_me():
    """Проверяет работу бота"""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getMe"
    
    logger.info("Checking bot status...")
    response = requests.get(url)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            bot_info = result.get('result', {})
            logger.info(f"OK: Bot active: @{bot_info.get('username')}")
            logger.info(f"   Name: {bot_info.get('first_name')}")
            logger.info(f"   ID: {bot_info.get('id')}")
            return True
    
    logger.error("ERROR: Bot not accessible")
    return False

def main():
    print("=" * 60)
    print("TELEGRAM BOT CLEANER")
    print("=" * 60)
    
    # Шаг 1: Проверка бота
    print("\n[1/3] Checking bot status...")
    if not get_me():
        print("ERROR: Cannot access bot. Check your token in config.py")
        return
    
    # Шаг 2: Информация о webhook
    print("\n[2/3] Getting webhook info...")
    webhook_info = get_webhook_info()
    
    # Шаг 3: Очистка webhook
    print("\n[3/3] Clearing webhook...")
    if clear_webhook():
        print("\n" + "=" * 60)
        print("SUCCESS! You can now run the bot.")
        print("=" * 60)
        print("\nRun: python main.py")
    else:
        print("\n" + "=" * 60)
        print("FAILED! Check the logs above.")
        print("=" * 60)

if __name__ == "__main__":
    main()
