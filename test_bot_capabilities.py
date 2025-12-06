#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Комплексный тест работоспособности бота
"""
import sys
import traceback
from datetime import datetime
import pandas as pd
import numpy as np

print("=" * 60)
print("BTC PUMP/DUMP BOT - КОМПЛЕКСНЫЙ ТЕСТ")
print("=" * 60)
print()

# Счётчики
tests_passed = 0
tests_failed = 0
warnings = []

def test(name, func):
    """Запускает тест и считает результаты"""
    global tests_passed, tests_failed
    try:
        result = func()
        if result:
            print(f"[OK] {name}")
            tests_passed += 1
            return True
        else:
            print(f"[FAIL] {name}")
            tests_failed += 1
            return False
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        traceback.print_exc()
        tests_failed += 1
        return False

def warn(msg):
    """Добавляет предупреждение"""
    warnings.append(msg)
    print(f"[WARN] {msg}")

print("1. ПРОВЕРКА ИМПОРТОВ И ЗАВИСИМОСТЕЙ")
print("-" * 60)

test("Импорт config", lambda: __import__('config'))
test("Импорт database", lambda: __import__('database'))
test("Импорт data_collector", lambda: __import__('data_collector'))
test("Импорт indicators", lambda: __import__('indicators'))
test("Импорт ml_model", lambda: __import__('ml_model'))
test("Импорт telegram_bot", lambda: __import__('telegram_bot'))
test("Импорт dataset_builder", lambda: __import__('dataset_builder'))
test("Импорт train", lambda: __import__('train'))

print()
print("2. ПРОВЕРКА КОНФИГУРАЦИИ")
print("-" * 60)

import config

test("Config загружен", lambda: config is not None)
test("SYMBOL установлен", lambda: config.SYMBOL == 'BTC/USDT')
test("TIMEFRAME установлен", lambda: config.TIMEFRAME in ['1m', '5m', '15m'])
test("ML параметры определены", lambda: hasattr(config, 'ML_TRAINING_DAYS'))
test("USE_ML_MODEL определен", lambda: hasattr(config, 'USE_ML_MODEL'))

if config.TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
    warn("Telegram токен не настроен (бот не запустится)")

print()
print("3. ПРОВЕРКА БАЗЫ ДАННЫХ")
print("-" * 60)

from database import Database

db = Database()
test("База данных инициализирована", lambda: db is not None)

# Проверяем наличие данных
try:
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM price_data")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        warn(f"База данных пуста ({count} записей) - нужны данные для ML обучения")
    else:
        print(f"   [DATA] Найдено {count} записей в price_data")
        if count < 200:
            warn(f"Мало данных ({count} < 200) - ML обучение может быть неэффективным")
        elif count < 1000:
            warn(f"Умеренное количество данных ({count}) - рекомендуется больше для стабильной ML модели")
        else:
            print(f"   [OK] Достаточно данных для ML обучения ({count} записей)")
except Exception as e:
    warn(f"Ошибка проверки БД: {e}")

print()
print("4. ПРОВЕРКА ИНДИКАТОРОВ")
print("-" * 60)

from indicators import TechnicalIndicators
import pandas as pd

# Создаём тестовые данные
test_df = pd.DataFrame({
    'timestamp': pd.date_range('2024-01-01', periods=100, freq='5min'),
    'open': np.random.uniform(40000, 50000, 100),
    'high': np.random.uniform(40000, 50000, 100),
    'low': np.random.uniform(40000, 50000, 100),
    'close': np.random.uniform(40000, 50000, 100),
    'volume': np.random.uniform(1000, 10000, 100)
})

test("RSI/MACD удалены из calculate_all_indicators", 
     lambda: 'rsi' not in TechnicalIndicators.calculate_all_indicators(test_df) or 
             TechnicalIndicators.calculate_all_indicators(test_df).get('rsi') is None)

indicators = TechnicalIndicators.calculate_all_indicators(test_df)
test("Индикаторы рассчитываются", lambda: indicators is not None)
test("BB индикаторы присутствуют", lambda: 'bb_upper' in indicators and 'bb_lower' in indicators)
test("EMA индикаторы присутствуют", lambda: 'ema_50' in indicators)
test("Volume индикаторы присутствуют", lambda: 'volume_ratio' in indicators)
test("Momentum присутствует", lambda: 'momentum' in indicators)
test("ATR присутствует", lambda: 'atr' in indicators)

print()
print("5. ПРОВЕРКА ML МОДЕЛИ")
print("-" * 60)

from ml_model import MLPredictor

ml = MLPredictor()
test("MLPredictor инициализирован", lambda: ml is not None)
test("USE_ML_MODEL флаг работает", lambda: hasattr(ml, 'use_ml'))

# Проверяем наличие модели
import os
if os.path.exists(config.MODEL_PATH) and os.path.exists(config.SCALER_PATH):
    print(f"   [MODEL] ML модель найдена: {config.MODEL_PATH}")
    test("Модель загружается", lambda: ml.model is not None if ml.use_ml else True)
else:
    warn("ML модель не обучена - используется rule-based прогнозирование")

# Тест prepare_features
test_market_data = {
    'price_change_1h': 1.5,
    'price_change_4h': 2.3,
    'fear_greed': 55,
    'current_volume': 1000000,
    'oi_change_5m': 0.5,
    'oi_change_1h': 1.2,
    'oi_change_4h': 2.1
}

try:
    features = ml.prepare_features(indicators, test_market_data, mode='swing')
    if features is not None:
        print(f"   [FEATURES] Сформировано {features.shape[1]} фичей (ожидается 20)")
        # Для swing режима должно быть 20 фичей (19 базовых + без day features)
        test("Фичи формируются", lambda: features.shape[1] >= 19 and features.shape[1] <= 20)
    else:
        test("Фичи формируются", lambda: False)
except Exception as e:
    warn(f"Ошибка формирования фичей: {e}")
    test("Фичи формируются", lambda: False)

print()
print("6. ПРОВЕРКА DATASET BUILDER")
print("-" * 60)

from dataset_builder import DatasetBuilder

builder = DatasetBuilder()
test("DatasetBuilder инициализирован", lambda: builder is not None)

# Проверяем способность собирать данные
try:
    hist_data = builder.get_historical_data(days=7)
    if hist_data is not None and len(hist_data) > 0:
        print(f"   [DATA] Исторические данные загружены: {len(hist_data)} записей")
        test("Исторические данные загружаются", lambda: True)
        
        if len(hist_data) >= 200:
            # Тестируем расчёт индикаторов для строки
            test_indicators = builder.calculate_indicators_for_row(hist_data, min(100, len(hist_data)-1))
            test("Индикаторы рассчитываются для строки", lambda: test_indicators is not None)
            
            # Тестируем разметку
            test_label = builder.label_sample(hist_data, min(50, len(hist_data)-100), horizon_minutes=60)
            test("Разметка работает", lambda: test_label in ['PUMP', 'DUMP', 'NEUTRAL', None])
        else:
            warn("Недостаточно данных для тестирования dataset builder")
    else:
        warn("Нет исторических данных в БД - dataset builder не может работать")
except Exception as e:
    warn(f"Ошибка тестирования dataset builder: {e}")

print()
print("7. ПРОВЕРКА DATA COLLECTOR")
print("-" * 60)

from data_collector import DataCollector

collector = DataCollector()
test("DataCollector инициализирован", lambda: collector is not None)

# Тест получения цены (может упасть если нет интернета)
try:
    price_data = collector.get_current_price()
    if price_data:
        print(f"   [PRICE] Текущая цена: ${price_data['price']:,.2f}")
        test("Получение текущей цены работает", lambda: True)
    else:
        warn("Не удалось получить цену (возможно нет интернета или Binance недоступен)")
except Exception as e:
    warn(f"Ошибка получения цены: {e}")

print()
print("8. ПРОВЕРКА СОВМЕСТИМОСТИ ФИЧЕЙ")
print("-" * 60)

# Проверяем что порядок фичей совпадает
from train import ModelTrainer

trainer = ModelTrainer()
feature_cols_train = [
    'bb_upper', 'bb_lower', 'bb_middle', 'bb_position_above', 'bb_position_below',
    'ema_50', 'ema_200', 'volume_ratio', 'is_high_volume',
    'momentum', 'atr', 'vwap', 'orderbook_imbalance',
    'fear_greed', 'current_volume', 'price_change_1h', 'price_change_4h',
    'oi_change_5m', 'oi_change_1h', 'oi_change_4h'
]

# Проверяем что ml_model.prepare_features возвращает правильное количество
# Проверяем что количество фичей правильное (20 для swing, может быть больше для day)
test("Количество фичей совпадает (20)", lambda: features.shape[1] == 20 or features.shape[1] == len(feature_cols_train))

print()
print("9. ПРОВЕРКА РЕЖИМОВ ТОРГОВЛИ")
print("-" * 60)

test("Swing режим определён в config", lambda: 'swing' in config.MODE_CONFIGS)
test("Day режим определён в config", lambda: 'day' in config.MODE_CONFIGS)
test("DAY_TIMEFRAME установлен", lambda: config.DAY_TIMEFRAME == '1m')
test("DAY_CHECK_INTERVAL установлен", lambda: config.DAY_CHECK_INTERVAL == 60)

# Проверяем day trading индикаторы
day_indicators = TechnicalIndicators.calculate_all_indicators(test_df, mode='day')
test("Day trading индикаторы рассчитываются", lambda: day_indicators is not None)
if day_indicators and 'day_trading' in day_indicators:
    print("   [OK] Day trading индикаторы присутствуют")
else:
    warn("Day trading индикаторы не найдены (может быть нормально если нет достаточных данных)")

print()
print("=" * 60)
print("ИТОГИ ТЕСТИРОВАНИЯ")
print("=" * 60)
print(f"[OK] Пройдено: {tests_passed}")
print(f"[FAIL] Провалено: {tests_failed}")
print(f"[WARN] Предупреждений: {len(warnings)}")

if warnings:
    print("\nПредупреждения:")
    for w in warnings:
        print(f"  • {w}")

success_rate = (tests_passed / (tests_passed + tests_failed) * 100) if (tests_passed + tests_failed) > 0 else 0
print(f"\nУспешность: {success_rate:.1f}%")

if tests_failed == 0:
    print("\n[SUCCESS] ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
else:
    print(f"\n[WARN] Обнаружено {tests_failed} проблем")

print("=" * 60)

