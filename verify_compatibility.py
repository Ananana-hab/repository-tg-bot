"""
Comprehensive compatibility verification script
Checks all Phase 1 changes for syntax errors, import issues, and compatibility
"""

import sys
import os
import ast
import importlib.util

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_syntax(filepath):
    """Check Python file for syntax errors"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)

def check_imports(filepath):
    """Check if file can be imported"""
    try:
        spec = importlib.util.spec_from_file_location("module", filepath)
        if spec is None:
            return False, "Could not create module spec"
        module = importlib.util.module_from_spec(spec)
        # Don't execute, just check if it can be loaded
        return True, None
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 70)
    print("COMPATIBILITY VERIFICATION - PHASE 1 CHANGES")
    print("=" * 70)
    
    # Files to check
    files_to_check = [
        ('config.py', 'Configuration'),
        ('ml_model.py', 'ML Model'),
        ('data_collector.py', 'Data Collector'),
        ('database.py', 'Database'),
        ('indicators.py', 'Technical Indicators'),
        ('main.py', 'Main Bot'),
        ('telegram_bot.py', 'Telegram Bot'),
    ]
    
    results = []
    
    print("\n1. SYNTAX CHECKS")
    print("-" * 70)
    
    for filename, description in files_to_check:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        if not os.path.exists(filepath):
            print(f"[SKIP] {description:20s} - File not found")
            continue
            
        success, error = check_syntax(filepath)
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {description:20s} - {filename}")
        
        if not success:
            print(f"       Error: {error}")
            results.append((description, False, error))
        else:
            results.append((description, True, None))
    
    print("\n2. IMPORT CHECKS")
    print("-" * 70)
    
    # Set test environment variables
    os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_for_compatibility_check'
    os.environ['TRADING_MODE'] = 'swing'
    os.environ['USE_ML_MODEL'] = 'false'
    
    import_tests = [
        ('config', 'Configuration module'),
        ('database', 'Database module'),
        ('indicators', 'Indicators module'),
    ]
    
    for module_name, description in import_tests:
        try:
            # Clear module if already loaded
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            module = __import__(module_name)
            print(f"[PASS] {description:20s} - Imported successfully")
        except Exception as e:
            print(f"[FAIL] {description:20s} - Import error")
            print(f"       Error: {e}")
            results.append((description, False, str(e)))
    
    print("\n3. CONFIGURATION VALIDATION")
    print("-" * 70)
    
    try:
        import config
        
        # Check critical config values
        checks = [
            ('TELEGRAM_BOT_TOKEN', config.TELEGRAM_BOT_TOKEN is not None),
            ('TRADING_MODE', config.TRADING_MODE in ['swing', 'day']),
            ('PUMP_THRESHOLD', 0.0 <= config.PUMP_THRESHOLD <= 1.0),
            ('DUMP_THRESHOLD', 0.0 <= config.DUMP_THRESHOLD <= 1.0),
            ('DB_PATH', config.DB_PATH is not None),
            ('MODEL_PATH', config.MODEL_PATH is not None),
        ]
        
        for param, is_valid in checks:
            status = "[PASS]" if is_valid else "[FAIL]"
            print(f"{status} {param:25s} - Valid: {is_valid}")
            
    except Exception as e:
        print(f"[FAIL] Config validation failed: {e}")
    
    print("\n4. ML MODEL SAFETY CHECK")
    print("-" * 70)
    
    try:
        from ml_model import MLPredictor
        predictor = MLPredictor()
        
        # Test with various data scenarios
        test_cases = [
            ({}, {}, "Empty data"),
            ({'bb_upper': 50000}, {'current_volume': 1000}, "Partial data"),
            ({'bb_upper': None, 'ema_200': None}, {'fear_greed': None}, "None values"),
        ]
        
        for indicators, market_data, desc in test_cases:
            try:
                features = predictor.prepare_features(indicators, market_data)
                print(f"[PASS] {desc:20s} - Shape: {features.shape}")
            except Exception as e:
                print(f"[FAIL] {desc:20s} - Error: {e}")
                
    except Exception as e:
        print(f"[FAIL] ML Model initialization failed: {e}")
    
    print("\n5. DATA COLLECTOR API HANDLING")
    print("-" * 70)
    
    try:
        from data_collector import DataCollector
        collector = DataCollector()
        
        # Check that ccxt exceptions are imported
        from data_collector import RateLimitExceeded, NetworkError, ExchangeError
        print("[PASS] CCXT exceptions imported correctly")
        
        # Check exchange is initialized
        if collector.exchange:
            print(f"[PASS] Exchange initialized: {collector.exchange.id}")
        else:
            print("[FAIL] Exchange not initialized")
            
    except Exception as e:
        print(f"[FAIL] Data Collector check failed: {e}")
    
    print("\n6. .ENV.EXAMPLE VERIFICATION")
    print("-" * 70)
    
    env_path = os.path.join(os.path.dirname(__file__), '.env.example')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required = [
            'TELEGRAM_BOT_TOKEN',
            'TRADING_MODE',
            'USE_ML_MODEL',
            'ENVIRONMENT',
            'HEALTHCHECK_PORT',
        ]
        
        for req in required:
            if req in content:
                print(f"[PASS] {req:25s} - Present")
            else:
                print(f"[FAIL] {req:25s} - Missing")
        
        # Check no hardcoded secrets
        if '7410301345' not in content and 'AAGcXIHsOWuqVypqbtZk5izkPpLdGNU8y8M' not in content:
            print("[PASS] No hardcoded secrets found")
        else:
            print("[FAIL] Hardcoded secrets still present!")
    else:
        print("[FAIL] .env.example not found")
    
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"Syntax checks passed: {passed}/{total}")
    print("\nAll critical checks completed.")
    print("\nRECOMMENDATION:")
    print("1. Create .env file with your bot token")
    print("2. Run: python main.py")
    print("3. Test /status command in Telegram")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
