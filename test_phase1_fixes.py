"""
Тест для проверки Phase 1 исправлений
Проверяет:
1. Валидацию конфигурации
2. Безопасность доступа к данным в ML модели
3. Обработку исключений API
"""

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config_validation():
    """Тест валидации конфигурации"""
    print("\n=== Test 1: Config Validation ===")
    
    # Сохраняем оригинальные значения
    original_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    original_mode = os.environ.get('TRADING_MODE')
    
    try:
        # Тест 1.1: Проверка что бот не запустится без токена
        print("1.1. Check TELEGRAM_BOT_TOKEN is required...")
        os.environ.pop('TELEGRAM_BOT_TOKEN', None)
        
        try:
            import config
            print("[FAIL] Bot should have raised error without token!")
            return False
        except ValueError as e:
            if "TELEGRAM_BOT_TOKEN" in str(e):
                print("[PASS] Correct error when token is missing")
            else:
                print(f"[FAIL] Unexpected error: {e}")
                return False
        
        # Тест 1.2: Проверка валидации TRADING_MODE
        print("\n1.2. Check TRADING_MODE validation...")
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_123'
        os.environ['TRADING_MODE'] = 'invalid_mode'
        
        # Перезагружаем модуль
        if 'config' in sys.modules:
            del sys.modules['config']
        
        try:
            import config
            print("[FAIL] Should have raised error for invalid TRADING_MODE!")
            return False
        except ValueError as e:
            if "TRADING_MODE" in str(e):
                print("[PASS] Correct TRADING_MODE validation")
            else:
                print(f"[FAIL] Unexpected error: {e}")
                return False
        
        # Тест 1.3: Проверка что валидные значения работают
        print("\n1.3. Check valid values work...")
        os.environ['TRADING_MODE'] = 'swing'
        
        if 'config' in sys.modules:
            del sys.modules['config']
        
        try:
            import config
            print(f"[PASS] Config loaded successfully (mode={config.TRADING_MODE})")
        except Exception as e:
            print(f"[FAIL] Error with valid values: {e}")
            return False
        
        return True
        
    finally:
        # Восстанавливаем оригинальные значения
        if original_token:
            os.environ['TELEGRAM_BOT_TOKEN'] = original_token
        if original_mode:
            os.environ['TRADING_MODE'] = original_mode


def test_ml_model_safety():
    """Тест безопасности ML модели"""
    print("\n\n=== Test 2: ML Model Safety ===")
    
    # Устанавливаем тестовые env vars
    os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_123'
    os.environ['TRADING_MODE'] = 'swing'
    os.environ['USE_ML_MODEL'] = 'false'
    
    # Перезагружаем config
    if 'config' in sys.modules:
        del sys.modules['config']
    
    try:
        from ml_model import MLPredictor
        
        predictor = MLPredictor()
        
        # Тест 2.1: Пустые индикаторы
        print("2.1. Test with empty indicators...")
        try:
            features = predictor.prepare_features({}, {})
            print(f"[PASS] Empty data handled (shape={features.shape})")
        except Exception as e:
            print(f"[FAIL] Error with empty data: {e}")
            return False
        
        # Тест 2.2: Частично заполненные индикаторы
        print("\n2.2. Test with partial data...")
        try:
            indicators = {
                'bb_upper': 50000,
                # Остальные поля отсутствуют
            }
            market_data = {
                'current_volume': 1000
                # Остальные поля отсутствуют
            }
            features = predictor.prepare_features(indicators, market_data)
            print(f"[PASS] Partial data handled (shape={features.shape})")
        except Exception as e:
            print(f"[FAIL] Error with partial data: {e}")
            return False
        
        # Тест 2.3: None значения
        print("\n2.3. Test with None values...")
        try:
            indicators = {
                'bb_upper': None,
                'ema_200': None,
                'vwap': None,
            }
            market_data = {
                'fear_greed': None,
                'current_volume': None,
            }
            features = predictor.prepare_features(indicators, market_data)
            print(f"[PASS] None values handled (shape={features.shape})")
        except Exception as e:
            print(f"[FAIL] Error with None values: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Error initializing ML model: {e}")
        return False


