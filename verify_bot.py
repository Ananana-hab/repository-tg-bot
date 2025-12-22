"""
Comprehensive Bot Verification Script
"""
import sys
sys.path.insert(0, '.')

print("=" * 70)
print("COMPREHENSIVE BOT VERIFICATION")
print("=" * 70)

errors = []
warnings = []

# Test 1: Syntax Check
print("\n1. SYNTAX CHECKS")
print("-" * 70)
files_to_check = [
    'config.py',
    'database.py',
    'indicators.py',
    'data_collector.py',
    'ml_model.py',
    'telegram_bot.py',
    'main.py',
    'data_collection_service.py',
    'feature_engineering.py'
]

import py_compile
for file in files_to_check:
    try:
        py_compile.compile(file, doraise=True)
        print(f"   [OK] {file}")
    except Exception as e:
        errors.append(f"Syntax error in {file}: {e}")
        print(f"   [ERROR] {file}: {e}")

# Test 2: Import Check
print("\n2. IMPORT CHECKS")
print("-" * 70)
try:
    import config
    print("   [OK] config")
except Exception as e:
    errors.append(f"Import error config: {e}")
    print(f"   [ERROR] config: {e}")

try:
    from database import Database
    print("   [OK] database.Database")
except Exception as e:
    errors.append(f"Import error Database: {e}")
    print(f"   [ERROR] database: {e}")

try:
    from indicators import TechnicalIndicators
    print("   [OK] indicators.TechnicalIndicators")
except Exception as e:
    errors.append(f"Import error TechnicalIndicators: {e}")
    print(f"   [ERROR] indicators: {e}")

try:
    from data_collector import DataCollector
    print("   [OK] data_collector.DataCollector")
except Exception as e:
    errors.append(f"Import error DataCollector: {e}")
    print(f"   [ERROR] data_collector: {e}")

try:
    from ml_model import MLPredictor
    print("   [OK] ml_model.MLPredictor")
except Exception as e:
    errors.append(f"Import error MLPredictor: {e}")
    print(f"   [ERROR] ml_model: {e}")

try:
    from telegram_bot import TelegramBot
    print("   [OK] telegram_bot.TelegramBot")
except Exception as e:
    errors.append(f"Import error TelegramBot: {e}")
    print(f"   [ERROR] telegram_bot: {e}")

try:
    from feature_engineering import FeatureEngineer
    print("   [OK] feature_engineering.FeatureEngineer")
except Exception as e:
    errors.append(f"Import error FeatureEngineer: {e}")
    print(f"   [ERROR] feature_engineering: {e}")

# Test 3: Configuration Check
print("\n3. CONFIGURATION CHECKS")
print("-" * 70)
try:
    import config
    print(f"   Trading Mode: {config.TRADING_MODE}")
    print(f"   Use ML Model: {config.USE_ML_MODEL}")
    print(f"   Pump Threshold: {config.PUMP_THRESHOLD}")
    print(f"   Dump Threshold: {config.DUMP_THRESHOLD}")
    print(f"   Check Interval: {config.CHECK_INTERVAL}s")
    
    # Check new indicator params exist
    if hasattr(config, 'RSI_PERIOD'):
        print(f"   RSI Period: {config.RSI_PERIOD}")
    else:
        warnings.append("RSI_PERIOD not in config (using defaults)")
        print("   [WARNING] RSI_PERIOD not defined (will use defaults)")
    
    print("   [OK] Configuration loaded")
except Exception as e:
    errors.append(f"Config error: {e}")
    print(f"   [ERROR] {e}")

# Test 4: Database Check
print("\n4. DATABASE CHECKS")
print("-" * 70)
try:
    from database import Database
    db = Database()
    
    # Check tables exist
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    required_tables = ['price_data', 'signals', 'users', 'market_snapshots']
    for table in required_tables:
        if table in tables:
            print(f"   [OK] Table '{table}' exists")
        else:
            errors.append(f"Missing table: {table}")
            print(f"   [ERROR] Table '{table}' missing")
    
    # Check user settings methods
    try:
        settings = db.get_user_settings(123456)
        print(f"   [OK] get_user_settings() works")
    except Exception as e:
        errors.append(f"get_user_settings error: {e}")
        print(f"   [ERROR] get_user_settings: {e}")
    
