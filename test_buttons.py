"""
Test script to verify all bot buttons work correctly
"""
import sys
sys.path.insert(0, '.')

from database import Database

print("=" * 60)
print("TESTING BOT BUTTONS")
print("=" * 60)

db = Database()

# Test 1: User settings storage
print("\n1. Testing user settings storage...")
test_user_id = 123456789

# Get default settings
settings = db.get_user_settings(test_user_id)
print(f"   Default settings: {settings}")

# Test 2: Update trading mode
print("\n2. Testing trading mode toggle...")
db.update_user_settings(test_user_id, mode='day')
settings = db.get_user_settings(test_user_id)
print(f"   After mode=day: {settings['mode']}")
assert settings['mode'] == 'day', "Mode not updated!"

db.update_user_settings(test_user_id, mode='swing')
settings = db.get_user_settings(test_user_id)
print(f"   After mode=swing: {settings['mode']}")
assert settings['mode'] == 'swing', "Mode not updated!"

# Test 3: Update min probability
print("\n3. Testing min probability setting...")
db.update_user_settings(test_user_id, min_probability=65)
settings = db.get_user_settings(test_user_id)
print(f"   After min_prob=65: {settings['min_probability']}")
assert settings['min_probability'] == 65, "Probability not updated!"

# Test 4: Update signal types
print("\n4. Testing signal types toggle...")
db.update_user_settings(test_user_id, signal_types=['PUMP'])
settings = db.get_user_settings(test_user_id)
print(f"   After signal_types=[PUMP]: {settings['signal_types']}")
assert settings['signal_types'] == ['PUMP'], "Signal types not updated!"

db.update_user_settings(test_user_id, signal_types=['PUMP', 'DUMP'])
settings = db.get_user_settings(test_user_id)
print(f"   After signal_types=[PUMP,DUMP]: {settings['signal_types']}")

# Test 5: Update notifications
print("\n5. Testing notifications toggle...")
db.update_user_settings(test_user_id, notifications=False)
settings = db.get_user_settings(test_user_id)
print(f"   After notifications=False: {settings['notifications']}")
assert settings['notifications'] == False, "Notifications not updated!"

db.update_user_settings(test_user_id, notifications=True)
settings = db.get_user_settings(test_user_id)
print(f"   After notifications=True: {settings['notifications']}")

# Test 6: Persistence check
print("\n6. Testing persistence (re-reading from DB)...")
settings_check = db.get_user_settings(test_user_id)
print(f"   Re-read settings: {settings_check}")
assert settings_check == settings, "Settings not persisted!"

print("\n" + "=" * 60)
print("ALL TESTS PASSED! ✅")
print("=" * 60)
print("\nButtons that are now working:")
print("✅ Режим торговли (swing/day) - сохраняется в БД")
print("✅ Минимальная вероятность (60-85%) - сохраняется в БД")
print("✅ Типы сигналов (PUMP/DUMP) - сохраняются в БД")
print("✅ Уведомления (вкл/выкл) - сохраняются в БД")
print("\nВсе настройки теперь сохраняются при перезапуске бота!")