def test_env_file_example():
    """Проверка что .env.example обновлен"""
    print("\n\n=== Test 3: Check .env.example ===")
    
    env_example_path = os.path.join(os.path.dirname(__file__), '.env.example')
    
    if not os.path.exists(env_example_path):
        print("[FAIL] .env.example not found!")
        return False
    
    with open(env_example_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем что нет hardcoded токена
    if '7410301345' in content or 'AAGcXIHsOWuqVypqbtZk5izkPpLdGNU8y8M' in content:
        print("[FAIL] Hardcoded token found in .env.example!")
        return False
    
    # Проверяем наличие обязательных секций
    required_sections = [
        'TELEGRAM_BOT_TOKEN',
        'TRADING_MODE',
        'USE_ML_MODEL',
        'ENVIRONMENT'
    ]
    
    for section in required_sections:
        if section not in content:
            print(f"[FAIL] Missing section {section}")
            return False
    
    print("[PASS] .env.example correctly updated")
    return True


def main():
    """Запуск всех тестов"""
    print("=" * 60)
    print("TESTING PHASE 1 FIXES")
    print("=" * 60)
    
    results = []
    
    # Тест 1: Валидация конфигурации
    results.append(("Config Validation", test_config_validation()))
    
    # Тест 2: Безопасность ML модели
    results.append(("ML Model Safety", test_ml_model_safety()))
    
    # Тест 3: .env.example
    results.append(("Check .env.example", test_env_file_example()))
    
    # Итоги
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")
    
    print("\n" + "=" * 60)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("SUCCESS: ALL TESTS PASSED!")
        return 0
    else:
        print("WARNING: SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())


def test_config_validation():
    """Тест валидации конфигурации"""
    print("\n=== Тест 1: Валидация конфигурации ===")
    
    # Сохраняем оригинальные значения
    original_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    original_mode = os.environ.get('TRADING_MODE')
    
    try:
        # Тест 1.1: Проверка что бот не запустится без токена
        print("1.1. Проверка обязательности TELEGRAM_BOT_TOKEN...")
        os.environ.pop('TELEGRAM_BOT_TOKEN', None)
        
        try:
            import config
            print("❌ FAIL: Бот должен был выдать ошибку без токена!")
            return False
        except ValueError as e:
            if "TELEGRAM_BOT_TOKEN" in str(e):
                print("✅ PASS: Правильная ошибка при отсутствии токена")
            else:
                print(f"❌ FAIL: Неожиданная ошибка: {e}")
                return False
        
        # Тест 1.2: Проверка валидации TRADING_MODE
        print("\n1.2. Проверка валидации TRADING_MODE...")
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_123'
        os.environ['TRADING_MODE'] = 'invalid_mode'
        
        # Перезагружаем модуль
        if 'config' in sys.modules:
            del sys.modules['config']
        
        try:
            import config
            print("❌ FAIL: Должна была быть ошибка для неверного TRADING_MODE!")
            return False
        except ValueError as e:
            if "TRADING_MODE" in str(e):
                print("✅ PASS: Правильная валидация TRADING_MODE")
            else:
                print(f"❌ FAIL: Неожиданная ошибка: {e}")
                return False
        
        # Тест 1.3: Проверка что валидные значения работают
        print("\n1.3. Проверка валидных значений...")
        os.environ['TRADING_MODE'] = 'swing'
        
        if 'config' in sys.modules:
            del sys.modules['config']
        
        try:
            import config
            print(f"✅ PASS: Конфигурация загружена успешно (mode={config.TRADING_MODE})")
        except Exception as e:
            print(f"❌ FAIL: Ошибка при валидных значениях: {e}")
            return False
        
        return True
        
    finally:
        # Восстанавливаем оригинальные значения
        if original_token:
            os.environ['TELEGRAM_BOT_TOKEN'] = original_token
        if original_mode:
            os.environ['TRADING_MODE'] = original_mode


def test_ml_model_safety():
    """Тест безопасности ML модели"""
    print("\n\n=== Тест 2: Безопасность ML модели ===")
    
    # Устанавливаем тестовые env vars
    os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_123'
    os.environ['TRADING_MODE'] = 'swing'
    os.environ['USE_ML_MODEL'] = 'false'
    
    # Перезагружаем config
    if 'config' in sys.modules:
        del sys.modules['config']
    
    try:
        from ml_model import MLPredictor
        
        predictor = MLPredictor()
        
        # Тест 2.1: Пустые индикаторы
        print("2.1. Тест с пустыми индикаторами...")
        try:
            features = predictor.prepare_features({}, {})
            print(f"✅ PASS: Обработка пустых данных (shape={features.shape})")
        except Exception as e:
            print(f"❌ FAIL: Ошибка при пустых данных: {e}")
            return False
        
        # Тест 2.2: Частично заполненные индикаторы
        print("\n2.2. Тест с частичными данными...")
        try:
            indicators = {
                'bb_upper': 50000,
                # Остальные поля отсутствуют
            }
            market_data = {
                'current_volume': 1000
                # Остальные поля отсутствуют
            }
            features = predictor.prepare_features(indicators, market_data)
            print(f"✅ PASS: Обработка частичных данных (shape={features.shape})")
        except Exception as e:
            print(f"❌ FAIL: Ошибка при частичных данных: {e}")
            return False
        
        # Тест 2.3: None значения
        print("\n2.3. Тест с None значениями...")
        try:
            indicators = {
                'bb_upper': None,
                'ema_200': None,
                'vwap': None,
            }
            market_data = {
                'fear_greed': None,
                'current_volume': None,
            }
            features = predictor.prepare_features(indicators, market_data)
            print(f"✅ PASS: Обработка None значений (shape={features.shape})")
        except Exception as e:
            print(f"❌ FAIL: Ошибка при None значениях: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Ошибка инициализации ML модели: {e}")
        return False


def test_env_file_example():
    """Проверка что .env.example обновлен"""
    print("\n\n=== Тест 3: Проверка .env.example ===")
    
    env_example_path = os.path.join(os.path.dirname(__file__), '.env.example')
    
    if not os.path.exists(env_example_path):
        print("❌ FAIL: .env.example не найден!")
        return False
    
    with open(env_example_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем что нет hardcoded токена
    if '7410301345' in content or 'AAGcXIHsOWuqVypqbtZk5izkPpLdGNU8y8M' in content:
        print("❌ FAIL: В .env.example найден hardcoded токен!")
        return False
    
    # Проверяем наличие обязательных секций
    required_sections = [
        'TELEGRAM_BOT_TOKEN',
        'TRADING_MODE',
        'USE_ML_MODEL',
        'ENVIRONMENT'
    ]
    
    for section in required_sections:
        if section not in content:
            print(f"❌ FAIL: Отсутствует секция {section}")
            return False
    
    print("✅ PASS: .env.example корректно обновлен")
    return True


def main():
    """Запуск всех тестов"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ PHASE 1 ИСПРАВЛЕНИЙ")
    print("=" * 60)
    
    results = []
    
    # Тест 1: Валидация конфигурации
    results.append(("Валидация конфигурации", test_config_validation()))
    
    # Тест 2: Безопасность ML модели
    results.append(("Безопасность ML модели", test_ml_model_safety()))
    
    # Тест 3: .env.example
    results.append(("Проверка .env.example", test_env_file_example()))
    
    # Итоги
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "=" * 60)
    print(f"Пройдено: {passed}/{total}")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        return 1


if __name__ == '__main__':
    sys.exit(main())