except Exception as e:
    errors.append(f"Database error: {e}")
    print(f"   [ERROR] {e}")

# Test 5: Indicators Check
print("\n5. INDICATORS CHECKS")
print("-" * 70)
try:
    import pandas as pd
    import numpy as np
    from indicators import TechnicalIndicators
    
    # Create test data
    test_df = pd.DataFrame({
        'high': np.random.uniform(90000, 100000, 100),
        'low': np.random.uniform(85000, 95000, 100),
        'close': np.random.uniform(87000, 98000, 100),
        'volume': np.random.uniform(1000, 5000, 100)
    })
    
    # Test RSI
    rsi = TechnicalIndicators.calculate_rsi(test_df, 14)
    print(f"   [OK] RSI calculation: {rsi:.2f}")
    
    # Test MACD
    macd = TechnicalIndicators.calculate_macd(test_df, 12, 26, 9)
    print(f"   [OK] MACD calculation: {macd['macd']:.2f}")
    
    # Test Stochastic
    stoch = TechnicalIndicators.calculate_stochastic(test_df, 14, 3, 3)
    print(f"   [OK] Stochastic calculation: K={stoch['k']:.2f}")
    
    # Test integration
    indicators = TechnicalIndicators.calculate_all_indicators(test_df, None, mode='swing')
    if indicators and 'rsi' in indicators and 'macd' in indicators:
        print(f"   [OK] Swing mode integration")
    else:
        warnings.append("Swing mode missing RSI or MACD")
        print(f"   [WARNING] Swing mode integration incomplete")
    
    indicators = TechnicalIndicators.calculate_all_indicators(test_df, None, mode='day')
    if indicators and 'day_trading' in indicators:
        day_ind = indicators['day_trading']
        if 'stochastic_k' in day_ind:
            print(f"   [OK] Day mode integration")
        else:
            warnings.append("Day mode missing Stochastic")
            print(f"   [WARNING] Day mode missing Stochastic")
    
except Exception as e:
    errors.append(f"Indicators error: {e}")
    print(f"   [ERROR] {e}")

# Test 6: Dependencies Check
print("\n6. DEPENDENCIES CHECKS")
print("-" * 70)
required_packages = [
    'pandas',
    'numpy',
    'ccxt',
    'sklearn',
    'telegram',
    'xgboost',
    'joblib',
    'aiohttp'
]

for package in required_packages:
    try:
        __import__(package)
        print(f"   [OK] {package}")
    except ImportError:
        errors.append(f"Missing package: {package}")
        print(f"   [ERROR] {package} not installed")

# Test 7: File Existence Check
print("\n7. FILE EXISTENCE CHECKS")
print("-" * 70)
import os
required_files = [
    'config.py',
    'database.py',
    'indicators.py',
    'data_collector.py',
    'ml_model.py',
    'telegram_bot.py',
    'main.py',
    '.env.example'
]

for file in required_files:
    if os.path.exists(file):
        print(f"   [OK] {file}")
    else:
        errors.append(f"Missing file: {file}")
        print(f"   [ERROR] {file} missing")

# Check .env
if os.path.exists('.env'):
    print(f"   [OK] .env exists")
else:
    warnings.append(".env file not found")
    print(f"   [WARNING] .env not found (create from .env.example)")

# Final Summary
print("\n" + "=" * 70)
print("VERIFICATION SUMMARY")
print("=" * 70)

if not errors and not warnings:
    print("\n[SUCCESS] All checks passed! Bot is ready to run.")
    print("\nNo errors found.")
    print("No warnings.")
elif not errors:
    print(f"\n[SUCCESS] All critical checks passed!")
    print(f"\nErrors: 0")
    print(f"Warnings: {len(warnings)}")
    print("\nWarnings:")
    for w in warnings:
        print(f"  - {w}")
else:
    print(f"\n[FAILURE] Found {len(errors)} error(s)")
    print(f"\nErrors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    print("\nErrors:")
    for e in errors:
        print(f"  - {e}")
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")

print("\n" + "=" * 70)
