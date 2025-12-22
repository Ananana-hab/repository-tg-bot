"""
Database migration: Add indexes for performance
"""
import sqlite3
import os

DB_PATH = 'btc_signals.db'

print("=" * 70)
print("DATABASE MIGRATION: ADDING INDEXES")
print("=" * 70)

if not os.path.exists(DB_PATH):
    print(f"\n[ERROR] Database not found: {DB_PATH}")
    print("Please ensure the bot has run at least once to create the database.")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check existing indexes
print("\n1. Checking existing indexes...")
cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index'")
existing = cursor.fetchall()
print(f"   Found {len(existing)} existing indexes:")
for idx in existing:
    print(f"   - {idx[0]} on {idx[1]}")

# Add new indexes
print("\n2. Adding new indexes...")

indexes = [
    ("idx_price_data_timestamp", "CREATE INDEX IF NOT EXISTS idx_price_data_timestamp ON price_data(timestamp DESC)"),
    ("idx_signals_user_timestamp", "CREATE INDEX IF NOT EXISTS idx_signals_user_timestamp ON signals(user_id, timestamp DESC)"),
    ("idx_market_snapshots_timestamp", "CREATE INDEX IF NOT EXISTS idx_market_snapshots_timestamp ON market_snapshots(timestamp DESC)"),
    ("idx_signals_signal_type", "CREATE INDEX IF NOT EXISTS idx_signals_signal_type ON signals(signal_type)"),
]

created = 0
for name, sql in indexes:
    try:
        cursor.execute(sql)
        print(f"   [OK] Created: {name}")
        created += 1
    except sqlite3.Error as e:
        print(f"   [ERROR] Failed to create {name}: {e}")

conn.commit()

# Verify indexes
print("\n3. Verifying new indexes...")
cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY tbl_name")
all_indexes = cursor.fetchall()
print(f"   Total indexes: {len(all_indexes)}")
for idx in all_indexes:
    if not idx[0].startswith('sqlite_'):  # Skip auto-created indexes
        print(f"   - {idx[0]} on {idx[1]}")

# Test query performance
print("\n4. Testing query performance...")

# Test 1: Get recent price data
import time
start = time.time()
cursor.execute("SELECT * FROM price_data ORDER BY timestamp DESC LIMIT 100")
results = cursor.fetchall()
elapsed = (time.time() - start) * 1000
print(f"   Query 1 (recent prices): {elapsed:.2f}ms ({len(results)} rows)")

# Test 2: Get user signals
start = time.time()
cursor.execute("SELECT * FROM signals WHERE user_id = 123 ORDER BY timestamp DESC LIMIT 50")
results = cursor.fetchall()
elapsed = (time.time() - start) * 1000
print(f"   Query 2 (user signals): {elapsed:.2f}ms ({len(results)} rows)")

# Test 3: Get market snapshots
start = time.time()
cursor.execute("SELECT * FROM market_snapshots ORDER BY timestamp DESC LIMIT 100")
results = cursor.fetchall()
elapsed = (time.time() - start) * 1000
print(f"   Query 3 (snapshots): {elapsed:.2f}ms ({len(results)} rows)")

# Database stats
print("\n5. Database statistics...")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = cursor.fetchall()

for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"   {table_name}: {count} rows")

conn.close()

print("\n" + "=" * 70)
print("MIGRATION COMPLETE")
print("=" * 70)
print(f"\n[SUCCESS] Added {created} new indexes")
print("Expected performance improvement: 2-3x faster queries")
print("\nNext steps:")
print("  - Restart the bot to use optimized queries")
print("  - Monitor query performance in logs")
print("=" * 70)
