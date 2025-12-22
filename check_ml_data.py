"""
Check ML data collection status
"""
import sys
sys.path.insert(0, '.')

from database import Database
import pandas as pd
from datetime import datetime, timedelta

print("=" * 70)
print("ML DATA COLLECTION STATUS")
print("=" * 70)

db = Database()
conn = db.get_connection()

# 1. Check total snapshots
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM market_snapshots')
total_count = cursor.fetchone()[0]

# 2. Check time range
cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM market_snapshots')
time_range = cursor.fetchone()
start_time = time_range[0]
end_time = time_range[1]

# 3. Calculate duration
if start_time and end_time:
    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time)
    duration = end_dt - start_dt
    hours = duration.total_seconds() / 3600
else:
    hours = 0

print(f"\n1. COLLECTION SUMMARY")
print(f"   Total snapshots: {total_count}")
print(f"   Start time: {start_time}")
print(f"   End time: {end_time}")
print(f"   Duration: {hours:.1f} hours")

# 4. Check data distribution
cursor.execute('''
    SELECT 
        COUNT(*) as count,
        MIN(price) as min_price,
        MAX(price) as max_price,
        AVG(price) as avg_price
    FROM market_snapshots
''')
stats = cursor.fetchone()

print(f"\n2. PRICE STATISTICS")
print(f"   Min price: ${stats[1]:,.2f}" if stats[1] else "   No data")
print(f"   Max price: ${stats[2]:,.2f}" if stats[2] else "   No data")
print(f"   Avg price: ${stats[3]:,.2f}" if stats[3] else "   No data")

# 5. Check recent snapshots
df = pd.read_sql_query('''
    SELECT timestamp, price, volume 
    FROM market_snapshots 
    ORDER BY timestamp DESC 
    LIMIT 5
''', conn)

print(f"\n3. RECENT SNAPSHOTS (last 5)")
print(df.to_string(index=False))

# 6. Check for future prices (labels)
cursor.execute('''
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN future_price_1h IS NOT NULL THEN 1 ELSE 0 END) as with_1h,
        SUM(CASE WHEN future_price_4h IS NOT NULL THEN 1 ELSE 0 END) as with_4h
    FROM market_snapshots
''')
labels = cursor.fetchone()

print(f"\n4. LABELS (future prices)")
print(f"   Total snapshots: {labels[0]}")
print(f"   With 1h label: {labels[1]} ({labels[1]/labels[0]*100:.1f}%)" if labels[0] > 0 else "   No data")
print(f"   With 4h label: {labels[2]} ({labels[2]/labels[0]*100:.1f}%)" if labels[0] > 0 else "   No data")

# 7. Readiness assessment
print(f"\n5. TRAINING READINESS")
min_samples = 100  # Minimum for training
recommended_samples = 1000  # Recommended

if total_count >= recommended_samples:
    print(f"   [READY] {total_count} samples (recommended: {recommended_samples}+)")
    print(f"   Can train ML model now!")
elif total_count >= min_samples:
    print(f"   [PARTIAL] {total_count} samples (min: {min_samples}, recommended: {recommended_samples})")
    print(f"   Can train, but more data recommended")
    print(f"   Need {recommended_samples - total_count} more samples for optimal training")
else:
    print(f"   [NOT READY] {total_count} samples (need: {min_samples}+)")
    print(f"   Need {min_samples - total_count} more samples to start training")
    if hours > 0:
        rate = total_count / hours
        hours_needed = (min_samples - total_count) / rate
        print(f"   Estimated time: {hours_needed:.1f} hours at current rate ({rate:.1f} samples/hour)")

# 8. Data quality check
cursor.execute('''
    SELECT 
        SUM(CASE WHEN rsi IS NULL THEN 1 ELSE 0 END) as null_indicators,
        SUM(CASE WHEN orderbook_imbalance IS NULL THEN 1 ELSE 0 END) as null_orderbook
    FROM market_snapshots
''')
quality = cursor.fetchone()

print(f"\n6. DATA QUALITY")
print(f"   Missing indicators: {quality[0]}/{total_count}")
print(f"   Missing orderbook: {quality[1]}/{total_count}")

if quality[0] == 0 and quality[1] == 0:
    print(f"   [OK] All data complete")
elif quality[0] < total_count * 0.1:
    print(f"   [WARNING] Some missing data, but acceptable")
else:
    print(f"   [ERROR] Too much missing data")

conn.close()

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

if total_count >= min_samples and quality[0] < total_count * 0.1:
    print("\n[SUCCESS] Data collection is working!")
    print(f"Collected {total_count} samples over {hours:.1f} hours")
    if total_count >= recommended_samples:
        print("Ready to train ML model.")
    else:
        print(f"Can train now, but recommend collecting {recommended_samples - total_count} more samples")
elif total_count > 0:
    print("\n[IN PROGRESS] Data collection is working")
    print(f"Collected {total_count} samples so far")
    print(f"Keep collecting data...")
else:
    print("\n[WARNING] No data collected yet")
    print("Check if data_collection_service.py is running")

print("\n" + "=" * 70)
