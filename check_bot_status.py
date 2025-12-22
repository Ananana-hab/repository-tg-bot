"""
Diagnostic script to check bot status
"""
import sys
sys.path.insert(0, '.')

from database import Database
import os

print("=" * 60)
print("BOT DIAGNOSTIC CHECK")
print("=" * 60)

# 1. Config check
print("\n1. CONFIGURATION:")
import config
print(f"   TRADING_MODE: {config.TRADING_MODE}")
print(f"   USE_ML_MODEL: {config.USE_ML_MODEL}")
print(f"   PUMP_THRESHOLD: {config.PUMP_THRESHOLD}")
print(f"   DUMP_THRESHOLD: {config.DUMP_THRESHOLD}")
print(f"   CHECK_INTERVAL: {config.CHECK_INTERVAL}s")

# 2. Data collection check
print("\n2. DATA COLLECTION:")
db = Database()
stats = db.get_snapshot_stats()
if stats:
    print(f"   Total snapshots: {stats['total']}")
    print(f"   Labeled: {stats['labeled']}")
    print(f"   PUMP: {stats['pump_count']}")
    print(f"   DUMP: {stats['dump_count']}")
    print(f"   NEUTRAL: {stats['neutral_count']}")
    print(f"   First: {stats['first_snapshot']}")
    print(f"   Last: {stats['last_snapshot']}")
else:
    print("   ⚠️  No snapshots collected yet!")

# 3. ML Model check
print("\n3. ML MODEL:")
model_exists = os.path.exists('models/btc_model.pkl')
scaler_exists = os.path.exists('models/btc_scaler.pkl')
print(f"   Model file exists: {model_exists}")
print(f"   Scaler file exists: {scaler_exists}")
if not model_exists:
    print("   ⚠️  ML model not trained! Using rule-based prediction.")

# 4. Recent signals check
print("\n4. RECENT SIGNALS:")
try:
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT signal_type, probability, price, timestamp, confidence
        FROM signals
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    signals = cursor.fetchall()
    conn.close()
    
    if signals:
        for sig in signals:
            print(f"   {sig[3]}: {sig[0]} ({sig[1]:.1%}) at ${sig[2]:,.2f} [{sig[4]}]")
    else:
        print("   ⚠️  No signals sent yet!")
except Exception as e:
    print(f"   Error: {e}")

# 5. Subscribed users check
print("\n5. SUBSCRIBED USERS:")
users = db.get_subscribed_users()
print(f"   Total subscribed: {len(users)}")
if len(users) == 0:
    print("   ⚠️  No users subscribed! Use /subscribe in Telegram.")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)
